import re
from pathlib import Path
from typing import List, Dict, Any
from .renderer import is_tamil_text

def format_ass_time(seconds: float) -> str:
    """Formats float seconds into ASS time format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def count_syllables(word: str) -> int:
    """Estimates syllable count using English vowel heuristic."""
    clean = re.sub(r'[^a-zA-Z]', '', word.lower())
    if not clean:
        return 1
    matches = re.findall(r'[aeiouy]+', clean)
    count = len(matches)
    if clean.endswith('e') and not clean.endswith('le') and count > 1:
        count -= 1
    return max(1, count)

def syllable_word_timings(text: str, duration_sec: float) -> List[Dict[str, Any]]:
    """
    Offline syllable-based word timing heuristic (ported from Automated-Video-Generator).
    When word boundaries are unavailable from the speech engine, estimates per-word timing
    from syllable counts (~165ms per syllable clamped to [120ms, 600ms], with 40ms inter-word gap).
    The sequence is normalized to precisely fill duration_sec.
    """
    words = text.split()
    if not words:
        return []
    total_ms = max(400.0, float(duration_sec) * 1000.0)

    weights = []
    for w in words:
        syl = count_syllables(w)
        raw_w = min(600.0, max(120.0, syl * 165.0))
        weights.append(raw_w)

    raw_total = sum(weights) + 40.0 * (len(words) - 1)
    if raw_total <= 0:
        raw_total = float(len(words))
    scale = total_ms / raw_total

    timings = []
    cur_ms = 0.0
    for i, w in enumerate(words):
        w_dur = weights[i] * scale
        start_sec = cur_ms / 1000.0
        end_sec = (cur_ms + w_dur) / 1000.0
        timings.append({
            "word": w,
            "start": round(start_sec, 3),
            "end": round(max(end_sec, start_sec + 0.08), 3),
            "duration": round(max(end_sec - start_sec, 0.08), 3)
        })
        cur_ms = cur_ms + w_dur + (40.0 * scale)

    if timings:
        timings[-1]["end"] = round(float(duration_sec), 3)
    return timings

def ffmpeg_drawtext_escape(text: str) -> str:
    """
    Escapes text for FFmpeg drawtext filtergraph strings (ported from Automated-Video-Generator).
    Replaces apostrophe with typographic ’ (U+2019) to prevent filtergraph leakage and crashes.
    """
    return (
        str(text)
        .replace("\\", "/")
        .replace(":", "\\:")
        .replace("'", "’")
        .replace('"', '\\"')
        .replace(",", "\\,")
    )

def format_srt_time(seconds: float) -> str:
    """Formats float seconds into SRT timestamp: HH:MM:SS,mmm"""
    total_ms = int(round(seconds * 1000))
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def format_vtt_time(seconds: float) -> str:
    """Formats float seconds into WebVTT timestamp: HH:MM:SS.mmm"""
    total_ms = int(round(seconds * 1000))
    h = total_ms // 3600000
    m = (total_ms % 3600000) // 60000
    s = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def export_srt(scenes: List[Dict[str, Any]], out_srt_path: Path) -> Path:
    """Serializes scenes into a standard SubRip (.srt) caption file."""
    out_srt_path = Path(out_srt_path)
    out_srt_path.parent.mkdir(parents=True, exist_ok=True)
    cues = []
    cursor = 0.0
    cue_idx = 1
    for scene in scenes:
        dur = float(scene.get("duration", 4.0))
        text = str(scene.get("narration") or scene.get("title") or "").strip()
        if text:
            start_str = format_srt_time(cursor)
            end_str = format_srt_time(cursor + dur)
            cues.append(f"{cue_idx}\n{start_str} --> {end_str}\n{text}\n")
            cue_idx += 1
        cursor += dur
    out_srt_path.write_text("\n".join(cues), encoding="utf-8")
    return out_srt_path

def export_vtt(scenes: List[Dict[str, Any]], out_vtt_path: Path) -> Path:
    """Serializes scenes into a standard WebVTT (.vtt) caption file."""
    out_vtt_path = Path(out_vtt_path)
    out_vtt_path.parent.mkdir(parents=True, exist_ok=True)
    cues = ["WEBVTT\n"]
    cursor = 0.0
    cue_idx = 1
    for scene in scenes:
        dur = float(scene.get("duration", 4.0))
        text = str(scene.get("narration") or scene.get("title") or "").strip()
        if text:
            start_str = format_vtt_time(cursor)
            end_str = format_vtt_time(cursor + dur)
            cues.append(f"{cue_idx}\n{start_str} --> {end_str}\n{text}\n")
            cue_idx += 1
        cursor += dur
    out_vtt_path.write_text("\n".join(cues), encoding="utf-8")
    return out_vtt_path

FONTS_DIR = Path(__file__).parent.parent / "assets" / "fonts"

SUBTITLE_PALETTES = {
    "gold": "\\c&H0000D7FF&",       # Vivid Gold / Amber (BGR)
    "white": "\\c&H00FFFFFF&",      # Crisp White
    "blue": "\\c&H00F6823B&",       # Corporate Blue (#3B82F6)
    "slate": "\\c&H00B8A394&",      # Slate Neutral (#94A3B8)
    "fire-red": "\\c&H000045FF&",   # Warm Crimson
    "hormozi": "\\c&H0000FFFF&",    # Yellow
    "neon-cyan": "\\c&H00FFFF00&",  # Cyan
    "neon-green": "\\c&H0000FF00&", # Emerald
    "magenta": "\\c&H00FF00FF&",    # Magenta / Fuchsia
    "purple": "\\c&H00D87093&",     # Soft Purple / Lavender
}

class KineticSubtitleGenerator:
    """Generates high-retention, word-by-word bouncy karaoke subtitles (Alex Hormozi / CapCut / MrBeast style)."""

    @staticmethod
    def generate_ass(
        scenes: List[Dict[str, Any]],
        out_ass_path: Path,
        is_shorts: bool = False,
        language: str = "en",
        palette_key: str = "auto",
        scene_overlap: float = 0.0
    ) -> Path:
        res_x = 1080 if is_shorts else 1920
        res_y = 1920 if is_shorts else 1080

        is_tamil = (language.lower() in ["ta", "tamil"])
        font_name = "Mukta Malar" if is_tamil else "JetBrains Mono"
        if is_shorts:
            font_size = 52
            margin_v = 700      # Golden sweet spot: centered at y=1220 (above TikTok/Shorts UI bar)
            lt_size = 28
            lt_margin_v = 90    # Upper chyron at y=90 (safely above slide headers and badges)
            lt_alignment = 7    # Top-Left alignment so it never touches subtitles
        else:
            font_size = 44
            margin_v = 180      # Broadcast bottom margin
            lt_size = 28
            lt_margin_v = 90    # Broadcast lower-third
            lt_alignment = 1    # Bottom-Left alignment

        # Primary Colors (AABBGGRR in ASS hex)
        if palette_key != "auto" and palette_key.lower() in SUBTITLE_PALETTES:
            accent_color = SUBTITLE_PALETTES[palette_key.lower()]
        else:
            accent_color = "\\c&H0000D7FF&" if is_shorts else "\\c&H00FFFFFF&"

        header = f"""[Script Info]
