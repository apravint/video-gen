import math
from pathlib import Path
from typing import List, Dict, Any, Optional

from .b_roll import MediaFetcher
from .audio_synth import synthesize_mood_track
from .ai_video import AIVideoEngine
from .motion_canvas import MotionCanvas, classify_semantic_beat
from .transitions import TransitionEngine
from .mastering import STANDARD_BT709_ARGS, master_video, resolve_dimensions, run_ffmpeg
from .state_machine import StateMachineAssetBuilder, AssetRenderState
from .soundscape_mixer import SoundscapeMixer

class RealVideoCompiler:
    """
    Compiles realistic documentary-style YouTube videos with AI video models (Veo/Wan/Kling),
    curated verified 4K B-roll photography, and deterministic programmatic motion graphics
    (route maps, metric cards, code cards, step cards, listicle countdowns, comparison cards).
    Features dynamic audio sidechain ducking, smoothstep Ken Burns easing, and xfade transitions.
    """

    def __init__(
        self,
        work_dir: Path,
        is_shorts: bool = False,
        is_cinema: bool = False,
        provider: str = "auto",
        global_topic: str = "",
        steady_camera: bool = True,
        start_image: Optional[Path] = None,
        aspect_ratio: str = "16:9",
        is_4k: bool = False
    ):
        self.work_dir = work_dir
        self.is_shorts = is_shorts
        self.is_cinema = is_cinema
        self.provider = provider
        self.global_topic = global_topic
        self.steady_camera = steady_camera
        self.start_image = start_image
        self.aspect_ratio = aspect_ratio
        self.is_4k = is_4k
        self.broll_dir = work_dir / "broll_media"
        self.broll_dir.mkdir(parents=True, exist_ok=True)
        self.shots_dir = work_dir / "real_shots"
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        self.state_machine = StateMachineAssetBuilder(self.work_dir / "checkpoints", max_retries=3, resume=True)

        self.w, self.h = resolve_dimensions(aspect_ratio, is_shorts, is_4k)
        # MotionCanvas cards render at 1920x1080 only; other frames would break the stream-copy concat.
        self.motion_cards = (self.w, self.h) == (1920, 1080)

    def _render_single_shot(self, beat: Dict[str, Any], duration: float, audio_file: Path, out_shot: Path, scene_idx: int) -> Path:
        beat_type = beat.get("beat_type", "real_media")
        query = beat.get("query") or beat.get("phrase") or self.global_topic or "documentary landscape"

        if self.motion_cards and beat_type in ("metric_card", "route_map", "code_card", "listicle_card", "step_card", "comparison_card"):
            tmp_video = self.shots_dir / f"tmp_single_{scene_idx:02d}.mp4"
            if beat_type == "metric_card":
                MotionCanvas.render_metric_card(beat, tmp_video, duration=duration, is_shorts=self.is_shorts)
            elif beat_type == "route_map":
                MotionCanvas.render_route_map(beat, tmp_video, duration=duration, is_shorts=self.is_shorts)
            elif beat_type == "code_card":
                MotionCanvas.render_code_card(beat, tmp_video, duration=duration, is_shorts=self.is_shorts)
            elif beat_type == "listicle_card":
                MotionCanvas.render_listicle_card(beat, tmp_video, duration=duration, is_shorts=self.is_shorts)
            elif beat_type == "step_card":
                MotionCanvas.render_step_card(beat, tmp_video, duration=duration, is_shorts=self.is_shorts)
            elif beat_type == "comparison_card":
                MotionCanvas.render_comparison_card(beat, tmp_video, duration=duration, is_shorts=self.is_shorts)

            cmd_mux = [
                "ffmpeg", "-y",
                "-i", str(tmp_video),
                "-i", str(audio_file),
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-t", f"{duration:.3f}",
                str(out_shot)
            ]
            run_ffmpeg(cmd_mux)
            return out_shot

        media_path = AIVideoEngine.fetch_or_generate_beat_media(
            beat, self.broll_dir, f"scene_{scene_idx:02d}", is_shorts=self.is_shorts, provider=self.provider, global_topic=self.global_topic
        )
        is_video = media_path.suffix.lower() in [".mp4", ".webm", ".mkv", ".mov"]

        if is_video:
            fc = (
                f"[0:v]scale={self.w}:{self.h}:force_original_aspect_ratio=increase,"
                f"crop={self.w}:{self.h},fps=30,setsar=1,format=yuv420p[v]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1", "-i", str(media_path),
                "-i", str(audio_file),
                "-filter_complex", fc,
                "-map", "[v]",
                "-map", "1:a",
                "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-tune", "film",
                "-c:a", "aac", "-b:a", "320k",
                *STANDARD_BT709_ARGS,
                "-t", f"{duration:.3f}",
                str(out_shot)
            ]
        else:
            try:
                from PIL import Image
                Image.MAX_IMAGE_PIXELS = 300_000_000
                with Image.open(media_path) as im:
                    if im.width > 3840 or im.height > 2160:
                        im.thumbnail((3840, 2160), Image.Resampling.LANCZOS)
                        im.convert("RGB").save(media_path, format="JPEG", quality=100, subsampling=0)
            except Exception:
                pass

            d_frames = int(duration * 30) + 30
            if self.steady_camera:
                sw, sh = ((int(self.w * 1.04) // 2) * 2, (int(self.h * 1.04) // 2) * 2)
                zp = f"zoompan=z='1.0+0.02*(3*pow(on/{d_frames},2)-2*pow(on/{d_frames},3))':d={d_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.w}x{self.h}:fps=30"
            else:
                sw, sh = ((int(self.w * 1.15) // 2) * 2, (int(self.h * 1.15) // 2) * 2)
                zp = f"zoompan=z='1.0+0.05*(3*pow(on/{d_frames},2)-2*pow(on/{d_frames},3))':d={d_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.w}x{self.h}:fps=30"
            fc = (
                f"[0:v]scale={sw}:{sh}:force_original_aspect_ratio=increase,"
                f"crop={sw}:{sh},"
                f"{zp},"
                f"scale={self.w}:{self.h},setsar=1,"
                f"fade=t=in:st=0:d=0.35,fade=t=out:st={max(0.1, duration - 0.35):.2f}:d=0.35,"
                f"format=yuv420p[v]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(media_path),
                "-i", str(audio_file),
                "-filter_complex", fc,
                "-map", "[v]",
                "-map", "1:a",
                "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-tune", "animation",
                "-c:a", "aac", "-b:a", "320k",
                *STANDARD_BT709_ARGS,
                "-t", f"{duration:.3f}",
                str(out_shot)
            ]

        run_ffmpeg(cmd)
        return out_shot

    def render_shot(self, scene: Dict[str, Any], scene_idx: int) -> Path:
        out_shot = self.shots_dir / f"shot_{scene_idx:02d}.mp4"
        asset_id = f"shot_{scene_idx:02d}"

        def _do_render() -> Path:
            duration = float(scene.get("duration", 4.0))
            audio_file = Path(scene["audio_file"])
            beats = MediaFetcher.extract_scene_beats(scene, duration, global_topic=self.global_topic)
            if scene_idx == 0 and self.start_image and beats:
                beats[0]["start_image"] = str(self.start_image)
            if len(beats) <= 1:
                beat = beats[0] if beats else {"query": self.global_topic, "duration": duration}
                return self._render_single_shot(beat, duration, audio_file, out_shot, scene_idx)

            beat_clips = []
            for b_idx, beat in enumerate(beats):
                b_dur = float(beat["duration"])
                beat_clip_path = self.shots_dir / f"beat_{scene_idx:02d}_{b_idx:02d}.mp4"
                beat_type = beat.get("beat_type", "real_media")
                if self.motion_cards:
                    if beat_type == "metric_card":
                        MotionCanvas.render_metric_card(beat, beat_clip_path, duration=b_dur, is_shorts=self.is_shorts)
                        beat_clips.append(beat_clip_path)
                        continue
                    if beat_type == "route_map":
                        MotionCanvas.render_route_map(beat, beat_clip_path, duration=b_dur, is_shorts=self.is_shorts)
                        beat_clips.append(beat_clip_path)
                        continue
                    if beat_type == "code_card":
                        MotionCanvas.render_code_card(beat, beat_clip_path, duration=b_dur, is_shorts=self.is_shorts)
                        beat_clips.append(beat_clip_path)
                        continue
                    if beat_type == "listicle_card":
                        MotionCanvas.render_listicle_card(beat, beat_clip_path, duration=b_dur, is_shorts=self.is_shorts)
                        beat_clips.append(beat_clip_path)
                        continue
                    if beat_type == "step_card":
                        MotionCanvas.render_step_card(beat, beat_clip_path, duration=b_dur, is_shorts=self.is_shorts)
                        beat_clips.append(beat_clip_path)
                        continue
                    if beat_type == "comparison_card":
                        MotionCanvas.render_comparison_card(beat, beat_clip_path, duration=b_dur, is_shorts=self.is_shorts)
                        beat_clips.append(beat_clip_path)
                        continue

                media_path = AIVideoEngine.fetch_or_generate_beat_media(
                    beat, self.broll_dir, f"{scene_idx:02d}_{b_idx:02d}", is_shorts=self.is_shorts, is_cinema=self.is_cinema, provider=self.provider, global_topic=self.global_topic
                )
                is_video = media_path.suffix.lower() in [".webm", ".mp4", ".mkv", ".mov"]
                if is_video:
                    fc = f"[0:v]scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h},fps=30,setsar=1,format=yuv420p[v]"
                    cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(media_path), "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", *STANDARD_BT709_ARGS, "-t", f"{b_dur:.3f}", "-an", str(beat_clip_path)]
                else:
                    d_frames = int(b_dur * 30) + 15
                    sw, sh = ((int(self.w * 1.04) // 2) * 2, (int(self.h * 1.04) // 2) * 2)
                    zp = f"zoompan=z='1.0+0.02*(3*pow(on/{d_frames},2)-2*pow(on/{d_frames},3))':d={d_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.w}x{self.h}:fps=30"
                    fc = (
                        f"[0:v]scale={sw}:{sh}:force_original_aspect_ratio=increase,"
                        f"crop={sw}:{sh},"
                        f"{zp},"
                        f"scale={self.w}:{self.h},setsar=1,"
                        f"fade=t=in:st=0:d=0.25,fade=t=out:st={max(0.1, b_dur-0.25):.2f}:d=0.25,"
                        f"format=yuv420p[v]"
                    )
                    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(media_path), "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-preset", "medium", "-crf", "18", *STANDARD_BT709_ARGS, "-t", f"{b_dur:.3f}", "-an", str(beat_clip_path)]
                run_ffmpeg(cmd)
                beat_clips.append(beat_clip_path)

            concat_txt = self.shots_dir / f"scene_{scene_idx:02d}_concat.txt"
            with open(concat_txt, "w") as f:
                for bc in beat_clips:
                    f.write(f"file '{bc.resolve()}'\n")
            raw_scene_video = self.shots_dir / f"scene_{scene_idx:02d}_raw_video.mp4"
            cmd_cat = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(raw_scene_video)]
            run_ffmpeg(cmd_cat)

            cmd_mux = ["ffmpeg", "-y", "-i", str(raw_scene_video), "-i", str(audio_file), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-t", f"{duration:.3f}", str(out_shot)]
            run_ffmpeg(cmd_mux)
            return out_shot

        def _fallback_render() -> Path:
            duration = float(scene.get("duration", 4.0))
            audio_file = Path(scene["audio_file"])
            fallback_beat = {
                "beat_type": "real_media",
                "query": scene.get("heading", self.global_topic),
                "phrase": scene.get("narration", "")[:120],
                "heading": scene.get("heading", self.global_topic)
            }
            return self._render_single_shot(fallback_beat, duration, audio_file, out_shot, scene_idx)

        return self.state_machine.render_asset_with_resilience(
            asset_id,
            out_shot,
            tier1_fn=_do_render,
            tier2_fn=_fallback_render
        )

    def compile_real_video(
        self,
        scenes: List[Dict[str, Any]],
        bg_music: Optional[Path],
        output_path: Path,
        global_topic: str = "",
        burn_subtitles: bool = False,
        language: str = "en",
        palette_key: str = "auto",
        transition: str = "fade",
        color_grade: str = "clean",
        music_volume: float = 0.20,
        soundscape_playlist: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Compiles full documentary video from real B-roll shots and programmatic motion graphics
        with dynamic audio sidechain compression ducking and cinematic transitions.
        """
        if global_topic:
            self.global_topic = global_topic
        MediaFetcher.reset_session()
        shot_paths = []
        total_duration = 0.0

        for idx, scene in enumerate(scenes):
            shot = self.render_shot(scene, idx)
            shot_paths.append(shot)
            total_duration += float(scene.get("duration", 4.0))

        # Join shots with TransitionEngine (xfade transitions or clean fallback concat)
        raw_concat = self.work_dir / "real_raw.mp4"
        TransitionEngine.join_clips_with_transitions(
            shot_paths,
            raw_concat,
            transition=transition,
            trans_duration=0.45,
            work_dir=self.work_dir
        )

        if soundscape_playlist and total_duration > 0:
            bg_music = self._layer_soundscape(soundscape_playlist, bg_music, total_duration)

        master_video(
            raw_concat,
            output_path,
            scenes,
            self.work_dir,
            self.w,
            self.h,
            is_shorts=self.is_shorts,
            bg_music=bg_music,
            music_volume=music_volume,
            burn_subtitles=burn_subtitles,
            language=language,
            palette_key=palette_key,
            color_grade=color_grade,
        )

    def _layer_soundscape(self, soundscape_playlist: List[Dict[str, Any]], bg_music: Optional[Path], total_duration: float) -> Optional[Path]:
        """Mixes the ambient layer under the music track, or uses it alone when there is no music."""
        layered_soundscape_wav = self.work_dir / "soundscape_mixed_bg.wav"
        primary_amb = soundscape_playlist[0].get("type", "room_tone")
        amb_path = self.work_dir / "ambient_layer.wav"
        SoundscapeMixer.generate_procedural_ambient(primary_amb, total_duration + 5.0, amb_path)
        if not (bg_music and bg_music.exists()):
            return amb_path
        cmd_premix = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(bg_music),
            "-stream_loop", "-1", "-i", str(amb_path),
            "-filter_complex", "[0:a]volume=1.0[bg];[1:a]volume=0.35[amb];[bg][amb]amix=inputs=2:duration=first:dropout_transition=2[outm]",
            "-map", "[outm]",
            "-c:a", "pcm_s16le",
            "-t", f"{total_duration + 2.0:.2f}",
            str(layered_soundscape_wav)
        ]
        try:
            run_ffmpeg(cmd_premix)
            if layered_soundscape_wav.exists() and layered_soundscape_wav.stat().st_size > 1000:
                return layered_soundscape_wav
        except RuntimeError as e:
            print(f"   ⚠️ Could not layer ambient sound: {e}")
        return bg_music
