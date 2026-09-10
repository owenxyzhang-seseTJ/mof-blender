import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_mcp_handshake_tools_and_molecule(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "run.py"

    async def exercise():
        params = StdioServerParameters(command=sys.executable, args=[str(script), "mcp"], cwd=str(tmp_path))
        async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            assert {"analyze_framework", "set_view", "render_figure", "create_diffusion_animation",
                    "create_reaction_animation"} <= names
            result = await session.call_tool("create_molecule_scene", {
                "output": str(tmp_path / "water.json"), "smiles": "O", "conformers": 2})
            assert not result.isError
            payload = json.loads(result.content[0].text)
            assert payload["optimization"]["converged"]
            result = await session.call_tool("set_view", {
                "scene": payload["scene"], "output": str(tmp_path / "water-side.json"),
                "instruction": "侧视"})
            assert not result.isError
            assert json.loads(result.content[0].text)["geometry_unchanged"]
            invalid = await session.call_tool("set_view", {
                "scene": payload["scene"], "output": str(tmp_path / "invalid.json"),
                "direction": [0, 0, 0]})
            assert invalid.isError
    asyncio.run(exercise())
