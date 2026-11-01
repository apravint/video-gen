"""
Author-supplied inputs: your own script or screenplay instead of an LLM-written one,
and your own images and clips instead of stock or generated footage.
"""

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}

DEFAULT_THEME = {"bg": [15, 23, 42], "accent": [59, 130, 246], "secondary": [148, 163, 184], "card_bg": [30, 41, 59]}

_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "your", "you", "are", "was", "were",
    "but", "not", "they", "their", "will", "what", "when", "into", "about", "there", "them", "then", "its",
}


def _keywords(text: str) -> List[str]:
    words = re.findall(r"[^\W\d_]{3,}", text.lower(), flags=re.UNICODE)
    return [w for w in words if w not in _STOPWORDS]


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text.strip()) if s.strip()]


def _fill_scene(scene: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Fills the fields downstream stages expect, without touching what the author provided."""
    narration = str(scene.get("narration") or "").strip()
    scene["id"] = str(scene.get("id") or f"scene_{index + 1:02d}")
    scene["narration"] = narration
    words = narration.split()
    scene.setdefault("heading", " ".join(words[:6]).upper()[:40] or f"SCENE {index + 1}")
    scene.setdefault("subheading", "")
    scene.setdefault("layout_type", "text_card")
    scene.setdefault("cards", [])
    if "broll_beats" not in scene:
        scene["broll_beats"] = [
            {"phrase": s, "search_query": " ".join(_keywords(s)[:5]) or s, "camera": "zoom_in"}
            for s in _sentences(narration)
        ]
    return scene


def normalize_screenplay(data: Dict[str, Any], fallback_title: str = "Untitled Video") -> Dict[str, Any]:
    """Validates a hand-written or edited screenplay and fills optional fields."""
    if isinstance(data, list):
        data = {"scenes": data}
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list) or not data["scenes"]:
        raise ValueError("A screenplay needs a non-empty 'scenes' list.")
    for i, scene in enumerate(data["scenes"]):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {i + 1} must be an object.")
        if not str(scene.get("narration") or "").strip() and not scene.get("duration"):
            raise ValueError(f"Scene {i + 1} needs 'narration' or, for a scene with no speech, 'duration'.")
        _fill_scene(scene, i)
    data.setdefault("video_title", fallback_title)
    data.setdefault("theme_palette", dict(DEFAULT_THEME))
    data.setdefault("youtube_metadata", {"description": "", "tags": []})
    return data


def parse_script_text(text: str, title: str = "Untitled Video") -> Dict[str, Any]:
    """
    Turns a plain script into a screenplay, keeping the words verbatim.
    Blank lines separate scenes. A '# Heading' line starts a scene and names it.
    """
    scenes: List[Dict[str, Any]] = []
    heading: Optional[str] = None
    lines: List[str] = []

    def flush():
        nonlocal heading, lines
        narration = " ".join(lines).strip()
        if narration:
            scene: Dict[str, Any] = {"narration": narration}
            if heading:
                scene["heading"] = heading.upper()[:40]
            scenes.append(scene)
            heading, lines = None, []

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            flush()
            heading = line.lstrip("#").strip()
        elif not line:
            flush()
        else:
            lines.append(line)
    flush()

    if not scenes:
        raise ValueError("The script has no spoken text.")
    return normalize_screenplay({"video_title": title, "scenes": scenes}, title)


def load_screenplay_file(path: Path, title: Optional[str] = None) -> Dict[str, Any]:
    """Loads a .json screenplay or a plain-text script."""
    fallback = title or path.stem.replace("-", " ").replace("_", " ").title()
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return normalize_screenplay(json.loads(text), fallback)
    return parse_script_text(text, fallback)


def target_scene_count(duration_sec: float) -> int:
    """Roughly one scene every 15 seconds, the pace the screenplay beats are written for."""
    return max(1, min(40, round(duration_sec / 15.0)))


class LocalMediaLibrary:
    """Serves beats from a folder of the user's images and clips."""

    def __init__(self, media_dir: Path, shuffle: bool = False):
        self.files = sorted(
            p for p in media_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS | VIDEO_EXTS
        )
        if not self.files:
            raise ValueError(f"No images or videos found in {media_dir}")
        if shuffle:
            random.shuffle(self.files)
        self._use_counts = {p: 0 for p in self.files}

    def pick(self, text: str) -> Path:
        """Prefers filename matches for the beat's words, then whichever file is least used."""
        words = set(_keywords(text))

        def score(p: Path):
            name_words = set(_keywords(p.stem.replace("_", " ").replace("-", " ")))
            return (-self._use_counts[p], len(words & name_words))

        matches = [p for p in self.files if words & set(_keywords(p.stem.replace("_", " ").replace("-", " ")))]
        pool = matches or self.files
        best_key = max(score(p) for p in pool)
        chosen = next(p for p in pool if score(p) == best_key)
        self._use_counts[chosen] += 1
        return chosen
