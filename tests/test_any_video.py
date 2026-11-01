import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from iram_video.director import Director, DirectorUnavailable
from iram_video.mastering import master_video, resolve_dimensions, run_ffmpeg
from iram_video.script_import import LocalMediaLibrary, load_screenplay_file, normalize_screenplay, parse_script_text
from iram_video.renderer import SlideRenderer, draw_mixed_line
from iram_video.subtitles import KineticSubtitleGenerator
from iram_video.color_grade import COLOR_GRADE_PRESETS
from iram_video.templates import VIDEO_TEMPLATES

REPO = Path(__file__).resolve().parent.parent


def make_clip(path: Path, duration: float = 2.0, size: str = "1080x1920"):
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c=black:s={size}:d={duration}:r=30",
        "-f", "lavfi", "-i", f"sine=f=220:d={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ], check=True)


def lit_pixels_in_bottom_row(video: Path, at: float, width: int = 1080, height: int = 1920) -> int:
    raw = subprocess.run([
        "ffmpeg", "-v", "error", "-ss", str(at), "-i", str(video), "-frames:v", "1",
        "-vf", f"crop={width}:1:0:{height - 2},format=gray", "-f", "rawvideo", "-",
    ], check=True, capture_output=True).stdout
    return sum(1 for px in raw if px > 100)


class ScriptImportTests(unittest.TestCase):
    def test_script_keeps_words_verbatim_and_splits_scenes(self):
        sp = parse_script_text("# Opening\nHello there.\nSecond line.\n\nNew scene here.", "T")
        self.assertEqual(len(sp["scenes"]), 2)
        self.assertEqual(sp["scenes"][0]["narration"], "Hello there. Second line.")
        self.assertEqual(sp["scenes"][0]["heading"], "OPENING")
        self.assertEqual(len(sp["scenes"][0]["broll_beats"]), 2)

    def test_empty_script_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_script_text("# Only a heading\n\n")

    def test_screenplay_needs_speech_or_duration(self):
        with self.assertRaises(ValueError):
            normalize_screenplay({"scenes": [{"heading": "Nothing"}]})
        sp = normalize_screenplay({"scenes": [{"duration": 5}]})
        self.assertEqual(sp["scenes"][0]["narration"], "")

    def test_saved_plan_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "plan.json"
            path.write_text(json.dumps({"video_title": "Mine", "scenes": [{"narration": "Words."}]}))
            self.assertEqual(load_screenplay_file(path)["video_title"], "Mine")


