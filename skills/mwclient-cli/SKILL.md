---
name: mwclient-cli
description: "Interact with any MediaWiki website or Wikipedia from the command line — read pages, search content, edit articles, upload files, query categories, and call the MediaWiki API. Use this skill whenever the user wants to fetch, read, search, browse, or edit content on Wikipedia, Wiktionary, Wikidata, Fandom wikis, or any MediaWiki-powered site. Also use when the user mentions wiki pages, wiki markup, wiki templates, Semantic MediaWiki queries, or needs to pull structured data from a wiki. Even if the user just says 'look up X on Wikipedia' or 'get the wiki page for Y' — this skill applies."
---

# mwclient-cli — MediaWiki & Wikipedia CLI

`mwclient-cli` lets you read, search, edit, and inspect any MediaWiki site (Wikipedia, Wiktionary, Wikidata, Fandom, private wikis, etc.) from the command line.

## Connecting to a wiki

Every command needs `--host` at minimum. Defaults: `--scheme https`, `--path /w/`, `--ext .php`.

**Wikipedia (English):**
```bash
uvx mwclient-cli --host en.wikipedia.org page "Main Page" text --markdown
```

**Other Wikimedia projects:**
```bash
uvx mwclient-cli --host en.wiktionary.org ...   # Wiktionary
uvx mwclient-cli --host www.wikidata.org ...     # Wikidata
uvx mwclient-cli --host commons.wikimedia.org ... # Commons
```

**Other languages — just change the subdomain:**
```bash
uvx mwclient-cli --host de.wikipedia.org ...   # German Wikipedia
uvx mwclient-cli --host ja.wikipedia.org ...   # Japanese Wikipedia
```

**Private / self-hosted MediaWiki:**
```bash
uvx mwclient-cli --host wiki.example.com --scheme http --path /w/ ...
```

**Local development wiki (Docker):**
```bash
uvx mwclient-cli --host host.docker.internal --scheme http --path /w/ ...
```

Environment variables (`MWCLI_HOST`, `MWCLI_SCHEME`, `MWCLI_PATH`) also work but flags are preferred — they're explicit and visible in each command.

## Quick examples

Read a Wikipedia article as markdown:
```bash
uvx mwclient-cli --host en.wikipedia.org page "Albert Einstein" text --markdown
```

Search Wikipedia:
```bash
uvx mwclient-cli --host en.wikipedia.org site search --arg "climate change" --kw what=text --max-items 10
```

List methods available:
```bash
uvx mwclient-cli methods all
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

## Common tasks

### Read a wiki page
```bash
uvx mwclient-cli --host en.wikipedia.org page "Photosynthesis" text --markdown
```

### Search for articles
```bash
uvx mwclient-cli --host en.wikipedia.org site search --arg "machine learning" --kw what=text --max-items 10
```

### Get page categories
```bash
uvx mwclient-cli --host en.wikipedia.org page "Python (programming language)" categories --max-items 20
```

### List pages in a category
```bash
uvx mwclient-cli --host en.wikipedia.org site categories --max-items 5
```

### Get page metadata / info
```bash
uvx mwclient-cli --host en.wikipedia.org page "Mars" revision
```

### Semantic MediaWiki query
```bash
uvx mwclient-cli --host wiki.example.com site ask --arg '[[Category:Item]]|?Has status' --max-items 20
```

### Raw MediaWiki API call
```bash
uvx mwclient-cli --host en.wikipedia.org site raw_api --arg query --arg GET --kw list=search --kw srsearch=space
```

### Edit a page (requires auth + explicit user intent)
```bash
uvx mwclient-cli --host wiki.example.com --username "User" --password "Secret" \
  page "Sandbox" edit --arg "new content" --kw summary="agent update"
```

## Playbook

1. **Set connection** to the target wiki (env vars or flags)
2. **Discover methods** if unsure what's available:
   ```bash
   uvx mwclient-cli methods site
   uvx mwclient-cli methods page
   uvx mwclient-cli methods image
   ```
3. **Read first** — prefer read-only operations before any writes
4. **Writes require explicit user intent** — never edit wiki pages unless the user clearly asked for it, and auth credentials are provided

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

