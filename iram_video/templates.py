"""
Video Template & Genre Architecture for IRAM Video.
Provides structured directorial blueprints, pacing curves, layout sequences,
and visual formatting rules for universal video genres, including:
- explainer: Standard deep-dive documentary (Vox, Kurzgesagt, Veritasium)
- tutorial: Step-by-step educational guide with practical milestones
- listicle: High-retention countdown (#5 through #1) with rank badges
- comparison: Head-to-head matchup (Product A vs B) with verdict
- news: Breaking broadcast bulletin with lower-third chyrons and ticker
- promo: High-energy marketing showcase with problem, solution, and CTA
- podcast: Audiogram soundbite card with waveform and speaker attribution
"""

from typing import Dict, Any, List, Optional

VIDEO_TEMPLATES = {
    "explainer": {
        "name": "Deep-Dive Explainer",
        "description": "Insightful documentary deep-dive explaining complex mechanisms with clarity and authority.",
        "default_scenes": 4,
        "default_music": "documentary",
        "default_grade": "clean",
        "structure": [
            {"role": "The Hook & Paradox", "layout": "hero_metric", "motion": "steady_push_in"},
            {"role": "The Core Architecture", "layout": "pillars", "motion": "macro_orbit"},
            {"role": "Deep Technical Breakdown", "layout": "code_or_terminal", "motion": "steady"},
            {"role": "Future Implications & Synthesis", "layout": "stack_list", "motion": "zoom_out"}
        ],
        "director_directive": (
            "TEMPLATE: EXPLAINER DOCUMENTARY.\n"
            "- Act I: Hook with an intriguing paradox or real-world friction.\n"
            "- Act II: Deconstruct the fundamental principles with clear visual anchors.\n"
            "- Act III: Walk through concrete implementation or case study.\n"
            "- Act IV: Synthesize the broader implications and future outlook.\n"
            "- Tone: Authoritative, conversational, intellectual, like Vox or Veritasium."
        )
    },
    "tutorial": {
        "name": "Step-by-Step Tutorial & How-To",
        "description": "Structured instructional walkthrough guiding the viewer from prerequisites to completed implementation.",
        "default_scenes": 5,
        "default_music": "lofi",
        "default_grade": "clean",
        "structure": [
            {"role": "Objective & Prerequisites", "layout": "hero_metric", "badge": "SETUP"},
            {"role": "Step 1: Foundation & Installation", "layout": "code_or_terminal", "badge": "STEP 1"},
            {"role": "Step 2: Core Configuration", "layout": "code_or_terminal", "badge": "STEP 2"},
            {"role": "Step 3: Verification & Execution", "layout": "code_or_terminal", "badge": "STEP 3"},
            {"role": "Summary & Pro Tips", "layout": "stack_list", "badge": "PRO TIPS"}
        ],
        "director_directive": (
            "TEMPLATE: STEP-BY-STEP TUTORIAL.\n"
            "- Scene 1: Objective — What we are building and what prerequisites are needed.\n"
            "- Scene 2: Step 1 — Initial setup, installation, or foundation.\n"
            "- Scene 3: Step 2 — Core implementation logic and configuration.\n"
            "- Scene 4: Step 3 — Testing, deployment, or verification of results.\n"
            "- Scene 5: Common pitfalls, optimization pro tips, and conclusion.\n"
            "- Include exact code snippets, terminal commands, or step numbers for each scene.\n"
            "- Tone: Encouraging, precise, pedagogical, clear."
        )
    },
    "listicle": {
        "name": "Top-N Countdown / Listicle",
        "description": "High-retention ranked countdown highlighting standout entries with rank shields and key metrics.",
        "default_scenes": 5,
        "default_music": "energetic",
        "default_grade": "vibrant",
        "structure": [
            {"role": "Viral Hook & Why It Matters", "layout": "hero_metric", "badge": "COUNTDOWN"},
            {"role": "Rank #4", "layout": "pillars", "badge": "#4"},
            {"role": "Rank #3", "layout": "pillars", "badge": "#3"},
            {"role": "Rank #2", "layout": "pillars", "badge": "#2"},
            {"role": "Rank #1 Winner & Final Takeaway", "layout": "hero_metric", "badge": "#1 WINNER"}
        ],
        "director_directive": (
            "TEMPLATE: TOP-N COUNTDOWN LISTICLE.\n"
            "- Scene 1: High-energy opening hook establishing why this ranking matters.\n"
            "- Subsequent scenes: Ranked countdown from lowest to highest (#4 -> #3 -> #2 -> #1 WINNER).\n"
            "- Each ranked scene MUST feature the entry's name, key metrics, and standout advantage.\n"
            "- Final scene: Unveil the #1 Winner with emphatic praise and summary verdict.\n"
            "- Tone: Fast-paced, punchy, engaging, high retention."
        )
    },
    "comparison": {
        "name": "Head-to-Head Comparison",
        "description": "Objective side-by-side analysis contrasting two contenders across features, performance, and trade-offs.",
        "default_scenes": 4,
        "default_music": "tech",
        "default_grade": "clean",
        "structure": [
            {"role": "The Matchup & Contenders", "layout": "comparison", "badge": "VS"},
            {"role": "Core Performance & Architecture", "layout": "comparison", "badge": "BENCHMARK"},
            {"role": "Developer Experience & Trade-offs", "layout": "comparison", "badge": "TRADEOFFS"},
            {"role": "Final Verdict & Recommendation", "layout": "hero_metric", "badge": "VERDICT"}
        ],
        "director_directive": (
            "TEMPLATE: HEAD-TO-HEAD COMPARISON.\n"
            "- Scene 1: Introduce the two contenders, their philosophies, and why the choice matters.\n"
            "- Scene 2: Direct performance/speed/cost benchmark comparison.\n"
            "- Scene 3: Ecosystem, ergonomics, and real-world trade-offs.\n"
            "- Scene 4: Clear verdict on who should pick Contender A vs Contender B.\n"
            "- Ensure cards use layout_type 'comparison' with symmetric pros/cons.\n"
            "- Tone: Objective, nuanced, data-driven, practical."
        )
    },
    "news": {
        "name": "Breaking News & Editorial Bulletin",
        "description": "Urgent broadcast news format with headline tickers, chyrons, facts, and expert analysis.",
        "default_scenes": 4,
        "default_music": "trailer",
        "default_grade": "editorial",
        "structure": [
            {"role": "Breaking Bulletin & Primary Headline", "layout": "hero_metric", "badge": "BREAKING"},
            {"role": "Verified Facts & Timeline", "layout": "stack_list", "badge": "DEVELOPING"},
            {"role": "Industry Reaction & Quotes", "layout": "pillars", "badge": "ANALYSIS"},
            {"role": "Key Takeaways & What Follows", "layout": "hero_metric", "badge": "OUTLOOK"}
        ],
        "director_directive": (
            "TEMPLATE: BREAKING NEWS & EDITORIAL BULLETIN.\n"
            "- Scene 1: Immediate breaking alert with headline, timestamp, and core event.\n"
            "- Scene 2: Timeline of verified facts and chronological developments.\n"
            "- Scene 3: Industry reaction, expert statements, or official responses.\n"
            "- Scene 4: Strategic impact, market consequences, and next milestones.\n"
            "- Include lower-third metadata and punchy journalistic headlines.\n"
            "- Tone: Urgent, authoritative, journalistic, credible."
        )
    },
    "promo": {
        "name": "Product Launch & SaaS Promo",
        "description": "High-conversion marketing showcase moving from customer pain to breakthrough product demo and CTA.",
        "default_scenes": 4,
        "default_music": "energetic",
        "default_grade": "vibrant",
        "structure": [
            {"role": "The Friction & Broken Way", "layout": "hero_metric", "badge": "THE PROBLEM"},
            {"role": "Introducing the Breakthrough", "layout": "pillars", "badge": "THE SOLUTION"},
            {"role": "Feature Superpowers & Proof", "layout": "stack_list", "badge": "FEATURES"},
            {"role": "Call-to-Action & Launch Offer", "layout": "hero_metric", "badge": "GET STARTED"}
        ],
        "director_directive": (
            "TEMPLATE: PRODUCT LAUNCH & PROMO.\n"
            "- Scene 1: Highlight the painful problem and current inefficient status quo.\n"
            "- Scene 2: Reveal the product/solution as the modern, effortless alternative.\n"
            "- Scene 3: Showcase 3 killer features with clear tangible benefits.\n"
            "- Scene 4: Irresistible Call-to-Action (CTA) urging viewers to start, star, or visit.\n"
            "- Tone: Inspiring, high energy, crisp, persuasive."
        )
    },
    "podcast": {
        "name": "Podcast Audiogram & Soundbite",
        "description": "Conversational audio showcase featuring quotes, speaker badges, soundbites, and insights.",
        "default_scenes": 3,
        "default_music": "lofi",
        "default_grade": "warm_editorial",
        "structure": [
            {"role": "Provocative Question or Quote", "layout": "hero_metric", "badge": "CLIP"},
            {"role": "Core Insight & Discussion", "layout": "pillars", "badge": "DEEP DIVE"},
            {"role": "Full Episode Invitation", "layout": "hero_metric", "badge": "FULL EPISODE"}
        ],
        "director_directive": (
            "TEMPLATE: PODCAST SOUNDBITE & AUDIOGRAM.\n"
            "- Scene 1: A powerful soundbite or provocative statement from the conversation.\n"
            "- Scene 2: Unpacking the underlying insight with conversational depth.\n"
            "- Scene 3: Memorable takeaway and invitation to hear the full episode.\n"
            "- Tone: Intimate, spontaneous, conversational, thought-provoking."
        )
    },
    "story": {
        "name": "Narrated Story",
        "description": "Fiction or true story with a beginning, turning point and resolution, told by a narrator.",
        "default_scenes": 6,
        "default_music": "cinematic",
        "default_grade": "cinematic",
        "is_real": True,
        "structure": [],
        "director_directive": (
            "TEMPLATE: NARRATED STORY.\n"
            "- Open in the middle of a concrete moment with a character the viewer can picture.\n"
            "- Build through a want, an obstacle and a turning point to a resolution that pays off the opening.\n"
            "- Use on-screen text sparingly; show places and actions in the visual beats.\n"
            "- Tone: Immersive storytelling, in the genre the prompt implies."
        )
    },
    "kids": {
        "name": "Kids & Learning",
        "description": "Cheerful, simple, age-appropriate learning video with repetition and big visuals.",
        "default_scenes": 5,
        "default_music": "lofi",
        "default_grade": "vibrant",
        "structure": [],
        "director_directive": (
            "TEMPLATE: KIDS & LEARNING.\n"
            "- Use short sentences and everyday words for young children. Teach one idea per scene.\n"
            "- Repeat the key idea, ask a simple question and pause for the child to answer.\n"
            "- Use a bright, friendly palette and keep content gentle and age-appropriate.\n"
            "- Tone: Warm, playful, patient."
        )
    },
    "travel": {
        "name": "Travel & Places",
        "description": "Destination film built on atmosphere, local detail and practical tips.",
        "default_scenes": 5,
        "default_music": "acoustic",
        "default_grade": "warm_editorial",
        "is_real": True,
        "structure": [],
        "director_directive": (
            "TEMPLATE: TRAVEL & PLACES.\n"
            "- Open with the single most striking view or feeling of the place.\n"
            "- Each scene covers one specific spot, dish or experience, with sensory detail.\n"
            "- Close with practical advice: when to go and what to skip.\n"
            "- Tone: Curious, warm, first-hand. Do not invent prices, opening hours or other facts you are unsure of."
        )
    },
    "recipe": {
        "name": "Recipe & Cooking",
        "description": "Clear cooking walkthrough from ingredients to the finished dish.",
        "default_scenes": 5,
        "default_music": "acoustic",
        "default_grade": "warm_editorial",
        "is_real": True,
        "structure": [],
        "director_directive": (
            "TEMPLATE: RECIPE & COOKING.\n"
            "- Scene 1: The finished dish and why it is worth making.\n"
            "- Scene 2: Ingredients with exact quantities on a card.\n"
            "- Middle scenes: One cooking step per scene with times, temperatures and visual cues of doneness.\n"
            "- Final scene: Serving suggestion and the most common mistake to avoid.\n"
            "- Tone: Friendly, precise, appetizing."
        )
    },
    "fitness": {
        "name": "Fitness & Workout",
        "description": "Guided routine with named exercises, form cues and timing.",
        "default_scenes": 5,
        "default_music": "energetic",
        "default_grade": "vibrant",
        "is_real": True,
        "structure": [],
        "director_directive": (
            "TEMPLATE: FITNESS & WORKOUT.\n"
            "- State who the routine is for and what equipment is needed.\n"
            "- One exercise per scene with sets or duration, the key form cue and an easier variation.\n"
            "- Finish with a cool-down, and advise stopping if anything hurts.\n"
            "- Tone: Encouraging, direct, energetic."
        )
    },
    "review": {
        "name": "Product Review",
        "description": "Honest review covering first impressions, real use, flaws and a verdict.",
        "default_scenes": 5,
        "default_music": "corporate",
        "default_grade": "clean",
        "is_real": True,
        "structure": [],
        "director_directive": (
            "TEMPLATE: PRODUCT REVIEW.\n"
            "- Lead with the verdict in one sentence, then earn it.\n"
            "- Cover what it does well, where it falls short, and who should not buy it.\n"
            "- Only state specs and measurements you are confident of, and never claim hands-on testing you cannot back up.\n"
            "- Tone: Candid, balanced, specific."
        )
    },
    "history": {
        "name": "History Documentary",
        "description": "Chronological account of people and events, with causes and consequences.",
        "default_scenes": 6,
        "default_music": "documentary",
        "default_grade": "vintage",
        "is_real": True,
        "structure": [],
        "director_directive": (
            "TEMPLATE: HISTORY DOCUMENTARY.\n"
            "- Open on one decisive moment, then step back to explain how it came about.\n"
            "- Anchor each scene with a date, a place and a named person.\n"
            "- Separate established fact from interpretation, and say where historians disagree.\n"
            "- Tone: Measured, vivid, accurate."
        )
    },
    "motivation": {
        "name": "Motivational Message",
        "description": "Short, sincere reflection built on one idea and one concrete action.",
        "default_scenes": 4,
        "default_music": "cinematic",
        "default_grade": "cinematic",
        "is_real": True,
        "structure": [],
        "director_directive": (
            "TEMPLATE: MOTIVATIONAL MESSAGE.\n"
            "- Build the whole video around one idea, shown through a specific real-life situation.\n"
            "- End with one small action the viewer can take today.\n"
            "- Tone: Sincere and grounded, not shouting or clichéd."
        )
    },
    "meditation": {
        "name": "Calm & Meditation",
        "description": "Slow guided relaxation with long pauses and nature visuals.",
        "default_scenes": 4,
        "default_music": "ambient",
        "default_grade": "warm_editorial",
        "is_real": True,
        "structure": [],
        "director_directive": (
            "TEMPLATE: CALM & MEDITATION.\n"
            "- Use very short, unhurried sentences and gentle invitations about breath and body.\n"
            "- Visual beats are slow natural scenes: water, forest, sky. No on-screen clutter.\n"
            "- Make no medical claims.\n"
            "- Tone: Soft, slow, reassuring."
        )
    }
}

