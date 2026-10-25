"""
Model Context Protocol (MCP) Server for IRAM Video.
Inspired by gyoridavid/short-video-maker MCP server architecture.
Exposes IRAM Video creation, B-roll search, scene extension, and soundscape design
as native tools over standard JSON-RPC 2.0 stdio protocol.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from .soundscape import SoundscapeAdvisor
from .b_roll import MediaFetcher
from .ai_video import AIVideoEngine
from .motion_canvas import MotionCanvas
from .templates import VIDEO_TEMPLATES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)

TOOLS_METADATA = [
    {
        "name": "create_video",
        "description": "Generates a complete broadcast-quality video or YouTube Short with voiceover, B-roll, score, transitions, and optional kinetic subtitles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The topic, premise, or screenplay brief."},
                "template": {"type": "string", "enum": list(VIDEO_TEMPLATES.keys()), "description": "High-level genre template ('explainer', 'tutorial', 'listicle', 'comparison', 'news', 'promo', 'podcast')."},
                "aspect_ratio": {"type": "string", "enum": ["16:9", "9:16", "1:1", "2.39:1"], "default": "16:9", "description": "Aspect ratio ('16:9', '9:16', '1:1', '2.39:1')."},
                "is_shorts": {"type": "boolean", "default": False, "description": "True for 9:16 vertical video (YouTube Shorts, Reels, TikTok); False for 16:9."},
                "is_real": {"type": "boolean", "default": True, "description": "True for real YouTube documentary with verified B-roll and acoustic score."},
                "is_4k": {"type": "boolean", "default": False, "description": "Render in 4K UHD high resolution."},
                "transition": {"type": "string", "enum": ["fade", "dissolve", "wipeleft", "wiperight", "slideleft", "slideright", "smoothleft", "circlecrop", "fadeblack", "fadewhite"], "default": "fade", "description": "Cinematic scene transition."},
                "color_grade": {"type": "string", "enum": ["clean", "documentary", "cinematic", "vintage", "noir", "vibrant", "none"], "default": "clean", "description": "Cinematic color grading preset."},
                "music": {"type": "string", "default": "documentary", "description": "Music mood ('documentary', 'acoustic', 'tech', 'ambient', 'trailer', 'corporate', 'energetic', 'minimal')."},
                "bg_music": {"type": "string", "description": "Custom background music audio file path."},
                "music_volume": {"type": "number", "default": 0.20, "description": "Background music ducking volume level (0.0 to 1.0)."},
                "steady_camera": {"type": "boolean", "default": True, "description": "Subtle steady-cam micro-drift framing (zero dizzying pans)."},
                "output_path": {"type": "string", "description": "Destination file path for the output MP4."}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "list_templates",
        "description": "Lists all available video genre templates with their scene defaults, mood music, and color grade presets.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "extend_video",
        "description": "Continuously extends an existing video clip into a multi-scene film using keyframe seeding.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "previous_video": {"type": "string", "description": "Absolute path to the existing MP4 video clip."},
                "prompt": {"type": "string", "description": "Description of the next narrative scene."},
                "output_path": {"type": "string", "description": "Destination path for the extended video."},
                "duration": {"type": "number", "default": 4.0, "description": "Duration of the extension in seconds."}
            },
            "required": ["previous_video", "prompt", "output_path"]
        }
    },
    {
        "name": "suggest_soundscape",
        "description": "Designs a Hollywood-grade musical score and audio foley soundscape tailored to a video scene description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scene_prompt": {"type": "string", "description": "Description of the visual scene or narrative action."}
            },
            "required": ["scene_prompt"]
        }
    },
    {
        "name": "search_stock_broll",
        "description": "Searches curated HD stock video clips and photography across Wikimedia Commons and Pexels with orientation filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword or entity name."},
                "orientation": {"type": "string", "enum": ["portrait", "landscape"], "default": "landscape", "description": "Target video orientation."},
                "require_video": {"type": "boolean", "default": True, "description": "True to prioritize MP4 video clips over still photos."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "render_metric_card",
        "description": "Programmatically renders a sleek 30 FPS animated infographic counter card video clip.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "number": {"type": "number", "description": "The target metric number to animate count-up."},
                "unit": {"type": "string", "description": "Unit label (e.g. 'KM', '%', 'CRORE', 'MS')."},
                "headline": {"type": "string", "description": "Metric headline or label."},
                "subheadline": {"type": "string", "default": "", "description": "Contextual subheadline."},
                "out_path": {"type": "string", "description": "Destination MP4 file path."},
                "duration": {"type": "number", "default": 4.0, "description": "Clip duration in seconds."},
                "is_shorts": {"type": "boolean", "default": False, "description": "Render in 9:16 vertical shorts aspect ratio."}
            },
            "required": ["number", "unit", "headline", "out_path"]
        }
    },
    {
        "name": "render_hyperframes_scene",
        "description": "Renders a declarative HTML/CSS/GSAP scene into a 60fps MP4 video clip using the HeyGen Hyperframes engine.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "template": {"type": "string", "enum": ["code_walkthrough", "metric_dashboard", "kinetic_quote"], "default": "kinetic_quote", "description": "Hyperframes motion template."},
                "title": {"type": "string", "description": "Title or headline for the scene."},
                "quote_or_code": {"type": "string", "description": "The quote text, narration, or code snippet to animate."},
                "author": {"type": "string", "default": "IRAM Video", "description": "Author attribution or subtitle."},
                "duration": {"type": "number", "default": 5.0, "description": "Duration in seconds."},
                "is_shorts": {"type": "boolean", "default": False, "description": "True for 9:16 vertical video."},
                "output_path": {"type": "string", "description": "Optional destination path for the output MP4."}
            },
            "required": ["quote_or_code"]
        }
    }
]

class MCPServer:
    """Standard Model Context Protocol (MCP) JSON-RPC 2.0 Server."""

    def __init__(self):
        self.running = True

    def handle_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "iram-video",
                        "version": "2.0.0"
                    }
                }
            }
        elif method == "notifications/initialized":
            return None
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS_METADATA}
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            try:
                res_content = self.execute_tool(tool_name, args)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res_content, indent=2)}]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "isError": True,
                        "content": [{"type": "text", "text": f"Error executing {tool_name}: {str(e)}"}]
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"}
            }

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "suggest_soundscape":
            return SoundscapeAdvisor.design_soundscape(args["scene_prompt"])

        elif tool_name == "search_stock_broll":
            query = args["query"]
            orientation = args.get("orientation", "landscape")

            # Explicitly intercept vertical flags to shield the layout canvas from landscape assets
            if args.get("is_shorts") or args.get("aspect_ratio") == "9:16":
                orientation = "portrait"

            req_vid = args.get("require_video", True)
            results = MediaFetcher.search_pexels(query, require_video=req_vid, orientation=orientation)
            if not results:
                results = MediaFetcher.search_wikimedia(query, require_video=req_vid)
            return results[:6]

        elif tool_name == "render_metric_card":
            beat = {
                "metric_number": args["number"],
                "metric_unit": args["unit"],
                "metric_label_en": args["headline"],
                "phrase": args.get("subheadline", "")
            }
            out_p = Path(args["out_path"])
            dur = float(args.get("duration", 4.0))
            is_sh = bool(args.get("is_shorts", False))
            MotionCanvas.render_metric_card(beat, out_p, duration=dur, is_shorts=is_sh)
            return {"status": "ok", "out_path": str(out_p), "duration": dur}

        elif tool_name == "render_hyperframes_scene":
            from .hyperframes_engine import HyperframesEngine
            tmpl = args.get("template", "kinetic_quote")
            title = args.get("title", "Hyperframes Showcase")
            text = args.get("quote_or_code", "")
            author = args.get("author", "IRAM Video")
            dur = float(args.get("duration", 5.0))
            is_sh = bool(args.get("is_shorts", False))
            out_p = Path(args.get("output_path") or "/tmp/mcp_hyperframes_output.mp4").resolve()

            res = HyperframesEngine.render_template(
                tmpl,
                {
                    "TITLE": title,
                    "QUOTE": text,
                    "CODE": text,
                    "AUTHOR": author,
                    "LABEL_1": "Performance", "VAL_1": "100%", "CHANGE_1": "2.4x",
                    "LABEL_2": "Throughput", "VAL_2": "60 FPS", "CHANGE_2": "1.8x",
                    "LABEL_3": "Precision", "VAL_3": "99.9%", "CHANGE_3": "0.5%",
                },
                out_p,
                duration=dur,
                is_shorts=is_sh
            )
            return {"status": "ok", "out_path": str(res), "duration": dur}

        elif tool_name == "extend_video":
            prev_v = Path(args["previous_video"]).resolve()
            if not prev_v.exists():
                raise FileNotFoundError(f"Previous video not found: {prev_v}")
            out_p = Path(args["output_path"]).resolve()
            prompt = args["prompt"]
            dur = float(args.get("duration", 4.0))
            is_sh = bool(args.get("is_shorts", False))
            res = AIVideoEngine.extend_video(prev_v, prompt, out_p, duration=dur, is_shorts=is_sh)
            return {"status": "ok", "out_path": str(res)}

        elif tool_name == "list_templates":
            return VIDEO_TEMPLATES

        elif tool_name == "create_video":
            import subprocess
            prompt = args["prompt"]
            out_p = Path(args.get("output_path", "/tmp/mcp_generated_video.mp4")).resolve()
            cmd = [sys.executable, "-m", "iram_video.cli", "-o", str(out_p)]

            is_shorts_flag = bool(args.get("is_shorts", False))
            target_aspect = "9:16" if is_shorts_flag else args.get("aspect_ratio", "16:9")

            if args.get("template"):
                cmd.extend(["--template", args["template"]])

            cmd.extend(["--aspect-ratio", target_aspect])

            if is_shorts_flag:
                cmd.append("--shorts")
            if args.get("is_real", True):
                cmd.append("--real")
            if args.get("is_4k"):
                cmd.append("--4k")
            if args.get("transition"):
                cmd.extend(["--transition", args["transition"]])
            if args.get("color_grade"):
                cmd.extend(["--grade", args["color_grade"]])
            if args.get("music"):
                cmd.extend(["--music", args["music"]])
            if args.get("bg_music"):
                cmd.extend(["--bg-music", args["bg_music"]])
            if "music_volume" in args:
                cmd.extend(["--music-volume", str(args["music_volume"])])
            if args.get("steady_camera", True):
                cmd.append("--steady")
            cmd.extend(["--", prompt])
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600)
                return {
                    "status": "ok" if proc.returncode == 0 else "error",
                    "output_video": str(out_p),
                    "stdout": proc.stdout[-500:],
                    "stderr": proc.stderr[-500:] if proc.returncode != 0 else ""
                }
            except subprocess.TimeoutExpired:
                return {
                    "status": "error",
                    "output_video": str(out_p),
                    "stdout": "",
                    "stderr": "Video creation timed out after 600 seconds"
                }
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def run_stdio(self):
        """Runs the JSON-RPC stdio event loop."""
        logging.info("IRAM Video MCP Server listening on stdio...")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self.handle_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()

def main():
    server = MCPServer()
    server.run_stdio()

if __name__ == "__main__":
    main()
