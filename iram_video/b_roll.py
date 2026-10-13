import os
import re
import time
import json
import random
import threading
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List, Set
from PIL import Image, ImageDraw
from .motion_canvas import classify_semantic_beat

# Allow Pillow to downscale high resolution public domain photography safely (max 300 megapixels)
Image.MAX_IMAGE_PIXELS = 300_000_000

USER_AGENT = "IramVideo/2.0 (https://github.com/apravint/iram-video; apravint@gmail.com)"

NEGATIVE_NOISE_TERMS = [
    "bird", "tree", "plant", "forest", "florestal", "fruit", "animal", "cartoon",
    "graffiti", "anime", "toy", "nagaokakyo", "happy bus", "doll", "drawing",
    "illustration", "sketch", "comic", "painting", "clipart", "costume", "cosplay", "mask",
    "etching", "engraving", "woodcut", "lithograph", "watercolor", "fresco",
    "flower", "season", "festival", "autumn", "summer", "winter", "blossom", "tulip", "cherry blossom",
    "book", "cover", "tarot", "card", "poster", "pamphlet", "sculpture", "figurine", "stamp", "coin",
    "text", "document", "newspaper", "article", "statue", "tombstone", "grave", "manuscript", "plaque",
    "diagram", "leaflet", "signage", "banner", "dreary", "democracy", "politics", "political", "election",
    "receipt", "bill", "invoice", "protest", "flyer", "paperback", "monument", "memorial",
    "garment", "clothing", "swimwear", "swimsuit", "underwear", "shorts", "trousers",
    "makeup", "cosmetics", "eyeshadow", "lipstick", "manicure", "pedicure", "nail polish", "skincare", "beauty product", "eyeliner", "mascara"
]

NEGATIVE_GEO_NOISE = [
    "china", "beijing", "shanghai", "guangzhou", "shenzhen", "hong kong", "wuhan", "tianjin",
    "japan", "tokyo", "osaka", "kyoto", "london", "uk", "korea", "seoul", "taiwan", "taipei",
    "brazil", "solar eclipse", "eclipse", "poll", "vote", "election", "ballot"
]

TAMIL_TO_ENGLISH_MAP = {
    'சென்னை': 'Chennai',
    'மெட்ரோ': 'Metro',
    'ரயில்': 'Rail',
    'தமிழ்நாடு': 'Tamil Nadu',
    'இந்தியா': 'India',
    'பெங்களூரு': 'Bengaluru',
    'டெல்லி': 'Delhi',
    'மும்பை': 'Mumbai',
    'ஹைதராபாத்': 'Hyderabad',
    'கொல்கத்தா': 'Kolkata',
    'விமானம்': 'Airport',
    'துறைமுகம்': 'Port',
    'விண்வெளி': 'Space',
    'செயற்கை நுண்ணறிவு': 'AI Artificial Intelligence',
    'கணினி': 'Computer',
    'இயற்பியல்': 'Physics',
    'விஞ்ஞானம்': 'Science',
    'இயற்கை': 'Nature',
    'தோல்வி': 'struggle overcome failure',
    'வெற்றி': 'success victory achievement',
    'விடாமுயற்சி': 'perseverance discipline focus',
    'முயற்சி': 'effort discipline hard work',
    'உழைப்பு': 'hard work athlete training',
    'கனவு': 'dreams vision horizon',
    'நம்பிக்கை': 'hope confidence courage',
    'துணிச்சல்': 'courage boldness strength',
    'எழுச்சி': 'rise sunrise strength',
    'பாடல்': 'music anthem inspiration',
    'வாழ்க்கை': 'life journey traveler',
    'பாதை': 'path road journey',
    'இலக்கு': 'goal target focus achievement',
    'சிகரம்': 'mountain peak summit conquer victory',
    'ஓடு': 'running sprinter athlete race',
    'தடை': 'obstacle challenge struggle breakthrough',
    'பயணம்': 'journey traveler pathway road',
    'அடி': 'first step sprinter starting blocks action',
    'துவங்கு': 'start begin journey step',
    'தொடங்கு': 'start begin journey step',
    'கைவிடாதே': 'never give up persevere warrior',
    'உயரம்': 'high altitude mountain peak horizon',
    'வீரம்': 'courage warrior strength bravery',
    'சக்தி': 'power strength energy',
    'வெல்': 'win conquer victory champion',
    'நெருப்பு': 'fire burning torch flame passion',
    'சிங்கம்': 'lion predator strength courage',
    'சூரியன்': 'sunrise golden hour dawn sunbeam',
    'மலை': 'mountain climb summit cliff peak',
    'கடல்': 'ocean waves storm horizon',
    'வானம்': 'sky clouds eagle soaring flight',
}

