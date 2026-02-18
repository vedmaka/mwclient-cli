"""Command-line wrapper for mwclient."""

from __future__ import annotations

import argparse
import base64
import importlib
import inspect
import json
import os
import sys
from collections.abc import Iterator, Mapping
from typing import Any

import html2text

_ENTITY_LOCATIONS = {
    "site": ("mwclient.client", "Site"),
    "page": ("mwclient.page", "Page"),
    "image": ("mwclient.image", "Image"),
}


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve newlines in help text."""


def resolve_entity_class(entity: str) -> Any:
    module_name, class_name = _ENTITY_LOCATIONS[entity]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def list_public_methods(entity: str) -> dict[str, Any]:
    cls = resolve_entity_class(entity)
    methods: dict[str, Any] = {}
    for name, member in inspect.getmembers(cls, predicate=callable):
        if name.startswith("_"):
            continue
        methods[name] = member
    return methods


def parse_cli_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def parse_keyword_args(items: list[str]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"invalid --kw value '{item}', expected key=value")
        key, raw_value = item.split("=", 1)
        if not key:
            raise ValueError("empty --kw key is not allowed")
        kwargs[key] = parse_cli_value(raw_value)
    return kwargs


def normalize_result(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return {
            "__type__": "bytes",
            "base64": base64.b64encode(value).decode("ascii"),
            "size": len(value),
        }
    if isinstance(value, Mapping):
        return {str(key): normalize_result(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [normalize_result(item) for item in value]
    return repr(value)


def build_site(args: argparse.Namespace) -> Any:
    site_class = resolve_entity_class("site")
    site = site_class(
        args.host,
        path=args.path,
        ext=args.ext,
        scheme=args.scheme,
        do_init=not args.no_init,
        force_login=not args.allow_anon,
        clients_useragent=args.clients_useragent,
    )
    if args.username:
        site.login(args.username, args.password)
    return site


def build_target(site: Any, args: argparse.Namespace) -> Any:
    if args.command == "site":
        return site
    if args.command == "page":
        return site.pages[args.title]
    if args.command == "image":
        return site.images[args.title]
    raise ValueError(f"unsupported command {args.command}")


def print_json(value: Any, indent: int | None) -> None:
    json.dump(normalize_result(value), sys.stdout, indent=indent, ensure_ascii=False)
    sys.stdout.write("\n")


def print_text(value: str) -> None:
    sys.stdout.write(value.rstrip("\n"))
    sys.stdout.write("\n")


def print_method_list(entity: str) -> int:
    methods = list_public_methods(entity)
    for name in sorted(methods):
        signature = inspect.signature(methods[name])
        print(f"{entity}.{name}{signature}")
    return 0


def html_to_markdown(value: str) -> str:
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = False
    converter.ignore_links = False
    return converter.handle(value).strip()


def normalize_page_title(value: str) -> str:
    return value.replace("_", " ").strip()


def extract_parse_html(parse_result: Any) -> str | None:
    if not isinstance(parse_result, Mapping):
        return None
    text_data = parse_result.get("text")
    if not isinstance(text_data, Mapping):
        return None
    text_html = text_data.get("*")
    return text_html if isinstance(text_html, str) else None


def maybe_convert_markdown(args: argparse.Namespace, target: Any, result: Any) -> Any:
    if not getattr(args, "markdown", False):
        return result

    if args.command == "page" and args.method == "text" and isinstance(result, str):
        parse_data = target.site.parse(text=result, title=getattr(target, "name", None))
        parse_html = extract_parse_html(parse_data)
        title = normalize_page_title(
            str(getattr(target, "name", getattr(target, "title", args.title)))
        )
        heading = f"# {title}".strip()
        if parse_html:
            body = html_to_markdown(parse_html).strip()
            return f"{heading}\n\n{body}" if body else heading
        body = result.strip()
        return f"{heading}\n\n{body}" if body else heading

    if args.command == "site" and args.method == "parse":
        parse_html = extract_parse_html(result)
        if parse_html:
            return html_to_markdown(parse_html)
        return result

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mwclient-cli",
        formatter_class=HelpFormatter,
        description=(
            "Command-line wrapper around mwclient\n\n"
            "Use one of these targets:\n"
            "  site  methods from mwclient.Site\n"
            "  page  methods from mwclient.page.Page\n"
            "  image methods from mwclient.image.Image"
        ),
        epilog=(
            "Examples:\n"
            "  mwclient-cli methods site\n"
            "  mwclient-cli --host host.docker.internal --scheme http --path /w/ "
            "page \"Main Page\" text\n"
            "  mwclient-cli --host host.docker.internal --scheme http --path /w/ "
            "site search --arg space --kw what=text --max-items 5"
        ),
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MWCLI_HOST"),
        metavar="HOST",
        help="Wiki host (no scheme). Env fallback: MWCLI_HOST",
    )
    parser.add_argument(
        "--path",
        default=os.getenv("MWCLI_PATH", "/w/"),
        metavar="PATH",
        help="MediaWiki script path with trailing slash. Default: /w/. Env: MWCLI_PATH",
    )
    parser.add_argument(
        "--ext",
        default=os.getenv("MWCLI_EXT", ".php"),
        metavar="EXT",
        help="Script extension. Default: .php. Env: MWCLI_EXT",
    )
    parser.add_argument(
        "--scheme",
        default=os.getenv("MWCLI_SCHEME", "https"),
        metavar="SCHEME",
        help="URL scheme: http or https. Default: https. Env: MWCLI_SCHEME",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("MWCLI_USERNAME"),
        metavar="USERNAME",
        help="Login username. If set, --password is required. Env: MWCLI_USERNAME",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("MWCLI_PASSWORD"),
        metavar="PASSWORD",
        help="Login password. If set, --username is required. Env: MWCLI_PASSWORD",
    )
    parser.add_argument(
        "--clients-useragent",
        default=os.getenv("MWCLI_USER_AGENT"),
        metavar="UA",
        help="Custom user-agent prefix. Env: MWCLI_USER_AGENT",
    )
    parser.add_argument(
        "--allow-anon",
        action="store_true",
        help="Allow unauthenticated edits (sets force_login=False on Site)",
    )
    parser.add_argument(
        "--no-init",
        action="store_true",
        help="Skip initial site_init() call during Site creation",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=None,
        metavar="N",
        help="Pretty-print JSON output with N-space indentation",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help=(
            "Convert content-read methods to Markdown "
            "(currently: page text, site parse)"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        title="commands",
        metavar="COMMAND",
    )

    methods_parser = subparsers.add_parser(
        "methods",
        formatter_class=HelpFormatter,
        help="list available methods on site/page/image targets",
        description="List callable public methods and signatures.",
        epilog=(
            "Examples:\n"
            "  mwclient-cli methods all\n"
            "  mwclient-cli methods page"
        ),
    )
    methods_parser.add_argument(
        "entity",
        choices=["site", "page", "image", "all"],
        help="Target entity to inspect",
    )

    for entity in ("site", "page", "image"):
        entity_parser = subparsers.add_parser(
            entity,
            formatter_class=HelpFormatter,
            help=f"call {entity} method by name",
            description=(
                f"Call public method on {entity} target.\n"
                "Arguments passed via repeated --arg and --kw options."
            ),
            epilog=(
                "Examples:\n"
                f"  mwclient-cli --host HOST {entity} "
                + ("\"Main Page\" " if entity == "page" else "\"Example.png\" " if entity == "image" else "")
                + "METHOD --arg VALUE --kw key=value\n"
                f"  mwclient-cli methods {entity}"
            ),
        )
        if entity in {"page", "image"}:
            entity_parser.add_argument("title", help=f"{entity} title")
        entity_parser.add_argument("method", help=f"{entity} method name")
        entity_parser.add_argument(
            "--arg",
            action="append",
            default=[],
            metavar="VALUE",
            help="Positional method arg (JSON parsed, fallback to string)",
        )
        entity_parser.add_argument(
            "--kw",
            action="append",
            default=[],
            metavar="KEY=VALUE",
            help="Keyword method arg (value JSON parsed, fallback to string)",
        )
        entity_parser.add_argument(
            "--stream",
            action="store_true",
            help="Stream list/tuple results as one JSON object per line",
        )
        entity_parser.add_argument(
            "--max-items",
            type=int,
            default=None,
            metavar="N",
            help="Limit number of emitted items for iterator/list results",
        )
        entity_parser.add_argument(
            "--markdown",
            action="store_true",
            default=argparse.SUPPRESS,
            help="Convert content-read methods to Markdown",
        )

    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "methods":
        if args.entity == "all":
            for entity in ("site", "page", "image"):
                print_method_list(entity)
            return 0
        return print_method_list(args.entity)

    if not args.host:
        parser.error("missing --host (or env MWCLI_HOST)")

    if bool(args.username) != bool(args.password):
        parser.error("set both --username and --password or neither")

    positionals = [parse_cli_value(raw) for raw in args.arg]
    try:
        kwargs = parse_keyword_args(args.kw)
    except ValueError as exc:
        parser.error(str(exc))

    target = build_target(build_site(args), args)
    methods = list_public_methods(args.command)
    if args.method not in methods:
        parser.error(f"unknown method {args.command}.{args.method}")
    method = getattr(target, args.method)

    result = method(*positionals, **kwargs)
    result = maybe_convert_markdown(args, target, result)
    if isinstance(result, Iterator):
        max_items = args.max_items
        count = 0
        for item in result:
            print_json(item, args.indent)
            count += 1
            if max_items is not None and count >= max_items:
                break
        return 0

    if args.stream and isinstance(result, (list, tuple)):
        max_items = args.max_items
        items = result if max_items is None else result[:max_items]
        for item in items:
            print_json(item, args.indent)
        return 0

    if args.markdown and isinstance(result, str):
        print_text(result)
    else:
        print_json(result, args.indent)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
