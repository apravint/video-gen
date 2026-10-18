import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import edge_tts

VOICE_MAP = {
    # English Voices
    "aria": "en-US-AriaNeural",            # Female English: Confident, clear (Default EN)
    "jenny": "en-US-JennyNeural",          # Female English: Friendly
    "emma": "en-US-EmmaNeural",            # Female English: Cheerful
    "christopher": "en-US-ChristopherNeural", # Male English: Authoritative tech
    "guy": "en-US-GuyNeural",              # Male English: Energetic
    "brian": "en-US-BrianNeural",          # Male English: Casual
    "eric": "en-US-EricNeural",            # Male English: Rational

    # IRAM VoiceStudio Sovereign Personas
    "jarvis": "en-US-ChristopherNeural",   # Calm, sophisticated AI copilot
    "samantha": "en-US-JennyNeural",       # Warm, conversationalist
    "cinema-narrator": "en-US-EricNeural", # Resonant, deep authoritative trailer voice
    "cyber-synth": "en-US-GuyNeural",      # Glitched energetic vocoded AI

    # Tamil Voices (தமிழ்)
    "pallavi": "ta-IN-PallaviNeural",      # Female Tamil: Friendly, positive (Default TA)
    "valluvar": "ta-IN-ValluvarNeural",    # Male Tamil: Friendly, authoritative
    "tamil-female": "ta-IN-PallaviNeural",
    "tamil-male": "ta-IN-ValluvarNeural",
    "tamil-tech": "ta-IN-PallaviNeural"
}