Title: IRAM Kinetic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {res_x}
PlayResY: {res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,3,2,60,60,{margin_v},1
Style: LowerThird,{font_name},{lt_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,3,2,{lt_alignment},70,70,{lt_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        timeline_cursor = 0.0

        for scene in scenes:
            text = str(scene.get("narration") or scene.get("title") or "").strip()
            duration = float(scene.get("duration", 4.0))
            scene_start = timeline_cursor
            scene_end = scene_start + duration
            timeline_cursor = scene_end - scene_overlap

            # Emit clean lower-third chyron for the first 3.5 seconds of the scene
            heading = str(scene.get("heading") or "").strip()
            subheading = str(scene.get("subheading") or "").strip()
            lt_meta = scene.get("lower_third")
            if isinstance(lt_meta, dict):
                heading = lt_meta.get("title", heading)
                subheading = lt_meta.get("subtitle", subheading)

            if heading and duration >= 2.0 and not is_shorts:
                chyron_end = min(scene_end, scene_start + 3.2)
                sub_part = f"\\N{{\\c&H00D0E0F0&\\fs{int(lt_size*0.75)}}}  {subheading}" if subheading else ""
                chyron_text = f"{{\\fad(250,250)\\c&H00F6823B&}}● {heading.upper()}{sub_part}"
                events.append(f"Dialogue: 1,{format_ass_time(scene_start)},{format_ass_time(chyron_end)},LowerThird,,0,0,0,,{chyron_text}")

            if not text:
                continue

            word_timings = scene.get("word_timings", [])
            if word_timings and len(word_timings) >= 1:
                # Millisecond-accurate timing directly from Edge-TTS telemetry
                chunk_size = 3 if len(word_timings) >= 6 else (2 if len(word_timings) >= 4 else len(word_timings))
                chunks = []
                for i in range(0, len(word_timings), chunk_size):
                    chunks.append(word_timings[i:i + chunk_size])

                for c_idx, chunk in enumerate(chunks):
                    c_start = scene_start + chunk[0]["start"]
                    c_end = scene_start + chunk[-1]["end"]
                    if c_idx < len(chunks) - 1:
                        next_c_start = scene_start + chunks[c_idx + 1][0]["start"]
                        c_end = min(c_end + 0.15, next_c_start)

                    for w_idx, active_item in enumerate(chunk):
                        w_start = scene_start + active_item["start"]
                        w_end = scene_start + active_item["end"]
                        if w_idx < len(chunk) - 1:
                            w_end = min(w_end + 0.08, scene_start + chunk[w_idx + 1]["start"])
                        else:
                            w_end = max(w_end, c_end)

                        styled_tokens = []
                        for k, item in enumerate(chunk):
                            w_word = item["word"].upper()
                            if k == w_idx:
                                styled_tokens.append(f"{{{accent_color}\\fscx112\\fscy112}}{w_word}{{\\c&H00FFFFFF&\\fscx100\\fscy100}}")
                            else:
                                styled_tokens.append(w_word)

                        line_text = " ".join(styled_tokens)
                        start_str = format_ass_time(w_start)
                        end_str = format_ass_time(w_end)
                        events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")
            else:
                syl_timings = syllable_word_timings(text, duration)
                if not syl_timings:
                    continue

                chunk_size = 3 if len(syl_timings) >= 6 else (2 if len(syl_timings) >= 4 else len(syl_timings))
                chunks = []
                for i in range(0, len(syl_timings), chunk_size):
                    chunks.append(syl_timings[i:i + chunk_size])

                for c_idx, chunk in enumerate(chunks):
                    c_start = scene_start + chunk[0]["start"]
                    c_end = scene_start + chunk[-1]["end"]
                    if c_idx < len(chunks) - 1:
                        next_c_start = scene_start + chunks[c_idx + 1][0]["start"]
                        c_end = min(c_end + 0.15, next_c_start)

                    for w_idx, active_item in enumerate(chunk):
                        w_start = scene_start + active_item["start"]
                        w_end = scene_start + active_item["end"]
                        if w_idx < len(chunk) - 1:
                            w_end = min(w_end + 0.08, scene_start + chunk[w_idx + 1]["start"])
                        else:
                            w_end = max(w_end, c_end)

                        styled_tokens = []
                        for k, item in enumerate(chunk):
                            w_word = item["word"].upper()
                            if k == w_idx:
                                styled_tokens.append(f"{{{accent_color}\\fscx112\\fscy112}}{w_word}{{\\c&H00FFFFFF&\\fscx100\\fscy100}}")
                            else:
                                styled_tokens.append(w_word)

                        line_text = " ".join(styled_tokens)
                        start_str = format_ass_time(w_start)
                        end_str = format_ass_time(w_end)
                        events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")

        with open(out_ass_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(events))
            f.write("\n")

        return out_ass_path