def get_template(template_name: Optional[str], is_shorts: bool = False) -> Dict[str, Any]:
    """Retrieves template configuration with intelligent vertical aspect mapping filters."""
    if not template_name:
        tmpl = VIDEO_TEMPLATES["explainer"]
    else:
        key = template_name.lower().strip().replace("-", "_").replace(" ", "_")
        tmpl = VIDEO_TEMPLATES.get(key, VIDEO_TEMPLATES["explainer"])

    import copy
    res = copy.deepcopy(tmpl)

    # RETINA GRID OVERRIDE: Enforce vertical layout adaptations for Shorts viewport space
    if is_shorts:
        vertical_structure = []
        for scene in res.get("structure", []):
            mod_scene = dict(scene)
            # Convert landscape multi-column elements to single-column phone viewports
            if mod_scene.get("layout") in ["pillars", "comparison"]:
                mod_scene["layout"] = "hero_metric" if "Winner" in mod_scene.get("role", "") else "stack_list"
            vertical_structure.append(mod_scene)
        res["structure"] = vertical_structure

        # Inject layout warnings directly into the AI director constraints
        res["director_directive"] = res.get("director_directive", "") + (
            "\nCRITICAL MOBILE FORMAT REQUIREMENT:\n"
            "- Visual viewport is strictly 9:16 VERTICAL.\n"
            "- Enforce SINGLE-COLUMN card presentation structures only.\n"
            "- Never request side-by-side grids or dual horizontal items.\n"
            "- Limit cards to a maximum of 1 or 2 items stacked vertically to preserve clear font details.\n"
        )

    res["default_color_grade"] = res.get("default_grade", "clean")
    res["directorial_hints"] = res.get("director_directive", "")
    return res

def list_templates() -> List[Dict[str, Any]]:
    """Returns catalog of all supported video templates."""
    catalog = []
    for k, v in VIDEO_TEMPLATES.items():
        catalog.append({
            "key": k,
            "name": v["name"],
            "description": v["description"],
            "default_scenes": v["default_scenes"],
            "default_music": v["default_music"],
            "default_grade": v["default_grade"]
        })
    return catalog
