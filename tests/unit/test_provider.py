from simplicio_loop.extension_handshake import extension_handshake
from simplicio_loop.extension_registry import ExtensionRegistry

from simplicio_loop_quality.provider import provider
import simplicio_loop_quality.provider as provider_module


def test_provider_has_exact_callable_role_and_effect_bindings():
    runtime = provider()
    expected = {row["role_id"] for row in runtime.manifest["role_bindings"]} | {
        row["effect_id"] for row in runtime.manifest["effect_handlers"]
    }
    assert set(runtime.bindings) == expected
    assert all(callable(binding) for binding in runtime.bindings.values())
    registry = ExtensionRegistry()
    registry.register(runtime.manifest, runtime=runtime)
    handshake = extension_handshake("simplicio_loop_quality", "strict-default", registry=registry)
    assert handshake["status"] == "PASS"
    assert handshake["authorities"]["provider_may_complete"] is False
    assert handshake["composition"]["worker_execution"] is False


def test_role_binding_and_receipt_handler_are_fail_closed_and_nonterminal():
    runtime = provider()
    role = runtime.bindings["unit_component_agent"]
    assert role()["reason_code"] == "INVALID_ROLE_REQUEST"
    result = role({"stage": "unit"})
    assert (result["status"], result["reason_code"], result["terminal"]) == (
        "BLOCKED",
        "HUB_STAGE_DISPATCH_REQUIRED",
        False,
    )
    publish = runtime.bindings["publish_quality_receipt"]
    invalid = publish({"schema": "unknown/v1"})
    assert (invalid["status"], invalid["terminal"]) == ("BLOCKED", False)


def test_productive_provider_submits_check_through_hub_adapter(tmp_path, monkeypatch):
    check = tmp_path / "scripts" / "check.py"
    check.parent.mkdir()
    check.write_text("raise SystemExit(0)\n", encoding="utf-8")
    captured = {}

    class _Receipt:
        status = "PASS"
        reason_code = "PROCESS_SUCCEEDED"
        raw_evidence = {"process_result": {"returncode": 0}}

    class _Adapter:
        def submit(self, request):
            captured["request"] = request
            return object()

        def poll(self, _submission):
            return {"state": "completed"}

        def collect(self, _submission):
            return _Receipt()

    monkeypatch.setattr(provider_module, "_hub_adapter", lambda: _Adapter())
    result = provider_module.run(
        run_id="run-1", tasks=[], attempt=1, repo=str(tmp_path), worktree="",
        head="head", diff_hash="diff", policy="strict-default",
    )
    assert result["status"] == "PASS"
    assert captured["request"].argv[1].endswith("scripts\\check.py") or captured["request"].argv[1].endswith("scripts/check.py")


def test_provider_run_missing_check_script(tmp_path):
    result = provider_module.run(
        run_id="run-1", tasks=[], attempt=1, repo=str(tmp_path), worktree="",
        head="head", diff_hash="diff", policy="strict-default",
    )
    assert result["status"] == "BLOCKED"
    assert "not found" in result["findings"][0]["message"]


def test_provider_run_cancellation(tmp_path, monkeypatch):
    check = tmp_path / "scripts" / "check.py"
    check.parent.mkdir()
    check.write_text("pass\n", encoding="utf-8")

    class _Receipt:
        raw_evidence = {"cancelled": True}
        reason_code = "CANCELLED_BY_TOKEN"

    class _Adapter:
        def submit(self, request):
            return object()

        def cancel(self, submission, reason):
            return _Receipt()

    class _CancelToken:
        def is_set(self):
            return True

    monkeypatch.setattr(provider_module, "_hub_adapter", lambda: _Adapter())
    result = provider_module.run(
        run_id="run-1", tasks=[], attempt=1, repo=str(tmp_path), worktree="",
        head="head", diff_hash="diff", policy="strict-default", cancel_token=_CancelToken(),
    )
    assert result["status"] == "BLOCKED"
    assert result["detail"] == "CANCELLED_BY_TOKEN"


def test_provider_run_failure_receipt(tmp_path, monkeypatch):
    check = tmp_path / "scripts" / "check.py"
    check.parent.mkdir()
    check.write_text("pass\n", encoding="utf-8")

    class _Receipt:
        status = "FAIL"
        reason_code = "CHECK_FAILED"
        raw_evidence = {"returncode": 1}

    class _Adapter:
        def submit(self, request):
            return object()

        def poll(self, submission):
            return {"state": "completed"}

        def collect(self, submission):
            return _Receipt()

    monkeypatch.setattr(provider_module, "_hub_adapter", lambda: _Adapter())
    result = provider_module.run(
        run_id="run-1", tasks=[], attempt=1, repo=str(tmp_path), worktree="",
        head="head", diff_hash="diff", policy="strict-default",
    )
    assert result["status"] == "BLOCKED"
    assert result["findings"][0]["message"] == "CHECK_FAILED"


def test_provider_run_adapter_exception(tmp_path, monkeypatch):
    check = tmp_path / "scripts" / "check.py"
    check.parent.mkdir()
    check.write_text("pass\n", encoding="utf-8")

    def _boom():
        raise RuntimeError("Hub socket unreachable")

    monkeypatch.setattr(provider_module, "_hub_adapter", _boom)
    result = provider_module.run(
        run_id="run-1", tasks=[], attempt=1, repo=str(tmp_path), worktree="",
        head="head", diff_hash="diff", policy="strict-default",
    )
    assert result["status"] == "BLOCKED"
    assert "Hub socket unreachable" in result["detail"]


def test_provider_run_timeout(tmp_path, monkeypatch):
    check = tmp_path / "scripts" / "check.py"
    check.parent.mkdir()
    check.write_text("pass\n", encoding="utf-8")

    class _Receipt:
        raw_evidence = {"timed_out": True}
        reason_code = "TIMEOUT"

    class _Adapter:
        def submit(self, request):
            return object()

        def poll(self, submission):
            return {"state": "running"}

        def cancel(self, submission, reason):
            return _Receipt()

    monkeypatch.setattr(provider_module, "_hub_adapter", lambda: _Adapter())
    import time
    monotonic_calls = [100.0, 300.0]  # First call deadline=100+120=220, second call >= 220
    monkeypatch.setattr(time, "monotonic", lambda: monotonic_calls.pop(0) if monotonic_calls else 400.0)
    result = provider_module.run(
        run_id="run-1", tasks=[], attempt=1, repo=str(tmp_path), worktree="",
        head="head", diff_hash="diff", policy="strict-default",
    )
    assert result["status"] == "BLOCKED"
    assert result["detail"] == "TIMEOUT"


def test_capability_negotiate():
    caps = provider_module.capability_negotiate()
    assert caps["version"] == provider_module.PROVIDER_VERSION
    assert caps["capabilities"]["structured_findings"] is True