class LocalMediaTests(unittest.TestCase):
    def test_prefers_matching_filename_then_spreads_usage(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("beach_sunset.jpg", "mountain.jpg", "notes.txt"):
                (Path(d) / name).write_bytes(b"x")
            lib = LocalMediaLibrary(Path(d))
            self.assertEqual(len(lib.files), 2)
            self.assertEqual(lib.pick("a mountain at dawn").name, "mountain.jpg")
            self.assertEqual(lib.pick("nothing relevant").name, "beach_sunset.jpg")

    def test_empty_folder_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                LocalMediaLibrary(Path(d))


class DirectorTests(unittest.TestCase):
    def _failing_director(self):
        director = Director.__new__(Director)
        director.model = "test-model"
        director.client = MagicMock()
        director.client.models.generate_content.side_effect = RuntimeError("quota")
        return director

    def test_no_placeholder_script_unless_accepted(self):
        with patch("iram_video.director.time.sleep"):
            with self.assertRaises(DirectorUnavailable):
                self._failing_director().direct("Grandma's dumplings", allow_offline=False)
            self.assertIn("scenes", self._failing_director().direct("Grandma's dumplings", allow_offline=True))

    def test_requested_style_replaces_default_look(self):
        director = self._failing_director()
        with patch("iram_video.director.time.sleep"):
            director.direct("A chase", style_hint="neon cyberpunk", duration_sec=60)
        sent = director.client.models.generate_content.call_args.kwargs["contents"][0]
        self.assertIn("neon cyberpunk", sent)
        self.assertNotIn("AVOID all cyberpunk", sent)
        self.assertIn("144 words", sent)


class FormatTests(unittest.TestCase):
    def test_dimensions(self):
        self.assertEqual(resolve_dimensions("4:5"), (1080, 1350))
        self.assertEqual(resolve_dimensions("2.39:1", is_4k=True), (3840, 1608))
        self.assertEqual(resolve_dimensions("16:9", is_shorts=True), (1080, 1920))

    def test_template_grades_exist(self):
        for key, tmpl in VIDEO_TEMPLATES.items():
            self.assertIn(tmpl["default_grade"], COLOR_GRADE_PRESETS, key)

    def test_every_color_grade_runs_in_ffmpeg(self):
        for key, preset in COLOR_GRADE_PRESETS.items():
            run_ffmpeg([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=64x64:d=0.1",
                "-vf", preset["ffmpeg_filter"], "-f", "null", "-",
            ])

    def test_ffmpeg_failure_reports_the_reason(self):
        with self.assertRaisesRegex(RuntimeError, "No such file"):
            run_ffmpeg(["ffmpeg", "-i", "/nonexistent/input.mp4", "-f", "null", "-"])


class RendererTests(unittest.TestCase):
    def _render_text(self, scene, **kwargs):
        with tempfile.TemporaryDirectory() as d, patch("iram_video.renderer.draw_mixed_line", wraps=draw_mixed_line) as spy:
            SlideRenderer(**kwargs).render_scene(scene, "Title", Path(d) / "s.png")
            return [c.args[3] for c in spy.call_args_list]

    def test_slides_show_no_invented_content(self):
        scene = normalize_screenplay({"scenes": [{"heading": "A QUIET HARBOUR", "narration": "Words."}]})["scenes"][0]
        for kwargs in ({}, {"is_shorts": True}, {"aspect_ratio": "1:1"}, {"aspect_ratio": "2.39:1"}, {"is_4k": True}):
            text = " ".join(self._render_text(scene, **kwargs))
            self.assertIn("A QUIET HARBOUR", text)
            for invented in ("100%", "BREAKDOWN", "termux", "TECH SHORTS", "IRAM AI Video"):
                self.assertNotIn(invented, text)

    def test_designed_layout_still_used_when_cards_have_content(self):
        scene = {"heading": "H", "layout_type": "stack_list", "cards": [{"title": "CARD ONE", "bullets": ["point"]}]}
        self.assertIn("CARD ONE", self._render_text(scene))


class MasteringTests(unittest.TestCase):
    def test_shorts_progress_bar_grows_over_time(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            make_clip(d / "raw.mp4", 2.0)
            scenes = [{"narration": "", "duration": 2.0}]
            master_video(d / "raw.mp4", d / "out.mp4", scenes, d, 1080, 1920, is_shorts=True, color_grade="none")
            early = lit_pixels_in_bottom_row(d / "out.mp4", 0.2)
            late = lit_pixels_in_bottom_row(d / "out.mp4", 1.8)
            self.assertLess(early, 250)
            self.assertGreater(late, 850)

    def test_subtitles_account_for_transition_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            ass = Path(d) / "s.ass"
            scenes = [
                {"narration": "first scene words", "duration": 10.0, "heading": "ONE"},
                {"narration": "second scene words", "duration": 10.0, "heading": "TWO"},
            ]
            KineticSubtitleGenerator.generate_ass(scenes, ass, scene_overlap=0.45)
            self.assertIn("0:00:09.55", ass.read_text(encoding="utf-8"))


class CliTests(unittest.TestCase):
    def test_3d_flag_no_longer_crashes_on_shutil(self):
        src = (REPO / "iram_video" / "cli.py").read_text(encoding="utf-8")
        self.assertNotIn("import shutil, subprocess", src)
        self.assertEqual(src.count("import shutil"), 1)

    def test_list_templates(self):
        out = subprocess.run(
            [sys.executable, str(REPO / "bin" / "video-gen"), "--list-templates"],
            capture_output=True, text=True, check=True,
        ).stdout
        for key in ("recipe", "story", "explainer"):
            self.assertIn(key, out)


if __name__ == "__main__":
    unittest.main()