def extract_sentence_boundaries_from_words(word_timings: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
    """Groups millisecond word boundary events into coherent sentence beats with exact start/end durations."""
    if not word_timings:
        return []
    sentences = []
    curr_words = []
    for i, wt in enumerate(word_timings):
        curr_words.append(wt)
        is_last = (i == len(word_timings) - 1)
        w_text = wt["word"]
        has_punct = any(w_text.endswith(p) for p in [".", "!", "?", ";", "|", ":"])
        has_pause = False
        if not is_last:
            next_start = word_timings[i + 1]["start"]
            if next_start - wt["end"] >= 0.38:
                has_pause = True
        if has_punct or has_pause or is_last:
            s_text = " ".join(w["word"] for w in curr_words)
            s_start = curr_words[0]["start"]
            s_end = curr_words[-1]["end"]
            sentences.append({
                "text": s_text,
                "start": s_start,
                "end": s_end,
                "duration": round(max(0.8, s_end - s_start), 3)
            })
            curr_words = []
    return sentences


class VoiceSynthesizer:
    def __init__(self, voice_key: str = None, language: str = "en", rate: str = "+2%"):
        self.language = language.lower()
        if not voice_key or voice_key == "default":
            if self.language in ["ta", "tamil"]:
                self.voice = "ta-IN-PallaviNeural"
            else:
                self.voice = "en-US-AriaNeural"
        else:
            self.voice = VOICE_MAP.get(voice_key.lower(), voice_key)
            
        self.rate = rate

    def get_duration(self, audio_file: Path) -> float:
        if not audio_file.exists() or audio_file.stat().st_size == 0:
            return 3.0
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_file)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return max(0.5, float(res.stdout.strip()))
        except Exception:
            return 3.0

    @staticmethod
    def align_with_whisper(audio_file: Path, text: str = "") -> List[Dict[str, Any]]:
        """
        Attempts acoustic word-level alignment using Whisper / WhisperX / faster-whisper.
        Returns a word-level timestamp matrix: [{'word': str, 'start': float, 'end': float, 'duration': float}].
        Falls back gracefully if libraries or models are not installed.
        """
        # 1. Try faster_whisper
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(str(audio_file), word_timestamps=True)
            words = []
            for seg in segments:
                if hasattr(seg, "words") and seg.words:
                    for w in seg.words:
                        words.append({
                            "word": w.word.strip(),
                            "start": round(float(w.start), 3),
                            "end": round(float(w.end), 3),
                            "duration": round(float(w.end - w.start), 3)
                        })
            if words:
                return words
        except Exception:
            pass

        # 2. Try standard openai whisper
        try:
            import whisper
            model = whisper.load_model("tiny")
            result = model.transcribe(str(audio_file), word_timestamps=True)
            words = []
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    words.append({
                        "word": w["word"].strip(),
                        "start": round(float(w["start"]), 3),
                        "end": round(float(w["end"]), 3),
                        "duration": round(float(w["end"] - w["start"]), 3)
                    })
            if words:
                return words
        except Exception:
            pass

        return []

    async def _generate_single(self, scene: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
        sid = scene["id"]
        out_mp3 = output_dir / f"{sid}.mp3"
        word_timings = []
        audio_bytes = bytearray()

        active_voice = self.voice
        if scene.get("voice"):
            active_voice = VOICE_MAP.get(str(scene["voice"]).lower().strip(), scene["voice"])

        try:
            communicate = edge_tts.Communicate(
                scene["narration"],
                active_voice,
                rate=self.rate,
                boundary="WordBoundary"
            )
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    offset_sec = chunk["offset"] / 10_000_000.0
                    dur_sec = chunk["duration"] / 10_000_000.0
                    word_timings.append({
                        "word": chunk["text"],
                        "start": round(offset_sec, 3),
                        "end": round(offset_sec + dur_sec, 3),
                        "duration": round(dur_sec, 3)
                    })
            if audio_bytes:
                out_mp3.write_bytes(audio_bytes)
        except Exception as e:
            print(f"[Notice] edge-tts stream error for scene '{sid}': {e}")

        # CLI fallback if streaming yielded no bytes
        if not out_mp3.exists() or out_mp3.stat().st_size == 0:
            cmd = [
                "edge-tts",
                "--voice", active_voice,
                f"--rate={self.rate}",
                "--text", scene["narration"],
                "--write-media", str(out_mp3)
            ]
            try:
                proc = await asyncio.create_subprocess_exec(*cmd)
                await proc.wait()
            except Exception as e:
                print(f"[Notice] edge-tts fallback error for scene '{sid}': {e}")

        # Silent audio fallback if completely offline
        if not out_mp3.exists() or out_mp3.stat().st_size == 0:
            fallback_cmd = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-t", "3.0", "-q:a", "9", str(out_mp3)
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *fallback_cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()
            except Exception as e:
                print(f"[Notice] Silent audio fallback error for scene '{sid}': {e}")

        dur = self.get_duration(out_mp3)
        if not word_timings:
            whisper_timings = self.align_with_whisper(out_mp3, scene["narration"])
            if whisper_timings:
                word_timings = whisper_timings

        scene["audio_file"] = str(out_mp3.resolve())
        scene["duration"] = dur
        scene["word_timings"] = word_timings
        scene["sentence_timings"] = extract_sentence_boundaries_from_words(word_timings, scene["narration"])
        return scene

    async def generate_all(self, scenes: List[Dict[str, Any]], output_dir: Path) -> List[Dict[str, Any]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        sem = asyncio.Semaphore(4)

        async def _bounded_single(s):
            async with sem:
                return await self._generate_single(s, output_dir)

        tasks = [_bounded_single(s) for s in scenes]
        return await asyncio.gather(*tasks)

    def synthesize(self, scenes: List[Dict[str, Any]], output_dir: Path) -> List[Dict[str, Any]]:
        return asyncio.run(self.generate_all(scenes, output_dir))

    def synthesize_line(self, text: str, output_file: Path) -> float:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        # 1. Try sovereign IRAM Voice CLI if available
        if synthesize_with_iram_voice(text, output_file, voice=self.voice):
            return self.get_duration(output_file)

        # 2. Try Edge-TTS streaming
        try:
            communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
            communicate.save_sync(str(output_file))
        except Exception:
            cmd = [
                "edge-tts",
                "--voice", self.voice,
                f"--rate={self.rate}",
                "--text", text,
                "--write-media", str(output_file)
            ]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                fallback_cmd = [
                    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", "3.0", "-q:a", "9", str(output_file)
                ]
                subprocess.run(fallback_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return self.get_duration(output_file)

    @staticmethod
    def trim_silence(audio_file: Path, out_path: Path = None, threshold_db: float = -40.0) -> Path:
        """
        Trims leading and trailing dead silence from speech audio files using FFmpeg silenceremove
        (ported from Automated-Video-Generator voice pacing engine).
        Improves video retention and pacing.
        """
        audio_file = Path(audio_file)
        if not audio_file.exists() or audio_file.stat().st_size == 0:
            return audio_file

        target = Path(out_path) if out_path else audio_file.with_name(f"{audio_file.stem}_trimmed{audio_file.suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)

        # silenceremove head and tail:
        filter_str = (
            f"silenceremove=start_periods=1:start_duration=0.03:start_threshold={threshold_db}dB:detection=peak,"
            f"areverse,silenceremove=start_periods=1:start_duration=0.03:start_threshold={threshold_db}dB:detection=peak,areverse"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(audio_file),
            "-af", filter_str,
            "-c:a", "libmp3lame" if target.suffix.lower() == ".mp3" else "pcm_s16le",
            str(target)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=8)
            if res.returncode == 0 and target.exists() and target.stat().st_size > 1000:
                return target
        except Exception:
            pass
        return audio_file

    @staticmethod
    def apply_voice_effect(
        audio_file: Path,
        effect: str = "none",
        out_path: Path = None,
        speed: float = 1.0,
        pitch_shift: int = 0
    ) -> Path:
        """
        Applies voice character shaping and acoustic filters using pure FFmpeg.
        Supported effects: 'deep', 'high', 'robot', 'telephone', 'radio', 'echo', 'chipmunk', 'monster'.
        """
        audio_file = Path(audio_file)
        if not audio_file.exists() or audio_file.stat().st_size == 0:
            return audio_file

        target = Path(out_path) if out_path else audio_file.with_name(f"{audio_file.stem}_fx_{effect}{audio_file.suffix}")
        target.parent.mkdir(parents=True, exist_ok=True)

        effects_map = {
            "deep": "asetrate=22050,aresample=44100,atempo=0.8",
            "high": "asetrate=88200,aresample=44100,atempo=1.2",
            "robot": "asetrate=16000,aresample=44100,vibrato=f=10:d=0.5",
            "echo": "aecho=0.8:0.9:1000:0.3",
            "telephone": "highpass=f=300,lowpass=f=3000",
            "radio": "highpass=f=400,lowpass=f=3500,volume=1.2",
            "chipmunk": "asetrate=66150,aresample=44100,atempo=1.5",
            "monster": "asetrate=11025,aresample=44100,atempo=0.6,vibrato=f=8:d=0.8",
        }

        filters = []
        eff_lower = effect.lower().strip()
        if eff_lower in effects_map:
            filters.append(effects_map[eff_lower])

        if pitch_shift != 0:
            rate = 2.0 ** (pitch_shift / 12.0)
            filters.append(f"asetrate=44100*{rate:.3f},aresample=44100")

        if speed != 1.0 and 0.5 <= speed <= 2.0:
            filters.append(f"atempo={speed:.2f}")

        if not filters:
            return audio_file

        filter_graph = ",".join(filters)
        cmd = [
            "ffmpeg", "-y", "-i", str(audio_file),
            "-af", filter_graph,
            "-c:a", "libmp3lame" if target.suffix.lower() == ".mp3" else "pcm_s16le",
            str(target)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=10)
            if res.returncode == 0 and target.exists() and target.stat().st_size > 1000:
                return target
        except Exception:
            pass
        return audio_file

    @staticmethod
    def estimate_audio_duration(text: str, wpm: float = 145.0) -> float:
        """Heuristic duration estimator from word/syllable count for offline or mocked runs."""
        words = text.split()
        if not words:
            return 3.0
        return max(2.5, round((len(words) / (wpm / 60.0)) + 0.8, 2))


def synthesize_with_iram_voice(text: str, output_file: Path, voice: str = "jarvis") -> bool:
    """Attempts synthesis using IRAM OS VoiceStudio CLI directly."""
    if not shutil.which("iram-voice"):
        return False
    # If full Azure identifier was passed, extract friendly name if possible
    voice_slug = voice
    for k, v in VOICE_MAP.items():
        if v == voice:
            voice_slug = k
            break

    cmd = [
        "iram-voice", "speak",
        text,
        "--voice", voice_slug,
        "--out", str(output_file),
        "--no-play"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0 and output_file.exists() and output_file.stat().st_size > 500:
            return True
    except Exception:
        pass
    return False


def preview_voiceover(text: str, voice: str = "jarvis"):
    """Plays voiceover narration through PipeWire studio audio for previewing before video render."""
    voice_slug = voice
    for k, v in VOICE_MAP.items():
        if v == voice:
            voice_slug = k
            break

    if shutil.which("iram-voice"):
        print(f"🔊 [IRAM VOICE] Playing preview via PipeWire Studio Audio ({voice_slug})...")
        subprocess.run(["iram-voice", "speak", text, "--voice", voice_slug])
    else:
        tmp = Path("/tmp/iram_voice_preview.mp3")
        generate_voiceover(text, str(tmp), voice=voice)
        if shutil.which("pw-play"):
            subprocess.run(["pw-play", str(tmp)])
        elif shutil.which("ffplay"):
            subprocess.run(["ffplay", "-nodisp", "-autoexit", str(tmp)])


def generate_voiceover(text: str, output_file: str, voice: str = "default") -> float:
    """Helper to synthesize a single line or script text to audio file."""
    synth = VoiceSynthesizer(voice_key=voice)
    return synth.synthesize_line(text, Path(output_file))


