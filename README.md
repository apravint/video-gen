# 🎬 Video-Gen: Universal High-Quality Video & Film AI Engine (English & தமிழ்)

An autonomous, production-grade video generation engine that transforms **any natural language prompt, technical codebase, or screenplay into broadcast-quality 1080p MP4 videos, YouTube Shorts, cinema trailers, and animated short films**.

[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-69%20passed-brightgreen.svg)](tests/)
[![CI](https://github.com/apravint/video-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/apravint/video-gen/actions)
[![Bilingual](https://img.shields.io/badge/languages-English%20%7C%20%E0%AE%A4%E0%AE%AE%E0%AE%BF%E0%AE%B4%E0%AF%8D-purple.svg)]()

---

## 📦 Installation

```bash
git clone https://github.com/apravint/video-gen.git
cd video-gen

# Install in editable mode:
pip install -e .

# Verify CLI binaries are installed:
video-gen --help
iram-video --help
```

---

## 🏛️ Comprehensive Architecture & Model Hub

```
User Prompt / Repo / Screenplay 
              │
              ▼
   🧠 Google Gemini 3.8 Flash (AI Creative Director & Dramatist)
              │
    ┌─────────┴────────────────────────┬────────────────────────┐
    ▼                                  ▼                        ▼
Screenplay & Shotcraft         Neural Voice Engine      Visual Synthesis Hub
• 12 Cinematic Shot Recipes    • Studio Edge Neural     • Google Veo 3.1 / 2.0
• Hollywood Tension Curves     • EBU R128 (-16 LUFS)    • Alibaba Wan 2.2 / 2.1
• Multi-Character Continuity   • 80Hz Cut + 3.2kHz EQ   • Tencent HunyuanVideo
                                                        • Zhipu CogVideoX
                                                        • NVIDIA Sana Linear DiT
                                                        • LivePortrait Avatars
                                                        • Verified 4K B-Roll
    │                                  │                        │
    └──────────────────────────────────┼────────────────────────┘
                                       ▼
                       ⚙️ FFMPEG Master Compositor
                    • Dynamic Sidechain Ducking (-18dB)
                    • Retention Laser Progress Bar (9:16 Shorts)
                    • Mukta Malar HarfBuzz Unicode Typography
                    • 320kbps 48,000Hz Studio AAC Master
                                       │
                                       ▼
                    🎬 Master 1080p Video / Shorts (.mp4)
                    🖼️ High-CTR YouTube Thumbnail (.png)
                    📋 Chapters, SEO & Viral Hooks (.txt)
```

---

## 🌟 Integrated Superpowers

1. **Next-Gen Generative Video Model Hub**:
   - **Google Veo 3.1 / 2.0**: Native generative video synthesis with cinematic lighting.
   - **Alibaba Wan 2.2 / 2.1**: Advanced open-source 14B Diffusion Transformer video generation.
   - **Tencent HunyuanVideo**: 13B open video DiT with cinema-grade motion fluidity.
   - **Zhipu CogVideoX**: Spatial-temporal expert transformer video generator.
   - **NVIDIA Sana**: Linear DiT for ultra-fast, high-resolution keyframe rendering.
   - **HeyGen Hyperframes Engine**: Declarative HTML5/CSS3/GSAP motion graphics compiled directly into deterministic 60fps MP4 video clips.
2. **Shotcraft Recipe Cards (`--recipe`)**:
   - 12 production-ready cinematic shot recipes with camera and lens physics: `hero_reveal`, `macro_orbit`, `speed_ramp`, `isometric_exploded`, `dutch_angle_tension`, `terminal_glitch_scan`, `split_comparison`, `broll_whip_pan`.
3. **Digital Human & LivePortrait Talking Avatars (`--avatar`)**:
   - Turn any single portrait image into an audio-driven talking digital presenter with natural eye-blinking, head bobbing, and lip viseme synchronization. Composited as a floating lower-third Picture-in-Picture (PiP).
4. **Project-to-Video 'Brag' Mode (`--brag`)**:
   - Point `video-gen` at any local codebase or git repository. It inspects commit logs, README value propositions, and tech stacks to build an explosive 30-45s developer launch trailer.
5. **Short Drama & Character Consistency Registry**:
   - Maintains strict facial, attire, and persona consistency across multiple scenes or episodes with Hollywood dramatic tension curve scoring.
6. **Viral Retention Progress Bar & HarfBuzz Typography**:
   - Glowing retention laser bar for YouTube Shorts and TikTok.
   - Bundled `Mukta Malar` font with HarfBuzz complex shaping (`shaping=1`) guaranteeing 100% accurate Tamil ligatures (`க்ஷ`, `ஸ்ரீ`).
   - EBU R128 audio mastering (-16 LUFS) with 80Hz rumble filter and 3.2kHz vocal presence boost.

---

## 🚀 Quick Usage

### 1. Developer Project Launch Video (`--brag`)
```bash
# Ingest local repo and produce a 30s launch showcase:
video-gen --brag /path/to/my-repo --shorts --music cyber
```

### 2. Shotcraft Cinematic Product & Tech Showcase
```bash
# Cinema trailer using the 'hero_reveal' shotcraft recipe:
video-gen "Next-Gen Quantum Computing Chip" --recipe hero_reveal --cinema --music trailer
```

### 3. Digital Human Talking Presenter (`--avatar`)
```bash
# Composite an audio-driven talking avatar presenter in the corner:
video-gen "What is Kubernetes Architecture" --avatar ./presenter.jpg --real
```

### 4. Bilingual Tamil Documentary or Shorts (தமிழ்)
```bash
# Tamil documentary with EBU R128 mastered audio and retention progress bar:
video-gen "சென்னை மெட்ரோ இரண்டாம் கட்ட விரிவாக்கம்" --lang ta --voice valluvar --shorts --subtitles
```

### 5. Multi-Model AI Video Generation
```bash
# Generate with specific model hubs:
video-gen "A futuristic rover landing on Mars" --generator veo
video-gen "Cyberpunk detective in rainy Neo-Tokyo" --generator wan2.2
video-gen "Ancient temple at sunrise" --generator hunyuan
```

---

## 🎛️ CLI Options

| Argument | Description | Default |
| :--- | :--- | :--- |
| `prompt` | Topic, brief, or script in English or Tamil | — |
| `--brag` | Inspect a local codebase/repo and build a developer launch showcase | `None` |
| `--recipe` | Shotcraft cinematic recipe card (`hero_reveal`, `speed_ramp`, `macro_orbit`, etc.) | `None` |
| `--avatar` | Path to portrait image for digital human talking avatar PiP | `None` |
| `--generator` | Generative video backend (`auto`, `veo`, `wan2.2`, `hunyuan`, `cogvideo`, `sana`, `hyperframes`, `stock`) | `auto` |
| `--hyperframes` | Render declarative HTML5/CSS/GSAP scenes via HeyGen Hyperframes engine | `False` |
| `--shorts` | Compile as vertical 9:16 (1080x1920) with retention progress bar | `False` |
| `--cinema` | Compile as 24 FPS 2.39:1 Hollywood trailer with 35mm film grain | `False` |
| `--real` | Real documentary YouTube video with authentic stock & acoustic score | `False` |
| `--subtitles` | Burn kinetic subtitles into the video | `False` |
| `--subtitle-palette` | Subtitle color theme (`gold`, `hormozi`, `neon-cyan`, `fire-red`, `purple`, `white`) | `auto` |
| `--tension` | Apply dramatic tension curve and pacing analysis | `False` |
| `--serve` | Launch the browser Web Studio dashboard (default port 7860) | `False` |

---

## 📄 License
MIT License. Created for Creators, Developers, and Autonomous Media Agents.
