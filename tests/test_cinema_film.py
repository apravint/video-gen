import unittest
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

from iram_video.renderer import is_tamil_text, split_runs, get_fonts, get_mixed_width, draw_mixed_line
from iram_video.characters import CharacterRenderer
from iram_video.environments import EnvironmentRenderer
from iram_video.sfx import SoundEffectsSynthesizer

class TestCinemaFilmEngine(unittest.TestCase):
    def test_tamil_detection_and_runs(self):
        ta_sample = "தமிழ் மற்றும் English கலவை"
        self.assertTrue(is_tamil_text(ta_sample))
        runs = split_runs(ta_sample)
        self.assertTrue(len(runs) >= 3)
        # Check first run is Tamil
        self.assertTrue(runs[0][1])

    def test_character_rendering(self):
        chars = ["robot", "presenter", "ferris", "gopher"]
        for c in chars:
            img = CharacterRenderer.render_character(c, w=300, h=400, mouth_open=0.5, eye_state="blink", pointing=True)
            self.assertIsInstance(img, Image.Image)
            self.assertEqual(img.size, (300, 400))

    def test_environment_rendering(self):
        sets = ["modern_studio", "executive_boardroom", "cyberpunk_city", "quantum_lab", "deep_space", "digital_matrix"]
        for s in sets:
            img = EnvironmentRenderer.render_set(s, w=640, h=360)
            self.assertIsInstance(img, Image.Image)
            self.assertEqual(img.size, (640, 360))

    def test_sfx_synthesis(self):
        with tempfile.TemporaryDirectory() as td:
            p_impact = Path(td) / "impact.wav"
            p_whoosh = Path(td) / "whoosh.wav"
            p_tele = Path(td) / "telemetry.wav"

            SoundEffectsSynthesizer.generate_impact(p_impact, duration=0.5)
            SoundEffectsSynthesizer.generate_whoosh(p_whoosh, duration=0.5)
            SoundEffectsSynthesizer.generate_telemetry(p_tele, duration=0.5)

            self.assertTrue(p_impact.exists() and p_impact.stat().st_size > 1000)
            self.assertTrue(p_whoosh.exists() and p_whoosh.stat().st_size > 1000)
            self.assertTrue(p_tele.exists() and p_tele.stat().st_size > 1000)

    def test_kinetic_subtitles(self):
        from iram_video.subtitles import KineticSubtitleGenerator
        with tempfile.TemporaryDirectory() as td:
            ass_out = Path(td) / "test.ass"
            scenes = [
                {"narration": "Artificial intelligence is expanding into cinematic storytelling", "duration": 4.0},
                {"narration": "தானியங்கி மென்பொருள் மற்றும் கணினி பார்வை", "duration": 3.5}
            ]
            KineticSubtitleGenerator.generate_ass(scenes, ass_out, is_shorts=True, language="ta")
            self.assertTrue(ass_out.exists())
            content = ass_out.read_text(encoding="utf-8")
            self.assertIn("[Script Info]", content)
            self.assertIn("Dialogue: 0,", content)
            self.assertTrue("Mukta Malar" in content or "Noto Sans Tamil" in content)

    def test_json_ingestion(self):
        from iram_video.cli import load_prompt_from_json
        sample_json = Path("/home/apravint/resources/video-creator-stacks.json")
        if sample_json.exists():
            prompt, style = load_prompt_from_json(sample_json)
            self.assertIn("Video Creator Projects", prompt)
            self.assertTrue(len(prompt) > 20)

    def test_emoji_mixed_typography(self):
        img = Image.new("RGBA", (500, 100), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        fta, fen = get_fonts(24)
        sample = "🎬 AI சினிமா & Code 🚀 🔥"
        w = get_mixed_width(sample, fta, fen, draw)
        self.assertTrue(w > 30)
        end_x = draw_mixed_line(draw, 10, 10, sample, (255, 255, 255), fta, fen)
        self.assertTrue(end_x > 30)

    def test_scene_beats_extraction(self):
        from iram_video.b_roll import MediaFetcher
        sample_scene = {
            "narration": "In 2021, the James Webb Space Telescope launched into deep space. It unfolded a massive gold mirror to capture distant infrared light.",
            "duration": 12.0
        }
        beats = MediaFetcher.extract_scene_beats(sample_scene, 12.0)
        self.assertTrue(len(beats) >= 2)
        total_dur = sum(b["duration"] for b in beats)
        self.assertAlmostEqual(total_dur, 12.0, delta=0.1)

    def test_ai_video_engine_fallback_chain(self):
        from iram_video.ai_video import AIVideoEngine
        out_dir = Path("/tmp/test_ai_video_fallback")
        out_dir.mkdir(parents=True, exist_ok=True)
        sample_beat = {
            "query": "solar flare space",
            "phrase": "A colossal solar flare erupts from the sun.",
            "duration": 4.5,
            "ai_prompt": "Cinematic 8k shot of a solar flare erupting into dark space"
        }
        # With veo requested, if quota limit hit or unbilled, it MUST gracefully fallback and return a valid file
        result_file = AIVideoEngine.fetch_or_generate_beat_media(
            sample_beat, out_dir, "test_01", is_shorts=False, provider="veo"
        )
        self.assertTrue(result_file.exists())
        self.assertTrue(result_file.stat().st_size > 1000)

    def test_anchor_phrase_extraction(self):
        from iram_video.b_roll import MediaFetcher
        ta_topic = "சென்னை மெட்ரோ இரண்டாம் கட்ட திட்டம் (Phase 2): 116 கி.மீ தொலைவு | Chennai Metro Phase 2 Launch"
        anchor = MediaFetcher.extract_anchor_phrase(ta_topic)
        self.assertIn("Chennai Metro", anchor)

        en_topic = "Quantum Computing Architecture and Qubits"
        en_anchor = MediaFetcher.extract_anchor_phrase(en_topic)
        self.assertIn("Quantum Computing", en_anchor)

    def test_noise_filtering(self):
        from iram_video.b_roll import MediaFetcher
        # Green fruit Brazilian forest must be flagged as noise
        is_noise_forest = MediaFetcher.is_noise_candidate(
            "File:Corredor Florestal - Pontal do Paranapanema.jpg",
            query="corridor",
            topic="Chennai Metro"
        )
        self.assertTrue(is_noise_forest)

        # Japanese bus with cartoon face must be flagged as noise
        is_noise_bus = MediaFetcher.is_noise_candidate(
            "File:Nagaokakyo Happy Bus.jpg",
            query="feeder",
            topic="Chennai Metro"
        )
        self.assertTrue(is_noise_bus)

        # Authentic Chennai Metro train/feeder must NOT be flagged as noise
        is_noise_metro = MediaFetcher.is_noise_candidate(
            "File:Chennai metro feeder service.jpg",
            query="feeder",
            topic="Chennai Metro"
        )
        self.assertFalse(is_noise_metro)

    def test_duplicate_media_avoidance(self):
        from iram_video.b_roll import MediaFetcher
        MediaFetcher.reset_session()
        self.assertEqual(len(MediaFetcher._used_urls), 0)
        MediaFetcher._used_urls.add("https://example.com/photo1.jpg")
        self.assertIn("https://example.com/photo1.jpg", MediaFetcher._used_urls)
        MediaFetcher.reset_session()
        self.assertEqual(len(MediaFetcher._used_urls), 0)

    def test_voice_synth_duration_guard(self):
        from iram_video.voice import VoiceSynthesizer
        vs = VoiceSynthesizer()
        # Non-existent or empty file should safely return default 3.0 seconds rather than crash
        dur = vs.get_duration(Path("/tmp/non_existent_audio_file.mp3"))
        self.assertAlmostEqual(dur, 3.0)

    def test_thumbnail_generation(self):
        from iram_video.thumbnail import generate_thumbnail
        with tempfile.TemporaryDirectory() as td:
            thumb_out = Path(td) / "test_thumb.png"
            theme = {"bg": [10, 14, 24], "accent": [0, 229, 255], "secondary": [168, 85, 247]}
            generate_thumbnail(
                title="சென்னை மெட்ரோ Phase 2 Launch",
                bullets=["116 km Network", "3 New Corridors", "Driverless Trains"],
                theme=theme,
                output_path=thumb_out,
                is_shorts=False,
                is_cinema=False,
                character="robot"
            )
            self.assertTrue(thumb_out.exists())
            self.assertTrue(thumb_out.stat().st_size > 1000)

    def test_geographic_noise_rejection(self):
        from iram_video.b_roll import MediaFetcher
        # Images from Beijing or Shanghai must be rejected when topic is Chennai/India
        self.assertTrue(MediaFetcher.is_noise_candidate("File:Beijing Subway Line 1 Train.jpg", topic="Chennai Metro"))
        self.assertTrue(MediaFetcher.is_noise_candidate("File:Shanghai Metro Phase 2.jpg", topic="Chennai Metro"))
        self.assertTrue(MediaFetcher.is_noise_candidate("File:Tokyo Minibus.jpg", topic="Chennai Metro"))
        self.assertFalse(MediaFetcher.is_noise_candidate("File:Chennai Metro Phase2 trainset.jpg", topic="Chennai Metro"))

    def test_semantic_beat_classifier(self):
        from iram_video.motion_canvas import classify_semantic_beat

        # Metric phrases
        b_metric = classify_semantic_beat("சென்னை மெட்ரோ இரண்டாம் கட்டம் 116 கி.மீ தொலைவில் 118 நிலையங்களுடன் அமைகிறது.")
        self.assertEqual(b_metric["beat_type"], "metric_card")
        self.assertEqual(b_metric["metric_number"], 116.0)

        # Route / Corridor phrases
        b_route3 = classify_semantic_beat("பாதை 3 மாதவரம் முதல் சிப்காட் வரை அமைகிறது.")
        self.assertEqual(b_route3["beat_type"], "route_map")
        self.assertEqual(len(b_route3["stations"]), 7)

        b_route4 = classify_semantic_beat("Corridor 4 connects Lighthouse to Poonamallee across 26.1 km.")
        self.assertEqual(b_route4["beat_type"], "route_map")

        # General real media phrases
        b_real = classify_semantic_beat("ஓட்டுநர் இல்லாத நவீன ரயில்கள் சென்னை மக்களின் பயணத்தை எளிதாக்கும்.")
        self.assertEqual(b_real["beat_type"], "real_media")

    def test_motion_canvas_rendering(self):
        from iram_video.motion_canvas import MotionCanvas, classify_semantic_beat
        from iram_video.b_roll import MediaFetcher
        with tempfile.TemporaryDirectory() as td:
            out_metric = Path(td) / "metric.mp4"
            out_route = Path(td) / "route.mp4"
            out_code = Path(td) / "code.mp4"
            out_frame = Path(td) / "frame.jpg"

            b_m = classify_semantic_beat("116 கி.மீ மற்றும் 118 நிலையங்கள்")
            MotionCanvas.render_metric_card(b_m, out_metric, duration=1.0)
            self.assertTrue(out_metric.exists())
            self.assertTrue(out_metric.stat().st_size > 1000)

            b_r = classify_semantic_beat("பாதை 3 மாதவரம் முதல் சிப்காட் வரை")
            MotionCanvas.render_route_map(b_r, out_route, duration=1.0)
            self.assertTrue(out_route.exists())
            self.assertTrue(out_route.stat().st_size > 1000)

            b_c = classify_semantic_beat("Modern Java and Spring Boot microservices with virtual threads")
            self.assertEqual(b_c["beat_type"], "code_card")
            MotionCanvas.render_code_card(b_c, out_code, duration=1.0)
            self.assertTrue(out_code.exists())
            self.assertTrue(out_code.stat().st_size > 1000)

            # Test clean documentary frame generation (editorial typography & code window, NO spirals)
            MediaFetcher.create_clean_documentary_frame("Modern Java Spring Architecture", out_frame)
            self.assertTrue(out_frame.exists())
            self.assertTrue(out_frame.stat().st_size > 5000)

    def test_sentence_boundary_extraction_from_words(self):
        from iram_video.voice import extract_sentence_boundaries_from_words
        sample_words = [
            {"word": "வணக்கம்.", "start": 0.1, "end": 0.8, "duration": 0.7},
            {"word": "இது", "start": 1.4, "end": 1.7, "duration": 0.3},
            {"word": "மெட்ரோ.", "start": 1.8, "end": 2.4, "duration": 0.6}
        ]
        sentences = extract_sentence_boundaries_from_words(sample_words, "வணக்கம். இது மெட்ரோ.")
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0]["text"], "வணக்கம்.")
        self.assertEqual(sentences[1]["text"], "இது மெட்ரோ.")
        self.assertAlmostEqual(sentences[0]["start"], 0.1)
        self.assertAlmostEqual(sentences[1]["start"], 1.4)

    def test_sidechain_ducking_filter_syntax(self):
        import subprocess
        fc = (
            "[1:a]volume=0.28[bg];"
            "[bg][0:a]sidechaincompress=threshold=0.08:ratio=5:attack=80:release=380[ducked];"
            "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-filter_complex", fc,
            "-map", "[aout]",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_smoothstep_zoompan_syntax(self):
        import subprocess
        d = 30
        zp = f"zoompan=z='1.0+0.10*(3*pow(on/{d},2)-2*pow(on/{d},3))':d={d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=640x360:fps=30"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=640x360:d=1",
            "-vf", zp,
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
    def test_ebu_r128_broadcast_mastering_syntax(self):
        import subprocess
        fc = (
            "[0:a]highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5,loudnorm=I=-16:TP=-1.5:LRA=10[voice_master];"
            "[1:a]lowpass=f=4000,volume=0.20[bg_clean];"
            "[bg_clean][voice_master]sidechaincompress=threshold=0.08:ratio=5:attack=80:release=380[ducked];"
            "[voice_master][ducked]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-filter_complex", fc,
            "-map", "[aout]",
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_retention_progress_bar_syntax(self):
        import subprocess
        vf = (
            "drawbox=x=0:y=1906:w=iw:h=14:color=black@0.45:t=fill,"
            "drawbox=x=0:y=1906:w='min(iw,iw*(t/5.0))':h=14:color=white@0.85:t=fill"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1",
            "-vf", vf,
            "-f", "null", "-"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)

    def test_named_camera_choreography_syntax(self):
        import subprocess
        d = 30
        for cam in ["zoom_in", "zoom_out", "pan_left", "pan_right"]:
            if cam == "zoom_in":
                zp = f"zoompan=z='1.0+0.12*(3*pow(on/{d},2)-2*pow(on/{d},3))':d={d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=640x360:fps=30"
            elif cam == "zoom_out":
                zp = f"zoompan=z='1.12-0.12*(3*pow(on/{d},2)-2*pow(on/{d},3))':d={d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=640x360:fps=30"
            elif cam == "pan_left":
                zp = f"zoompan=z=1.12:d={d}:x='(iw-iw/zoom)*(1-(3*pow(on/{d},2)-2*pow(on/{d},3)))':y='ih/2-(ih/zoom/2)':s=640x360:fps=30"
            else:
                zp = f"zoompan=z=1.12:d={d}:x='(iw-iw/zoom)*(3*pow(on/{d},2)-2*pow(on/{d},3))':y='ih/2-(ih/zoom/2)':s=640x360:fps=30"

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=640x360:d=1",
                "-vf", zp,
                "-f", "null", "-"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

    def test_bundled_mukta_malar_font_exists(self):
        from pathlib import Path
        font_file = Path(__file__).parent.parent / "assets" / "fonts" / "MuktaMalar-Bold.ttf"
        self.assertTrue(font_file.exists())
        self.assertTrue(font_file.stat().st_size > 100000)

    def test_shotcraft_recipes(self):
        from iram_video.shotcraft import SHOT_RECIPES, get_shot_recipe, build_recipe_filter
        self.assertIn("hero_reveal", SHOT_RECIPES)
        self.assertIn("speed_ramp", SHOT_RECIPES)
        self.assertIn("macro_orbit", SHOT_RECIPES)
        recipe = get_shot_recipe("hero_reveal")
        self.assertIn("lens", recipe)
        f_str = build_recipe_filter("hero_reveal", frames=30, w=1920, h=1080, fps=30)
        self.assertIn("zoompan", f_str)

    def test_brag_harvester(self):
        from iram_video.brag import BragHarvester, ViralHookGenerator
        from pathlib import Path
        repo_dir = Path(__file__).parent.parent
        info = BragHarvester.inspect_repository(repo_dir)
        self.assertIn("name", info)
        self.assertIn("Python", info.get("tech_stack", []))
        prompt = BragHarvester.craft_launch_prompt(info)
        self.assertTrue(len(prompt) > 30)
        hooks = ViralHookGenerator.generate_variants("Distributed Consensus")
        self.assertEqual(len(hooks), 3)

    def test_drama_and_character_consistency(self):
        from iram_video.drama import CharacterAnchorRegistry, DramaTensionCurve
        registry = CharacterAnchorRegistry()
        char = registry.register_character(
            "Maya",
            role="Cyber Detective",
            appearance="Silver hair with cybernetic neon blue eye",
            wardrobe="Black carbon-fiber trenchcoat"
        )
        self.assertEqual(char["name"], "Maya")
        anchor = registry.get_prompt_anchor("Maya")
        self.assertIn("Silver hair", anchor)

        scenes = [{"id": f"sc_{i}", "heading": f"Scene {i}"} for i in range(5)]
        annotated = DramaTensionCurve.calculate_tension_curve(scenes)
        self.assertEqual(len(annotated), 5)
        self.assertTrue(annotated[3]["tension_score"] >= annotated[0]["tension_score"])

    def test_steady_camera_and_clean_color_palette(self):
        from iram_video.real_compiler import RealVideoCompiler
        from iram_video.renderer import SlideRenderer
        from iram_video.shotcraft import SHOT_RECIPES
        from iram_video.subtitles import SUBTITLE_PALETTES

        # Verify RealVideoCompiler defaults to steady camera
        compiler = RealVideoCompiler(Path("/tmp"), is_shorts=False)
        self.assertTrue(compiler.steady_camera)

        # Verify shot recipes have subtle steady zoom factor <= 1.05
        hero_filter = SHOT_RECIPES["hero_reveal"]["ffmpeg_filter"]
        self.assertIn("1.03", hero_filter)
        self.assertNotIn("1.25", hero_filter)

        # Verify SlideRenderer defaults to clean slate and corporate blue, not neon cyan
        sr = SlideRenderer()
        self.assertNotEqual(sr.accent_color[:3], (0, 229, 255))
        self.assertEqual(sr.accent_color[:3], (59, 130, 246))

        # Verify subtitles have clean corporate palettes
        self.assertIn("blue", SUBTITLE_PALETTES)
        self.assertIn("slate", SUBTITLE_PALETTES)

    def test_soundscape_advisor(self):
        from iram_video.soundscape import SoundscapeAdvisor
        advice = SoundscapeAdvisor.advise_soundscape("Documentary about modern autonomous AI systems")
        self.assertIsInstance(advice, dict)
        self.assertIn("tempo_bpm", advice)
        self.assertTrue(50 <= advice["tempo_bpm"] <= 140)
        self.assertIn("foley_cues", advice)
        self.assertIn("bgm_style", advice)
        self.assertIn("bgm_mood", advice)
        self.assertIn("instruments", advice)
        self.assertTrue(len(advice["foley_cues"]) >= 1)

    def test_mcp_server_protocol(self):
        from iram_video.mcp_server import MCPServer
        server = MCPServer()

        # 1. Test initialize
        init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        init_res = server.handle_request(init_req)
        self.assertEqual(init_res["id"], 1)
        self.assertEqual(init_res["result"]["serverInfo"]["name"], "iram-video")

        # 2. Test tools/list
        list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        list_res = server.handle_request(list_req)
        tools = list_res["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("create_video", tool_names)
        self.assertIn("extend_video", tool_names)
        self.assertIn("suggest_soundscape", tool_names)
        self.assertIn("search_stock_broll", tool_names)
        self.assertIn("render_metric_card", tool_names)

        # 3. Test tools/call suggest_soundscape
        call_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "suggest_soundscape",
                "arguments": {"scene_prompt": "An executive boardroom discussing quarterly tech growth"}
            }
        }
        call_res = server.handle_request(call_req)
        self.assertEqual(call_res["id"], 3)
        self.assertFalse(call_res["result"].get("isError", False))
        content_txt = call_res["result"]["content"][0]["text"]
        import json
        parsed_soundscape = json.loads(content_txt)
        self.assertIn("tempo_bpm", parsed_soundscape)

    def test_pexels_orientation_support(self):
        from iram_video.b_roll import MediaFetcher
        # Ensure search_pexels accepts orientation and doesn't crash without credentials
        results_landscape = MediaFetcher.search_pexels("coding", require_video=True, orientation="landscape")
        self.assertIsInstance(results_landscape, list)
        results_portrait = MediaFetcher.search_pexels("coding", require_video=True, orientation="portrait")
        self.assertIsInstance(results_portrait, list)

    def test_extend_video_api(self):
        from iram_video.ai_video import AIVideoEngine
        self.assertTrue(hasattr(AIVideoEngine, "extend_video"))
        self.assertTrue(callable(AIVideoEngine.extend_video))

if __name__ == "__main__":
    unittest.main()
