"""
Shotcraft & Cinematic Recipe System for IRAM Video.
Provides 12 production-ready cinematic shot recipe cards with lens physics,
camera movement, and aspect-ratio adaptive optical grading curves.
"""

from typing import Dict, Any, Tuple, Optional

# Recipes contain distinct parameters for landscape and vertical layouts
SHOT_RECIPES = {
    "hero_reveal": {
        "name": "Hero Reveal",
        "description": "Slow dramatic steady push-in rising smoothly to illuminate the central subject.",
        "lens": "50mm anamorphic",
        "lighting": "Volumetric rim light with subtle warm key",
        "camera_movement": "steady_push_in",
        "prompt_enhancer": "dramatic hero reveal shot, subtle rising camera, soft volumetric rim lighting, 8k cinematic masterpiece, 35mm film grain, 50mm anamorphic bokeh",
        "ffmpeg_filter_landscape": "zoompan=z='min(zoom+0.0003,1.03)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.03:brightness=0.0:saturation=1.02,format=yuv420p",
        "ffmpeg_filter_portrait": "zoompan=z='min(zoom+0.0003,1.03)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.03:brightness=0.0:saturation=1.02,format=yuv420p"
    },
    "macro_orbit": {
        "name": "Macro Orbit",
        "description": "Ultra close-up smooth steady focal drift with shallow depth of field.",
        "lens": "100mm macro",
        "lighting": "Softbox studio rim light with specularity",
        "camera_movement": "steady_macro_drift",
        "prompt_enhancer": "extreme macro steady camera sweep, 100mm macro lens, ultra shallow depth of field, micro textures, specular reflections, 8k resolution",
        "ffmpeg_filter_landscape": "zoompan=z=1.02:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.02:saturation=1.02,format=yuv420p",
        "ffmpeg_filter_portrait": "zoompan=z=1.02:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.02:saturation=1.02,format=yuv420p"
    },
    "speed_ramp": {
        "name": "Speed Ramp Drift",
        "description": "Smooth cinematic dolly movement decelerating into crisp slow-motion focus.",
        "lens": "35mm prime",
        "lighting": "High-contrast dynamic studio rim light with soft falloff",
        "camera_movement": "steady_decelerate",
        "prompt_enhancer": "smooth cinematic dolly shot, gradual deceleration into slow motion, razor sharp focal point, 8k",
        "ffmpeg_filter_landscape": "zoompan=z='1.0+0.025*(3*pow(on/{frames},2)-2*pow(on/{frames},3))':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.03:saturation=1.02,format=yuv420p",
        "ffmpeg_filter_portrait": "zoompan=z='1.0+0.025*(3*pow(on/{frames},2)-2*pow(on/{frames},3))':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.03:saturation=1.02,format=yuv420p"
    },
    "isometric_exploded": {
        "name": "Isometric Exploded Architecture",
        "description": "Technical isometric perspective revealing layers, code nodes, or structural blueprints.",
        "lens": "Orthographic telephoto",
        "lighting": "Clean ambient occlusion with architectural key light",
        "camera_movement": "isometric_steady",
        "prompt_enhancer": "isometric 3D technical exploded architecture view, clean layers, precise wireframes, modern engineering schematic, octane render 8k",
        "ffmpeg_filter_landscape": "zoompan=z=1.02:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.03:saturation=1.02,format=yuv420p",
        "ffmpeg_filter_portrait": "zoompan=z=1.02:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.03:saturation=1.02,format=yuv420p"
    },
    "dutch_angle_tension": {
        "name": "Dutch Angle Tension",
        "description": "Tilted camera with high-contrast chiaroscuro shadows and psychological stakes.",
        "lens": "28mm wide-angle",
        "lighting": "Chiaroscuro side lighting with deep obsidian shadows",
        "camera_movement": "steady_slow_hold",
        "prompt_enhancer": "dutch angle tilted cinematic shot, tense psychological atmosphere, high contrast chiaroscuro lighting, deep shadows, 28mm wide angle, cinematic film still",
        "ffmpeg_filter_landscape": "zoompan=z='min(zoom+0.0003,1.03)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.05:saturation=1.0,format=yuv420p",
        "ffmpeg_filter_portrait": "zoompan=z='min(zoom+0.0003,1.03)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.05:saturation=1.0,format=yuv420p"
    },
    "terminal_glitch_scan": {
        "name": "Terminal Code Focus",
        "description": "Modern developer terminal scan with crisp typography and clean code buffers.",
        "lens": "50mm prime",
        "lighting": "Natural studio ambient light with clean matte screen",
        "camera_movement": "steady_push",
        "prompt_enhancer": "modern clean developer code terminal on minimalist desk, crisp typography, subtle syntax highlights, professional cinematography 8k",
        "ffmpeg_filter_landscape": "zoompan=z='min(zoom+0.0002,1.025)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.02:saturation=1.02,format=yuv420p",
        "ffmpeg_filter_portrait": "zoompan=z='min(zoom+0.0002,1.025)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.02:saturation=1.02,format=yuv420p"
    },
    "split_comparison": {
        "name": "Split-Screen Contrast",
        "description": "Dynamic split composition contrasting traditional vs modernized execution.",
        "lens": "50mm dual",
        "lighting": "Balanced dual studio lighting with natural color balance",
        "camera_movement": "steady_center",
        "prompt_enhancer": "cinematic split screen comparison, side-by-side contrast, balanced dual focal points, natural lighting, 8k",
        "ffmpeg_filter_landscape": "zoompan=z=1.0:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.02:saturation=1.02,format=yuv420p",
        "ffmpeg_filter_portrait": "zoompan=z=1.0:d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.02:saturation=1.02,format=yuv420p"
    },
    "broll_whip_pan": {
        "name": "B-Roll Gentle Transition",
        "description": "Smooth cinematic motion linking two thematic visual beats.",
        "lens": "35mm documentary",
        "lighting": "Natural golden hour daylight",
        "camera_movement": "gentle_drift",
        "prompt_enhancer": "cinematic documentary camera sweep across modern cityscape, natural sunlight, crisp details, authentic 4k",
        "ffmpeg_filter_landscape": "zoompan=z='min(zoom+0.0003,1.03)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.02:saturation=1.02,format=yuv420p",
        "ffmpeg_filter_portrait": "zoompan=z='min(zoom+0.0003,1.03)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},eq=contrast=1.02:saturation=1.02,format=yuv420p"
    }
}

