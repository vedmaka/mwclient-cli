---
name: mwclient-cli
description: Use this skill when an LLM needs to read, search, edit, upload, or inspect MediaWiki data through the mwclient-cli command-line wrapper around mwclient. Trigger for tasks involving site/page/image method calls, MediaWiki API queries, Markdown conversion, or Semantic MediaWiki ask/raw_api operations.
---

# mwclient-cli skill

Use `mwclient-cli` as thin wrapper over `mwclient` methods.

## Quick start

Set connection once:

```bash
export MWCLI_HOST=host.docker.internal
export MWCLI_SCHEME=http
export MWCLI_PATH=/w/
```

Discover methods first:

```bash
uvx mwclient-cli methods all
```

Read page:

```bash
uvx mwclient-cli page "Main Page" text --markdown
```

## Command model

Shape:

```bash
uvx mwclient-cli [connection flags] <site|page|image> <target args> <method> [--arg ...] [--kw ...]
```

Targets:
- `site <method>`
- `page "<title>" <method>`
- `image "<title>" <method>`

Method arguments:
- `--arg VALUE`: positional; JSON parsed when valid
- `--kw KEY=VALUE`: keyword; value JSON parsed when valid
- `--max-items N`: cap iterator/list output
- `--stream`: emit list/tuple as JSONL
- `--markdown`: convert `page text` and `site parse` results to markdown text

## Connection/auth

Required:
- `--host` or `MWCLI_HOST`

Defaults:
- scheme `https`
- path `/w/`
- ext `.php`

Auth:
- pass both `--username` and `--password`, or neither
- env alternatives: `MWCLI_USERNAME`, `MWCLI_PASSWORD`

## Playbook

1. Inspect command surface:
```bash
uvx mwclient-cli methods site
uvx mwclient-cli methods page
uvx mwclient-cli methods image
```

2. Prefer read-only first:
```bash
uvx mwclient-cli site search --arg "query" --kw what=text --max-items 10
uvx mwclient-cli page "Title" text --markdown
```

3. For writes, require explicit user intent + auth:
```bash
uvx mwclient-cli --username "User" --password "Secret" \
  page "Sandbox" edit --arg "new content" --kw summary="agent update"
```

4. For SMW/custom API:
```bash
uvx mwclient-cli site ask --arg '[[Category:Item]]|?Has status' --max-items 20
uvx mwclient-cli site raw_api --arg query --arg GET --kw list=search --kw srsearch=space
```

## JSON parsing rules

`--arg/--kw` values are parsed with JSON first.

Examples:
- `--kw limit=5` -> number
- `--kw minor=true` -> boolean
- `--kw tags='["a","b"]'` -> array
- `--kw summary="plain text"` -> string

If parse fails, value stays raw string.

## Failure handling

Common CLI errors:
- `missing --host (or env MWCLI_HOST)`
- `set both --username and --password or neither`
- `Unknown method <target>.<method>`
- `invalid --kw value 'X', expected key=value`

Recovery:
1. run `methods <target>` and pick valid method name
2. validate `--kw` has `key=value`
3. set/fix connection env flags
4. retry read-only call before write

## Output contract

- default output: JSON
- iterators: JSONL (one JSON object per line), honor `--max-items`
- markdown mode on string result prints plain text markdown
- bytes values encoded as:
  - `{"__type__":"bytes","base64":"...","size":N}`

