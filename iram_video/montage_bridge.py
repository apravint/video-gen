"""
IRAM OS & OpenMontage Integration Bridge
Bridges IRAM OS Universal Film & Video Engine with OpenMontage's 12 agentic video pipelines,
Backlot living storyboard server, and multi-point automated quality inspection.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional

OPENMONTAGE_ROOT = Path("/home/apravint/OpenMontage")
VENV_PYTHON = OPENMONTAGE_ROOT / ".venv/bin/python"


def is_montage_available() -> bool:
    """Checks if OpenMontage repository and its virtual environment are ready."""
    return (
        OPENMONTAGE_ROOT.exists()
        and (OPENMONTAGE_ROOT / "pipeline_defs").exists()
        and VENV_PYTHON.exists()
    )


def get_python_exec() -> str:
    """Returns the isolated Python executable for OpenMontage."""
    if VENV_PYTHON.exists() and os.access(VENV_PYTHON, os.X_OK):
        return str(VENV_PYTHON)
    return sys.executable


def list_pipelines() -> List[Dict[str, Any]]:
    """Discovers and parses all 12 OpenMontage pipeline definitions."""
    if not is_montage_available():
        return []

    pipeline_dir = OPENMONTAGE_ROOT / "pipeline_defs"
    pipelines = []

    try:
        import yaml
    except ImportError:
        yaml = None

    for f in sorted(pipeline_dir.glob("*.yaml")):
        pipeline_id = f.stem
        meta: Dict[str, Any] = {
            "id": pipeline_id,
            "name": pipeline_id.replace("-", " ").title(),
            "description": "Agentic video production pipeline",
            "category": "general",
            "stages": [],
        }

        try:
            content = f.read_text(encoding="utf-8")
            if yaml:
                data = yaml.safe_load(content) or {}
                meta["name"] = data.get("name", meta["name"])
                meta["description"] = (data.get("description") or meta["description"]).strip()
                meta["category"] = data.get("category", "general")
                meta["stages"] = [s.get("name", "") for s in data.get("stages", []) if isinstance(s, dict)]
            else:
                for line in content.splitlines():
                    if line.startswith("name:"):
                        meta["name"] = line.split(":", 1)[1].strip()
                    elif line.startswith("category:"):
                        meta["category"] = line.split(":", 1)[1].strip()
        except Exception:
            pass

        pipelines.append(meta)

    return pipelines


def format_pipeline_catalog() -> str:
    """Renders a formatted ANSI/ASCII table of all OpenMontage pipelines."""
    pipelines = list_pipelines()
    if not pipelines:
        return "OpenMontage is not installed or pipeline definitions are missing."

    lines = [
        "╭─────────────────────────────────────────────────────────────────────────────╮",
        "│              🎬 IRAM VIDEO · OPENMONTAGE PRODUCTION PIPELINES               │",
        "├──────────────────────┬─────────────┬────────────────────────────────────────┤",
        "│ PIPELINE             │ CATEGORY    │ DESCRIPTION                            │",
        "├──────────────────────┼─────────────┼────────────────────────────────────────┤",
    ]

    for p in pipelines:
        pid = p["id"][:20]
        cat = p["category"][:11]
        desc = p["description"].split(".")[0].strip()
        desc = (desc[:37] + "...") if len(desc) > 40 else desc
        lines.append(f"│ {pid:<20} │ {cat:<11} │ {desc:<38} │")

    lines.append("╰──────────────────────┴─────────────┴────────────────────────────────────────╯")
    lines.append("\nRun with: iram video montage \"<prompt>\" --pipeline <pipeline-id>")
    lines.append("Launch Storyboard: iram video backlot")
    return "\n".join(lines)


def list_demos() -> List[str]:
    """Returns a list of zero-key Remotion demo composition IDs."""
    props_dir = OPENMONTAGE_ROOT / "remotion-composer/public/demo-props"
    if not props_dir.exists():
        return []
    return [p.stem for p in sorted(props_dir.glob("*.json"))]


def run_demo(demo_name: str = "code-to-screen") -> int:
    """Renders one of the zero-key Remotion motion graphics demos."""
    if not is_montage_available():
        print("Error: OpenMontage is not installed in ~/OpenMontage.")
        return 1

    py_bin = get_python_exec()
    print(f"🎬 [OPENMONTAGE] Rendering Remotion composition demo: '{demo_name}' ...")
    cmd = [py_bin, str(OPENMONTAGE_ROOT / "render_demo.py"), demo_name]
    res = subprocess.run(cmd, cwd=str(OPENMONTAGE_ROOT))
    return res.returncode


def launch_backlot(port: int = 8080) -> None:
    """Launches OpenMontage's Backlot living storyboard web server."""
    if not is_montage_available():
        print("Error: OpenMontage is not installed in ~/OpenMontage.")
        sys.exit(1)

    py_bin = get_python_exec()
    print(f"🎬 [BACKLOT] Launching OpenMontage Living Storyboard HUD on http://localhost:{port} ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(OPENMONTAGE_ROOT)
    
    cmd = [py_bin, "-m", "backlot", "serve", "--port", str(port)]
    try:
        subprocess.run(cmd, cwd=str(OPENMONTAGE_ROOT), env=env)
    except KeyboardInterrupt:
        print("\nBacklot server stopped.")


def audit_media(file_path: str) -> Dict[str, Any]:
    """Runs OpenMontage automated multi-point quality check on a video file."""
    p = Path(file_path).resolve()
    if not p.exists():
        return {"error": f"File not found: {file_path}"}

    py_bin = get_python_exec()
    script = f"""
import sys, json
sys.path.insert(0, '{OPENMONTAGE_ROOT}')
from tools.analysis.audio_probe import AudioProbe
try:
    probe = AudioProbe()
    res = probe.execute({{'input_path': '{p}'}})
    if res.success:
        print(json.dumps({{'status': 'ok', 'media': res.data}}))
    else:
        print(json.dumps({{'status': 'error', 'error': res.error}}))
except Exception as e:
    print(json.dumps({{'status': 'exception', 'error': str(e)}}))
"""
    try:
        out = subprocess.check_output([py_bin, "-c", script], cwd=str(OPENMONTAGE_ROOT), text=True)
        return json.loads(out.strip())
    except Exception as e:
        return {"error": f"Audit execution error: {e}"}
