import math
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from .b_roll import MediaFetcher
from .audio_synth import synthesize_mood_track
from .ai_video import AIVideoEngine
from .motion_canvas import MotionCanvas, classify_semantic_beat
from .subtitles import KineticSubtitleGenerator
from .transitions import TransitionEngine
from .color_grade import get_color_grade_filter
from .state_machine import StateMachineAssetBuilder, AssetRenderState
from .soundscape_mixer import SoundscapeMixer

STANDARD_BT709_ARGS = [
    "-pix_fmt", "yuv420p",
    "-colorspace", "bt709",
    "-color_primaries", "bt709",
    "-color_trc", "bt709",
    "-color_range", "tv",
    "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709",
]

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

        if aspect_ratio == "1:1":
            self.w, self.h = (2160, 2160) if is_4k else (1080, 1080)
        elif aspect_ratio == "9:16" or is_shorts:
            self.w, self.h = (2160, 3840) if is_4k else (1080, 1920)
        elif aspect_ratio == "2.39:1":
            self.w, self.h = (3840, 1608) if is_4k else (2560, 1072)
        else:
            self.w, self.h = (3840, 2160) if is_4k else (1920, 1080)

    def _render_single_shot(self, beat: Dict[str, Any], duration: float, audio_file: Path, out_shot: Path, scene_idx: int) -> Path:
        beat_type = beat.get("beat_type", "real_media")
        query = beat.get("query") or beat.get("phrase") or self.global_topic or "documentary landscape"

        if not self.is_shorts and beat_type in ("metric_card", "route_map", "code_card", "listicle_card", "step_card", "comparison_card"):
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
            subprocess.run(cmd_mux, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
                if not self.is_shorts:
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
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                beat_clips.append(beat_clip_path)

            concat_txt = self.shots_dir / f"scene_{scene_idx:02d}_concat.txt"
            with open(concat_txt, "w") as f:
                for bc in beat_clips:
                    f.write(f"file '{bc.resolve()}'\n")
            raw_scene_video = self.shots_dir / f"scene_{scene_idx:02d}_raw_video.mp4"
            cmd_cat = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(raw_scene_video)]
            subprocess.run(cmd_cat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            cmd_mux = ["ffmpeg", "-y", "-i", str(raw_scene_video), "-i", str(audio_file), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-t", f"{duration:.3f}", str(out_shot)]
            subprocess.run(cmd_mux, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

        # Prepare Video Post-Filters: Retention Progress Bar, Color Grading & Kinetic Subtitles
        v_filters = []

        # Color grading preset
        cg_filter = get_color_grade_filter(color_grade)
        if cg_filter and cg_filter != "null":
            v_filters.append(cg_filter)

        if self.is_shorts and total_duration > 0:
            # 1. Shorts retention progress bar (14px track + clean neutral white fill along bottom)
            v_filters.append("drawbox=x=0:y=1906:w=iw:h=14:color=black@0.45:t=fill")
            v_filters.append(f"drawbox=x=0:y=1906:w='min(iw,iw*(t/{max(0.1, total_duration):.2f}))':h=14:color=white@0.85:t=fill")

        if burn_subtitles:
            ass_path = self.work_dir / "real_subtitles.ass"
            KineticSubtitleGenerator.generate_ass(scenes, ass_path, is_shorts=self.is_shorts, language=language, palette_key=palette_key)
            if ass_path.exists():
                ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")
                fonts_dir = Path(__file__).parent.parent / "assets" / "fonts"
                if fonts_dir.exists():
                    fonts_dir_escaped = str(fonts_dir).replace("\\", "/").replace(":", "\\:")
                    v_filters.append(f"ass=filename={ass_escaped}:fontsdir={fonts_dir_escaped}:shaping=1")
                else:
                    v_filters.append(f"ass={ass_escaped}")

        # Broadcast Studio Audio Mastering (EBU R128 + Vocal Presence EQ + BGM Low-pass Ducking)
        filter_complex_list = []
        maps = []

        if v_filters:
            filter_complex_list.append(f"[0:v]{','.join(v_filters)},setsar=1,format=yuv420p[vout]")
            maps.extend(["-map", "[vout]"])
            video_codec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-b:v", "15M", "-maxrate", "20M", "-bufsize", "30M", *STANDARD_BT709_ARGS]
        else:
            filter_complex_list.append("[0:v]setsar=1,format=yuv420p[vout]")
            maps.extend(["-map", "[vout]"])
            video_codec_args = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-b:v", "15M", "-maxrate", "20M", "-bufsize", "30M", *STANDARD_BT709_ARGS]
        if soundscape_playlist and total_duration > 0:
            layered_soundscape_wav = self.work_dir / "soundscape_mixed_bg.wav"
            primary_amb = soundscape_playlist[0].get("type", "room_tone") if soundscape_playlist else "room_tone"
            amb_path = self.work_dir / "ambient_layer.wav"
            SoundscapeMixer.generate_procedural_ambient(primary_amb, total_duration + 5.0, amb_path)
            if bg_music and bg_music.exists():
                cmd_premix = [
                    "ffmpeg", "-y",
                    "-i", str(bg_music),
                    "-stream_loop", "-1", "-i", str(amb_path),
                    "-filter_complex", "[0:a]volume=1.0[bg];[1:a]volume=0.35[amb];[bg][amb]amix=inputs=2:duration=first:dropout_transition=2[outm]",
                    "-map", "[outm]",
                    "-c:a", "pcm_s16le",
                    "-t", f"{total_duration + 2.0:.2f}",
                    str(layered_soundscape_wav)
                ]
                try:
                    subprocess.run(cmd_premix, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if layered_soundscape_wav.exists() and layered_soundscape_wav.stat().st_size > 1000:
                        bg_music = layered_soundscape_wav
                except Exception:
                    pass
            else:
                bg_music = amb_path

        if bg_music and bg_music.exists():
            vol_val = max(0.02, min(1.0, float(music_volume)))
            filter_complex_list.append(
                f"[0:a]highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5[voice_raw];"
                f"[voice_raw]loudnorm=I=-15:TP=-1.5:LRA=9[voice_master];"
                f"[1:a]lowpass=f=4000,volume={vol_val:.2f}[bg_clean];"
                f"[bg_clean][voice_master]sidechaincompress=threshold=0.08:ratio=5:attack=80:release=380[ducked];"
                f"[voice_master][ducked]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=7:TP=-1.5[aout]"
            )
            maps.extend(["-map", "[aout]"])
            audio_inputs = ["-i", str(bg_music)]
        else:
            filter_complex_list.append(
                "[0:a]highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5,loudnorm=I=-14:LRA=7:TP=-1.5[aout]"
            )
            maps.extend(["-map", "[aout]"])
            audio_inputs = []

        cmd_mix = [
            "ffmpeg", "-y",
            "-i", str(raw_concat),
            *audio_inputs,
            "-filter_complex", ";".join(filter_complex_list),
            *maps,
            *video_codec_args,
            "-c:a", "aac",
            "-b:a", "320k",
            "-ac", "2",
            "-ar", "48000",
            "-movflags", "+faststart",
            str(output_path)
        ]

        subprocess.run(cmd_mix, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
