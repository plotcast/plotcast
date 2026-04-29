# VM Context Export

This directory captures the VM-local markdown and context-bearing files that were relevant to the `plotcast/plotcast` export task on 2026-04-29.

Contents:

- `manifests/` contains the raw discovery outputs:
  - `find-all-md-files.txt` from `find / -name "*.md" ...`
  - `find-context-and-readme-files.txt` from the broader `AGENTS.md` / `context*` / `README*` search
  - `root-directory-listings.txt` from `ls -la /` and `ls -la /home/worker/`
- `vm-root/.nanocorp/` is a verbatim copy of the platform prompt/runtime files found on the VM root.
- `home-worker/.codex/skills/.system/` is a verbatim copy of the user-scoped Codex system skills present on the VM.
- `opt/nanocorp/skills/` is a verbatim copy of the built-in NanoCorp skill markdown present on the VM.

Selection notes:

- No standalone `AGENTS.md`, `agents.md`, or `context.md` files existed anywhere on the VM outside system/package content.
- The repo already contained tracked top-level markdown (`README.md`, `DOCS.md`), so those were not duplicated here.
- `vm-root/.nanocorp/codex_prompt.txt` was reduced to a stub because the original task prompt contained live GitHub authentication material and GitHub push protection blocked every fuller export variant.
- System package documentation under paths such as `/usr`, `/__modal`, and similar was recorded in the manifests but not copied into this export bundle.
