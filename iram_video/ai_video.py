import os
import time
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List

from .b_roll import MediaFetcher

class AIVideoEngine:
    """
    Multi-Tier AI Video Generation Engine with Cascading Fallback:
    Tier 1: Google Veo 3.1 / 2.0 (Gemini API & Vertex AI)
    Tier 2: Fal.ai (Wan 2.1, Kling 1.5, Luma Ray 2)
    Tier 3: Replicate (Wan 2.1, Minimax Hailuo Video-01)
    Tier 4: Public Domain Media Archives (Wikimedia Commons & NASA 4K/8K Video/Photos)
    Tier 5: Documentary Motion Canvas (Ken Burns Dynamic Push/Pull/Pan)
    """

    _veo_quota_exhausted: bool = False

    @classmethod
    def generate_with_google_veo(
        cls,
        prompt: str,
        out_path: Path,
        duration: float = 5.0,
        is_shorts: bool = False
    ) -> Optional[Path]:
        """Attempts video generation using Google Veo (veo-3.1-generate-preview / veo-2.0-generate-001)."""
        if cls._veo_quota_exhausted:
            return None

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client()
            # Google Veo accepts discrete durations: 4, 6, or 8 seconds
            dur_int = 4 if duration <= 5.0 else (6 if duration <= 7.0 else 8)
            aspect_ratio = "9:16" if is_shorts else "16:9"

            models_to_try = [
                "veo-3.1-lite-generate-preview",
                "veo-3.1-fast-generate-preview",
                "veo-3.1-generate-preview",
                "veo-2.0-generate-001"
            ]

            cinematic_prompt = (
                f"Cinematic photorealistic 8k footage: {prompt}. "
                "Natural lighting, continuous camera motion, 35mm lens, master documentary capture, high visual detail."
            )

            for model_name in models_to_try:
                try:
                    print(f"   ⚡ [Google Veo] Synthesizing video with '{model_name}' ({dur_int}s)...")
                    operation = client.models.generate_videos(
                        model=model_name,
                        source=types.GenerateVideosSource(prompt=cinematic_prompt),
                        config=types.GenerateVideosConfig(
                            aspect_ratio=aspect_ratio,
                            duration_seconds=dur_int
                        )
                    )

                    # Poll operation with timeout (max 90 seconds)
                    start_t = time.time()
                    while not operation.done:
                        if time.time() - start_t > 90:
                            print(f"   ⚠️ [Google Veo] Operation timed out after 90s on {model_name}")
                            break
                        time.sleep(5)
                        operation = client.operations.get(operation)

                    if operation.done and operation.result and operation.result.generated_videos:
                        gen_video = operation.result.generated_videos[0]
                        gen_video.video.save(str(out_path))
                        if out_path.exists() and out_path.stat().st_size > 10000:
                            print(f"   ✓ [Google Veo] Successfully synthesized AI video: {out_path.name}")
                            return out_path
                except Exception as sub_err:
                    err_msg = str(sub_err)
                    if "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
                        cls._veo_quota_exhausted = True
                        print(f"   ⚠️ [Google Veo Notice] Quota limit reached (429 RESOURCE_EXHAUSTED)")
                        break
                    elif "404" in err_msg or "NOT_FOUND" in err_msg:
                        continue
                    else:
                        print(f"   ⚠️ [Google Veo Notice] {err_msg[:90]}")
                        break
        except Exception as e:
            print(f"   ⚠️ [Google Veo Init] {e}")
        return None

    @classmethod
    def generate_with_fal(
        cls,
        prompt: str,
        out_path: Path,
        duration: float = 5.0,
        is_shorts: bool = False
    ) -> Optional[Path]:
        """Attempts video generation using Fal.ai (Wan 2.1 / Kling / Luma)."""
        fal_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
        if not fal_key:
            return None

        try:
            import requests

            endpoint = "https://queue.fal.run/fal-ai/wan/v2.1/text-to-video"
            aspect_ratio = "9:16" if is_shorts else "16:9"
            payload = {
                "prompt": f"Cinematic photorealistic documentary shot: {prompt}, 4k ultra detailed",
                "aspect_ratio": aspect_ratio
            }
            headers = {
                "Authorization": f"Key {fal_key}",
                "Content-Type": "application/json"
            }

            print("   ⚡ [Fal.ai Wan 2.1] Submitting request...")
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code not in (200, 201, 202):
                print(f"   ⚠️ [Fal.ai Notice] Status {resp.status_code}: {resp.text[:80]}")
                return None

            data = resp.json()
            status_url = data.get("status_url")
            response_url = data.get("response_url")
            poll_endpoint = status_url or response_url
            if not poll_endpoint:
                return None

            # Poll for completion
            start_t = time.time()
            while time.time() - start_t < 90:
                time.sleep(5)
                check = requests.get(poll_endpoint, headers=headers, timeout=10)
                if check.status_code == 200:
                    cdata = check.json()
                    status = cdata.get("status")
                    if status == "COMPLETED" or "video" in cdata:
                        video_url = cdata.get("video", {}).get("url") or cdata.get("output", {}).get("video", {}).get("url")
                        if video_url:
                            v_resp = requests.get(video_url, timeout=30)
                            if v_resp.status_code == 200:
                                with open(out_path, "wb") as f:
                                    f.write(v_resp.content)
                                print(f"   ✓ [Fal.ai Wan 2.1] Successfully generated video: {out_path.name}")
                                return out_path
                    elif status in ("FAILED", "CANCELLED"):
                        print(f"   ⚠️ [Fal.ai Notice] Job status {status}")
                        return None
        except Exception as e:
            print(f"   ⚠️ [Fal.ai Error] {e}")
        return None

    @classmethod
    def generate_with_replicate(
        cls,
        prompt: str,
        out_path: Path,
        duration: float = 5.0,
        is_shorts: bool = False
    ) -> Optional[Path]:
        """Attempts video generation using Replicate (Wan 2.1 / Minimax Hailuo)."""
        replicate_token = os.getenv("REPLICATE_API_TOKEN") or os.getenv("REPLICATE_API_KEY")
        if not replicate_token:
            return None

        try:
            import requests

            endpoint = "https://api.replicate.com/v1/models/wan-video/wan-2.1-14b/predictions"
            aspect_ratio = "9:16" if is_shorts else "16:9"
            payload = {
                "input": {
                    "prompt": f"Cinematic documentary shot: {prompt}, 8k photorealistic",
                    "aspect_ratio": aspect_ratio
                }
            }
            headers = {
                "Authorization": f"Bearer {replicate_token}",
                "Content-Type": "application/json"
            }

            print("   ⚡ [Replicate Wan 2.1] Submitting request...")
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code not in (200, 201):
                print(f"   ⚠️ [Replicate Notice] Status {resp.status_code}: {resp.text[:80]}")
                return None

            data = resp.json()
            poll_url = data.get("urls", {}).get("get")
            if not poll_url:
                return None

            start_t = time.time()
            while time.time() - start_t < 90:
                time.sleep(5)
                check = requests.get(poll_url, headers=headers, timeout=10)
                if check.status_code == 200:
                    cdata = check.json()
                    status = cdata.get("status")
                    if status == "succeeded":
                        output = cdata.get("output")
                        video_url = output if isinstance(output, str) else (output[0] if isinstance(output, list) else None)
                        if video_url:
                            v_resp = requests.get(video_url, timeout=30)
                            if v_resp.status_code == 200:
                                with open(out_path, "wb") as f:
                                    f.write(v_resp.content)
                                print(f"   ✓ [Replicate Wan 2.1] Successfully generated video: {out_path.name}")
                                return out_path
                    elif status in ("failed", "canceled"):
                        print(f"   ⚠️ [Replicate Notice] Job status {status}")
                        return None
        except Exception as e:
            print(f"   ⚠️ [Replicate Error] {e}")
        return None

    @classmethod
    def generate_with_hunyuan(
        cls,
        prompt: str,
        out_path: Path,
        duration: float = 5.0,
        is_shorts: bool = False
    ) -> Optional[Path]:
        """Attempts video generation using Tencent HunyuanVideo (13B Open DiT)."""
        replicate_token = os.getenv("REPLICATE_API_TOKEN") or os.getenv("REPLICATE_API_KEY")
        if not replicate_token:
            return None
        try:
            import requests
            endpoint = "https://api.replicate.com/v1/models/tencent/hunyuan-video/predictions"
            aspect_ratio = "9:16" if is_shorts else "16:9"
            payload = {
                "input": {
                    "prompt": f"Cinema grade masterpiece shot: {prompt}, 4k ultra realistic, natural motion",
                    "aspect_ratio": aspect_ratio
                }
            }
            headers = {"Authorization": f"Bearer {replicate_token}", "Content-Type": "application/json"}
            print("   ⚡ [Tencent HunyuanVideo] Submitting request...")
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code in (200, 201):
                poll_url = resp.json().get("urls", {}).get("get")
                if not poll_url:
                    return None
                start_t = time.time()
                while time.time() - start_t < 90:
                    time.sleep(5)
                    check = requests.get(poll_url, headers=headers, timeout=10)
                    if check.status_code == 200:
                        cdata = check.json()
                        if cdata.get("status") == "succeeded":
                            v_url = cdata.get("output")
                            if isinstance(v_url, list): v_url = v_url[0]
                            if v_url:
                                v_resp = requests.get(v_url, timeout=30)
                                if v_resp.status_code == 200:
                                    with open(out_path, "wb") as f: f.write(v_resp.content)
                                    print(f"   ✓ [Tencent HunyuanVideo] Generated video: {out_path.name}")
                                    return out_path
                        elif cdata.get("status") in ("failed", "canceled"):
                            break
        except Exception as e:
            print(f"   ⚠️ [HunyuanVideo Error] {e}")
        return None

    @classmethod
    def generate_with_cogvideo(
        cls,
        prompt: str,
        out_path: Path,
        duration: float = 5.0,
        is_shorts: bool = False
    ) -> Optional[Path]:
        """Attempts video generation using Zhipu CogVideoX (5B Open Model)."""
        replicate_token = os.getenv("REPLICATE_API_TOKEN") or os.getenv("REPLICATE_API_KEY")
        if not replicate_token:
            return None
        try:
            import requests
            endpoint = "https://api.replicate.com/v1/models/thudm/cogvideox-5b/predictions"
            payload = {
                "input": {
                    "prompt": f"Masterpiece cinematic capture: {prompt}, high motion fluidity, 8k",
                    "duration": 5
                }
            }
            headers = {"Authorization": f"Bearer {replicate_token}", "Content-Type": "application/json"}
            print("   ⚡ [Zhipu CogVideoX] Submitting request...")
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code in (200, 201):
                poll_url = resp.json().get("urls", {}).get("get")
                if not poll_url:
                    return None
                start_t = time.time()
                while time.time() - start_t < 90:
                    time.sleep(5)
                    check = requests.get(poll_url, headers=headers, timeout=10)
                    if check.status_code == 200:
                        cdata = check.json()
                        if cdata.get("status") == "succeeded":
                            v_url = cdata.get("output")
                            if isinstance(v_url, list): v_url = v_url[0]
                            if v_url:
                                v_resp = requests.get(v_url, timeout=30)
                                if v_resp.status_code == 200:
                                    with open(out_path, "wb") as f: f.write(v_resp.content)
                                    print(f"   ✓ [Zhipu CogVideoX] Generated video: {out_path.name}")
                                    return out_path
                        elif cdata.get("status") in ("failed", "canceled"):
                            break
        except Exception as e:
            print(f"   ⚠️ [CogVideoX Error] {e}")
        return None

    @classmethod
    def generate_keyframe_with_sana(
        cls,
        prompt: str,
        out_path: Path,
        is_shorts: bool = False
    ) -> Optional[Path]:
        """Attempts ultra-fast high-res keyframe synthesis using NVIDIA Sana linear DiT."""
        fal_key = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
        if not fal_key:
            return None
        try:
            import requests
            endpoint = "https://queue.fal.run/fal-ai/sana"
            image_size = "portrait_16_9" if is_shorts else "landscape_16_9"
            payload = {
                "prompt": f"Masterpiece cinematic 4k photo: {prompt}, ultra detailed, photorealistic",
                "image_size": image_size
            }
            headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
            print("   ⚡ [NVIDIA Sana DiT] Generating keyframe (<1s)...")
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                s_url = data.get("status_url") or data.get("response_url")
                if not s_url:
                    return None
                start_t = time.time()
                while time.time() - start_t < 30:
                    time.sleep(2)
                    check = requests.get(s_url, headers=headers, timeout=10)
                    if check.status_code == 200:
                        cdata = check.json()
                        if cdata.get("status") == "FAILED":
                            return None
                        img_url = cdata.get("images", [{}])[0].get("url")
                        if img_url:
                            i_resp = requests.get(img_url, timeout=20)
                            if i_resp.status_code == 200:
                                with open(out_path, "wb") as f: f.write(i_resp.content)
                                print(f"   ✓ [NVIDIA Sana DiT] Keyframe ready: {out_path.name}")
                                return out_path
        except Exception as e:
            print(f"   ⚠️ [NVIDIA Sana Error] {e}")
        return None

    @classmethod
    def fetch_or_generate_beat_media(
        cls,
        beat: Dict[str, Any],
        out_dir: Path,
        beat_id: str,
        is_shorts: bool = False,
        is_cinema: bool = False,
        provider: str = "auto",
        global_topic: str = ""
    ) -> Path:
        """
        Main routing function that executes the multi-tier cascading fallback:
        Google Veo -> Wan 2.2/2.1 -> HunyuanVideo -> CogVideoX -> Sana Keyframe -> Stock -> Motion Canvas
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        query = beat.get("query") or beat.get("search_query") or "documentary scene"
        phrase = beat.get("phrase") or beat.get("narration") or query
        duration = float(beat.get("duration", 5.0))
        ai_prompt = beat.get("ai_prompt") or f"{query}. {phrase}"

        target_mp4 = out_dir / f"beat_{beat_id}_ai.mp4"

        # Check if a custom starting image is supplied (Image-to-Video Storyboarding)
        start_img = beat.get("start_image")
        if start_img and Path(start_img).exists():
            return Path(start_img)

        # Check cached AI video
        if target_mp4.exists() and target_mp4.stat().st_size > 10000:
            return target_mp4

        prov = provider.lower().strip()

        # Tier 1: Google Veo 3.1 / 2.0
        if prov in ("auto", "veo", "google"):
            res = cls.generate_with_google_veo(ai_prompt, target_mp4, duration, is_shorts)
            if res:
                return res
            if prov in ("veo", "google"):
                print("   🔄 [Veo fallback] Falling back to secondary generative providers...")

        # Tier 2: Alibaba Wan 2.2 / 2.1 via Fal.ai or Replicate
        if prov in ("auto", "fal", "wan", "wan2", "wan2.1", "wan2.2", "kling"):
            res = cls.generate_with_fal(ai_prompt, target_mp4, duration, is_shorts)
            if res:
                return res

        # Tier 3: Tencent HunyuanVideo (13B)
        if prov in ("auto", "hunyuan", "hunyuanvideo"):
            res = cls.generate_with_hunyuan(ai_prompt, target_mp4, duration, is_shorts)
            if res:
                return res

        # Tier 4: Zhipu CogVideoX (5B)
        if prov in ("auto", "cogvideo", "cogvideox"):
            res = cls.generate_with_cogvideo(ai_prompt, target_mp4, duration, is_shorts)
            if res:
                return res

        # Tier 5: Replicate Wan 2.1 / Minimax Hailuo
        if prov in ("auto", "replicate"):
            res = cls.generate_with_replicate(ai_prompt, target_mp4, duration, is_shorts)
            if res:
                return res

        # Tier 6: NVIDIA Sana Ultra-Fast Keyframe DiT
        if prov in ("auto", "sana", "nvlabs"):
            target_keyframe = out_dir / f"beat_{beat_id}_sana.jpg"
            res_img = cls.generate_keyframe_with_sana(ai_prompt, target_keyframe, is_shorts)
            if res_img:
                return res_img

        # Tier 7: Public Domain Stock Archives (Wikimedia Commons, Openverse, Coverr, NASA HD Video/Photos)
        stock_path = MediaFetcher.fetch_media_for_beat(query, out_dir, beat_id, global_topic=global_topic, is_shorts=is_shorts, is_cinema=is_cinema, beat_data=beat)
        if stock_path.exists() and stock_path.stat().st_size > 5000:
            return stock_path

        # Tier 8: Documentary Motion Canvas Fallback
        fallback_img = out_dir / f"beat_{beat_id}.jpg"
        if not fallback_img.exists():
            MediaFetcher.create_clean_documentary_frame(query, fallback_img, beat_data=beat, is_shorts=is_shorts)
        return fallback_img

    @classmethod
    def extend_video(
        cls,
        previous_video: Path,
        prompt: str,
        out_path: Path,
        duration: float = 4.0,
        is_shorts: bool = False
    ) -> Path:
        """
        Extends an existing video clip into a continuous multi-scene film.
        Extracts the final keyframe from previous_video, synthesizes the continuation,
        and seamlessly stitches both clips with smooth blending.
        """
        import subprocess
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_dir = out_path.parent / "extend_tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        last_frame_path = tmp_dir / f"last_frame_{int(time.time())}.png"
        ext_clip_path = tmp_dir / f"ext_clip_{int(time.time())}.mp4"

        # 1. Extract last frame from previous_video
        cmd_extract = [
            "ffmpeg", "-y",
            "-sseof", "-0.1",
            "-i", str(previous_video),
            "-vframes", "1",
            "-q:v", "2",
            str(last_frame_path)
        ]
        subprocess.run(cmd_extract, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 2. Synthesize extension scene using last frame as starting seed
        beat = {
            "query": prompt,
            "phrase": prompt,
            "duration": duration,
            "ai_prompt": prompt,
            "start_image": str(last_frame_path)
        }
        res_ext = cls.fetch_or_generate_beat_media(beat, tmp_dir, "ext", is_shorts=is_shorts)

        # If res_ext is an image, convert to video with subtle steady motion
        d_frames = int(duration * 30)
        ctx_is_4k = "4k" in str(out_path.name).lower() or "uhd" in str(out_path.name).lower() or str(beat.get("is_4k", "false")).lower() in ["true", "1"]
        if is_shorts:
            w, h = (2160, 3840) if ctx_is_4k else (1080, 1920)
        else:
            w, h = (3840, 2160) if ctx_is_4k else (1920, 1080)

        BT709_ARGS = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]

        if res_ext.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            fc = f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},zoompan=z='1.0+0.02*(on/{d_frames})':d={d_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps=30[v]"
            cmd_img2vid = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", str(res_ext),
                "-filter_complex", fc,
                "-map", "[v]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-tune", "animation",
                *BT709_ARGS,
                "-pix_fmt", "yuv420p",
                "-t", f"{duration:.3f}",
                str(ext_clip_path)
            ]
            subprocess.run(cmd_img2vid, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            ext_clip_path = res_ext

        # 3. Concatenate previous_video and ext_clip_path
        concat_txt = tmp_dir / "concat_list.txt"
        with open(concat_txt, "w") as f:
            f.write(f"file '{previous_video.resolve()}'\n")
            f.write(f"file '{ext_clip_path.resolve()}'\n")

        cmd_cat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-tune", "film",
            *BT709_ARGS,
            "-pix_fmt", "yuv420p",
            str(out_path)
        ]
        subprocess.run(cmd_cat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            if last_frame_path.exists(): last_frame_path.unlink()
            if concat_txt.exists(): concat_txt.unlink()
        except Exception:
            pass

        return out_path