class MediaFetcher:
    """
    Fetches real high-definition B-roll stock video clips and 4K/8K photography with cascading multi-provider search:
    - Pre-fetched topic pool: queries authentic local archives once and matches beats deterministically
    - Entity Geographic Guard: rejects mismatched foreign geographic media (China, Japan, London)
    - Multi-provider fallback: Google CSE -> Pexels -> Pixabay -> Wikimedia Commons -> Motion Canvas
    """

    _lock = threading.Lock()
    _used_urls: Set[str] = set()
    _PERSISTENT_CACHE_FILE = Path.home() / ".cache" / "iram_video" / "used_media_registry.json"
    _persistent_urls: Set[str] = set()
    _topic_media_pool: List[Dict[str, Any]] = []
    _cached_topic: str = ""

    @classmethod
    def _load_persistent_urls(cls) -> Set[str]:
        try:
            if cls._PERSISTENT_CACHE_FILE.exists():
                with open(cls._PERSISTENT_CACHE_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
        except Exception:
            pass
        return set()

    @classmethod
    def _mark_url_used(cls, url: str):
        if not url:
            return
        with cls._lock:
            cls._used_urls.add(url)
            cls._persistent_urls.add(url)
            try:
                cls._PERSISTENT_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                existing = cls._load_persistent_urls()
                merged = list(existing | cls._persistent_urls)
                if len(merged) > 5000:
                    merged = merged[-5000:]
                with open(cls._PERSISTENT_CACHE_FILE, "w") as f:
                    json.dump(merged, f)
            except Exception:
                pass

    @classmethod
    def reset_session(cls):
        """Resets the session caches so each video compilation gets fresh variety without duplicate shots."""
        with cls._lock:
            cls._used_urls = set()
            cls._persistent_urls = cls._load_persistent_urls()
            cls._topic_media_pool = []
            cls._cached_topic = ""

    @classmethod
    def extract_anchor_phrase(cls, topic: str) -> str:
        """Extracts high-signal core subject words from the global topic, including Tamil entity recognition."""
        if not topic:
            return ""

        # 1. Check for Tamil entity names
        tamil_found = []
        for ta, en in TAMIL_TO_ENGLISH_MAP.items():
            if ta in topic:
                tamil_found.append(en)

        # 2. Extract Latin words
        clean = re.sub(r'[\|#\(\)\[\]:,\-–—\.]+', ' ', topic)
        words = [w for w in clean.split() if re.match(r'^[a-zA-Z]+$', w) and len(w) > 2]
        stopwords = {
            'the', 'and', 'for', 'with', 'from', 'about', 'how', 'why', 'what', 'launch',
            'phase', 'update', 'video', 'tamil', 'english', 'full', 'latest', 'news', 'project',
            'shorts', 'short', 'reel', 'reels', 'tiktok', 'youtube'
        }
        informative = [w for w in words if w.lower() not in stopwords]

        if len(informative) >= 2:
            return ' '.join(informative[:3])
        elif len(informative) == 1:
            if tamil_found:
                return f"{informative[0]} {' '.join(tamil_found)}"
            return informative[0]

        if tamil_found:
            return ' '.join(tamil_found)
        return ""

    @classmethod
    def is_noise_candidate(cls, title: str, query: str = "", topic: str = "") -> bool:
        """Detects and rejects irrelevant domain noise and foreign geographic mismatches (e.g. China when topic is Chennai)."""
        t_low = title.lower()
        q_low = query.lower()
        top_low = topic.lower()

        # Reject domain noise (trees, fruits, anime buses)
        is_nature_query = any(k in q_low or k in top_low for k in ["nature", "forest", "wildlife", "outdoor", "environment", "jungle", "landscape", "tree", "plant", "safari"])
        nature_terms = {"forest", "tree", "plant", "florestal", "fruit", "animal", "bird", "flower", "season", "festival", "autumn", "summer", "winter", "blossom", "tulip", "cherry blossom"}
        for noise in NEGATIVE_NOISE_TERMS:
            if is_nature_query and noise in nature_terms:
                continue
            if noise in t_low and noise not in q_low and noise not in top_low:
                return True

        # Reject geographic mismatches (China, London, etc.) when the topic is Indian/Chennai
        is_indian_topic = any(k in top_low for k in ["chennai", "tamil", "india", "delhi", "mumbai", "bengaluru"])
        if is_indian_topic:
            for geo in NEGATIVE_GEO_NOISE:
                if geo in t_low and geo not in top_low:
                    return True

        return False

    @classmethod
    def prefetch_topic_media(cls, global_topic: str) -> List[Dict[str, Any]]:
        """Pre-fetches a rich pool of verified authentic assets for the global topic in a single request."""
        if cls._topic_media_pool and cls._cached_topic == global_topic:
            return cls._topic_media_pool

        anchor = cls.extract_anchor_phrase(global_topic)
        if not anchor or anchor.lower() in ("shorts", "short", "video", "reels", "reel", "youtube") or len(anchor.strip()) < 3:
            return []

        print(f"   🔍 [Asset Curator] Pre-fetching verified media pool for topic anchor: \"{anchor}\"...")
        cls._topic_media_pool = []
        cls._cached_topic = global_topic

        # Search Wikimedia Commons for core anchor
        clean_anchor = anchor.strip()
        url = (
            "https://commons.wikimedia.org/w/api.php?action=query&generator=search&"
            f"gsrsearch={urllib.parse.quote(clean_anchor)}&gsrnamespace=6&prop=imageinfo&"
            "iiprop=url|mime|size&format=json&gsrlimit=30"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    t = p.get("title", "")
                    if cls.is_noise_candidate(t, query=clean_anchor, topic=global_topic):
                        continue
                    ii_list = p.get("imageinfo", [])
                    if not ii_list:
                        continue
                    ii = ii_list[0]
                    u = ii.get("url", "")
                    w = ii.get("width", 0)
                    h = ii.get("height", 0)
                    mime = ii.get("mime", "")

                    if (mime in ["image/jpeg", "image/png", "image/webp"] or mime.startswith("video/")) and (w >= 480 or h >= 360):
                        cls._topic_media_pool.append({
                            "type": "video" if mime.startswith("video/") else "image",
                            "url": u,
                            "width": w,
                            "height": h,
                            "title": t
                        })
            print(f"   ✓ [Asset Curator] Cached {len(cls._topic_media_pool)} authentic assets for \"{anchor}\"")
        except Exception as e:
            print(f"   ⚠️ [Asset Curator Notice] Pre-fetch error: {e}")

        return cls._topic_media_pool

    @staticmethod
    def search_google_custom_search(query: str) -> List[Dict[str, Any]]:
        """Searches Google Custom Search API (CSE) for high-resolution images if credentials are provided."""
        cse_id = os.getenv("GOOGLE_CSE_ID") or os.getenv("GOOGLE_SEARCH_CX")
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not cse_id or not api_key:
            return []

        url = (
            "https://www.googleapis.com/customsearch/v1?"
            f"q={urllib.parse.quote(query)}&searchType=image&cx={cse_id}&key={api_key}&num=10&imgSize=large"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        results = []
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("items", []):
                    link = item.get("link")
                    title = item.get("title", "")
                    w = int(item.get("image", {}).get("width", 1920))
                    h = int(item.get("image", {}).get("height", 1080))
                    if link and any(link.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                        results.append({
                            "type": "image",
                            "url": link,
                            "width": w,
                            "height": h,
                            "title": title
                        })
        except Exception as e:
            sanitized = re.sub(r'(?:key|cx)=[^&"\s]+', 'key=[REDACTED]', str(e))
            print(f"[Notice] Google Custom Search API: {sanitized}")
        return results

    @staticmethod
    def search_pexels(query: str, require_video: bool = False, orientation: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches Pexels API for HD video clips and photography with orientation filtering (portrait / landscape)."""
        key = os.getenv("PEXELS_API_KEY") or os.getenv("PEXELS_KEY")
        if not key:
            return []
        headers = {"Authorization": key, "User-Agent": USER_AGENT}
        results = []
        orient_param = f"&orientation={orientation}" if orientation in ["portrait", "landscape"] else ""
        try:
            v_url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&per_page=12{orient_param}"
            req = urllib.request.Request(v_url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for video in data.get("videos", []):
                    v_files = sorted(video.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
                    for vf in v_files:
                        link = vf.get("link")
                        if link and vf.get("file_type") == "video/mp4":
                            # Ensure width or height hits a target threshold (e.g. HD 720p or 1080p minimums)
                            if vf.get("width", 0) >= 720 or vf.get("height", 0) >= 1280:
                                results.append({
                                    "type": "video",
                                    "url": link,
                                    "width": vf.get("width", 1920),
                                    "height": vf.get("height", 1080),
                                    "title": f"Pexels Video {video.get('id')}"
                                })
                                break
            if not require_video:
                p_url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page=12{orient_param}"
                req = urllib.request.Request(p_url, headers=headers)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for photo in data.get("photos", []):
                        src = photo.get("src", {})
                        link = src.get("original") or src.get("large2x") or src.get("large")
                        if link:
                            results.append({
                                "type": "image",
                                "url": link,
                                "width": photo.get("width", 1920),
                                "height": photo.get("height", 1080),
                                "title": photo.get("alt", "Pexels Photo")
                            })
        except Exception as e:
            print(f"[Notice] Pexels API: {e}")
        return results

    @staticmethod
    def search_pixabay(query: str, require_video: bool = False) -> List[Dict[str, Any]]:
        """Searches Pixabay API for HD video clips and photography if PIXABAY_API_KEY is available."""
        key = os.getenv("PIXABAY_API_KEY")
        if not key:
            return []
        results = []
        try:
            if require_video:
                v_url = f"https://pixabay.com/api/videos/?key={key}&q={urllib.parse.quote(query)}&per_page=6"
                req = urllib.request.Request(v_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for hit in data.get("hits", []):
                        videos = hit.get("videos", {})
                        v_meta = videos.get("large") or videos.get("medium") or videos.get("small")
                        if v_meta and v_meta.get("url"):
                            results.append({
                                "type": "video",
                                "url": v_meta["url"],
                                "width": v_meta.get("width", 1920),
                                "height": v_meta.get("height", 1080),
                                "title": hit.get("tags", "Pixabay Video")
                            })
            else:
                p_url = f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(query)}&image_type=photo&per_page=8"
                req = urllib.request.Request(p_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for hit in data.get("hits", []):
                        link = hit.get("largeImageURL") or hit.get("webformatURL")
                        if link:
                            results.append({
                                "type": "image",
                                "url": link,
                                "width": hit.get("imageWidth", 1920),
                                "height": hit.get("imageHeight", 1080),
                                "title": hit.get("tags", "Pixabay Photo")
                            })
        except Exception as e:
            sanitized = re.sub(r'(?:key|cx)=[^&"\s]+', 'key=[REDACTED]', str(e))
            print(f"[Notice] Pixabay API: {sanitized}")
        return results

    @classmethod
    def search_wikimedia(cls, query: str, require_video: bool = False, global_topic: str = "") -> List[Dict[str, Any]]:
        """Searches Wikimedia Commons public domain archives with negative keyword and geo filtering."""
        clean_query = query.strip()
        if require_video:
            clean_query = f"filetype:video {clean_query}"

        url = (
            "https://commons.wikimedia.org/w/api.php?action=query&generator=search&"
            f"gsrsearch={urllib.parse.quote(clean_query)}&gsrnamespace=6&prop=imageinfo&"
            "iiprop=url|mime|size&format=json&gsrlimit=12"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        results = []
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    title = p.get("title", "")
                    if cls.is_noise_candidate(title, query=clean_query, topic=global_topic):
                        continue

                    ii_list = p.get("imageinfo", [])
                    if not ii_list:
                        continue
                    ii = ii_list[0]
                    media_url = ii.get("url", "")
                    mime = ii.get("mime", "")
                    w = ii.get("width", 0)
                    h = ii.get("height", 0)

                    if not media_url or "thumb" in media_url or mime == "image/svg+xml":
                        continue

                    if mime.startswith("video/") and any(media_url.lower().endswith(ext) for ext in [".mp4", ".webm", ".mkv", ".mov"]):
                        results.append({
                            "type": "video",
                            "url": media_url,
                            "width": w,
                            "height": h,
                            "title": title
                        })
                    elif mime in ["image/jpeg", "image/png", "image/webp"] and (w >= 480 or h >= 360):
                        results.append({
                            "type": "image",
                            "url": media_url,
                            "width": w,
                            "height": h,
                            "title": title
                        })
        except Exception as e:
            print(f"[Notice] Wikimedia search failed for '{query}': {e}")
        return results

    @classmethod
    def search_openverse(cls, query: str, require_video: bool = False, count: int = 8, global_topic: str = "") -> List[Dict[str, Any]]:
        """Searches Openverse API for zero-cost CC-licensed public imagery (ported from Automated-Video-Generator)."""
        if require_video:
            return []
        results = []
        try:
            url = f"https://api.openverse.engineering/v1/images/?q={urllib.parse.quote(query)}&page_size={count}"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for r in data.get("results", []):
                    title = r.get("title", "")
                    if cls.is_noise_candidate(title, query=query, topic=global_topic):
                        continue
                    img_url = r.get("url")
                    if img_url:
                        results.append({
                            "type": "image",
                            "url": img_url,
                            "width": r.get("width", 1920),
                            "height": r.get("height", 1080),
                            "title": title or "Openverse CC Image",
                            "provider": "openverse"
                        })
        except Exception as e:
            pass
        return results

    @classmethod
    def search_coverr(cls, query: str, count: int = 8, global_topic: str = "", is_shorts: bool = False) -> List[Dict[str, Any]]:
        """Searches Coverr for free, unwatermarked stock video clips (ported from Automated-Video-Generator)."""
        results = []
        try:
            url = f"https://coverr.co/api/videos?query={urllib.parse.quote(query)}&page_size={count}"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                hits = data.get("hits") or data.get("data") or data.get("videos") or []
                for v in hits:
                    if v.get("is_premium"):
                        continue
                    base_fn = v.get("base_filename", "")
                    if base_fn and "watermarked" not in base_fn.lower():
                        v_url = f"https://cdn.coverr.co/videos/{base_fn}/1080p.mp4"
                    elif v.get("url"):
                        v_url = v["url"]
                    elif v.get("file"):
                        v_url = f"https://storage.coverr.co/videos/{v['file']}"
                    else:
                        continue
                    title = v.get("title", "")
                    if cls.is_noise_candidate(title, query=query, topic=global_topic):
                        continue
                    results.append({
                        "type": "video",
                        "url": v_url,
                        "width": v.get("max_width", v.get("width", 1920)),
                        "height": v.get("max_height", v.get("height", 1080)),
                        "title": title or "Coverr Free Video",
                        "provider": "coverr",
                        "is_vertical": bool(v.get("is_vertical"))
                    })
        except Exception as e:
            pass

        # Salient noun query relaxation for zero-result descriptive queries
        if not results and len(query.split()) > 2:
            stop_words = {"the", "a", "an", "in", "on", "at", "of", "and", "or", "for", "with", "out", "by", "from", "to", "up", "into"}
            content_words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', query.lower()) if w not in stop_words]
            candidate_queries = []
            if len(content_words) >= 2:
                candidate_queries.append(f"{content_words[-2]} {content_words[-1]}")
                candidate_queries.append(f"{content_words[0]} {content_words[1]}")
            for cw in content_words:
                if cw not in candidate_queries:
                    candidate_queries.append(cw)
            for rq in candidate_queries:
                r_hits = cls.search_coverr(rq, count=count, global_topic=global_topic, is_shorts=is_shorts)
                if r_hits:
                    return r_hits

        return results

    @classmethod
    def search_nasa(cls, query: str, count: int = 6) -> List[Dict[str, Any]]:
        """Searches NASA Image & Video Library for public domain scientific imagery."""
        results = []
        try:
            url = f"https://images-api.nasa.gov/search?q={urllib.parse.quote(query)}&media_type=image&page_size={count}"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("collection", {}).get("items", []):
                    links = item.get("links", [])
                    img_link = next((l["href"] for l in links if l.get("href")), None)
                    item_data = item.get("data", [{}])[0]
                    if img_link:
                        results.append({
                            "type": "image",
                            "url": img_link,
                            "width": 1920,
                            "height": 1080,
                            "title": item_data.get("title", "NASA Image"),
                            "provider": "nasa"
                        })
        except Exception as e:
            pass
        return results

    @classmethod
    def search_metmuseum(cls, query: str, count: int = 6) -> List[Dict[str, Any]]:
        """Searches Met Museum Open Access collection for historical and artistic visual assets."""
        results = []
        try:
            url = f"https://collectionapi.metmuseum.org/public/collection/v1/search?q={urllib.parse.quote(query)}&hasImages=true"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                object_ids = data.get("objectIDs") or []
                for oid in object_ids[:count]:
                    try:
                        obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{oid}"
                        obj_req = urllib.request.Request(obj_url, headers={"User-Agent": USER_AGENT})
                        with urllib.request.urlopen(obj_req, timeout=3) as o_resp:
                            obj_data = json.loads(o_resp.read().decode("utf-8"))
                            img = obj_data.get("primaryImage") or obj_data.get("primaryImageSmall")
                            if img:
                                results.append({
                                    "type": "image",
                                    "url": img,
                                    "width": 1920,
                                    "height": 1080,
                                    "title": obj_data.get("title", "Met Museum Art"),
                                    "provider": "metmuseum"
                                })
                    except Exception:
                        continue
        except Exception as e:
            pass
        return results

    @classmethod
    def expand_visual_query(cls, query: str, topic: str = "", beat_id: str = "") -> str:
        """
        Translates abstract semantic narration & topic phrases into concrete, high-aesthetic
        physical cinematography queries (runners at sunrise, boxing, glowing cityscapes, dominos)
        that stock engines index effectively.
        """
        combined = f"{topic} {query}".lower()
        combined_tamil_eng = [eng_v for tam_k, eng_v in TAMIL_TO_ENGLISH_MAP.items() if tam_k in combined]
        if combined_tamil_eng:
            combined = f"{combined} {' '.join(combined_tamil_eng)}".lower()

        query_eng = query.lower()
        query_tamil_eng = [eng_v for tam_k, eng_v in TAMIL_TO_ENGLISH_MAP.items() if tam_k in query_eng]
        if query_tamil_eng:
            query_eng = f"{query_eng} {' '.join(query_tamil_eng)}".lower()

        # Parse index from beat_id for shot variety across beats
        b_idx = 0
        m = re.search(r'\d+', str(beat_id))
        if m:
            b_idx = int(m.group())

        seed_offset = abs(hash(f"{topic}_{query}_{beat_id}")) + random.randint(0, 50)

        # 1. Mindset / Motivation / Discipline / Habit / Fear / Bold Action
        is_mindset = any(k in combined for k in [
            "discipline", "motivation", "unstoppable", "mindset", "habit",
            "focus", "success", "willpower", "trap", "action", "results",
            "execution", "hesitation", "procrastination", "grind", "commit",
            "fear", "bold", "courage", "brave", "anxiety", "conquer", "overcome",
            "victory", "runner", "athlete", "peak", "summit", "perseverance"
        ])
        if is_mindset:
            if any(k in query_eng for k in ["fear", "doubt", "anxious", "scared", "hesitat", "stuck", "comfort", "trap", "paraly", "wait", "obstacle", "struggle", "failure"]):
                shots = [
                    "stormy ocean waves crashing rocks",
                    "dark shadows dramatic silhouette standing",
                    "lone figure walking foggy forest",
                    "rain window solitary person thinking",
                    "hourglass sand flowing",
                    "old pocket watch ticking desk",
                    "foggy mountain cliff edge",
                    "frosty glass window dawn",
                ]
            elif any(k in query_eng for k in ["bold", "courage", "brave", "action", "leap", "jump", "start", "movement", "move", "first step", "step", "sprinter"]):
                shots = [
                    "rock climber gripping cliff mountain peak",
                    "sprinter starting blocks athletic track",
                    "boxer hitting speed bag workout",
                    "athlete sprinting beach sunrise waves",
                    "cyclist climbing steep mountain road",
                    "swimmer diving into Olympic pool",
                    "running shoes pavement morning",
                    "skydiver leaping open sky",
                    "trail runner forest morning sunbeams",
                ]
            elif any(k in query_eng for k in ["compound", "result", "lifelong", "massive", "scale", "future", "victory", "extraordinary", "unstoppable", "conquer", "summit", "peak", "dreams"]):
                shots = [
                    "mountain summit sunrise golden rays",
                    "runner raising arms finish line victory",
                    "chess game grandmaster king checkmate",
                    "domino falling chain reaction slow motion",
                    "city skyline dawn golden hour aerial",
                    "seedling sprouting green dark rich soil",
                    "lighthouse ocean waves storm beacon beam",
                    "airplane soaring above sunrise clouds",
                    "ancient massive oak tree roots forest",
                ]
            else:
                shots = [
                    "gym workout barbell deadlift power",
                    "athlete sprinting beach sunrise waves",
                    "boxer wrapping hands locker room",
                    "study desk lamp open book writing",
                    "martial arts karate training punch dojo",
                    "marathon runners crossing bridge dawn",
                    "swimmer underwater butterfly stroke pool",
                    "blacksmith hammering glowing iron anvil",
                    "solo runner track stadium night lights",
                ]
            return shots[(seed_offset + b_idx) % len(shots)]

        # 2. Software Architecture / Coding / AI / Cloud
        is_tech = any(k in combined for k in [
            "code", "software", "java", "spring", "python", "developer", "cloud",
            "server", "database", "api", "virtual thread", "loom", "system", "architecture"
        ])
        if is_tech:
            tech_shots = [
                "coding multiple monitors dark room",
                "datacenter glowing server racks rows",
                "cyber network data stream nodes",
                "hands typing mechanical keyboard close up",
                "circuit board microchip glowing traces",
                "cloud infrastructure architecture diagram screen",
                "robotics arm automated precision factory",
                "software engineer debugging laptop coffee",
            ]
            return tech_shots[(seed_offset + b_idx) % len(tech_shots)]

        # 3. Preserve concrete physical entities if present
        concrete_tokens = [
            "metro", "train", "rail", "airport", "plane", "rocket", "satellite",
            "car", "bridge", "port", "ship", "temple", "tower", "mountain", "ocean",
            "highway", "city", "building", "laboratory", "factory", "stadium"
        ]
        clean_words = [w for w in query.split() if len(w) > 2]
        matched_concrete = [w for w in clean_words if any(ct in w.lower() for ct in concrete_tokens)]
        if matched_concrete:
            return f"{' '.join(matched_concrete[:3])} cinematic 4k"

        # 4. Fallback: clean words + cinematic
        stopwords = {
            "the", "and", "for", "with", "from", "about", "how", "why", "what",
            "this", "that", "over", "into", "when", "your", "secret", "becoming"
        }
        filtered = [w for w in clean_words if w.lower() not in stopwords]
        if filtered:
            return f"{' '.join(filtered[:3])} cinematic 4k"

        return "cinematic documentary scenery 4k"

    @staticmethod
    def verify_media_file(file_path: Path, min_size_bytes: int = 4000, is_shorts: bool = False) -> bool:
        """Verifies media asset is non-empty, non-corrupt, and decodable via PIL/ffprobe with luminance and aspect ratio checks."""
        p = Path(file_path)
        if not p.exists() or p.stat().st_size < min_size_bytes:
            return False
        ext = p.suffix.lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            try:
                from PIL import ImageStat
                with Image.open(p) as img:
                    img_rgb = img.convert("RGB")
                    stat = ImageStat.Stat(img_rgb)
                    r, g, b = stat.mean[:3]
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    r_std, g_std, b_std = stat.stddev[:3]
                    avg_std = (r_std + g_std + b_std) / 3.0

                    # Reject underexposed / pitch-black images (< 12, e.g. Dreary) or pure white washed-out scans (> 252)
                    if lum < 12 or lum > 252:
                        return False

                    # For 9:16 Shorts: reject extreme landscape panoramas (w / h > 2.6)
                    if is_shorts and (img.width / max(1, img.height)) > 2.6:
                        return False

                return True
            except Exception:
                return False
        import subprocess
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5)
            dur = float(res.stdout.strip())
            return dur > 0.05
        except Exception:
            return False

    @classmethod
    def search_media(cls, query: str, require_video: bool = False, global_topic: str = "", is_shorts: bool = False) -> List[Dict[str, Any]]:
        """Multi-source stock provider aggregator: Google CSE + Pexels + Pixabay + Wikimedia + Coverr + Openverse + NASA."""
        results: List[Dict[str, Any]] = []

        g_results = cls.search_google_custom_search(query)
        if g_results:
            results.extend(g_results)

        orientation = "portrait" if is_shorts else "landscape"
        px_results = cls.search_pexels(query, require_video=require_video, orientation=orientation)
        if px_results:
            results.extend(px_results)

        pb_results = cls.search_pixabay(query, require_video=require_video)
        if pb_results:
            results.extend(pb_results)

        wm_results = cls.search_wikimedia(query, require_video=require_video, global_topic=global_topic)
        if wm_results:
            results.extend(wm_results)

        # Zero-cost unwatermarked 1080p video clips from Coverr
        cv_results = cls.search_coverr(query, count=8, global_topic=global_topic, is_shorts=is_shorts)
        if cv_results:
            results.extend(cv_results)

        # Additional public domain imagery when video not strictly required
        if not require_video:
            ov_results = cls.search_openverse(query, global_topic=global_topic)
            if ov_results:
                results.extend(ov_results)
            nasa_results = cls.search_nasa(query)
            if nasa_results:
                results.extend(nasa_results)
            met_results = cls.search_metmuseum(query)
            if met_results:
                results.extend(met_results)

        # Prioritize real video clips first
        results.sort(key=lambda x: 0 if x.get("type") == "video" else 1)
        return results

    @classmethod
    def download_file(cls, url: str, out_path: Path) -> bool:
        # Pre-flight Metadata Auditing Filter (Copyright & Content ID Safeguard)
        for blocked in getattr(cls, "_BLOCKED_ASSET_IDS", set()):
            if blocked in url.lower():
                return False

        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read()
                if len(content) < 5000:
                    return False
                with open(out_path, "wb") as f:
                    f.write(content)

            if out_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                try:
                    with Image.open(out_path) as img:
                        if img.width > 3840 or img.height > 2160:  # Allow up to 4K resolution safely
                            img.thumbnail((3840, 2160), Image.Resampling.LANCZOS)
                        rgb_img = img.convert("RGB")
                        # Strips all IPTC/EXIF fingerprint tracking while saving lossless-quality JPEG
                        rgb_img.save(
                            out_path, format="JPEG", quality=100, subsampling=0, qtables="web_maximum"
                        )
                except Exception:
                    if out_path.exists():
                        out_path.unlink()
                    return False
            elif out_path.suffix.lower() in [".mp4", ".mov", ".webm"]:
                try:
                    import subprocess
                    tmp_clean = out_path.with_name(f"clean_{out_path.name}")
                    cmd = ["ffmpeg", "-y", "-i", str(out_path), "-map_metadata", "-1", "-c", "copy", str(tmp_clean)]
                    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0 and tmp_clean.exists() and tmp_clean.stat().st_size > 0:
                        tmp_clean.replace(out_path)
                except Exception:
                    pass

            return True
        except Exception as e:
            print(f"[Notice] Media download error for {url}: {e}")
            if out_path.exists():
                try:
                    out_path.unlink()
                except Exception:
                    pass
            return False

    @classmethod
    def extract_scene_beats(cls, scene: Dict[str, Any], total_duration: float, global_topic: str = "") -> List[Dict[str, Any]]:
        """
        Decomposes a scene into multiple visual beats synced to spoken sentences,
        and applies the Semantic Beat Classifier to route to MotionCanvas or Real Media.
        """
        anchor = cls.extract_anchor_phrase(global_topic)

        # 1. Native millisecond sentence boundary synchronization from Edge-TTS
        sentence_timings = scene.get("sentence_timings", [])
        if sentence_timings and isinstance(sentence_timings, list) and len(sentence_timings) >= 2:
            beats = []
            explicit_broll = scene.get("broll_beats", [])
            for s_idx, st in enumerate(sentence_timings):
                s_text = st["text"]
                b_query = s_text
                ai_prompt = None
                if s_idx < len(explicit_broll) and isinstance(explicit_broll[s_idx], dict):
                    eb = explicit_broll[s_idx]
                    if eb.get("search_query"):
                        b_query = eb["search_query"]
                    ai_prompt = eb.get("ai_prompt")
                classification = classify_semantic_beat(b_query, global_topic=global_topic)
                beat_dict = {
                    "phrase": s_text,
                    "query": b_query,
                    "duration": float(st["duration"]),
                    **classification
                }
                if ai_prompt:
                    beat_dict["ai_prompt"] = ai_prompt
                beats.append(beat_dict)
            curr_sum = sum(b["duration"] for b in beats)
            if curr_sum > 0:
                scale = total_duration / curr_sum
                for b in beats:
                    b["duration"] = round(b["duration"] * scale, 3)
            return beats

        # 2. Explicit beats defined in screenplay
        explicit_beats = scene.get("broll_beats", [])
        if explicit_beats and isinstance(explicit_beats, list) and len(explicit_beats) >= 2:
            dur_per_beat = total_duration / len(explicit_beats)
            beats = []
            for b in explicit_beats:
                q = (b.get("search_query") or b.get("phrase") or scene.get("heading", "")).strip()
                classification = classify_semantic_beat(q, global_topic=global_topic)
                beats.append({
                    "phrase": q,
                    "query": q,
                    "duration": round(dur_per_beat, 3),
                    **classification
                })
            return beats

        narration = str(scene.get("narration") or scene.get("heading") or "").strip()
        if not narration:
            base_q = scene.get("search_query") or anchor or "documentary landscape"
            classification = classify_semantic_beat(base_q, global_topic=global_topic)
            return [{
                "phrase": base_q,
                "query": base_q,
                "duration": total_duration,
                **classification
            }]

        raw_sentences = [s.strip() for s in re.split(r'[\.\?!;]+', narration) if len(s.strip()) > 8]
        if len(raw_sentences) < 2:
            raw_sentences = [s.strip() for s in re.split(r'[,—]+', narration) if len(s.strip()) > 10]

        if len(raw_sentences) < 2:
            base_q = scene.get("search_query") or scene.get("heading") or anchor or "documentary landscape"
            classification = classify_semantic_beat(narration or base_q, global_topic=global_topic)
            return [{
                "phrase": narration or base_q,
                "query": base_q,
                "duration": total_duration,
                **classification
            }]

        total_words = sum(max(1, len(s.split())) for s in raw_sentences)
        stopwords = {
            "in", "the", "an", "a", "from", "over", "to", "it", "its", "have", "has", "of",
            "and", "these", "that", "this", "with", "by", "for", "on", "at", "as", "is",
            "are", "was", "were", "been", "be", "we", "they", "our", "their", "into"
        }

        beats = []
        for s in raw_sentences:
            w_list = s.split()
            w_count = max(1, len(w_list))
            b_dur = (w_count / total_words) * total_duration

            clean_words = [w for w in re.sub(r'[^a-zA-Z0-9\s]', '', s).split() if w.lower() not in stopwords]
            if len(clean_words) >= 2:
                beat_q = " ".join(clean_words[:4])
            else:
                beat_q = f"{scene.get('heading', '')} {' '.join(w_list[:3])}"

            classification = classify_semantic_beat(s, global_topic=global_topic)
            beats.append({
                "phrase": s,
                "query": beat_q.strip(),
                "duration": max(2.5, b_dur),
                **classification
            })

        current_sum = sum(b["duration"] for b in beats)
        if current_sum > 0:
            scale = total_duration / current_sum
            for b in beats:
                b["duration"] = round(b["duration"] * scale, 3)

        return beats

    @classmethod
    def fetch_media_for_beat(
        cls,
        query: str,
        out_dir: Path,
        beat_id: str,
        global_topic: str = "",
        is_shorts: bool = False,
        is_cinema: bool = False,
        beat_data: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Finds and downloads a unique, authentic B-roll video clip or high-res photo for an individual beat.
        Uses semantic visual expansion (mapping abstract concepts into physical cinematography) and
        validates media quality, brightness/luminance, and aspect ratio.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        clean_q = query.strip()

        # 1. Expand query into concrete cinematography query
        expanded_q = cls.expand_visual_query(clean_q, topic=global_topic, beat_id=beat_id)

        # 2. Check or load pre-fetched verified topic pool (if authentic topic pool exists)
        pool = cls.prefetch_topic_media(global_topic)
        def _is_url_already_used(u: str) -> bool:
            if not u:
                return True
            return (u in cls._used_urls) or (u in cls._persistent_urls)

        if pool:
            query_words = [w.lower() for w in clean_q.split() if len(w) > 3]

            # Pass 1: Try keyword match inside the authentic topic pool with random shuffling
            p1_items = [
                item for item in pool
                if not _is_url_already_used(item.get("url", ""))
                and any(w in item.get("title", "").lower() for w in query_words)
            ]
            random.shuffle(p1_items)
            if is_shorts or is_cinema:
                p1_items.sort(key=lambda x: 0 if x.get("type") == "video" else 1)
            for item in p1_items:
                ext = ".webm" if item["type"] == "video" else ".jpg"
                target = out_dir / f"beat_{beat_id}{ext}"
                if cls.download_file(item["url"], target):
                    if cls.verify_media_file(target, is_shorts=is_shorts):
                        cls._mark_url_used(item["url"])
                        return target
                    else:
                        target.unlink(missing_ok=True)

            # Pass 2: Pick next available authentic item from pool with random shuffling
            p2_items = [
                item for item in pool
                if not _is_url_already_used(item.get("url", ""))
            ]
            random.shuffle(p2_items)
            if is_shorts or is_cinema:
                p2_items.sort(key=lambda x: 0 if x.get("type") == "video" else 1)
            for item in p2_items:
                ext = ".webm" if item["type"] == "video" else ".jpg"
                target = out_dir / f"beat_{beat_id}{ext}"
                if cls.download_file(item["url"], target):
                    if cls.verify_media_file(target, is_shorts=is_shorts):
                        cls._mark_url_used(item["url"])
                        return target
                    else:
                        target.unlink(missing_ok=True)

        # 3. Dynamic multi-source search fallback with rate-limit protection
        queries_to_try = [expanded_q]
        if expanded_q != clean_q:
            queries_to_try.append(f"{expanded_q} cinematic")
            # If clean_q has concrete physical terms, also try it
            concrete_tokens = ["train", "metro", "car", "rocket", "airplane", "bridge", "tower", "city", "building"]
            if any(term in clean_q.lower() for term in concrete_tokens):
                queries_to_try.append(clean_q)

        req_video = is_shorts or is_cinema
        for q in queries_to_try:
            time.sleep(0.1)
            results = cls.search_media(q, require_video=req_video, global_topic=global_topic, is_shorts=is_shorts)
            candidates = [
                item for item in results
                if not _is_url_already_used(item.get("url", ""))
                and not cls.is_noise_candidate(item.get("title", ""), query=q, topic=global_topic)
            ]
            random.shuffle(candidates)

            for item in candidates:
                ext = ".webm" if item["type"] == "video" else ".jpg"
                target = out_dir / f"beat_{beat_id}{ext}"
                if target.exists() and cls.verify_media_file(target, is_shorts=is_shorts):
                    cls._mark_url_used(item["url"])
                    return target
                if cls.download_file(item["url"], target):
                    if cls.verify_media_file(target, is_shorts=is_shorts):
                        cls._mark_url_used(item["url"])
                        return target
                    else:
                        target.unlink(missing_ok=True)

        # 4. Universal High-Quality Stock Video Fallback (Coverr / Pexels / Pixabay)
        # Guarantees continuous authentic real video footage instead of static slide cards
        stop_words = {"the", "a", "an", "in", "on", "at", "of", "and", "or", "for", "with", "out", "by", "from", "to", "up", "into", "how", "what", "why"}
        topic_words = [w for w in re.findall(r'\b[a-zA-Z]{3,}\b', (global_topic or clean_q).lower()) if w not in stop_words]

        cinematic_fallbacks = [
            "cinematic", "action", "athlete workout", "nature landscape", "city skyline dawn", "ocean waves", "dramatic lighting", "mountain sunrise", "running athlete", "person walking"
        ]
        fallback_queries = []
        if len(topic_words) >= 2:
            fallback_queries.append(f"{topic_words[0]} {topic_words[1]}")
        if topic_words:
            fallback_queries.append(topic_words[0])

        h = abs(hash(f"{query}_{beat_id}"))
        fallback_queries.append(cinematic_fallbacks[h % len(cinematic_fallbacks)])
        fallback_queries.append(cinematic_fallbacks[(h + 3) % len(cinematic_fallbacks)])

        for fq in fallback_queries:
            fb_results = cls.search_coverr(fq, count=6, global_topic=global_topic, is_shorts=is_shorts)
            fb_candidates = [
                item for item in fb_results
                if not _is_url_already_used(item.get("url", ""))
            ]
            random.shuffle(fb_candidates)
            for item in fb_candidates:
                ext = ".webm" if item["type"] == "video" else ".jpg"
                target = out_dir / f"beat_{beat_id}{ext}"
                if target.exists() and cls.verify_media_file(target, is_shorts=is_shorts):
                    cls._mark_url_used(item["url"])
                    return target
                if cls.download_file(item["url"], target):
                    if cls.verify_media_file(target, is_shorts=is_shorts):
                        cls._mark_url_used(item["url"])
                        return target
                    else:
                        target.unlink(missing_ok=True)

        # 5. Clean documentary frame fallback (offline emergency fallback)
        fallback_img = out_dir / f"beat_{beat_id}.jpg"
        if not fallback_img.exists() or not cls.verify_media_file(fallback_img, is_shorts=is_shorts):
            cls.create_clean_documentary_frame(query, fallback_img, beat_data=beat_data, is_shorts=is_shorts)
        return fallback_img

    @classmethod
    def fetch_scene_broll(cls, query: str, out_dir: Path, scene_idx: int, global_topic: str = "", is_shorts: bool = False) -> Path:
        """Finds and downloads real B-roll video or photo for a scene."""
        return cls.fetch_media_for_beat(query, out_dir, f"scene_{scene_idx:02d}", global_topic=global_topic, is_shorts=is_shorts)

    @classmethod
    def create_clean_documentary_frame(
        cls,
        title: str,
        out_path: Path,
        beat_data: Optional[Dict[str, Any]] = None,
        is_shorts: bool = False
    ):
        """
        Renders a broadcast-quality editorial documentary frame.
        In Shorts mode, renders a clean cinematic atmospheric visual with ZERO cards or UI elements.
        """
        w, h = (1080, 1920) if is_shorts else (1920, 1080)
        if is_shorts:
            # Clean cinematic backdrop for vertical video without presentation cards or window buttons
            img = Image.new("RGBA", (w, h), (11, 15, 25, 255))
            draw = ImageDraw.Draw(img)
            # Subtle radial vignette glow at center
            for r in range(min(w, h) // 2, 0, -20):
                alpha = int(25 * (1.0 - r / (min(w, h) // 2)))
                draw.ellipse([(w // 2 - r, h // 2 - r), (w // 2 + r, h // 2 + r)], fill=(20, 32, 55, alpha))
            img.convert("RGB").save(out_path, quality=95)
            return

        img = Image.new("RGBA", (w, h), (15, 23, 42, 255))  # Deep Slate-900
        draw = ImageDraw.Draw(img)

        # 1. Subtle architectural background grid (clean, modern tech pattern)
        grid_color = (24, 34, 53, 160)
        grid_step = 80
        for x in range(0, w, grid_step):
            draw.line([(x, 0), (x, h)], fill=grid_color, width=1)
        for y in range(0, h, grid_step):
            draw.line([(0, y), (w, y)], fill=grid_color, width=1)

        # Subtle horizontal top brand accent line in cobalt blue
        draw.rectangle([(0, 0), (w, 6)], fill=(59, 130, 246, 255))

        # Fonts
        from .renderer import get_fonts, draw_mixed_line, wrap_text
        fta_lg, fen_lg = get_fonts(64 if is_shorts else 44, bold=True)
        fta_md, fen_md = get_fonts(36 if is_shorts else 28, bold=True)
        fta_sm, fen_sm = get_fonts(24 if is_shorts else 20, bold=False)
        fta_code, fen_code = get_fonts(24 if is_shorts else 22, bold=False)

        # 2. Clean narrative headline first (derived from story beat, NOT raw camera query)
        narrative_title = ""
        if beat_data and isinstance(beat_data, dict):
            narrative_title = beat_data.get("heading") or beat_data.get("title") or beat_data.get("phrase") or beat_data.get("narration") or ""
        if not narrative_title:
            narrative_title = title or "Core Concept & Analysis"
        headline = narrative_title.strip()
        headline = re.sub(r'[\r\n\t]+', ' ', headline)[:100]

        # 3. Category badge
        badge_y = 60 if not is_shorts else 145
        is_mindset = any(k in headline.lower() for k in ["discipline", "motivation", "unstoppable", "mindset", "habit", "focus", "success", "willpower", "trap", "action", "results", "execution"])
        from .motion_canvas import detect_code_language, MotionCanvas
        is_code_topic = any(k in headline.lower() for k in [
            "java", "spring", "code", "thread", "virtual", "compile", "rest", "api", "loom", "graalvm",
            "python", "rust", "golang", "typescript", "javascript", "sql", "bash", "linux", "c++"
        ])

        if is_code_topic:
            badge_text = "SOFTWARE ARCHITECTURE & CODE"
        elif is_mindset:
            badge_text = "MINDSET & RELENTLESS EXECUTION"
        else:
            badge_text = "STRATEGIC ANALYSIS & INSIGHT"

        badge_w = 400 if is_shorts else 440
        draw.rounded_rectangle(
            [(80, badge_y), (80 + badge_w, badge_y + 36)],
            radius=6,
            fill=(30, 41, 59, 220),
            outline=(59, 130, 246, 200),
            width=1
        )
        draw_mixed_line(draw, 96, badge_y + 8, badge_text, (56, 189, 248), fta_sm, fen_sm)

        # 4. Clean headline placement
        max_title_w = w - 160
        lines = wrap_text(headline, fta_lg, fen_lg, max_title_w, draw)
        title_y = badge_y + (65 if is_shorts else 55)
        for line in lines[:2]:
            draw_mixed_line(draw, 80, title_y, line, (248, 250, 252), fta_lg, fen_lg)
            title_y += 74 if is_shorts else 54

        # 5. Main Presentation Container Card (safely placed above kinetic subtitle zone)
        card_x = 80
        card_y = title_y + 25
        card_w = w - 160
        card_h = min(780, 1060 - card_y) if is_shorts else (h - card_y - 80)

        # Draw glassmorphism card
        draw.rounded_rectangle(
            [(card_x, card_y), (card_x + card_w, card_y + card_h)],
            radius=12,
            fill=(20, 29, 44, 240),
            outline=(51, 65, 85, 255),
            width=2
        )

        # Window controls
        draw.ellipse([(card_x + 24, card_y + 20), (card_x + 36, card_y + 32)], fill=(100, 116, 139))
        draw.ellipse([(card_x + 44, card_y + 20), (card_x + 56, card_y + 32)], fill=(148, 163, 184))
        draw.ellipse([(card_x + 64, card_y + 20), (card_x + 76, card_y + 32)], fill=(203, 213, 225))

        # Window title bar & content detection
        content_y = card_y + 70

        if is_code_topic:
            detected_lang, detected_fname = detect_code_language(headline, title)
            win_title = detected_fname
            _, code_lines, status_msg, _ = MotionCanvas.get_code_snippet_for_language(detected_lang, headline)
            draw_mixed_line(draw, card_x + 90, card_y + 16, win_title, (148, 163, 184), fta_sm, fen_sm)
            draw.line([(card_x, card_y + 48), (card_x + card_w, card_y + 48)], fill=(30, 41, 59), width=1)

            # Render syntax-highlighted code block with line numbers
            for idx, (c_txt, c_col) in enumerate(code_lines):
                if content_y + 34 > card_y + card_h - 30:
                    break
                draw_mixed_line(draw, card_x + 30, content_y, f"{idx+1:2d}", (71, 85, 105), fta_code, fen_code)
                draw_mixed_line(draw, card_x + 75, content_y, c_txt, c_col, fta_code, fen_code)
                content_y += 34
        else:
            statement = ""
            if beat_data and isinstance(beat_data, dict):
                statement = str(beat_data.get("phrase") or beat_data.get("narration") or beat_data.get("query") or "").strip()
            if not statement or statement.lower() == headline.lower():
                statement = headline

            # Editorial quote typography
            quote_text = f"“{statement}”" if len(statement) < 140 else statement
            quote_lines = wrap_text(quote_text, fta_md, fen_md, card_w - 70, draw)

            # Elegant cobalt accent pillar
            accent_h = min(280, max(40, len(quote_lines) * 36))
            draw.rectangle([(card_x + 24, content_y + 4), (card_x + 30, content_y + 4 + accent_h)], fill=(59, 130, 246))

            d_y = content_y + 4
            for q_line in quote_lines[:6]:
                draw_mixed_line(draw, card_x + 48, d_y, q_line, (248, 250, 252), fta_md, fen_md)
                d_y += 36

            # Context badge derived from headline
            badge_text = f"KEY INSIGHT • {headline.upper()[:40]}"
            draw_mixed_line(draw, card_x + 48, d_y + 20, badge_text, (148, 163, 184), fta_sm, fen_sm)

        # 6. Bottom footer tag
        footer_text = "IRAM FILM STUDIO • UNIVERSAL HIGH-QUALITY PRODUCTION"
        draw_mixed_line(draw, 80, h - 45, footer_text, (100, 116, 139), fta_sm, fen_sm)

        img.convert("RGB").save(
            out_path, format="JPEG", quality=100, subsampling=0, qtables="web_maximum"
        )
