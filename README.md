# MHH Hematology Galaxy tools

Galaxy tool wrappers maintained by the Department of Hematology, Hemostasis,
Oncology and Stem Cell Transplantation, Hannover Medical School (MHH).

This repository works like [galaxyproject/tools-iuc](https://github.com/galaxyproject/tools-iuc)
and [bgruening/galaxytools](https://github.com/bgruening/galaxytools):

1. Tool wrappers live in `tools/<toolname>/`, each with a `.shed.yml`.
2. Pull requests are linted and tested by CI (planemo via
   `galaxyproject/planemo-ci-action`).
3. On merge to `main`, CI automatically uploads the changed tools to the
   [Galaxy ToolShed](https://toolshed.g2.bx.psu.edu) under the owner
   `mhh-hematology` (and to the Test ToolShed first).
4. Every Galaxy server in the world has the main ToolShed preconfigured, so
   once a tool is published there, any Galaxy admin can find and install it
   via "Admin > Install and Uninstall". That is all "showing up in Galaxy by
   default" means; no further registration is needed.

## One-time setup (do once, in this order)

1. **GitHub organisation and repo**: create the org `mhh-hematology` on
   GitHub and push this repository as `mhh-hematology/galaxytools`.

2. **ToolShed accounts**: register the same account name on both sheds:
   - https://testtoolshed.g2.bx.psu.edu (Test ToolShed, for staging)
   - https://toolshed.g2.bx.psu.edu (main ToolShed, what Galaxy servers use)

   Pick the public name `mhh-hematology` (lowercase letters, digits and `-`
   only). The public name becomes the `owner:` in every `.shed.yml` and
   **cannot be changed later**, so use a lab account (shared lab e-mail), not
   a personal one.

3. **API keys as GitHub secrets**: in each ToolShed go to
   User > API Keys and generate a key. In the GitHub repo, add them under
   Settings > Secrets and variables > Actions:
   - `TTS_API_KEY` = Test ToolShed key
   - `TS_API_KEY`  = main ToolShed key

That is the entire setup. From then on, merging a PR that touches
`tools/<name>/` creates or updates the ToolShed repository automatically
(`planemo shed_update` with repository auto-creation; no manual
`shed_create` needed).

## Adding a tool

```
tools/mytool/
├── .shed.yml          # ToolShed metadata (see docs/shed.yml.template)
├── mytool.xml         # the wrapper, @TOOL_VERSION@+galaxy0 versioning
├── macros.xml         # optional
└── test-data/         # small test files (< 1 MB each, CI enforces this)
```

- Requirements must be resolvable from Bioconda, otherwise installations
  will fail on other servers.
- Every tool needs at least one `<test>`; CI runs them with planemo.
- `categories:` in `.shed.yml` must be names that already exist in the
  ToolShed (e.g. "Sequence Analysis", "Variant Analysis").
- Open a PR, let CI pass, merge. Deployment to the sheds happens on merge.

## Getting tools onto the big public servers

Publishing to the ToolShed makes tools *installable* everywhere, but each
server's admins decide what is *installed*:

- **usegalaxy.eu**: PR a `mhh-hematology.yml` tool list to
  [usegalaxy-eu/usegalaxy-eu-tools](https://github.com/usegalaxy-eu/usegalaxy-eu-tools).
  Tools in those lists are installed and then auto-updated weekly. This is
  how bgruening's tools appear on usegalaxy.eu.
- **usegalaxy.org**: PR to
  [galaxyproject/usegalaxy-tools](https://github.com/galaxyproject/usegalaxy-tools).
- **Own/local Galaxy instances** (e.g. the MRD appliance): install via the
  admin UI, or reproducibly with ephemeris:

  ```
  shed-tools install -g https://your.galaxy -a <admin-api-key> \
      --name mytool --owner mhh-hematology
  ```

## Manual deployment (fallback, normally not needed)

CI does this on merge, but it can be done locally with planemo. Put the keys
in `~/.planemo.yml`:

```yaml
shed_username: mhh-hematology
sheds:
  toolshed:
    key: <main shed API key>
  testtoolshed:
    key: <test shed API key>
```

Then, from the repo root:

```
planemo shed_update --shed_target testtoolshed --check_diff -r tools/mytool
planemo shed_update --shed_target toolshed     --check_diff -r tools/mytool
```

Note for the MHH network: `planemo test`/`planemo serve` hang behind the
proxy unless `no_proxy` starts with `127.0.0.1,localhost`. `shed_update` is
plain HTTPS and works with the normal proxy settings. When in doubt, rely on
CI instead of local runs.

## Relation to tools-iuc

Tools of broad general interest are still best contributed to tools-iuc
(wider review, `iuc` owner). This repository is for MHH-specific tooling and
for wrappers where we want full control over release timing. A tool should
be published under exactly one ToolShed owner to avoid duplicate listings.
