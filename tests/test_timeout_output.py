"""Timeout diagnostics must retain data from a real child process."""

import json
import subprocess
import sys

import pytest

from cli_shim import run_shim


@pytest.mark.parametrize("agent_mode", [False, True])
@pytest.mark.parametrize("stderr_newline", [False, True])
def test_timeout_preserves_partial_streams(agent_mode, stderr_newline):
    stdout = b"\x1b[32mcaf\xc3\xa9\xff\x1b[0m\n"
    stderr = b"\x1b[31mdiagnostic\xfe\x1b[0m" + (b"\n" if stderr_newline else b"")
    code = (
        "import sys, time; "
        f"sys.stdout.buffer.write({stdout!r}); sys.stdout.buffer.flush(); "
        f"sys.stderr.buffer.write({stderr!r}); sys.stderr.buffer.flush(); "
        "time.sleep(60)"
    )
    command = [sys.executable, "-c", code]

    result = run_shim(command, agent_mode=agent_mode, timeout=2)

    expected_stdout = "caf\u00e9\ufffd\n"
    expected_stderr = "diagnostic\ufffd"
    if not agent_mode:
        expected_stdout = "\x1b[32mcaf\u00e9\ufffd\x1b[0m\n"
        expected_stderr = "\x1b[31mdiagnostic\ufffd\x1b[0m"
    assert result.returncode == 124
    assert not result.success
    assert result.command == command
    assert result.stdout == expected_stdout
    assert result.stderr == expected_stderr + "\nCommand timed out after 2s"


@pytest.mark.parametrize(
    "stdout, stderr",
    [(b"", b""), (b"output only\n", b""), (b"", b"error only\n")],
)
def test_timeout_handles_empty_streams(stdout, stderr):
    code = (
        "import sys, time; "
        f"sys.stdout.buffer.write({stdout!r}); sys.stdout.buffer.flush(); "
        f"sys.stderr.buffer.write({stderr!r}); sys.stderr.buffer.flush(); "
        "time.sleep(60)"
    )

    result = run_shim([sys.executable, "-c", code], agent_mode=True, timeout=2)

    assert result.returncode == 124
    assert result.stdout == stdout.decode("utf-8")
    assert result.stderr == stderr.decode("utf-8") + "Command timed out after 2s"


def test_timeout_cli_json_keeps_partial_data():
    child = (
        "import sys, time; print('partial data', flush=True); "
        "print('child diagnostic', file=sys.stderr, flush=True); time.sleep(60)"
    )
    result = subprocess.run(
        [sys.executable, "-c", "from cli_shim import main; main()",
         "--json", "--timeout", "2", sys.executable, "-c", child],
        capture_output=True, text=True, encoding="utf-8", timeout=15, check=False,
    )
    assert result.returncode == 124, result.stderr
    payload = json.loads(result.stdout)
    assert payload["stdout"] == "partial data\n"
    assert payload["stderr"] == "child diagnostic\nCommand timed out after 2s"
    assert payload["returncode"] == 124
    assert payload["success"] is False
