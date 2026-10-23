"""Discover commands from help emitted by a real executable."""

import os
import sys

import pytest

from cli_shim import discover_manifest


def discover_help(tmp_path, help_text):
    script = tmp_path / "help_fixture.py"
    script.write_text(
        f"#!{sys.executable}\nimport sys\n"
        "assert '--help' in sys.argv\n"
        f"sys.stdout.buffer.write({help_text.encode('utf-8')!r})\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        command = tmp_path / "help_fixture.cmd"
        command.write_text(
            f'@echo off\n"{sys.executable}" "{script}" %*\n', encoding="utf-8"
        )
    else:
        command = script
        command.chmod(0o755)
    result = discover_manifest(str(command))
    assert "error" not in result, result
    return result["commands"]


@pytest.mark.parametrize("header", ["Commands:", "Available Commands:", "SUBCOMMANDS:"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("final_newline", [False, True])
def test_command_section_rows(tmp_path, header, newline, final_newline):
    lines = [
        "Usage: fixture [OPTIONS] COMMAND", "", header,
        "  add     Add a file", "  commit  Commit changes", "  push    Push to remote",
        "", "Options:", "  --help  Show help",
    ]
    text = newline.join(lines) + (newline if final_newline else "")
    assert discover_help(tmp_path, text) == [
        {"name": "add", "description": "Add a file"},
        {"name": "commit", "description": "Commit changes"},
        {"name": "push", "description": "Push to remote"},
    ]


def test_wrapped_description_and_command_without_description(tmp_path):
    text = (
        "  Commands:\n"
        "    build  Build the project\n"
        "           with all configured targets\n"
        "    clean\n"
        "  Options:\n"
        "    --help  Show help\n"
    )
    assert discover_help(tmp_path, text) == [
        {"name": "build", "description": "Build the project with all configured targets"},
        {"name": "clean", "description": ""},
    ]


def test_tab_indentation_and_eof(tmp_path):
    assert discover_help(tmp_path, "Commands:\n\tserve\tStart a server") == [
        {"name": "serve", "description": "Start a server"},
    ]


def test_empty_command_section_does_not_read_options(tmp_path):
    assert discover_help(tmp_path, "Commands:\n\nOptions:\n  --help  Show help\n") == []


def test_headerless_indented_commands(tmp_path):
    text = "Usage: fixture\n\n  add    Add a file\n  commit  Commit changes\n"
    assert discover_help(tmp_path, text) == [
        {"name": "add", "description": "Add a file"},
        {"name": "commit", "description": "Commit changes"},
    ]
