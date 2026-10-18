import argparse
import json
import os
import re
import sys
import random
import tempfile
from pathlib import Path

from .director import Director
from .voice import VoiceSynthesizer
from .renderer import SlideRenderer, is_tamil_text
from .audio_synth import synthesize_mood_track
from .compiler import VideoCompiler
from .thumbnail import generate_thumbnail
from .film_director import FilmDirector
from .film_compiler import FilmCompiler
from .real_compiler import RealVideoCompiler
from .server import start_server
from .shotcraft import SHOT_RECIPES, get_shot_recipe
from .avatar import AvatarEngine
from .brag import BragHarvester, ViralHookGenerator
from .drama import CharacterAnchorRegistry, DramaTensionCurve
from .ai_video import AIVideoEngine

def slugify(text: str) -> str:
    clean = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[-\s]+", "_", clean)[:40]
    return slug or "iram_video_output"

def load_prompt_from_json(json_path: Path):
    """Extracts a rich video directing prompt and style hint from a structured JSON document."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        names = [item.get("name", "") for item in data[:8] if isinstance(item, dict)]
        title = json_path.stem.replace("-", " ").title()
        prompt = f"Comprehensive breakdown of {title}: Featuring {', '.join(names)}"
        style = f"Educational tech showcase reviewing {len(data)} tools"
        return prompt, style

    title = data.get("title", json_path.stem.replace("-", " ").title())
    desc = data.get("description", "")
    workflow = data.get("workflow_stages") or data.get("architecture_pipeline") or data.get("business_logic") or ""

    items = []
    if "skills" in data and isinstance(data["skills"], list):
        items = [s.get("name", "") for s in data["skills"][:8]]
    elif "categories" in data and isinstance(data["categories"], dict):
        for cat, tool_list in data["categories"].items():
            if isinstance(tool_list, list):
                items.extend([t.get("name", "") for t in tool_list[:3] if isinstance(t, dict)])
    elif "offers" in data and isinstance(data["offers"], list):
        items = [o.get("name", "") for o in data["offers"][:5]]

    items_str = f" Highlights: {', '.join(items[:8])}." if items else ""
    flow_str = f" Pipeline: {workflow}." if workflow else ""
    prompt = f"{title}. {desc}{items_str}{flow_str}"
    style = f"Technical and architectural deep-dive based on {json_path.name}"
    return prompt, style

from .templates import VIDEO_TEMPLATES, get_template

def main():
    parser = argparse.ArgumentParser(
        prog="iram-video",
        description="Universal Film & Video Engine (Real YouTube Documentary Videos, Animation Feature Films, Cinema Trailers, Shorts & Landscape, English & தமிழ்)."
    )
    parser.add_argument("prompt", nargs="?", default="", help="Topic, brief, or screenplay premise (English or தமிழ்)")
    parser.add_argument("--real", "--youtube", "--documentary", "--broll", dest="real", action="store_true", help="Generate as real documentary YouTube video with real 1080p/4K stock B-roll footage, photography, and acoustic score (NO cyberpunk, NO subtitles)")
    parser.add_argument("--subtitles", action="store_true", help="Burn subtitles into the video (disabled by default)")
    parser.add_argument("--no-subtitles", action="store_true", help="Ensure subtitles are completely disabled (default)")
    parser.add_argument("--from-json", default=None, help="Directly ingest a structured JSON document or stack blueprint (e.g. software-factory-skills.json)")
    parser.add_argument("--serve", action="store_true", help="Launch the local Web Studio dashboard server (default port 7860)")
    parser.add_argument("--port", type=int, default=7860, help="Web Studio port (default: 7860)")
    parser.add_argument("-o", "--output", help="Output MP4 file path (default: ./<slug>.mp4)")
    parser.add_argument("--film", "--feature", dest="film", action="store_true", help="Generate as full Multi-Character Animated Feature Film with dialogue, procedural sets, score & rolling end credits")
    parser.add_argument("--cast", default=None, help="Cast preference (e.g. 'nova,unit-7' or 'ferris,gopher')")
    parser.add_argument("--shorts", action="store_true", help="Generate as vertical YouTube Shorts (9:16, 1080x1920, < 60s)")
    parser.add_argument("--cinema", "--movie", dest="cinema", action="store_true", help="Generate as Hollywood-grade cinema trailer (24 FPS, 2.39:1 letterbox, 35mm grain, color grade, Inception BRAAMs)")
    parser.add_argument("--character", default="none", choices=["none", "auto", "robot", "presenter", "ferris", "gopher"], help="Add animated character mascot ('robot', 'presenter', 'ferris', 'gopher', 'auto')")
    parser.add_argument("--lang", default="auto", choices=["auto", "en", "ta", "tamil", "english"], help="Language: 'en' for English, 'ta' for Tamil, 'auto' for auto-detection (default: auto)")
    parser.add_argument("--voice", default="default", help="Voice persona ('aria', 'christopher', 'jenny', 'pallavi' [Tamil female], 'valluvar' [Tamil male], etc.)")
    parser.add_argument("--scenes", type=int, default=None, help="Desired scene count (default: auto)")
    parser.add_argument("--music", default="auto", choices=["auto", "documentary", "acoustic", "lofi", "tech", "ambient", "trailer", "cinematic", "corporate", "energetic", "minimal", "cyber", "none"], help="Background music mood (default: auto)")
    parser.add_argument("--bg-music", default=None, help="Custom background music track file path (MP3, WAV, AAC)")
    parser.add_argument("--music-volume", type=float, default=0.20, help="Background music volume ducking level (default: 0.20)")
    parser.add_argument("--style", default=None, help="Style hint for the director (e.g. 'documentary', 'realistic', 'vox style', 'educational')")
    parser.add_argument("--template", choices=list(VIDEO_TEMPLATES.keys()), default=None, help="Video genre template ('explainer', 'tutorial', 'listicle', 'comparison', 'news', 'promo', 'podcast')")
    parser.add_argument("--tutorial", action="store_true", help="Shortcut for --template tutorial")
    parser.add_argument("--listicle", action="store_true", help="Shortcut for --template listicle")
    parser.add_argument("--comparison", action="store_true", help="Shortcut for --template comparison")
    parser.add_argument("--news", action="store_true", help="Shortcut for --template news")
    parser.add_argument("--promo", action="store_true", help="Shortcut for --template promo")
    parser.add_argument("--explainer", action="store_true", help="Shortcut for --template explainer")
    parser.add_argument("--podcast", action="store_true", help="Shortcut for --template podcast")
    parser.add_argument("--aspect-ratio", "--ratio", dest="aspect_ratio", default="auto", choices=["auto", "16:9", "9:16", "1:1", "2.39:1"], help="Video aspect ratio (default: auto, 16:9 or 9:16 for shorts)")
    parser.add_argument("--4k", dest="is_4k", action="store_true", help="Render in 4K UHD high resolution")
    parser.add_argument("--transition", default="fade", choices=["fade", "dissolve", "wipeleft", "wiperight", "slideleft", "slideright", "smoothleft", "circlecrop", "fadeblack", "fadewhite", "cut", "none"], help="Cinematic transition between scenes (default: fade)")
    parser.add_argument("--grade", default="auto", choices=["auto", "clean", "documentary", "cinematic", "vintage", "noir", "vibrant", "none"], help="Cinematic color grading preset (default: auto)")
    parser.add_argument("--no-thumbnail", action="store_true", help="Skip thumbnail generation")
    parser.add_argument("--generator", default="auto", choices=["auto", "veo", "wan", "wan2", "wan2.1", "wan2.2", "hunyuan", "cogvideo", "sana", "fal", "replicate", "kling", "stock"], help="Video generator model hub")
    parser.add_argument("--veo", dest="generator_veo", action="store_true", help="Prioritize Google Veo 3.1 / 2.0 generative video synthesis")
    parser.add_argument("--ai-video", dest="ai_video", action="store_true", help="Enable AI generative video synthesis with automatic multi-tier fallback")
    parser.add_argument("--subtitle-palette", default="auto", choices=["auto", "gold", "hormozi", "neon-cyan", "neon-green", "fire-red", "purple", "white"], help="Subtitle color palette")
    parser.add_argument("--recipe", choices=list(SHOT_RECIPES.keys()), default=None, help="Cinematic shotcraft recipe card")
    parser.add_argument("--steady", "--steady-cam", dest="steady_camera", action="store_true", default=True, help="Enable steady-cam mode (default: True)")
    parser.add_argument("--dynamic-cam", dest="steady_camera", action="store_false", help="Enable dynamic legacy camera motion")
    parser.add_argument("--mcp", action="store_true", help="Launch the Model Context Protocol (MCP) JSON-RPC server on stdio for LLMs & AI agents")
    parser.add_argument("--extend", default=None, help="Continuous scene extension mode: path to previous MP4 video to chain and extend")
    parser.add_argument("--image", "--start-image", dest="start_image", default=None, help="Image-to-Video storyboarding: path to seed starting image/photo")
    parser.add_argument("--brag", default=None, help="Repository-to-video mode: auto-inspect a codebase/git repository and craft a developer launch showcase")
    parser.add_argument("--avatar", default=None, help="Digital human talking avatar mode: pass a portrait image to composite talking presenter")
    parser.add_argument("--api", "--fastapi", dest="fastapi", action="store_true", help="Launch the decoupled FastAPI REST API & Async Task Queue server")
    parser.add_argument("--api-port", type=int, default=8000, help="FastAPI port (default: 8000)")
    parser.add_argument("--tension", action="store_true", help="Apply drama tension curve analysis and dramatic beat scoring")
    parser.add_argument("--threejs", "--3d", dest="threejs", action="store_true", help="Launch Three.js 3D WebGL motion graphics & kinetic titles studio")
    parser.add_argument("--harness", action="store_true", help="Run with Harness² cyclic verification loop (Plan -> Act -> Verify -> Reflect)")

    args = parser.parse_args()

    if getattr(args, "threejs", False):
        import subprocess
        print("🪐 [THREE.JS] Launching Three.js 3D Motion Graphics Studio...")
        subprocess.run(["iram-video-3d"])
        return

    if getattr(args, "harness", False):
        import subprocess
        task = f"Compile video for topic '{args.prompt or 'IRAM OS Technology'}' with {args.scenes or 'auto'} scenes"
        print(f"🧠 [HARNESS²] Dispatching cyclic verification loop for video task...")
        subprocess.run(["iram-harness2", task])
        return

    if args.fastapi:
        from .api import start_fastapi
        start_fastapi(port=args.api_port)
        return

    if args.mcp:
        from .mcp_server import main as mcp_main
        mcp_main()
        return

    if args.extend:
        prev_video = Path(args.extend).resolve()
        if not prev_video.exists():
            print(f"❌ Previous video not found for extension: {prev_video}")
            sys.exit(1)
        out_video = Path(args.output or f"./{prev_video.stem}_extended.mp4").resolve()
        prompt = args.prompt or "Continuing the sequence seamlessly into the next scene"
        print(f"🎞️ [SCENE EXTENSION] Extending '{prev_video.name}' with prompt: '{prompt}'...")
        AIVideoEngine.extend_video(prev_video, prompt, out_video, duration=4.0, is_shorts=args.shorts)
        print(f"🎉 EXTENDED VIDEO CREATED: {out_video}")
        return

    if args.serve or (len(sys.argv) > 1 and sys.argv[1] == "serve"):
        start_server(args.port)
        return

    # Ingest from repository in Brag mode
    if args.brag:
        repo_dir = Path(args.brag).resolve()
        if not repo_dir.exists():
            print(f"❌ Brag repository path not found: {repo_dir}")
            sys.exit(1)
        brag_info = BragHarvester.inspect_repository(repo_dir)
        args.prompt = BragHarvester.craft_launch_prompt(brag_info)
        args.style = "High-energy developer launch showcase with code terminal simulation and architecture cards"
        if not args.output:
            args.output = f"./{repo_dir.name}_launch_showcase.mp4"
        print(f"🚀 [BRAG LAUNCHPAD] Ingested repository \"{brag_info['name']}\" ({', '.join(brag_info.get('tech_stack', []))})")

    # Ingest from JSON document if provided
    if args.from_json:
        json_file = Path(args.from_json).resolve()
        if not json_file.exists():
            print(f"❌ JSON document not found: {json_file}")
            sys.exit(1)
        j_prompt, j_style = load_prompt_from_json(json_file)
        if not args.prompt:
            args.prompt = j_prompt
        if not args.style:
            args.style = j_style
        print(f"📄 [JSON INGESTION] Loaded blueprint: \"{json_file.name}\"")

    # Apply Shotcraft recipe card if specified
    if args.recipe:
        recipe_data = get_shot_recipe(args.recipe)
        args.prompt = f"{args.prompt} Shotcraft Camera Direction: {recipe_data['name']} ({recipe_data['description']})."
        print(f"🎬 [SHOTCRAFT RECIPE] Applied: \"{recipe_data['name']}\" ({recipe_data['lens']}, {recipe_data['lighting']})")

    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    # Detect language
    lang = args.lang.lower()
    if lang == "auto":
        lang = "ta" if is_tamil_text(args.prompt) else "en"
    elif lang in ["tamil", "ta"]:
        lang = "ta"
    else:
        lang = "en"

    # Template resolution
    # Template resolution
    selected_template = args.template
    # HIGH QUALITY COMPACT MAPPING: Parse template keys using an evaluation tuple map
    for flag_attr, key_name in [
        ("tutorial", "tutorial"), ("listicle", "listicle"), 
        ("comparison", "comparison"), ("news", "news"), 
        ("promo", "promo"), ("explainer", "explainer"), ("podcast", "podcast")
    ]:
        if getattr(args, flag_attr, False):
            selected_template = key_name
            break

    if selected_template:
        t_spec = get_template(selected_template)
        if args.scenes is None:
            args.scenes = t_spec.get("default_scenes", 4)
        if not args.style:
            args.style = t_spec.get("directorial_hints", "")
        if args.music == "auto":
            args.music = t_spec.get("default_music", "auto")
        if args.grade == "auto":
            args.grade = t_spec.get("default_color_grade", "clean")
        if t_spec.get("is_real", False) and not (args.cinema or args.film):
            args.real = True

    is_film = args.film
    is_shorts = args.shorts
    is_cinema = args.cinema or is_film
    is_real = args.real

    # Aspect ratio resolution
    aspect_ratio = args.aspect_ratio
    if aspect_ratio == "auto":
        if is_shorts:
            aspect_ratio = "9:16"
        elif is_cinema:
            aspect_ratio = "2.39:1"
        else:
            aspect_ratio = "16:9"
    else:
        if aspect_ratio == "9:16":
            is_shorts = True
        elif aspect_ratio == "2.39:1":
            is_cinema = True

    generator_prov = args.generator
    if args.generator_veo:
        generator_prov = "veo"
        is_real = True
    elif args.ai_video:
        generator_prov = "auto"
        is_real = True

    p_low = args.prompt.lower()
    doc_triggers = [r"\breal\b", r"\bdocumentary\b", r"\bhistory\b", r"\bnature\b", r"\bscience\b", r"\bhow to\b"]
    if not is_film and not is_cinema and (args.real or any(re.search(pat, p_low) for pat in doc_triggers)):
        is_real = True

    # Color grading preset
    color_grade = args.grade
    if color_grade == "auto":
        color_grade = "clean"

    transition = args.transition

    # Subtitles disabled by default unless explicitly requested
    burn_subtitles = args.subtitles and not args.no_subtitles

    # Character selection
    character = args.character
    if character == "auto":
        if is_real:
            character = None
        elif "rust" in p_low:
            character = "ferris"
        elif bool(re.search(r"\bgo\b", p_low)) or "golang" in p_low:
            character = "gopher"
        elif any(k in p_low for k in ["girl", "host", "presenter"]):
            character = "presenter"
        else:
            character = "robot"
    elif character == "none":
        character = None

    # Music default for cinema / film / real documentary
    music_mood = args.music
    if music_mood == "auto":
        if is_cinema or is_film:
            music_mood = random.choice(["trailer", "cinematic"])
        elif is_real:
            music_mood = random.choice(["documentary", "cinematic", "acoustic", "energetic", "minimal"])
        else:
            music_mood = random.choice(["tech", "lofi", "ambient", "corporate"])

    res_badge = "4K UHD" if args.is_4k else "1080p HD"
    tmpl_badge = f" [{selected_template.upper()} TEMPLATE]" if selected_template else ""
    if is_film:
        format_label = f"Animated Feature Film ({res_badge}, Multi-Character Dialogue & Procedural Sets){tmpl_badge}"
    elif is_cinema:
        format_label = f"Hollywood Cinema Trailer ({res_badge}, 24 FPS, 2.39:1 Scope){tmpl_badge}" if not is_shorts else f"Vertical Cinematic Shorts ({res_badge}, 24 FPS){tmpl_badge}"
    elif is_real:
        format_label = f"Real YouTube Documentary ({res_badge}, {aspect_ratio}, Real B-Roll, Grade: {color_grade}){tmpl_badge}"
    elif is_shorts:
        format_label = f"YouTube Shorts ({res_badge}, Vertical 9:16, 1080x1920){tmpl_badge}"
    else:
        format_label = f"Universal Video ({res_badge}, {aspect_ratio}, Grade: {color_grade}, Transition: {transition}){tmpl_badge}"

    slug = slugify(args.prompt)
    if is_shorts and not slug.endswith("_shorts"):
        slug += "_shorts"
    if is_cinema and not slug.endswith("_cinema") and not is_film:
        slug += "_cinema"
    if is_film and not slug.endswith("_film"):
        slug += "_film"
    if is_real and not slug.endswith("_real") and not is_shorts and not is_cinema and not is_film:
        slug += "_real"

    output_mp4 = Path(args.output).resolve() if args.output else Path(f"./{slug}.mp4").resolve()
    thumb_png = output_mp4.with_suffix(".png")
    meta_txt = output_mp4.with_suffix(".txt")

    lang_display = "தமிழ் (Tamil)" if lang == "ta" else "English"
    char_display = f" | Mascot: {character}" if character else ""
    print(f"\n🎬 [IRAM FILM STUDIO] Initializing Video Generation Pipeline")
    print(f"► Premise: \"{args.prompt}\"")
    print(f"► Format: {format_label}{char_display}")
    print(f"► Language: {lang_display} | Score: {music_mood}")
    print(f"► Master Output: {output_mp4}\n")

    with tempfile.TemporaryDirectory(prefix="iram_video_") as tmpdir:
        work_dir = Path(tmpdir)

        if is_film:
            # --- ANIMATED FEATURE FILM PIPELINE ---
            print(f"🧠 [1/4] Screenwriting & Directing Animated Feature Film...")
            film_director = FilmDirector()
            try:
                screenplay = film_director.direct_film(
                    args.prompt,
                    scene_count=args.scenes or 3,
                    language=lang,
                    style_hint=args.style,
                    cast_hint=args.cast
                )
            except Exception as e:
                print(f"❌ Screenplay direction failed: {e}")
                sys.exit(1)

            film_title = screenplay.get("film_title", args.prompt[:60])
            cast = screenplay.get("cast", [])
            print(f"✓ Feature Screenplay Written: \"{film_title}\" ({len(screenplay.get('scenes', []))} Acts)")
            print(f"🎭 Cast: {', '.join(c.get('name', 'Actor') + ' as ' + c.get('role', 'Role') for c in cast)}")

            print(f"⚙️  [2/4] Recording multi-character dialogue & staging procedural sets...")
            compiler = FilmCompiler(work_dir, language=lang)
            print(f"🎥 [3/4] Compiling 24 FPS cinema shots with animated lip-sync & 35mm film grain...")
            compiler.compile_film(screenplay, output_mp4)
            print(f"🎉 MASTER FEATURE FILM GENERATED: {output_mp4}")

            print(f"🖼️  [4/4] Designing theatrical film poster & metadata...")
            if not args.no_thumbnail:
                act_titles = [s.get("act_title", "") for s in screenplay.get("scenes", [])]
                primary_char = cast[0].get("character_type", "presenter") if cast else "presenter"
                generate_thumbnail(
                    film_title,
                    act_titles,
                    {"bg": [8, 10, 20], "accent": [0, 229, 255], "secondary": [168, 85, 247]},
                    thumb_png,
                    is_cinema=True,
                    character=primary_char
                )
                print(f"🖼️  THEATRICAL POSTER: {thumb_png}")

            yt_meta = screenplay.get("youtube_metadata", {})
            with open(meta_txt, "w") as f:
                f.write(f"FILM TITLE:\n{film_title}\n\n")
                f.write(f"GENRE:\n{screenplay.get('genre', 'Sci-Fi Animation')}\n\n")
                f.write(f"SYNOPSIS:\n{yt_meta.get('description', '')}\n\n")
                f.write("CAST & ROLES:\n")
                for c in cast:
                    f.write(f"• {c.get('name')}: {c.get('role')} (Rig: {c.get('character_type')})\n")
                f.write("\nACTS & SCENES:\n")
                for s in screenplay.get("scenes", []):
                    f.write(f"• {s.get('act_title')} [{s.get('setting')}] — {s.get('time_and_place')}\n")
                f.write(f"\nCLOSING QUOTE:\n\"{screenplay.get('closing_quote', '')}\"\n")
                f.write(f"\nCREDITS:\n{chr(10).join(screenplay.get('credits', []))}\n")
                f.write(f"\nTAGS:\n{', '.join(yt_meta.get('tags', []))}\n")
            print(f"📋 FILM ARCHIVE & METADATA: {meta_txt}")

            print("\n" + "=" * 60)
            print(f"🎬 Feature Film Production Complete!")
            print(f"• Movie Master: {output_mp4}")
            if not args.no_thumbnail:
                print(f"• Film Poster:  {thumb_png}")
            print(f"• Screenplay:   {meta_txt}")
            print("=" * 60 + "\n")
            return

        # --- STANDARD VIDEO & CINEMA TRAILER PIPELINE ---
        audio_dir = work_dir / "audio"
        slides_dir = work_dir / "slides"
        slides_dir.mkdir(parents=True, exist_ok=True)

        # 1. Direct with Google Gemini (Shorts-aware & Bilingual)
        print(f"🧠 [1/5] Directing screenplay with Google Gemini 3.8 Flash ({format_label})...")
        director = Director()
        try:
            screenplay = director.direct(
                args.prompt,
                scene_count=args.scenes,
                style_hint=args.style,
                language=lang,
                is_shorts=is_shorts,
                is_cinema=is_cinema,
                is_real=is_real,
                character=character,
                template=selected_template
            )
        except Exception as e:
            print(f"❌ Failed to direct screenplay with Google Gemini: {e}")
            sys.exit(1)

        video_title = screenplay.get("video_title", args.prompt[:60])
        if is_shorts and "#Shorts" not in video_title and "#shorts" not in video_title:
            video_title += " #Shorts"

        scenes = screenplay.get("scenes", [])
        theme_palette = screenplay.get("theme_palette", {})
        print(f"✓ Screenplay ready: \"{video_title}\" ({len(scenes)} scenes)")

        # 2. Voiceover Synthesis
        rate = "+3%" if is_shorts else ("-2%" if is_cinema else "+0%")
        chosen_voice = args.voice
        if not chosen_voice or chosen_voice.lower() == "auto":
            if lang == "ta":
                chosen_voice = random.choice(["pallavi", "valluvar"])
            else:
                if is_cinema or is_film:
                    chosen_voice = random.choice(["christopher", "guy", "eric"])
                else:
                    chosen_voice = random.choice(["aria", "christopher", "jenny", "guy", "eric"])

        print(f"🎙️  [2/5] Synthesizing neural voiceover ({lang_display})...")
        voice_synth = VoiceSynthesizer(voice_key=chosen_voice, language=lang, rate=rate)
        scenes = voice_synth.synthesize(scenes, audio_dir)
        total_duration = sum(s["duration"] for s in scenes)
        print(f"✓ Voiceover complete using voice '{voice_synth.voice}': {total_duration:.1f}s total duration")

        # 3. Background Music (Custom track or synthesized mood track)
        bg_music_wav = work_dir / "bg_music.wav"
        if args.bg_music:
            custom_bg = Path(args.bg_music).resolve()
            if custom_bg.exists():
                print(f"🎵 [3/5] Using custom background music track: '{custom_bg.name}'...")
                bg_music_wav = custom_bg
            else:
                print(f"⚠️ Custom music file not found: {custom_bg}. Falling back to '{music_mood}' synth track...")
                if music_mood != "none":
                    synthesize_mood_track(music_mood, total_duration + 5.0, bg_music_wav)
                else:
                    bg_music_wav = None
        elif music_mood != "none":
            print(f"🎵 [3/5] Synthesizing '{music_mood}' soundtrack...")
            synthesize_mood_track(music_mood, total_duration + 5.0, bg_music_wav)
            print("✓ Soundtrack ready")
        else:
            bg_music_wav = None

        if aspect_ratio == "1:1":
            dim_str = "2160x2160" if args.is_4k else "1080x1080"
        elif aspect_ratio == "9:16" or is_shorts:
            dim_str = "2160x3840" if args.is_4k else "1080x1920"
        elif aspect_ratio == "2.39:1":
            dim_str = "3840x1608" if args.is_4k else "2560x1072"
        else:
            dim_str = "3840x2160" if args.is_4k else "1920x1080"

        # 4 & 5. Video Sourcing & Compilation
        if is_real:
            combined_topic = f"{args.prompt} | {video_title}"
            print(f"🎥 [4/5] Sourcing video footage ({generator_prov.upper()} generative AI + stock fallback)...")
            start_img = Path(args.start_image).resolve() if args.start_image else None
            real_compiler = RealVideoCompiler(
                work_dir,
                is_shorts=is_shorts,
                is_cinema=is_cinema,
                provider=generator_prov,
                global_topic=combined_topic,
                steady_camera=args.steady_camera,
                start_image=start_img,
                aspect_ratio=aspect_ratio,
                is_4k=args.is_4k
            )
            soundscape_info = screenplay.get("soundscape", {})
            soundscape_playlist = soundscape_info.get("soundscape_playlist")
            if not soundscape_playlist and soundscape_info.get("ambient_track"):
                soundscape_playlist = [{"type": soundscape_info.get("ambient_track"), "volume": 0.12}]

            chosen_palette = args.subtitle_palette
            if not chosen_palette or chosen_palette.lower() == "auto":
                chosen_palette = random.choice(["gold", "white", "hormozi"])

            sub_status = f"with subtitles [{chosen_palette}]" if burn_subtitles else "no subtitles"
            print(f"⚙️  [5/5] Compiling master documentary video with acoustic score ({sub_status}, transition={transition}, grade={color_grade})...")
            real_compiler.compile_real_video(
                scenes,
                bg_music_wav,
                output_mp4,
                global_topic=combined_topic,
                burn_subtitles=burn_subtitles,
                language=lang,
                palette_key=chosen_palette,
                transition=transition,
                color_grade=color_grade,
                music_volume=args.music_volume,
                soundscape_playlist=soundscape_playlist
            )
            print(f"🎉 MASTER REAL VIDEO GENERATED: {output_mp4}")
        else:
            # --- SLIDE/GRAPHICS VIDEO PIPELINE ---
            print(f"🎨 [4/5] Rendering {dim_str} slide frames ({lang_display} typography)...")
            renderer = SlideRenderer(
                theme=theme_palette,
                is_shorts=is_shorts,
                aspect_ratio=aspect_ratio,
                is_4k=args.is_4k
            )
            slide_paths = []
            for i, scene in enumerate(scenes):
                out_slide = slides_dir / f"{scene['id']}.png"
                renderer.render_scene(scene, video_title, out_slide)
                slide_paths.append(out_slide)
            print(f"✓ Rendered {len(slide_paths)} {dim_str} slide frames")

            print(f"⚙️  [5/5] Compiling master {dim_str} MP4 with FFMPEG (transition={transition}, grade={color_grade})...")
            compiler = VideoCompiler(
                work_dir,
                is_cinema=is_cinema,
                is_shorts=is_shorts,
                character=character,
                aspect_ratio=aspect_ratio,
                is_4k=args.is_4k
            )
            compiler.compile(
                scenes,
                slide_paths,
                bg_music_wav,
                output_mp4,
                language=lang,
                burn_subtitles=burn_subtitles,
                palette_key=args.subtitle_palette,
                transition=transition,
                color_grade=color_grade,
                music_volume=args.music_volume
            )
            print(f"🎉 MASTER VIDEO GENERATED: {output_mp4}")

        # Digital Human Talking Avatar Overlay (LivePortrait / Duix-Avatar)
        if args.avatar:
            avatar_path = Path(args.avatar).resolve()
            if avatar_path.exists():
                print(f"👤 [DIGITAL HUMAN] Compositing talking avatar presenter from '{avatar_path.name}'...")
                avatar_tmp_video = work_dir / "avatar_clip.mp4"
                composite_output = work_dir / "composite_with_avatar.mp4"
                primary_audio = scenes[0].get("audio_file") or (work_dir / "audio" / f"{scenes[0]['id']}.mp3")
                if primary_audio and Path(primary_audio).exists():
                    AvatarEngine.create_talking_avatar_video(
                        avatar_path,
                        Path(primary_audio),
                        avatar_tmp_video,
                        duration=total_duration,
                        width=380,
                        height=380
                    )
                    AvatarEngine.overlay_presenter_pip(
                        output_mp4,
                        avatar_tmp_video,
                        composite_output,
                        position="bottom_right"
                    )
                    if composite_output.exists() and composite_output.stat().st_size > 10000:
                        import shutil
                        shutil.move(str(composite_output), str(output_mp4))
                        print(f"✓ [DIGITAL HUMAN] Avatar presenter successfully composited onto master video")

        # 6. Thumbnail Generation
        if not args.no_thumbnail:
            bullets = [s.get("heading", "") for s in scenes]
            generate_thumbnail(video_title, bullets, theme_palette, thumb_png, is_shorts=is_shorts, is_cinema=is_cinema, character=character)
            print(f"🖼️  YOUTUBE THUMBNAIL: {thumb_png}")

        # 7. Metadata Export
        yt_meta = screenplay.get("youtube_metadata", {})
        tags = yt_meta.get("tags", [])
        if is_shorts and "Shorts" not in tags and "#Shorts" not in tags:
            tags.insert(0, "#Shorts")

        with open(meta_txt, "w") as f:
            f.write(f"TITLE:\n{video_title}\n\n")
            f.write(f"DESCRIPTION:\n{yt_meta.get('description', '')}\n\n")
            f.write("CHAPTERS:\n")
            curr_sec = 0.0
            for s in scenes:
                mins = int(curr_sec // 60)
                secs = int(curr_sec % 60)
                f.write(f"{mins}:{secs:02d} {s.get('heading', '')}\n")
                curr_sec += s["duration"]
            f.write(f"\nTAGS:\n{', '.join(tags)}\n")
        print(f"📋 YOUTUBE METADATA: {meta_txt}")

        print("\n" + "="*60)
        print(f"✅ Video creation complete ({format_label})!")
        print(f"• Video:     {output_mp4} ({total_duration:.1f}s)")
        if not args.no_thumbnail:
            print(f"• Thumbnail: {thumb_png}")
        print(f"• Metadata:  {meta_txt}")
        print("="*60 + "\n")

if __name__ == "__main__":
    main()
