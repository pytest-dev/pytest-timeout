import asyncio
import gc
import io
import signal
import sys
from types import SimpleNamespace

import pytest
from _pytest._io import TerminalWriter

import pytest_timeout

pytest_plugins = "pytester"

timeout_methods = [
    "thread",
    pytest.param(
        "signal",
        marks=pytest.mark.skipif(
            not hasattr(signal, "SIGALRM"), reason="OS does not have SIGALRM"
        ),
    ),
]


@pytest.mark.parametrize("method", timeout_methods)
@pytest.mark.parametrize("blocked_loop", [False, True])
def test_timeout_suspended_asyncio_chains_across_threads(
    pytester, method, blocked_loop
):
    pytester.makepyfile(
        f"""
        import asyncio
        import gc
        import threading
        import time
        import types

        ready = threading.Event()
        stop = threading.Event()

        async def background_leaf():
            ready.set()
            while not stop.is_set():
                await asyncio.sleep(0.01)

        async def background_root():
            asyncio.current_task().set_name("background-worker")
            await background_leaf()

        @types.coroutine
        def legacy_wait():
            yield from asyncio.Event().wait().__await__()

        async def foreground_leaf():
            await legacy_wait()

        async def foreground_root():
            await foreground_leaf()

        async def main():
            # Keep the task alive while collecting suspended reference cycles.
            foreground_task = asyncio.create_task(
                foreground_root(), name="foreground-worker"
            )
            await asyncio.sleep(0)
            gc.collect()
            if {blocked_loop}:
                time.sleep(10)
            await foreground_task

        def test_hang():
            thread = threading.Thread(
                target=lambda: asyncio.run(background_root()),
                name="background-loop", daemon=True,
            )
            thread.start()
            try:
                assert ready.wait(5)
                asyncio.run(main())
            finally:
                stop.set()
                thread.join(5)
        """
    )

    result = pytester.runpytest_subprocess(
        "--timeout=1", f"--timeout-method={method}", timeout=20
    )

    assert result.ret == 1
    if method == "signal":
        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(["*Failed: Timeout (>1.0s) from pytest-timeout.*"])
    else:
        result.stdout.fnmatch_lines(["*Stack of MainThread*", "*Asyncio task stacks*"])
        assert "++ Timeout ++" in result.stdout.lines[-1]
    async_stacks = result.stdout.str().split("Asyncio task stacks", 1)[1]
    for name in (
        "foreground-worker",
        "background-worker",
        "in foreground_root",
        "in foreground_leaf",
        "in legacy_wait",
        "in background_root",
        "in background_leaf",
    ):
        assert name in async_stacks


@pytest.mark.parametrize("method", timeout_methods)
def test_asyncio_inspection_error_preserves_timeout(pytester, method):
    pytester.makepyfile(
        """
        import asyncio
        import gc
        import time

        def fail_inspection():
            raise RuntimeError("task inspection failed")

        def test_hang(monkeypatch):
            monkeypatch.setattr(gc, "get_objects", fail_inspection)
            time.sleep(10)
        """
    )

    result = pytester.runpytest_subprocess(
        "--timeout=1", f"--timeout-method={method}", timeout=20
    )

    assert result.ret == 1
    result.stdout.fnmatch_lines(
        [
            "*Unable to collect asyncio task stacks:*",
            "*RuntimeError: task inspection failed*",
        ]
    )
    if method == "signal":
        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(["*Failed: Timeout (>1.0s) from pytest-timeout.*"])
    else:
        assert "++ Timeout ++" in result.stdout.lines[-1]


@pytest.mark.parametrize("imported", [False, True])
def test_no_asyncio_tasks_leave_output_unchanged(monkeypatch, imported):
    if imported:
        monkeypatch.setattr(gc, "get_objects", lambda: [])
    else:
        monkeypatch.delitem(sys.modules, "asyncio")
    stream = io.StringIO()

    pytest_timeout._dump_asyncio_stacks(TerminalWriter(file=stream))

    assert stream.getvalue() == ""


def test_completed_asyncio_tasks_are_omitted(monkeypatch):
    loop = asyncio.new_event_loop()
    stream = io.StringIO()

    async def finished():
        pass

    task = loop.create_task(finished(), name="completed-task")
    try:
        loop.run_until_complete(task)
        monkeypatch.setattr(gc, "get_objects", lambda: [task])

        pytest_timeout._dump_asyncio_stacks(TerminalWriter(file=stream))

        assert stream.getvalue() == ""
    finally:
        loop.close()


def test_uninspectable_task_preserves_other_tasks(monkeypatch):
    class UninspectableTask(asyncio.Task):
        def get_coro(self):
            raise RuntimeError("cannot inspect coroutine")

    async def pending():
        await asyncio.Event().wait()

    loop = asyncio.new_event_loop()
    broken = UninspectableTask(pending(), loop=loop, name="broken-task")
    healthy = loop.create_task(pending(), name="healthy-task")
    stream = io.StringIO()
    try:
        monkeypatch.setattr(gc, "get_objects", lambda: [broken, healthy])

        pytest_timeout._dump_asyncio_stacks(TerminalWriter(file=stream))

        output = stream.getvalue()
        assert "RuntimeError: cannot inspect coroutine" in output
        assert "healthy-task" in output
        assert "in pending" in output
    finally:
        broken.cancel()
        healthy.cancel()
        loop.run_until_complete(asyncio.gather(broken, healthy, return_exceptions=True))
        loop.close()


@pytest.mark.parametrize("cyclic", [False, True])
def test_await_chain_is_bounded(cyclic):
    current = SimpleNamespace()
    root = current
    for _ in range(60):
        current.cr_await = SimpleNamespace()
        current = current.cr_await
    if cyclic:
        root.cr_await = root
    stream = io.StringIO()

    pytest_timeout._dump_await_chain(root, stream)

    expected = "cycle" if cyclic else "truncated after 50 frames"
    assert expected in stream.getvalue()
