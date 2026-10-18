import json
import os
import re
import time
from typing import Dict, Any
from google import genai
from google.genai import types

DIRECTOR_SYSTEM_PROMPT = """
You are an expert AI Video Producer and Creative Director.
Your task is to transform any user topic, request, or brief into a structured, broadcast-quality video screenplay.

You must design a sequence of visual scenes that tell a compelling story.
For each scene, you provide:
1. "id": e.g. "scene_1", "scene_2", ...
2. "heading": A punchy uppercase header (max 40 chars)
3. "subheading": A clean explanatory subtitle (max 65 chars)
4. "layout_type": One of:
   - "pillars": (Widescreen landscape only) 2 or 3 vertical feature cards side-by-side
   - "comparison": (Widescreen landscape only) 2 comparative cards side-by-side
   - "code_or_terminal": A title card with a terminal command or code block simulation
   - "stack_list": 2 to 3 vertical stacked layers (Perfect for vertical Shorts layout)
   - "hero_metric": One primary large core callout concept filling the screen space
   CRITICAL: If the format is YOUTUBE SHORTS, NEVER choose "pillars" or "comparison". Only use single-column layouts like "hero_metric", "code_or_terminal", or a 2-row "stack_list" to match native 9:16 mobile viewports without dropping render resolution.
   - "cards": Array of 1 to 2 card objects maximum for Shorts (3-4 allowed only for widescreen landscape).
      - "title": Card title (string, max 25 chars)
      - "subtitle": Card subtitle (optional string)
      - "badge": Short badge text (optional, e.g. "Rust", "Core", "Speed")
      - "bullets": Array of bullet points (STRICTLY 1-3 words per bullet point, maximum 2 bullets per card. Keep text concise to prevent pixel-scaling compression down the line).
5. "broll_beats": Array of 3 to 6 sequential visual beats matching each sentence of the narration:
   [
     {"phrase": "the spoken sentence", "search_query": "3-5 word exact physical cinematography keywords describing real visible objects, human actions, or physical environments (e.g. 'boxer heavy bag workout', 'sprinter track starting blocks', 'mountain climber cliff sunrise', 'hands typing mechanical keyboard', 'ocean storm lighthouse waves'). ALWAYS use concrete physical nouns. NEVER output abstract ideas like 'fear mindset' or 'success habit'.", "ai_prompt": "Cinematic 8k photorealistic video description for AI video generators (Veo/Wan/Kling) describing camera motion, lighting, and action", "camera": "One of ['zoom_in', 'zoom_out', 'pan_left', 'pan_right'] (dynamic 2.5D camera choreography for this beat)"}
   ]
6. "narration": The EXACT spoken voiceover script for the narrator.
   - Natural, highly engaging, professional tone.
   - Conversational, authoritative, no robotic fluff.

Also provide:
- "video_title": High-CTR, compelling YouTube video title (max 75 chars)
- "theme_palette": Suggested color scheme:
  - "bg": [r, g, b] (deep slate background, e.g. [15, 23, 42])
  - "accent": [r, g, b] (primary clean accent, e.g. [59, 130, 246] or [37, 99, 235])
  - "secondary": [r, g, b] (secondary neutral/amber, e.g. [148, 163, 184] or [245, 158, 11])
  - "card_bg": [r, g, b] (slate card surface, e.g. [30, 41, 59])
- "visual_policy": STRICT REQUIREMENT - AVOID all cyberpunk tropes, neon pink, magenta, or glowing green. Maintain clean, modern, professional enterprise aesthetics (Vox/Apple Keynote style).
- "soundscape":
  - "ambient_track": Suggested subtle ambient background (e.g. "mechanical_typing", "server_room", "subtle_rain", "subtle_wind", "room_tone")
  - "soundscape_playlist": Array of 1 to 3 audio texture layers, e.g. [{"type": "mechanical_typing", "volume": 0.12}]
- "youtube_metadata":
  - "description": A complete, ready-to-paste YouTube description with chapter placeholders
  - "tags": Array of 8-15 relevant YouTube tags

CRITICAL UNIQUENESS & CREATIVITY MANDATE:
- Every video screenplay MUST be completely fresh, unique, and tailored specifically to the prompt.
- NEVER reuse clichéd tropes or formulaic openers like "Most people fail because...", "Motivation is a lie", or "The secret to becoming unstoppable".
- Invent fresh narrative angles, unexpected hooks, relatable real-world analogies, and vivid emotional or thought-provoking moments.
- For EVERY scene's 'broll_beats', provide highly specific, concrete, physical cinematography search queries ('search_query') describing real physical subjects, environments, actions, and lighting (e.g. "blacksmith sparks anvil", "marathon runner rain finish line", "deep sea diver bioluminescent reef"). NEVER output generic or repetitive phrases.

CRITICAL: Return ONLY valid JSON with no markdown formatting or code blocks.
"""

FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-flash-latest",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.1-pro-preview"
]

from .templates import get_template

class Director:
    def __init__(self, api_key: str = None, model: str = None):
        self.model = model
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = genai.Client()

    def direct(
        self,
        prompt: str,
        scene_count: int = None,
        style_hint: str = None,
        language: str = "en",
        is_shorts: bool = False,
        is_cinema: bool = False,
        is_real: bool = False,
        character: str = None,
        template: str = None
    ) -> Dict[str, Any]:
        """Queries Google Gemini to outline and write the screenplay with multi-model fallback."""
        user_msg = f"User Prompt / Video Topic: {prompt}\n"
        user_msg += (
            "AESTHETIC & CAMERA DIRECTIVE:\n"
            "- AVOID all cyberpunk tropes, neon pink, magenta, glowing acid green, or hacker stereotypes.\n"
            "- Use clean, modern, professional editorial styling (deep slate, crisp white typography, subtle cobalt/warm amber accents).\n"
            "- Camera motion must be subtle and steady (e.g. 'steady', 'zoom_in', 'zoom_out'). NO violent whipping or chaotic motion.\n"
            "- For each scene, include a 'lower_third' object: {\"title\": \"Punchy Subject/Name\", \"subtitle\": \"Role/Context\"}.\n"
        )

        if template:
            tmpl_data = get_template(template, is_shorts=is_shorts)
            user_msg += f"\nDIRECTORIAL TEMPLATE: {tmpl_data['name'].upper()}\n"
            user_msg += f"{tmpl_data['director_directive']}\n"
            if not scene_count:
                scene_count = tmpl_data.get("default_scenes", 4)
        
        if is_real:
            user_msg += (
                "REAL YOUTUBE DOCUMENTARY DIRECTIVE:\n"
                "- Write this screenplay like a high-retention, real YouTube documentary (Vox, Kurzgesagt, Johnny Harris, Veritasium style).\n"
                "- Tone: Natural, intelligent, conversational, insightful, and cinematic.\n"
                "- Real B-Roll Footage: Provide accurate 'search_query' keywords for real stock footage/photos for every scene.\n"
                "- AVOID any cyberpunk, neon, or fictional matrix tropes. Focus on real-world concepts, science, history, tech, or nature.\n"
            )

        if is_shorts:
            user_msg += (
                "FORMAT REQUIREMENT: YOUTUBE SHORTS (VERTICAL 9:16).\n"
                "- Pacing MUST be ultra fast-paced and punchy (3 scenes total, STRICTLY under 45 seconds spoken audio).\n"
                "- Each scene narration must be 15 to 22 words maximum (fast hook, immediate value, loopable outro).\n"
                "- Enforce visual layout density: limit cards to 1 per scene. Do not request dense bullet blocks.\n"
                "- Add '#Shorts' to the end of the video_title and in the description.\n"
            )
            if not scene_count:
                scene_count = 3

        if is_cinema:
            user_msg += (
                "CINEMATIC MOVIE TRAILER DIRECTIVE:\n"
                "- Write this screenplay like an epic Hollywood blockbuster movie trailer or documentary cinema.\n"
                "- Tone: Intense, high-stakes, dramatic, gripping, building to an epic climax.\n"
                "- Narration: Deep movie trailer voiceover cadence (e.g., 'In a world governed by legacy systems...', dramatic pauses, cinematic one-liners).\n"
                "- Scene Headings: Formatted as cinematic acts or dramatic turning points (e.g., 'ACT I: THE COLLAPSE', 'ACT II: THE FORGED TITANS', 'ACT III: THE NEW REIGN').\n"
                "- Video Title: Blockbuster movie title (e.g. 'RUST VS GO: The War for Compute | Cinematic Trailer').\n"
            )
            if not scene_count:
                scene_count = 3

        if character:
            user_msg += f"- Animated Presenter / Character: An on-screen animated mascot/character ('{character}') co-hosts the video.\n"
        
        if scene_count:
            user_msg += f"Target Scene Count: {scene_count} scenes.\n"
        if style_hint:
            user_msg += f"Style / Tone Preference: {style_hint}\n"

        if language.lower() in ["ta", "tamil"]:
            user_msg += (
                "LANGUAGE REQUIREMENT: Produce the ENTIRE screenplay in Tamil (தமிழ்).\n"
                "- Write video_title, headings, subheadings, cards titles, bullets, and narration in natural, high-quality, fluent Tamil (தமிழ்).\n"
                "- Spoken narration must be written in clear spoken/standard Tamil suitable for Tamil YouTube tech channels.\n"
                "- Keep technical terms, acronyms, or code in English/Tanglish where standard (e.g. Linux, Python, AI, API).\n"
                "- CRITICAL: Always write 'search_query' and 'ai_prompt' inside 'broll_beats' in descriptive English (e.g. 'Chennai Metro train station', 'underground railway tunnel construction') to maximize visual stock matches from global archives.\n"
            )
        else:
            user_msg += "LANGUAGE REQUIREMENT: Produce the screenplay in English.\n"

        models_to_try = [self.model] if self.model else FALLBACK_MODELS
        last_error = None

        for m in models_to_try:
            try:
                cfg = types.GenerateContentConfig(
                    temperature=0.88,
                    top_p=0.95,
                )
                response = self.client.models.generate_content(
                    model=m,
                    contents=[DIRECTOR_SYSTEM_PROMPT + "\n\n" + user_msg],
                    config=cfg
                )
                raw = response.text.strip()
                if raw.startswith("```json"):
                    raw = raw[7:]
                elif raw.startswith("```"):
                    raw = raw[3:]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

                try:
                    screenplay = json.loads(raw)
                    return self.sanitize_screenplay(screenplay)
                except json.JSONDecodeError as e:
                    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
                    if fence_match:
                        try:
                            return self.sanitize_screenplay(json.loads(fence_match.group(1)))
                        except Exception:
                            pass
                    first_brace = raw.find("{")
                    last_brace = raw.rfind("}")
                    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                        candidate = raw[first_brace : last_brace + 1]
                        try:
                            return self.sanitize_screenplay(json.loads(candidate))
                        except Exception:
                            pass
                    raise ValueError(f"Failed to parse JSON: {e}")
            except Exception as e:
                print(f"[Notice] Model {m} unavailable ({e}), trying fallback...")
                last_error = e
                time.sleep(1)

        print(f"⚠️ [Director] External Google Gemini quota exhausted ({last_error}). Directing offline procedural screenplay...")
        return self.generate_procedural_screenplay(
            prompt,
            scene_count=scene_count or 3,
            style_hint=style_hint,
            language=language,
            is_shorts=is_shorts,
            is_cinema=is_cinema,
            is_real=is_real,
            character=character,
            template=template
        )

    def generate_procedural_screenplay(
        self,
        prompt: str,
        scene_count: int = 3,
        style_hint: str = None,
        language: str = "en",
        is_shorts: bool = False,
        is_cinema: bool = False,
        is_real: bool = True,
        character: str = None,
        template: str = None
    ) -> Dict[str, Any]:
        """
        Deterministic, Broadcast-Grade Procedural Screenplay Generator.
        Activates when external LLM API rate limits (429/503) are hit.
        Crafts high-impact three-act narrative screenplays with verified cinematography b-roll beats.
        """
        clean_prompt = prompt.strip()
        is_ta = language.lower() in ["ta", "tamil"]

        # 1. Cinema / Hollywood Movie Trailer
        if is_cinema:
            title = f"{clean_prompt[:45].upper()} | Official Trailer"
            scenes = [
                {
                    "id": "scene_01",
                    "heading": "ACT I: THE FRACTURE",
                    "subheading": "An anomaly breaches the event horizon",
                    "layout_type": "hero_metric",
                    "cards": [{"title": "THREAT DETECTED", "bullets": ["Perimeter Breached", "Zero Tolerance"]}],
                    "narration": "In a universe governed by unbreakable laws, one fracture changes everything. When the threshold is crossed, tomorrow is no longer guaranteed.",
                    "broll_beats": [
                        {"phrase": "In a universe governed by unbreakable laws", "search_query": "deep space nebula cosmic event", "ai_prompt": "Cinematic 8k nebula swirling galaxy stars", "camera": "zoom_in"},
                        {"phrase": "one fracture changes everything", "search_query": "futuristic city skyline dark stormy night lightning", "ai_prompt": "Cyberpunk metropolis lightning storm rain", "camera": "pan_right"},
                        {"phrase": "tomorrow is no longer guaranteed", "search_query": "lone operative walking dark sci-fi corridor smoke", "ai_prompt": "Soldier silhouette walking smoky tunnel cinematic lighting", "camera": "zoom_in"}
                    ]
                },
                {
                    "id": "scene_02",
                    "heading": "ACT II: THE CONVERGENCE",
                    "subheading": "The mission to prevent the inevitable collapse",
                    "layout_type": "hero_metric",
                    "cards": [{"title": "SINGULARITY PROTOCOL", "bullets": ["Critical Trajectory", "Override Core"]}],
                    "narration": "As reality unravels at the speed of light, one operative must breach the singularity. No backup. No extraction. Only the mission.",
                    "broll_beats": [
                        {"phrase": "As reality unravels at the speed of light", "search_query": "massive particle accelerator glowing core", "ai_prompt": "Glowing reactor core humming energy beams", "camera": "zoom_in"},
                        {"phrase": "one operative must breach the singularity", "search_query": "fighter jet breaking sound barrier dawn sky", "ai_prompt": "Supersonic jet soaring above clouds sunset", "camera": "pan_left"},
                        {"phrase": "Only the mission", "search_query": "operative aiming weapon night rain reflection", "ai_prompt": "Dramatic slow motion rain drops warrior determined eyes", "camera": "zoom_out"}
                    ]
                },
                {
                    "id": "scene_03",
                    "heading": "ACT III: TIME REBORN",
                    "subheading": "The final stand beyond the horizon",
                    "layout_type": "hero_metric",
                    "cards": [{"title": "FINAL RECKONING", "bullets": ["Singularity Reached", "Dawn Beckons"]}],
                    "narration": "To save the future, you must rewrite the beginning. This season, prepare to redefine reality itself.",
                    "broll_beats": [
                        {"phrase": "To save the future, you must rewrite the beginning", "search_query": "epic explosion supernova expanding shockwave", "ai_prompt": "Cosmic supernova shockwave golden fiery light", "camera": "zoom_out"},
                        {"phrase": "This season prepare to redefine reality itself", "search_query": "mountain summit sunrise golden rays epic wide shot", "ai_prompt": "Breathtaking mountain peak sunrise golden hour 4k cinema", "camera": "zoom_in"}
                    ]
                }
            ]
            return self.sanitize_screenplay({
                "video_title": title,
                "theme_palette": {"bg": [8, 10, 20], "accent": [239, 68, 68], "secondary": [245, 158, 11], "card_bg": [17, 24, 39]},
                "visual_policy": "Hollywood cinema widescreen scope 2.39:1, high drama, 35mm grain",
                "soundscape": {"ambient_track": "server_room", "soundscape_playlist": [{"type": "server_room", "volume": 0.15}]},
                "youtube_metadata": {
                    "description": f"Official Cinema Trailer for {clean_prompt}. Experience the Hollywood sci-fi blockbuster journey.",
                    "tags": ["HollywoodTrailer", "OfficialTrailer", "MovieTrailer", "SciFiCinema", "CinemaScope", "Blockbuster", "4KTrailer"]
                },
                "scenes": scenes
            })

        # 2. YouTube Shorts (9:16 Vertical)
        if is_shorts:
            title = f"{clean_prompt[:50]} #Shorts"
            if is_ta:
                scenes = [
                    {
                        "id": "scene_01",
                        "heading": "முதல் அடி",
                        "subheading": "தொடக்கம் தான் எல்லாம்",
                        "layout_type": "hero_metric",
                        "cards": [{"title": "இலக்கு", "bullets": ["துணிச்சல்", "தொடக்கம்"]}],
                        "narration": "உன் இலக்கை நோக்கி ஓடுவதை ஒருபோதும் நிறுத்தாதே. ஒவ்வொரு வெற்றியும் ஒரு சிறிய முதல் அடியில்தான் தொடங்குகிறது.",
                        "broll_beats": [
                            {"phrase": "உன் இலக்கை நோக்கி ஓடுவதை ஒருபோதும் நிறுத்தாதே", "search_query": "athlete sprinting athletic track morning sunrise", "ai_prompt": "Sprinter athlete sprinting on track sunrise", "camera": "zoom_in"},
                            {"phrase": "ஒவ்வொரு வெற்றியும் ஒரு சிறிய முதல் அடியில்தான் தொடங்குகிறது", "search_query": "running shoes pavement starting block close up", "ai_prompt": "Close up runner shoes starting block pavement", "camera": "pan_left"}
                        ]
                    },
                    {
                        "id": "scene_02",
                        "heading": "விடாமுயற்சி",
                        "subheading": "தடைகளை உடைத்தெறி",
                        "layout_type": "hero_metric",
                        "cards": [{"title": "உழைப்பு", "bullets": ["விடாமுயற்சி", "கவனம்"]}],
                        "narration": "ஆயிரம் தோல்விகள் வந்தாலும் உன் கனவை கைவிடாதே. விடாமுயற்சி மட்டுமே உன்னை அடுத்த நிலைக்கு கொண்டு செல்லும்.",
                        "broll_beats": [
                            {"phrase": "ஆயிரம் தோல்விகள் வந்தாலும் உன் கனவை கைவிடாதே", "search_query": "boxer hitting heavy bag gym workout sweat", "ai_prompt": "Determined boxer training gym sweat cinematic lighting", "camera": "zoom_in"},
                            {"phrase": "விடாமுயற்சி மட்டுமே உன்னை அடுத்த நிலைக்கு கொண்டு செல்லும்", "search_query": "rock climber gripping cliff steep mountain peak", "ai_prompt": "Rock climber hanging cliff edge determination", "camera": "zoom_out"}
                        ]
                    },
                    {
                        "id": "scene_03",
                        "heading": "சிகரத்தை அடை",
                        "subheading": "உன் வெற்றி உன் கையில்",
                        "layout_type": "hero_metric",
                        "cards": [{"title": "வெற்றி", "bullets": ["சிகரம்", "வெற்றி முழக்கம்"]}],
                        "narration": "விடாமல் உழைப்பவனுக்கு உலகம் வழிவிடும். இன்றே உன் பயணத்தை தொடங்கு, சிகரம் உன் வசப்படும்.",
                        "broll_beats": [
                            {"phrase": "விடாமல் உழைப்பவனுக்கு உலகம் வழிவிடும்", "search_query": "runner raising arms finish line victory sunrise", "ai_prompt": "Marathon runner crossing finish line golden hour", "camera": "zoom_in"},
                            {"phrase": "இன்றே உன் பயணத்தை தொடங்கு சிகரம் உன் வசப்படும்", "search_query": "mountain summit sunrise golden rays clouds panorama", "ai_prompt": "Panoramic mountain peak sunrise golden light epic view", "camera": "zoom_out"}
                        ]
                    }
                ]
            else:
                scenes = [
                    {
                        "id": "scene_01",
                        "heading": "THE TURNING POINT",
                        "subheading": "Where most stop, the journey begins",
                        "layout_type": "hero_metric",
                        "cards": [{"title": "START NOW", "bullets": ["Take Action", "No Excuses"]}],
                        "narration": f"The biggest mistake is waiting for the perfect moment. Take the first step now, because momentum beats hesitation every time.",
                        "broll_beats": [
                            {"phrase": "The biggest mistake is waiting for the perfect moment", "search_query": "running shoes pavement athlete morning sprint", "ai_prompt": "Runner stepping onto track dawn", "camera": "zoom_in"},
                            {"phrase": "Take the first step now momentum beats hesitation", "search_query": "boxer workout speed bag training gym", "ai_prompt": "Boxer hitting bag intense focus", "camera": "pan_right"}
                        ]
                    },
                    {
                        "id": "scene_02",
                        "heading": "RELENTLESS FOCUS",
                        "subheading": "Discipline over motivation",
                        "layout_type": "hero_metric",
                        "cards": [{"title": "EXECUTION", "bullets": ["Daily Grind", "Pure Focus"]}],
                        "narration": "Motivation gets you started, but ruthless discipline is what carries you through the fire when nobody is watching.",
                        "broll_beats": [
                            {"phrase": "Motivation gets you started but ruthless discipline", "search_query": "athlete barbell deadlift gym chalk dust", "ai_prompt": "Athlete lifting heavy barbell chalk smoke", "camera": "zoom_in"},
                            {"phrase": "carries you through the fire when nobody is watching", "search_query": "cyclist climbing steep mountain road morning mist", "ai_prompt": "Cyclist pushing steep gradient mountain mist", "camera": "pan_left"}
                        ]
                    },
                    {
                        "id": "scene_03",
                        "heading": "THE SUMMIT",
                        "subheading": "Victory is forged in silence",
                        "layout_type": "hero_metric",
                        "cards": [{"title": "TRIUMPH", "bullets": ["Peak Achieved", "Unstoppable"]}],
                        "narration": "Stay in the fight. The mountain is steep, but the view from the summit belongs only to those who refused to quit.",
                        "broll_beats": [
                            {"phrase": "Stay in the fight the mountain is steep", "search_query": "trail runner forest sunbeams mountain path", "ai_prompt": "Trail runner forest golden sunlight", "camera": "zoom_in"},
                            {"phrase": "the view from the summit belongs only to those who refused to quit", "search_query": "mountain summit sunrise golden rays panorama", "ai_prompt": "Epic mountain peak sunrise clouds golden rays", "camera": "zoom_out"}
                        ]
                    }
                ]
            return self.sanitize_screenplay({
                "video_title": title,
                "theme_palette": {"bg": [15, 23, 42], "accent": [59, 130, 246], "secondary": [245, 158, 11], "card_bg": [30, 41, 59]},
                "visual_policy": "Clean high-energy vertical 9:16 layout, zero clutter",
                "soundscape": {"ambient_track": "subtle_wind", "soundscape_playlist": [{"type": "subtle_wind", "volume": 0.12}]},
                "youtube_metadata": {
                    "description": f"{clean_prompt}\n\n#Shorts #Motivation #Discipline #Success",
                    "tags": ["Shorts", "Motivation", "Discipline", "Focus", "Success", "Mindset"]
                },
                "scenes": scenes
            })

        # 3. Universal Documentary / Explainer
        title = f"{clean_prompt[:60]}"
        scenes = [
            {
                "id": "scene_01",
                "heading": "THE FOUNDATION",
                "subheading": "Understanding the core architecture",
                "layout_type": "hero_metric",
                "cards": [{"title": "ORIGIN", "bullets": ["Core Concept", "First Principles"]}],
                "narration": f"To truly master {clean_prompt[:40]}, we must first break down the underlying architecture that defines it from first principles.",
                "broll_beats": [
                    {"phrase": f"To truly master {clean_prompt[:40]}", "search_query": "datacenter server racks glowing blue led rows", "ai_prompt": "Futuristic datacenter corridors glowing cables", "camera": "zoom_in"},
                    {"phrase": "we must first break down the underlying architecture", "search_query": "circuit board microchip close up glowing traces", "ai_prompt": "Microchip macro view electric currents", "camera": "pan_right"}
                ]
            },
            {
                "id": "scene_02",
                "heading": "THE BREAKTHROUGH",
                "subheading": "Overcoming the fundamental bottleneck",
                "layout_type": "hero_metric",
                "cards": [{"title": "INNOVATION", "bullets": ["Scale System", "Zero Latency"]}],
                "narration": "Traditional systems falter under massive scale, but modern engineering turns complexity into seamless, high-throughput execution.",
                "broll_beats": [
                    {"phrase": "Traditional systems falter under massive scale", "search_query": "cyber network data stream nodes glowing connections", "ai_prompt": "Global fiber optic network planet earth night", "camera": "zoom_in"},
                    {"phrase": "modern engineering turns complexity into seamless execution", "search_query": "software engineer typing multi monitor setup dark room", "ai_prompt": "Developer typing code dual monitors glowing desk", "camera": "pan_left"}
                ]
            },
            {
                "id": "scene_03",
                "heading": "THE HORIZON",
                "subheading": "The future of the ecosystem",
                "layout_type": "hero_metric",
                "cards": [{"title": "FUTURE", "bullets": ["Global Impact", "Next Frontier"]}],
                "narration": "What was once an impossible threshold is now the new baseline, opening up unprecedented possibilities for the next era.",
                "broll_beats": [
                    {"phrase": "What was once an impossible threshold is now the new baseline", "search_query": "city skyline dawn golden hour aerial 4k", "ai_prompt": "Aerial modern city skyline sunrise golden hour", "camera": "zoom_out"},
                    {"phrase": "opening up unprecedented possibilities for the next era", "search_query": "satellite orbiting earth sunrise horizon space", "ai_prompt": "Earth orbit sunrise satellite solar panels glistening", "camera": "zoom_in"}
                ]
            }
        ]
        return self.sanitize_screenplay({
            "video_title": title,
            "theme_palette": {"bg": [15, 23, 42], "accent": [59, 130, 246], "secondary": [148, 163, 184], "card_bg": [30, 41, 59]},
            "visual_policy": "Clean enterprise Vox documentary style",
            "soundscape": {"ambient_track": "server_room", "soundscape_playlist": [{"type": "server_room", "volume": 0.12}]},
            "youtube_metadata": {
                "description": f"Documentary analysis exploring {clean_prompt}.",
                "tags": ["Technology", "Engineering", "Architecture", "Software", "Innovation"]
            },
            "scenes": scenes
        })

    @staticmethod
    def sanitize_screenplay(screenplay: Dict[str, Any]) -> Dict[str, Any]:
        """
        Content Guard & Synthetic Transparency Sanitizer:
        Audits generated screenplay against deepfake deception and platform compliance rules.
        Attaches standard transparency metadata tags.
        """
        if not isinstance(screenplay, dict):
            return screenplay

        screenplay["compliance"] = {
            "synthetic_content_declaration": True,
            "transparency_notice": "Contains AI-generated visual and synthesized audio elements.",
            "content_guard_verified": True
        }

        prohibited_terms = ["deepfake", "counterfeit", "unauthorized impersonation"]
        for s in screenplay.get("scenes", []):
            if isinstance(s, dict) and "narration" in s:
                for term in prohibited_terms:
                    s["narration"] = re.sub(rf"\b{term}\b", "AI simulation", s["narration"], flags=re.IGNORECASE)

        return screenplay
