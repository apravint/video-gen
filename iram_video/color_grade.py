"""
Cinematic Color Grading & Visual Mood System for IRAM Video.
Provides FFmpeg video filter chains for enterprise editorial,
Hollywood cinema, vintage 35mm, high-contrast monochrome, and vibrant marketing palettes.
"""

from typing import Dict, Any, Optional

COLOR_GRADE_PRESETS = {
    "clean": {
        "name": "Editorial Clean",
        "description": "Natural enterprise balance with crisp contrast and faithful saturation.",
        "ffmpeg_filter": "eq=contrast=1.02:brightness=0.0:saturation=1.02,format=yuv420p"
    },
    "documentary": {
        "name": "Documentary Natural",
        "description": "Natural, true-to-life documentary visual fidelity with original balance.",
        "ffmpeg_filter": "eq=contrast=1.02:brightness=0.0:saturation=1.02,format=yuv420p"
    },
    "cinematic": {
        "name": "Subtle Cinematic Contrast",
        "description": "Pure cinematic tone curve with neutral color balance and zero pink/green distortion.",
        "ffmpeg_filter": "colorbalance=rs=0.0:gs=0.0:bs=0.0:rm=0.0:gm=0.0:bm=0.0:rh=0.0:gh=0.0:bh=0.0,eq=contrast=1.02:saturation=1.02,format=yuv420p"
    },
    "vintage": {
        "name": "35mm Analog Subtle",
        "description": "Subtle analog film texture with natural colors.",
        "ffmpeg_filter": "eq=contrast=0.98:saturation=0.96,noise=alls=3:allf=t,format=yuv420p"
    },
    "noir": {
        "name": "Dramatic Monochrome",
        "description": "High-contrast black & white with deep obsidian shadows and crisp highlights.",
        "ffmpeg_filter": "hue=s=0,eq=contrast=1.10:brightness=-0.01,format=yuv420p"
    },
    "vibrant": {
        "name": "Vibrant Promo & Tech",
        "description": "High-impact punchy colors with heightened contrast for marketing and launch showcases.",
        "ffmpeg_filter": "eq=contrast=1.04:saturation=1.08,format=yuv420p"
    },
    "editorial": {
        "name": "Broadcast Editorial",
        "description": "Slightly cool, firm contrast for news and journalism.",
        "ffmpeg_filter": "eq=contrast=1.05:saturation=0.98,colorbalance=bm=0.02:rm=-0.01,format=yuv420p"
    },
    "warm_editorial": {
        "name": "Warm Editorial",
        "description": "Soft warm tones for conversation, food, travel and lifestyle.",
        "ffmpeg_filter": "eq=contrast=1.02:saturation=1.05,colorbalance=rm=0.03:bm=-0.03,format=yuv420p"
    },
    "none": {
        "name": "Passthrough (Original)",
        "description": "No color alteration. 100% original camera colors.",
        "ffmpeg_filter": "null"
    }
}

def get_color_grade_filter(grade_key: Optional[str]) -> str:
    """Returns the FFmpeg filter string for a given color grade preset."""
    if not grade_key:
        return COLOR_GRADE_PRESETS["clean"]["ffmpeg_filter"]
    key = grade_key.lower().strip().replace("-", "_").replace(" ", "_")
    preset = COLOR_GRADE_PRESETS.get(key, COLOR_GRADE_PRESETS["clean"])
    return preset["ffmpeg_filter"]
