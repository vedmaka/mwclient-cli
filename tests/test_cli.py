import json
from unittest.mock import patch

import pytest

from mwcli import cli


class DummyPage:
    def __init__(self, title: str):
        self.title = title

    def text(self) -> str:
        return f"text:{self.title}"

    def numbers(self):
        for number in range(3):
            yield {"n": number}


class DummyPages:
    def __getitem__(self, title: str) -> DummyPage:
        return DummyPage(title)


class DummySite:
    def __init__(self):
        self.pages = DummyPages()
        self.images = DummyPages()

    def ping(self, value: int = 1) -> dict[str, int]:
        return {"value": value}


def test_parse_cli_value_json_and_string():
    assert cli.parse_cli_value("3") == 3
    assert cli.parse_cli_value("true") is True
    assert cli.parse_cli_value("hello") == "hello"


def test_parse_keyword_args():
    kwargs = cli.parse_keyword_args(["a=1", "b=true", "c=raw"])
    assert kwargs == {"a": 1, "b": True, "c": "raw"}


def test_parse_keyword_args_rejects_invalid():
    with pytest.raises(ValueError):
        cli.parse_keyword_args(["broken"])


def test_site_method_call_prints_json(capsys):
    with patch.object(cli, "build_site", return_value=DummySite()), patch.object(
        cli, "list_public_methods", return_value={"ping": DummySite.ping}
    ):
        rc = cli.run(["--host", "example.org", "site", "ping", "--kw", "value=5"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    assert json.loads(out) == {"value": 5}


def test_page_iterator_stream(capsys):
    with patch.object(cli, "build_site", return_value=DummySite()), patch.object(
        cli, "list_public_methods", return_value={"numbers": DummyPage.numbers}
    ):
        rc = cli.run(
            [
                "--host",
                "example.org",
                "page",
                "Main_Page",
                "numbers",
                "--max-items",
                "2",
            ]
        )
    assert rc == 0
    out = capsys.readouterr().out.strip()
    lines = [json.loads(line) for line in out.splitlines()]
    assert lines == [{"n": 0}, {"n": 1}]


def test_root_help_includes_core_flags(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.run(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--host" in out
    assert "--scheme" in out
    assert "--path" in out
    assert "methods site" in out


def test_site_help_includes_method_arg_flags(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.run(["site", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--arg VALUE" in out
    assert "--kw KEY=VALUE" in out
    assert "--max-items N" in out
