import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from .characters import CharacterRenderer
from .transitions import TransitionEngine
from .mastering import master_video, resolve_dimensions, run_ffmpeg

class VideoCompiler:
    def __init__(self, work_dir: Path, is_cinema: bool = False, is_shorts: bool = False, character: Optional[str] = None, aspect_ratio: str = "16:9", is_4k: bool = False):
        self.work_dir = work_dir
        self.is_cinema = is_cinema
        self.is_shorts = is_shorts
        self.character = character
        self.aspect_ratio = aspect_ratio
        self.is_4k = is_4k
        self.clips_dir = work_dir / "clips"
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.sprites_dir = work_dir / "char_sprites"
        self.sprites_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare character sprites if requested
        self.has_character = bool(character and character.lower() not in ["none", "false"])
        if self.has_character:
            self._prepare_character_sprites()

    def _prepare_character_sprites(self):
        """Generates cycling animated sprite frames for the character mascot with high-DPI scaling."""
        char_name = self.character or "robot"
        cw, ch = (640, 840) if self.is_shorts else (760, 960)
        
        mouth_sequence = [0.0, 0.4, 0.85, 0.5, 0.15, 0.0]
        for i, mouth in enumerate(mouth_sequence):
            eye = "blink" if i == 4 else ("happy" if i in [2, 3] else "normal")
            bob = int(math.sin(i * 1.05) * 16)
            img = CharacterRenderer.render_character(
                char_name,
                w=cw,
                h=ch,
                mouth_open=mouth,
                eye_state=eye,
                pointing=True,
                bob_offset=bob
            )
            img.save(self.sprites_dir / f"sprite_{i:02d}.png")

    def render_clip(self, scene: Dict[str, Any], slide_img: Path) -> Path:
        sid = scene["id"]
        duration = scene["duration"]
        audio_file = Path(scene["audio_file"])
        out_clip = self.clips_dir / f"{sid}.mp4"

        framerate = 24 if self.is_cinema else 30
        width, height = resolve_dimensions(self.aspect_ratio, self.is_shorts, self.is_4k)
        fade_out = max(0, duration - 0.4)

        # Build sequential filter graph
        fc_parts = []
        cur_v = "[0:v]"

        # 1. Base motion (Cinematic subtle steady push-in)
        if self.is_cinema:
            d_frames = int(duration * framerate) + 48
            fc_parts.append(f"{cur_v}zoompan=z='min(zoom+0.0002,1.03)':d={d_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={framerate}[v_bg]")
            cur_v = "[v_bg]"

        # 2. Character overlay
        inputs = [
            "-loop", "1",
            "-framerate", str(framerate),
            "-i", str(slide_img)
        ]

        if self.has_character:
            inputs.extend([
                "-stream_loop", "-1",
                "-framerate", "8",
                "-i", str(self.sprites_dir / "sprite_%02d.png")
            ])
            pos_x = width - (400 if self.is_shorts else 420)
            pos_y = height - (480 if self.is_shorts else 540)
            fc_parts.append(f"{cur_v}[1:v]overlay={pos_x}:{pos_y}[v_char]")
            cur_v = "[v_char]"

        # 3. Cinema post-processing: 2.39:1 Anamorphic letterbox, color grading & film grain
        post_filters = []
        if self.is_cinema:
            if width > height and width / height < 2.0:
                # Hollywood 2.39:1 scope bars on a 16:9 frame; a 2.39:1 frame is already scope
                bar_h = (height - int(width / 2.39)) // 2
                post_filters.append(f"drawbox=y=0:h={bar_h}:color=black:t=fill")
                post_filters.append(f"drawbox=y=ih-{bar_h}:h={bar_h}:color=black:t=fill")
            elif self.is_shorts:
                # Scope accent bars for vertical video
                post_filters.append("drawbox=y=0:h=90:color=black:t=fill")
                post_filters.append("drawbox=y=ih-90:h=90:color=black:t=fill")

            # Teal & Orange cinematic color matrix
            post_filters.append("colorbalance=rs=0.08:gs=-0.04:bs=-0.08:rm=-0.04:gm=0.0:bm=0.12:rh=-0.04:gh=0.04:bh=0.18")
            # 35mm analog film grain (smooth gaussian noise)
            post_filters.append("noise=alls=3:allf=t")

        # 4. Fade in/out
        post_filters.append(f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out:.2f}:d=0.35")

        if post_filters:
            fc_parts.append(f"{cur_v}{','.join(post_filters)}[vfinal]")
            v_map = "[vfinal]"
        else:
            v_map = cur_v

        filter_complex = ";".join(fc_parts)

        # Voice processing (bass boost & cinematic room acoustics in cinema mode)
        af_opts = []
        if self.is_cinema:
            af_opts.extend([
                "-af", "bass=g=4:f=110,equalizer=f=3200:t=q:w=1:g=2,aecho=0.8:0.88:35:0.2"
            ])

        audio_idx = 2 if self.has_character else 1

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-i", str(audio_file),
            "-filter_complex", filter_complex,
            "-map", v_map,
            "-map", f"{audio_idx}:a",
            *af_opts,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "16",
            "-tune", "animation",
            "-c:a", "aac",
            "-b:a", "320k",
            "-ac", "2",
            "-pix_fmt", "yuv420p",
            "-t", f"{duration:.3f}",
            str(out_clip)
        ]

        run_ffmpeg(cmd)
        return out_clip

    def compile(
        self,
        scenes: List[Dict[str, Any]],
        slide_paths: List[Path],
        bg_music: Optional[Path],
        final_output: Path,
        language: str = "en",
        burn_subtitles: bool = True,
        palette_key: str = "auto",
        transition: str = "fade",
        color_grade: str = "clean",
        music_volume: float = 0.18
    ):
        clip_paths = []
        for scene, slide in zip(scenes, slide_paths):
            c = self.render_clip(scene, slide)
            clip_paths.append(c)

        raw_concat = self.work_dir / "raw_concat.mp4"
        TransitionEngine.join_clips_with_transitions(
            clip_paths,
            raw_concat,
            transition=transition,
            trans_duration=0.45,
            work_dir=self.work_dir
        )

        width, height = resolve_dimensions(self.aspect_ratio, self.is_shorts, self.is_4k)
        master_video(
            raw_concat,
            final_output,
            scenes,
            self.work_dir,
            width,
            height,
            is_shorts=self.is_shorts,
            bg_music=bg_music,
            music_volume=music_volume,
            burn_subtitles=burn_subtitles,
            language=language,
            palette_key=palette_key,
            color_grade=color_grade,
        )
