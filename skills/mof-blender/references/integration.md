# Runtime and integration

The distributable contains a Python package, stdio MCP server, agent-neutral SKILL.md,
Codex plugin manifest and Claude Code plugin manifest. The runtime does not import Blender's
Python into the chemistry environment. It invokes an installed Blender executable with JSON.

Install Python 3.12+ and Blender 4.5+ (actual rendering tested on Blender 5.2.1/macOS). In a
fresh checkout create `.venv`, install `requirements.lock.txt`, then install this package with
`.venv/bin/python -m pip install --no-deps .` (a normal, noneditable installation).
`requirements.lock.txt` records exact tested dependency versions;
AuToGraFS is pinned to 3.2.0 because its geometry adapter uses version-specific internals,
guarded by an exact quotient-graph cross-check. A newer API is not assumed compatible.

The source launcher `.venv/bin/python scripts/run.py ...` loads the checkout directly, so
new invocations reflect source edits without reinstalling. Installed `mof-blender` and
`mof-blender-mcp` entrypoints use the installed package. After checkout updates, reinstall it
with `.venv/bin/python -m pip install --no-deps --force-reinstall .`, or
`uv pip install --python .venv/bin/python --no-deps --reinstall .` when using uv.

Use `scripts/configure_agents.py --output integrations/local` to produce absolute-path Codex,
Claude/Cursor/Windsurf-style and VS Code MCP configuration snippets. It does not edit global
agent configuration. Use the generated paths exactly. Restart/reload the host after registration.

With the package executable on PATH, `.mcp.json` is a portable plugin default. If the host
cannot inherit a virtual environment's PATH, use generated absolute-path configuration.
Codex CLI: `codex mcp add mof-blender -- /absolute/.venv/bin/python /absolute/scripts/run.py mcp`.
Claude Code: `claude mcp add --scope user --transport stdio mof-blender -- /absolute/.venv/bin/python /absolute/scripts/run.py mcp`.
Install the skill folder into the agent's skill directory as well. A host with MCP but no skill
support can still discover tools and their schemas.

`BLENDER_PATH` selects the executable. The diagnostic looks at PATH, the standard macOS app
location and standard Windows installation folders. There is no remote Blender control socket
and no tool that executes arbitrary Python supplied by the agent. A render launches a fresh
Blender process and cannot overwrite an existing output directory.

On macOS a constrained sandbox may block Blender's Metal initialization, even when Cycles is
set to CPU. Permit the normal render command in the host if needed. Do not claim a render
succeeded on the basis of a `.blend` or an incomplete output folder; require a manifest.

See the [README](../../../README.md), [example gallery](../../../docs/gallery.md), and
[validation record](../../../docs/validation.md) for capabilities, artifacts, test status and
known limitations.
