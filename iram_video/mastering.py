"""
Shared output format and final mastering pass for the slide and footage compilers.
Owns frame dimensions, FFmpeg error reporting, grading, progress bar, subtitles and audio mix.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .color_grade import get_color_grade_filter
from .transitions import TransitionEngine

ASPECT_DIMENSIONS = {
    "16:9": ((1920, 1080), (3840, 2160)),
    "9:16": ((1080, 1920), (2160, 3840)),
    "1:1": ((1080, 1080), (2160, 2160)),
    "4:5": ((1080, 1350), (2160, 2700)),
    "2.39:1": ((2560, 1072), (3840, 1608)),
}

STANDARD_BT709_ARGS = [
    "-pix_fmt", "yuv420p",
    "-colorspace", "bt709",
    "-color_primaries", "bt709",
    "-color_trc", "bt709",
    "-color_range", "tv",
    "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709",
]


def resolve_dimensions(aspect_ratio: str = "16:9", is_shorts: bool = False, is_4k: bool = False) -> Tuple[int, int]:
    """Returns the (width, height) of the master frame for an aspect ratio."""
    key = aspect_ratio if aspect_ratio in ASPECT_DIMENSIONS else ("9:16" if is_shorts else "16:9")
    if is_shorts and key not in ("1:1", "4:5"):
        key = "9:16"
    return ASPECT_DIMENSIONS[key][1 if is_4k else 0]


def run_ffmpeg(cmd: List[str]) -> None:
    """Runs FFmpeg and raises with the tail of its stderr, so failures can be diagnosed."""
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, errors="replace")
    if res.returncode != 0:
        tail = "\n".join((res.stderr or "").strip().splitlines()[-8:])
        raise RuntimeError(f"FFmpeg exited with code {res.returncode}:\n{tail}")


def master_video(
    raw_concat: Path,
    output_path: Path,
    scenes: List[Dict[str, Any]],
    work_dir: Path,
    width: int,
    height: int,
    is_shorts: bool = False,
    bg_music: Optional[Path] = None,
    music_volume: float = 0.20,
    burn_subtitles: bool = False,
    language: str = "en",
    palette_key: str = "auto",
    color_grade: str = "clean",
) -> None:
    """Grades, adds the progress bar and subtitles, mixes audio and writes the final MP4."""
    # Imported here because subtitles -> renderer -> mastering would otherwise be circular
    from .subtitles import KineticSubtitleGenerator

    total_duration = TransitionEngine.get_clip_duration(raw_concat)
    # Transitions overlap neighbouring clips, so scene starts land earlier than their summed durations.
    summed = sum(float(s.get("duration", 4.0)) for s in scenes)
    scene_overlap = max(0.0, summed - total_duration) / max(1, len(scenes) - 1)

    graph = []
    cur_v = "[0:v]"

    pre_filters = []
    cg_filter = get_color_grade_filter(color_grade)
    if cg_filter and cg_filter != "null":
        pre_filters.append(cg_filter)
    if pre_filters:
        graph.append(f"{cur_v}{','.join(pre_filters)}[v_graded]")
        cur_v = "[v_graded]"

    if is_shorts:
        # Retention bar slides in from the left. drawbox cannot animate: its 't' means thickness.
        bar_h = max(8, height // 137)
        graph.append(f"color=c=black@0.45:s={width}x{bar_h}:r=30,format=rgba[bar_track]")
        graph.append(f"color=c=white@0.85:s={width}x{bar_h}:r=30,format=rgba[bar_fill]")
        graph.append(f"{cur_v}[bar_track]overlay=x=0:y=H-h:shortest=1[v_track]")
        graph.append(f"[v_track][bar_fill]overlay=x='-W+W*t/{max(0.1, total_duration):.3f}':y=H-h:shortest=1[v_bar]")
        cur_v = "[v_bar]"

    post_filters = []
    if burn_subtitles:
        ass_path = work_dir / "kinetic_subtitles.ass"
        KineticSubtitleGenerator.generate_ass(
            scenes, ass_path, is_shorts=is_shorts, language=language, palette_key=palette_key, scene_overlap=scene_overlap
        )
        if ass_path.exists():
            ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")
            fonts_dir = Path(__file__).parent.parent / "assets" / "fonts"
            if fonts_dir.exists():
                fonts_dir_escaped = str(fonts_dir).replace("\\", "/").replace(":", "\\:")
                post_filters.append(f"ass=filename={ass_escaped}:fontsdir={fonts_dir_escaped}:shaping=1")
            else:
                post_filters.append(f"ass={ass_escaped}")
    post_filters.extend(["setsar=1", "format=yuv420p"])
    graph.append(f"{cur_v}{','.join(post_filters)}[vout]")

    # Broadcast Studio Audio Mastering (EBU R128 + Vocal Presence EQ + BGM Low-pass Ducking)
    audio_inputs = []
    if bg_music and Path(bg_music).exists():
        music_vol = max(0.02, min(1.0, float(music_volume)))
        graph.append(
            f"[0:a]highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5[voice_raw];"
            f"[voice_raw]loudnorm=I=-15:TP=-1.5:LRA=9[voice_master];"
            f"[1:a]lowpass=f=4000,volume={music_vol:.2f}[bg_clean];"
            f"[bg_clean][voice_master]sidechaincompress=threshold=0.08:ratio=5:attack=80:release=380[ducked];"
            f"[voice_master][ducked]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-14:LRA=7:TP=-1.5[aout]"
        )
        # Loop the track so music shorter than the video does not cut out partway through.
        audio_inputs = ["-stream_loop", "-1", "-i", str(bg_music)]
    else:
        graph.append("[0:a]highpass=f=80,equalizer=f=3200:t=q:w=1.2:g=2.5,loudnorm=I=-14:LRA=7:TP=-1.5[aout]")

    # CRF with a ceiling only: adding -b:v would switch x264 to bitrate mode and ignore the CRF.
    max_rate, buf_size = ("60M", "90M") if max(width, height) > 2000 else ("20M", "30M")
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", str(raw_concat),
        *audio_inputs,
        "-filter_complex", ";".join(graph),
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", max_rate, "-bufsize", buf_size,
        *STANDARD_BT709_ARGS,
        "-c:a", "aac",
        "-b:a", "320k",
        "-ac", "2",
        "-ar", "48000",
        "-t", f"{total_duration:.3f}",
        "-movflags", "+faststart",
        str(output_path),
    ])
