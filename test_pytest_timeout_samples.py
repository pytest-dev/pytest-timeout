import signal
import threading

import pytest

import pytest_timeout

pytest_plugins = "pytester"


def test_sample_thread_stacks(pytester):
    pytester.makepyfile(
        """
        import threading
        import time

        ready = threading.Event()
        stop = threading.Event()

        def background_leaf():
            ready.set()
            stop.wait(5)

        def background_root():
            background_leaf()

        def foreground_leaf():
            time.sleep(0.6)

        def foreground_root():
            foreground_leaf()

        def test_slow():
            thread = threading.Thread(
                target=background_root, name="background-worker"
            )
            thread.start()
            try:
                assert ready.wait(5)
                foreground_root()
            finally:
                stop.set()
                thread.join()
        """
    )

    result = pytester.runpytest_subprocess("--slow-test-sample=0.2")

    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(
        ["slow test sample: 0.2s", "slow test sample directory: *"]
    )
    artifacts = list((pytester.path / "slow_test_samples").glob("*.log"))
    assert len(artifacts) == 1
    assert "test_slow" in artifacts[0].name
    snapshot = artifacts[0].read_text(encoding="utf-8")
    assert "Test: test_sample_thread_stacks.py::test_slow" in snapshot
    assert "MainThread" in snapshot
    for name in (
        "background-worker",
        "in foreground_root",
        "in foreground_leaf",
        "in background_root",
        "in background_leaf",
    ):
        assert name in snapshot


@pytest.mark.parametrize(
    ("ini_seconds", "args", "sampled"),
    [
        (None, [], False),
        ("0.05", [], True),
        ("0.05", ["--slow-test-sample=0"], False),
        ("0", ["--slow-test-sample=0.05", "--timeout=0"], True),
        ("10", [], False),
    ],
)
def test_sample_configuration(pytester, ini_seconds, args, sampled):
    pytester.makepyfile(
        """
        import time

        def test_slow():
            time.sleep(0.2)
        """
    )
    ini = "[pytest]\nslow_test_sample_dir = configured-samples\n"
    if ini_seconds is not None:
        ini += f"slow_test_sample = {ini_seconds}\n"
    pytester.makeini(ini)

    result = pytester.runpytest_subprocess(*args)

    result.assert_outcomes(passed=1)
    artifacts = list((pytester.path / "configured-samples").glob("*.log"))
    assert len(artifacts) == int(sampled)


def test_sample_directory_override(pytester):
    pytester.makeini("[pytest]\nslow_test_sample = 0.05\nslow_test_sample_dir = unused")
    pytester.makepyfile("import time\ndef test_slow(): time.sleep(0.2)")
    directory = pytester.path / "custom samples" / "nested"

    result = pytester.runpytest_subprocess(f"--slow-test-sample-dir={directory}")

    result.assert_outcomes(passed=1)
    assert len(list(directory.glob("*.log"))) == 1
    assert not (pytester.path / "unused").exists()


@pytest.mark.parametrize("outcome", ["pass", "skip", "fail"])
@pytest.mark.parametrize("func_only", [False, True])
def test_sample_cancels_between_tests(pytester, outcome, func_only):
    pytester.makeini(f"[pytest]\ntimeout_func_only = {func_only}")
    action = {
        "pass": "pass",
        "skip": "pytest.skip('skip')",
        "fail": "pytest.fail('fail')",
    }[outcome]
    pytester.makepyfile(
        f"""
        import time
        import pytest

        def test_fast():
            {action}

        def test_slow():
            time.sleep(0.4)
        """
    )

    result = pytester.runpytest_subprocess("--slow-test-sample=0.1")

    result.assert_outcomes(
        passed=1 + (outcome == "pass"),
        skipped=int(outcome == "skip"),
        failed=int(outcome == "fail"),
    )
    artifacts = list((pytester.path / "slow_test_samples").glob("*.log"))
    assert len(artifacts) == 1
    assert "test_slow" in artifacts[0].name


@pytest.mark.parametrize(
    ("func_only", "marker", "sampled"),
    [
        (False, "", True),
        (True, "", False),
        (False, "@pytest.mark.timeout(func_only=True)", False),
        (True, "@pytest.mark.timeout(func_only=False)", True),
    ],
)
def test_sample_fixture_scope(pytester, func_only, marker, sampled):
    pytester.makeini(f"[pytest]\ntimeout_func_only = {func_only}")
    pytester.makepyfile(
        f"""
        import time
        import pytest

        @pytest.fixture
        def slow_fixture():
            time.sleep(0.2)
            yield
            time.sleep(0.2)

        {marker}
        def test_fast(slow_fixture):
            pass
        """
    )

    result = pytester.runpytest_subprocess("--slow-test-sample=0.05")

    result.assert_outcomes(passed=1)
    artifacts = list((pytester.path / "slow_test_samples").glob("*.log"))
    assert len(artifacts) == int(sampled)


