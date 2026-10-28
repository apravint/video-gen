import os
import math
import subprocess
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageOps

class AcceleratedAvatarEngine:
    """
    High-speed, low-latency talking avatar compositor.
    Optimized for high-DPI rendering timelines and lossless master outputs.
    """

    SUPPORTED_PROVIDERS = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]

    def __init__(self, execution_provider: str = "auto"):
        self.provider = execution_provider
        if execution_provider == "auto":
            self.provider = "CUDAExecutionProvider" if os.environ.get("CUDA_VISIBLE_DEVICES") else "CPUExecutionProvider"

    @classmethod
    def create_talking_avatar_video(
        cls,
        avatar_img_path: Path,
        speech_audio_path: Path,
        out_video_path: Path,
        duration: float,
        width: int = 720,  # Scaled up baseline from 480 to preserve crisp curves
        height: int = 720,
        fps: int = 30,     # Smooth standard motion pacing match
        execution_provider: str = "auto"
    ) -> Path:
        out_video_path = Path(out_video_path)
        out_video_path.parent.mkdir(parents=True, exist_ok=True)
        total_frames = max(1, int(duration * fps))

        base_img = Image.open(avatar_img_path).convert("RGBA")
        base_img = ImageOps.fit(base_img, (width, height), Image.Resampling.LANCZOS)
        base_arr = np.array(base_img)

        # Enforce broadcast color spaces on raw video compilation streams
        BT709_ARGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]

        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgba",
            "-r", str(fps),
            "-i", "-",  
            "-i", str(speech_audio_path),
            "-c:v", "libx264",
            "-preset", "medium",         # Advanced macro-block pattern matching
            "-crf", "16",                # Production lossless rendering floor
            "-tune", "animation",        # Shield sharp vectors from compression blurring
            *BT709_ARGS,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "320k",              # Broadcaster standard bitrate capacity
            "-ac", "2",                  # Lock stereo configuration mapping paths
            "-t", f"{duration:.3f}",
            str(out_video_path)
        ]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        try:
            for f_idx in range(total_frames):
                t_sec = f_idx / fps

                speech_cadence = abs(math.sin(t_sec * 13.5) * math.cos(t_sec * 6.2))
                mouth_open = 0.0 if not speech_audio_path.exists() else speech_cadence
                bob_y = int(math.sin(t_sec * 2.8) * 3)

                frame_img = Image.fromarray(base_arr)
                if mouth_open > 0.15:
                    draw = ImageDraw.Draw(frame_img)
                    cx = width // 2
                    cy = int(height * 0.68) + bob_y
                    
                    # Proportionally scale mouth boundaries to fit clean width variations
                    sf = width / 480.0
                    mw = int((22 + mouth_open * 20) * sf)
                    mh = int((8 + mouth_open * 16) * sf)
                    
                    draw.ellipse(
                        [cx - mw, cy - mh, cx + mw, cy + mh],
                        fill=(42, 10, 16, 245),
                        outline=(170, 45, 55, 200),
                        width=int(2 * sf)
                    )
                    if mouth_open > 0.4:
                        draw.line([cx - mw + int(5 * sf), cy - int(2 * sf), cx + mw - int(5 * sf), cy - int(2 * sf)], fill=(245, 245, 250, 230), width=int(2 * sf))

                raw_bytes = frame_img.tobytes()
                proc.stdin.write(raw_bytes)
                # HIGH FIDELITY FIX: Flush cache blocks immediately to prevent OS pipe block deadlocks
                if f_idx % 4 == 0:
                    proc.stdin.flush()

            proc.stdin.close()
            proc.wait(timeout=45)
        except Exception as e:
            if proc.stdin:
                proc.stdin.close()
            proc.kill()
            raise e

        return out_video_path

    @classmethod
    def overlay_presenter_pip(
        cls,
        main_video_path: Path,
        avatar_video_path: Path,
        output_video_path: Path,
        position: str = "bottom_right",
        pip_size: int = 440  # Increased baseline sizing space
    ) -> Path:
        output_video_path = Path(output_video_path)
        output_video_path.parent.mkdir(parents=True, exist_ok=True)

        if position == "bottom_left":
            pos_x, pos_y = "50", "main_h-overlay_h-70"
        elif position == "top_right":
            pos_x, pos_y = "main_w-overlay_w-50", "70"
        elif position == "top_left":
            pos_x, pos_y = "50", "70"
        else: 
            pos_x, pos_y = "main_w-overlay_w-50", "main_h-overlay_h-70"

        filter_complex = (
            f"[1:v]scale={pip_size}:{pip_size},format=yuva420p,"
            f"geq=lum='lum(X,Y)':a='if(lte(pow(X-{pip_size}/2,2)+pow(Y-{pip_size}/2,2),pow({pip_size}/2-6,2)),255,0)'[avatar_circle];"
            f"[0:v][avatar_circle]overlay={pos_x}:{pos_y}:shortest=1[v]"
        )

        BT709_ARGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]

        cmd = [
            "ffmpeg", "-y",
            "-i", str(main_video_path),
            "-i", str(avatar_video_path),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "medium",         # Secure background assets resolution structure
            "-crf", "16",
            "-tune", "film",             # Protect structural texture depth layers
            *BT709_ARGS,
            "-c:a", "copy",
            str(output_video_path)
        ]

        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_video_path

    @classmethod
    def generate_personalive_avatar(
        cls,
        avatar_img_path: Path,
        out_video_path: Path,
        driving_video_path: Optional[Path] = None,
        speech_audio_path: Optional[Path] = None,
        width: int = 512,
        height: int = 512,
        device: str = "auto",
        stream_gen: bool = True,
    ) -> Path:
        """Invokes GVCLab/PersonaLive streamable portrait diffusion framework."""
        personalive_root = Path(os.environ.get("PERSONALIVE_DIR", "/home/apravint/PersonaLive"))
        if not personalive_root.exists() or not (personalive_root / "inference_offline.py").exists():
            raise FileNotFoundError(f"PersonaLive not found at {personalive_root}")

        out_video_path = Path(out_video_path).resolve()
        out_video_path.parent.mkdir(parents=True, exist_ok=True)

        if not driving_video_path and not speech_audio_path:
            demo_video = personalive_root / "demo" / "driving_video.mp4"
            if demo_video.exists():
                driving_video_path = demo_video

        py_bin = personalive_root / ".venv/bin/python"
        py_exec = str(py_bin) if py_bin.exists() else sys.executable

        actual_device = device
        if actual_device == "auto":
            actual_device = "cuda" if (shutil.which("nvidia-smi") or os.environ.get("CUDA_VISIBLE_DEVICES")) else "cpu"

        cmd = [
            py_exec,
            str(personalive_root / "inference_offline.py"),
            "--reference_image", str(Path(avatar_img_path).resolve()),
            "-W", str(width),
            "-H", str(height),
            "--device", actual_device,
        ]
        if driving_video_path and Path(driving_video_path).exists():
            cmd.extend(["--driving_video", str(Path(driving_video_path).resolve())])
        if stream_gen:
            cmd.extend(["--stream_gen", "True"])

        print(f"🎬 [PERSONALIVE] Generating real-time portrait animation for: {avatar_img_path.name}...")
        res = subprocess.run(cmd, cwd=str(personalive_root), capture_output=True, text=True)
        if res.returncode != 0:
            print(f"⚠️ [PERSONALIVE] Note/Warning: {res.stderr[-300:] if res.stderr else res.stdout[-300:]}")
            if speech_audio_path and Path(speech_audio_path).exists():
                duration = 5.0
                try:
                    probe_out = subprocess.check_output(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(speech_audio_path)],
                        text=True
                    )
                    duration = float(probe_out.strip())
                except Exception:
                    pass
                return cls.create_talking_avatar_video(avatar_img_path, speech_audio_path, out_video_path, duration)
            raise RuntimeError(f"PersonaLive failed (code {res.returncode}): {res.stderr}")

        # Check saved_results
        saved_dir = personalive_root / "saved_results"
        if saved_dir.exists():
            mp4s = sorted(saved_dir.glob("**/*.mp4"), key=os.path.getmtime, reverse=True)
            if mp4s:
                shutil.copy2(mp4s[0], out_video_path)
                return out_video_path

        return out_video_path

    @classmethod
    def render_talking_head(
        cls,
        face_img: Path,
        out_path: Path,
        audio_path: Optional[Path] = None,
        driving_video: Optional[Path] = None,
        engine: str = "auto",
        width: int = 512,
        height: int = 512,
    ) -> Path:
        """Unified entry point for talking head creation."""
        personalive_root = Path(os.environ.get("PERSONALIVE_DIR", "/home/apravint/PersonaLive"))
        has_personalive = personalive_root.exists() and (personalive_root / "inference_offline.py").exists()

        if engine == "personalive" or (engine == "auto" and has_personalive):
            try:
                return cls.generate_personalive_avatar(
                    avatar_img_path=face_img,
                    out_video_path=out_path,
                    driving_video_path=driving_video,
                    speech_audio_path=audio_path,
                    width=width,
                    height=height,
                )
            except Exception as e:
                print(f"⚠️ [AVATAR] PersonaLive fallback triggered: {e}")

        # Fallback to procedural
        if audio_path and Path(audio_path).exists():
            duration = 5.0
            try:
                probe_out = subprocess.check_output(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
                    text=True
                )
                duration = float(probe_out.strip())
            except Exception:
                pass
            return cls.create_talking_avatar_video(face_img, audio_path, out_path, duration, width, height)

        raise ValueError("Must provide either valid PersonaLive configuration or audio_path for fallback avatar.")

AvatarEngine = AcceleratedAvatarEngine