# Ensure backwards-compatibility for callers accessing 'ffmpeg_filter' directly
for r in SHOT_RECIPES.values():
    if "ffmpeg_filter" not in r:
        r["ffmpeg_filter"] = r.get("ffmpeg_filter_landscape", "")

def get_shot_recipe(recipe_key: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve recipe card with default fallback."""
    if not recipe_key:
        return SHOT_RECIPES["hero_reveal"]
    clean_key = recipe_key.lower().strip().replace(" ", "_").replace("-", "_")
    return SHOT_RECIPES.get(clean_key, SHOT_RECIPES["hero_reveal"])

def build_recipe_filter(recipe_key: str, frames: int, w: int, h: int, fps: int = 30, for_video: bool = False) -> str:
    """Renders the exact aspect-ratio adaptive FFmpeg video filtergraph for the selected recipe card."""
    recipe = get_shot_recipe(recipe_key)
    
    # Check orientation and extract the correct scaling string matrix
    is_shorts = h > w
    filter_key = "ffmpeg_filter_portrait" if is_shorts else "ffmpeg_filter_landscape"

    if for_video:
        vf = recipe.get("video_filter")
        if vf:
            return vf
        raw_filter = recipe.get(filter_key, "") or recipe.get("ffmpeg_filter", "")
        parts = [p.strip() for p in raw_filter.split(",") if not p.strip().startswith("zoompan")]
        return ",".join(parts) if parts else ""
    
    raw_filter = recipe.get(filter_key, "")
    if not raw_filter:
        raw_filter = recipe.get("ffmpeg_filter", "")
    return raw_filter.format(frames=frames, w=w, h=h, fps=fps)
