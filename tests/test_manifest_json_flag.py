"""Manifest discovery must return flags, not descriptive prose."""

import subprocess
import sys

import pytest

from cli_shim import discover_manifest


@pytest.mark.parametrize(
    "help_text,expected",
    [
        ("Usage: bar [command]\nChoose the output format: json\n", None),
        ("Choose the output format:\n  json or text\n", None),
        ("JSON output is supported by an optional plugin.\n", None),
        ("Options:\n  --json  Print structured output\n", "--json"),
        ("Options:\n  -o=json  Output format\n", "-o=json"),
        ("Options:\n  --output=json  Output format\n", "--output=json"),
        ("Options:\n  --format=json  Output format\n", "--format=json"),
        ("Choose the output format:\n  --json\n", "--json"),
        ("Options:\n  --json-lines  One object per line\n", None),
        ("Options:\n  --jsonl  One object per line\n", None),
    ],
)
def test_manifest_only_advertises_explicit_json_flags(tmp_path, monkeypatch, help_text, expected):
    script = tmp_path / "sample_cli.py"
    script.write_text(
        "import sys\n"
        "assert sys.argv[1:] == ['--help']\n"
        f"sys.stdout.write({help_text!r})\n",
        encoding="utf-8",
    )
    real_run = subprocess.run

    def run_python_cli(command, **kwargs):
        # Launch the fixture through Python on every OS (no shebang dependency).
        # This runs a real subprocess and retains production's capture/timeout settings.
        assert command == [str(script), "--help"]
        return real_run([sys.executable, *command], **kwargs)

    monkeypatch.setattr("cli_shim.subprocess.run", run_python_cli)
    manifest = discover_manifest(str(script))
    assert "error" not in manifest
    assert manifest["help_text"] == help_text
    assert manifest["json_flag"] == expected