@pytest.mark.parametrize(
    "method",
    [
        "thread",
        pytest.param(
            "signal",
            marks=pytest.mark.skipif(
                not hasattr(signal, "SIGALRM"), reason="OS does not have SIGALRM"
            ),
        ),
    ],
)
def test_sample_before_hard_timeout(pytester, method):
    pytester.makepyfile("import time\ndef test_hang(): time.sleep(10)")

    result = pytester.runpytest_subprocess(
        "--slow-test-sample=0.1", "--timeout=1", f"--timeout-method={method}"
    )

    assert result.ret == 1
    artifacts = list((pytester.path / "slow_test_samples").glob("*.log"))
    assert len(artifacts) == 1
    snapshot = artifacts[0].read_text(encoding="utf-8")
    assert "in test_hang" in snapshot
    assert "Stack of MainThread" in snapshot


@pytest.mark.parametrize("seconds", ["-1", "nan", "inf"])
@pytest.mark.parametrize("source", ["cli", "ini"])
def test_invalid_sample_threshold(pytester, seconds, source):
    args = []
    if source == "cli":
        args.append(f"--slow-test-sample={seconds}")
    else:
        pytester.makeini(f"[pytest]\nslow_test_sample = {seconds}")

    result = pytester.runpytest_subprocess(*args)

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(
        ["ERROR: slow_test_sample must be a finite, non-negative number"]
    )


def test_sample_filenames_are_portable_and_unique(tmp_path):
    nodeid = "tests/test_feature.py::test_slow[" + "a/b:c\\d?*ü" * 30 + "]"
    settings = pytest_timeout.Settings(None, "thread", False, True)

    for _ in range(2):
        pytest_timeout._sample_stacks(nodeid, 1, tmp_path, settings)

    artifacts = list(tmp_path.glob("*.log"))
    assert len(artifacts) == 2
    for artifact in artifacts:
        assert artifact.name.startswith("test_feature.py__test_slow_")
        assert len(artifact.name) < 255
        assert all(
            char.isascii() and (char.isalnum() or char in "_.-")
            for char in artifact.name
        )
        assert f"Test: {nodeid}" in artifact.read_text(encoding="utf-8")


def test_sample_output_error_is_nonfatal(tmp_path, capsys):
    directory = tmp_path / "not-a-directory"
    directory.write_text("occupied", encoding="utf-8")
    settings = pytest_timeout.Settings(None, "thread", False, True)

    pytest_timeout._sample_stacks("test_example.py::test_slow", 1, directory, settings)

    assert (
        "could not write stack sample for test_example.py::test_slow"
        in capsys.readouterr().err
    )
    assert directory.read_text(encoding="utf-8") == "occupied"


@pytest.mark.parametrize("disable_detection", [False, True])
def test_sample_debugger_detection(tmp_path, monkeypatch, disable_detection):
    monkeypatch.setattr(pytest_timeout, "is_debugging", lambda: True)
    settings = pytest_timeout.Settings(None, "thread", False, disable_detection)

    pytest_timeout._sample_stacks("test_example.py::test_slow", 1, tmp_path, settings)

    assert len(list(tmp_path.glob("*.log"))) == int(disable_detection)


def test_sample_reuses_timeout_stack_dumper(tmp_path, monkeypatch):
    def dump_stacks(terminal):
        terminal.sep("~", title="Shared timeout stack dumper")
        terminal.write("Shared thread stacks\n")

    monkeypatch.setattr(pytest_timeout, "dump_stacks", dump_stacks)
    settings = pytest_timeout.Settings(None, "thread", False, True)

    pytest_timeout._sample_stacks("test_example.py::test_slow", 1, tmp_path, settings)

    (artifact,) = tmp_path.glob("*.log")
    sample = artifact.read_text(encoding="utf-8")
    assert "Shared timeout stack dumper" in sample
    assert "Shared thread stacks" in sample


@pytest.mark.parametrize("fixture", ["capsys", "capfd", "capsysbinary", "capfdbinary"])
def test_sample_preserves_capture_fixtures(pytester, fixture):
    expected = (
        'b"BEFORE\\nAFTER\\n"' if fixture.endswith("binary") else '"BEFORE\\nAFTER\\n"'
    )
    pytester.makepyfile(
        f"""
        import time

        def test_slow({fixture}):
            print("BEFORE")
            time.sleep(0.2)
            print("AFTER")
            assert {fixture}.readouterr().out == {expected}
        """
    )

    result = pytester.runpytest_subprocess("--slow-test-sample=0.05")

    result.assert_outcomes(passed=1)
    assert len(list((pytester.path / "slow_test_samples").glob("*.log"))) == 1


def test_sample_cancellation_waits_for_running_callback():
    started = threading.Event()
    release = threading.Event()
    cancelled = threading.Event()

    def callback():
        started.set()
        release.wait(5)

    timer = threading.Timer(0, callback)

    def cancel():
        pytest_timeout._cancel_sample_timer(timer)
        cancelled.set()

    waiter = threading.Thread(target=cancel)
    timer.start()
    try:
        assert started.wait(5)
        waiter.start()
        assert not cancelled.wait(0.05)
    finally:
        release.set()
        timer.join(5)
        if waiter.ident is not None:
            waiter.join(5)
    assert cancelled.is_set()
