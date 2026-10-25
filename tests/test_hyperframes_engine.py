import unittest
import tempfile
from pathlib import Path
from iram_video.hyperframes_engine import HyperframesEngine, HYPERFRAMES_TEMPLATES
from iram_video.mcp_server import TOOLS_METADATA, MCPServer

class TestHyperframesEngine(unittest.TestCase):
    def test_templates_exist_and_valid(self):
        self.assertIn("code_walkthrough", HYPERFRAMES_TEMPLATES)
        self.assertIn("metric_dashboard", HYPERFRAMES_TEMPLATES)
        self.assertIn("kinetic_quote", HYPERFRAMES_TEMPLATES)

        for name, html in HYPERFRAMES_TEMPLATES.items():
            self.assertIn("<!DOCTYPE html>", html)
            self.assertIn("{{WIDTH}}", html)
            self.assertIn("{{HEIGHT}}", html)

    def test_render_template_to_mp4(self):
        with tempfile.TemporaryDirectory() as td:
            out_mp4 = Path(td) / "test_hyperframes.mp4"
            data = {
                "TITLE": "Fast API Engine",
                "QUOTE": "Code is poetry in motion",
                "AUTHOR": "Hyperframes",
                "CODE": "def hello(): return 'world'"
            }
            res = HyperframesEngine.render_template(
                "kinetic_quote",
                data,
                out_mp4,
                duration=1.0,
                fps=30,
                is_shorts=False
            )
            self.assertTrue(res.exists())
            self.assertGreater(res.stat().st_size, 500)

    def test_mcp_tool_registered(self):
        tool_names = [t["name"] for t in TOOLS_METADATA]
        self.assertIn("render_hyperframes_scene", tool_names)

        server = MCPServer()
        with tempfile.TemporaryDirectory() as td:
            out_mp4 = Path(td) / "mcp_hf.mp4"
            res = server.execute_tool("render_hyperframes_scene", {
                "template": "kinetic_quote",
                "title": "MCP Test",
                "quote_or_code": "Automated Scene Generation",
                "duration": 1.0,
                "output_path": str(out_mp4)
            })
            self.assertEqual(res["status"], "ok")
            self.assertTrue(Path(res["out_path"]).exists())

if __name__ == "__main__":
    unittest.main()
