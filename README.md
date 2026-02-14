# mwcli

CLI wrapper around `mwclient`.

Exposes `mwclient` methods from 3 targets:
- `site` -> `mwclient.Site`
- `page` -> `mwclient.page.Page`
- `image` -> `mwclient.image.Image`

## Install

From project dir:

```bash
cd /app/mwcli
pip install -r requirements.txt
pip install -e .
```

## Command shape

```bash
python -m mwcli [connection flags] <site|page|image> <target args> <method> [--arg ...] [--kw ...]
```

Connection flags:
- `--host` required (or `MWCLI_HOST`)
- `--scheme` default `https`
- `--path` default `/w/`
- `--ext` default `.php`
- `--username`, `--password` optional auth

Method args:
- `--arg VALUE` positional arg, JSON-parsed when possible
- `--kw KEY=VALUE` keyword arg, value JSON-parsed when possible
- `--max-items N` cap iterator/list output
- `--stream` print list/tuple one JSON per line

Tip: quote strings with spaces/pipes.

## Discover available methods

```bash
python -m mwcli methods all
python -m mwcli methods site
python -m mwcli methods page
python -m mwcli methods image
```

## All commands

Top-level commands:

- `python -m mwcli methods {all|site|page|image}`
- `python -m mwcli site <method> [--arg ...] [--kw ...]`
- `python -m mwcli page "<title>" <method> [--arg ...] [--kw ...]`
- `python -m mwcli image "<title>" <method> [--arg ...] [--kw ...]`

`site` methods (mwclient 0.11.0):

- `allcategories`, `allimages`, `alllinks`, `allpages`, `allusers`
- `api`, `ask`, `blocks`, `checkuserlog`, `chunk_upload`, `clientlogin`
- `deletedrevisions`, `email`, `expandtemplates`, `exturlusage`
- `get`, `get_token`, `handle_api_result`, `logevents`, `login`
- `parse`, `patrol`, `post`, `random`, `raw_api`, `raw_call`, `raw_index`
- `recentchanges`, `require`, `revisions`, `search`, `site_init`
- `upload`, `usercontributions`, `users`, `version_tuple_from_generator`, `watchlist`

`page` methods:

- `append`, `backlinks`, `can`, `categories`, `delete`, `edit`, `embeddedin`
- `extlinks`, `get_token`, `handle_edit_error`, `images`, `iwlinks`, `langlinks`, `links`
- `move`, `normalize_title`, `prepend`, `purge`, `redirects_to`, `resolve_redirect`
- `revisions`, `save`, `strip_namespace`, `templates`, `text`, `touch`

`image` methods:

- all `page` methods, plus:
- `download`, `duplicatefiles`, `imagehistory`, `imageusage`

To confirm runtime command surface on your installed version:

```bash
python -m mwcli methods all
```

## Main usage examples

### Get page content

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  page "Main Page" text
```

Read one section:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  page "Main Page" text --kw section=1
```

### Search

Full text search:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  site search --arg "space" --kw what=text --max-items 10
```

Title-only search:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  site search --arg "Main" --kw what=title --max-items 10
```

### Authentication + edit

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  --username "Admin" --password "secret" \
  page "Sandbox" edit \
  --arg "Edited from mwcli ~~~~" \
  --kw summary="mwcli test edit" \
  --kw bot=false
```

### File upload

Local file upload:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  --username "Admin" --password "secret" \
  site upload \
  --kw file="/tmp/example.png" \
  --kw filename="Example.png" \
  --kw description="Uploaded by mwcli"
```

Upload from URL:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  --username "Admin" --password "secret" \
  site upload \
  --kw url="https://example.com/example.png" \
  --kw filename="ExampleFromURL.png"
```

### Semantic MediaWiki ask API

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  site ask --arg '[[Category:Item]]|?Has author|?Has status' --max-items 20
```

With an explicit title context:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  site ask --arg '[[Category:Item]]|?Has author' --kw title="Main Page" --max-items 20
```

Fetch all SMW properties for a page (`smwbrowse`):

```bash
python -m mwcli --indent 2 --host host.docker.internal --scheme http --path /w/ \
  site raw_api --arg smwbrowse --arg GET --kw browse=subject \
  --kw params='"{\"subject\":\"Main Page\",\"ns\":0}"'
```

Note: `smwbrowse` expects `params` as a JSON string, so pass a JSON object wrapped as a quoted string (double-encoded).

### Arbitrary API calls

Use `get` / `post` / `api` / `raw_api` directly.

Get siteinfo:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  site get --arg query --kw meta=siteinfo --kw siprop='general|namespaces'
```

Generic `api` call with GET method:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  site api --arg query --arg GET --kw prop=info --kw titles="Main Page"
```

Raw API (no extra wrapper logic):

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  site raw_api --arg query --arg GET --kw list=search --kw srsearch=space
```

### Page and image list iterators

Recent changes:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  site recentchanges --kw prop='title|timestamp|user|comment' --max-items 5
```

Image usage:

```bash
python -m mwcli --host host.docker.internal --scheme http --path /w/ \
  image "Example.png" imageusage --max-items 10
```

## Env vars

You can use env vars instead of flags:

- `MWCLI_HOST`
- `MWCLI_PATH` (default `/w/`)
- `MWCLI_EXT` (default `.php`)
- `MWCLI_SCHEME` (default `https`)
- `MWCLI_USERNAME`
- `MWCLI_PASSWORD`
- `MWCLI_USER_AGENT`

Then run shorter commands, for example:

```bash
export MWCLI_HOST=host.docker.internal
export MWCLI_SCHEME=http
export MWCLI_PATH=/w/
python -m mwcli site search --arg "space" --kw what=text --max-items 5
```
