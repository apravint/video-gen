import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont

from .mastering import resolve_dimensions

_BUNDLED_FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_USER_FONTS = Path.home() / ".local" / "share" / "fonts"

def _first_existing(*candidates) -> str:
    """Returns the first font that exists, so rendering works beyond one machine's font setup."""
    for c in candidates:
        if Path(c).exists():
            return str(c)
    return str(candidates[-1])

FONT_EN_BOLD = _first_existing(
    _USER_FONTS / "JetBrainsMono/JetBrainsMonoNerdFontPropo-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    _BUNDLED_FONTS / "MuktaMalar-Bold.ttf",
)
FONT_EN_REG = _first_existing(
    _USER_FONTS / "JetBrainsMono/JetBrainsMonoNerdFontPropo-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
    _BUNDLED_FONTS / "MuktaMalar-Bold.ttf",
)

FONT_TA_BOLD = _first_existing("/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf", _BUNDLED_FONTS / "MuktaMalar-Bold.ttf")
FONT_TA_REG = _first_existing("/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf", _BUNDLED_FONTS / "MuktaMalar-Bold.ttf")

FONT_EMOJI = _first_existing(_USER_FONTS / "SegoeUI/seguiemj.ttf", "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")

_EMOJI_FONT_CACHE: Dict[int, ImageFont.FreeTypeFont] = {}

def get_emoji_font(size: int):
    """Loads and caches the scalable Segoe UI color emoji font."""
    if size not in _EMOJI_FONT_CACHE:
        try:
            _EMOJI_FONT_CACHE[size] = ImageFont.truetype(FONT_EMOJI, size)
        except Exception:
            _EMOJI_FONT_CACHE[size] = ImageFont.load_default()
    return _EMOJI_FONT_CACHE[size]

def is_tamil_text(text: str) -> bool:
    return any("\u0b80" <= c <= "\u0bff" for c in str(text))

def is_emoji_char(c: str) -> bool:
    """Detects whether a Unicode character is an emoji, pictogram, or symbol."""
    cp = ord(c)
    if (0x1F300 <= cp <= 0x1FAFF or
        0x2600 <= cp <= 0x27BF or
        0x2B50 <= cp <= 0x2B55 or
        0x2300 <= cp <= 0x23FF or
        0x2190 <= cp <= 0x21FF or
        0x200D == cp or 0xFE0E <= cp <= 0xFE0F):
        return True
    return unicodedata.category(c) in ("So", "Sk") and cp > 0x2000

def get_char_kind(c: str) -> str:
    """Classifies character into emoji, tamil, or english."""
    if is_emoji_char(c):
        return "emoji"
    elif "\u0b80" <= c <= "\u0bff":
        return "tamil"
    return "english"

def split_runs(text: str) -> List[Tuple[str, str]]:
    """Splits a string into sequential runs of 'tamil', 'english', or 'emoji'."""
    runs = []
    if not text:
        return runs
    current_run = []
    current_kind = None
    for char in str(text):
        kind = get_char_kind(char)
        if current_kind is None:
            current_kind = kind
            current_run.append(char)
        elif kind == current_kind:
            current_run.append(char)
        else:
            runs.append(("".join(current_run), current_kind))
            current_run = [char]
            current_kind = kind
    if current_run:
        runs.append(("".join(current_run), current_kind))
    return runs

def get_fonts(size: int, bold: bool = False):
    p_en = FONT_EN_BOLD if bold else FONT_EN_REG
    p_ta = FONT_TA_BOLD if bold else FONT_TA_REG
    try:
        f_en = ImageFont.truetype(p_en, size)
    except Exception:
        f_en = ImageFont.load_default()
    try:
        f_ta = ImageFont.truetype(p_ta, size)
    except Exception:
        f_ta = f_en
    return f_ta, f_en

def get_mixed_width(text: str, font_ta, font_en, draw: ImageDraw.Draw) -> int:
    size = getattr(font_en, "size", 28)
    f_emoji = get_emoji_font(size)
    w = 0
    for chunk, kind in split_runs(text):
        if kind == "emoji":
            f = f_emoji
        elif kind == "tamil":
            f = font_ta
        else:
            f = font_en
        bbox = draw.textbbox((0, 0), chunk, font=f)
        w += (bbox[2] - bbox[0])
    return w

def draw_mixed_line(draw: ImageDraw.Draw, x: int, y: int, text: str, fill, font_ta, font_en) -> int:
    size = getattr(font_en, "size", 28)
    f_emoji = get_emoji_font(size)
    cx = x
    for chunk, kind in split_runs(text):
        if kind == "emoji":
            draw.text((cx, y), chunk, font=f_emoji, embedded_color=True)
            bbox = draw.textbbox((cx, y), chunk, font=f_emoji)
        elif kind == "tamil":
            draw.text((cx, y), chunk, fill=fill, font=font_ta)
            bbox = draw.textbbox((cx, y), chunk, font=font_ta)
        else:
            draw.text((cx, y), chunk, fill=fill, font=font_en)
            bbox = draw.textbbox((cx, y), chunk, font=font_en)
        cx += (bbox[2] - bbox[0])
    return cx

def wrap_text(text: str, font_ta, font_en, max_width: int, draw: ImageDraw.Draw) -> List[str]:
    lines = []
    for paragraph in str(text).split("\n"):
        words = paragraph.split(" ")
        cur = []
        for word in words:
            test = " ".join(cur + [word])
            w = get_mixed_width(test, font_ta, font_en, draw)
            if w <= max_width:
                cur.append(word)
            else:
                if cur:
                    lines.append(" ".join(cur))
                    cur = [word]
                else:
                    lines.append(word)
                    cur = []
        if cur:
            lines.append(" ".join(cur))
    return lines

class SlideRenderer:
    def __init__(self, theme: Dict[str, Any] = None, is_shorts: bool = False, aspect_ratio: str = "16:9", is_4k: bool = False):
        self.is_shorts = is_shorts or aspect_ratio in ("9:16", "4:5")
        self.aspect_ratio = aspect_ratio
        self.is_4k = is_4k
        self.width, self.height = resolve_dimensions(aspect_ratio, self.is_shorts, is_4k)

        theme = theme or {}
        self.bg_color = tuple(theme.get("bg", [15, 23, 42])) + (255,)
        self.accent_color = tuple(theme.get("accent", [59, 130, 246])) + (255,)
        self.sec_color = tuple(theme.get("secondary", [148, 163, 184])) + (255,)
        self.card_bg = tuple(theme.get("card_bg", [30, 41, 59])) + (245,)

    def create_canvas(self, video_title: str) -> Tuple[Image.Image, ImageDraw.Draw]:
        img = Image.new("RGBA", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Grid lines
        grid_col = (25, 36, 56, 90)
        grid_step = 60 if self.is_shorts else 80
        for x in range(0, self.width, grid_step):
            draw.line([(x, 0), (x, self.height)], fill=grid_col, width=1)
        for y in range(0, self.height, grid_step):
            draw.line([(0, y), (self.width, y)], fill=grid_col, width=1)

        # Top gradient border
        for x in range(self.width):
            r = int(self.accent_color[0] + (self.sec_color[0] - self.accent_color[0]) * (x / self.width))
            g = int(self.accent_color[1] + (self.sec_color[1] - self.accent_color[1]) * (x / self.width))
            b = int(self.accent_color[2] + (self.sec_color[2] - self.accent_color[2]) * (x / self.width))
            draw.line([(x, 0), (x, 6)], fill=(r, g, b, 255), width=6)

        if not self.is_shorts:
            draw.line([(0, self.height - 45), (self.width, self.height - 45)], fill=(30, 44, 70, 255), width=1)
            fta_bot, fen_bot = get_fonts(18, bold=False)
            draw_mixed_line(draw, 60, self.height - 34, video_title[:80], (120, 145, 180), fta_bot, fen_bot)

        return img, draw

    def draw_card_frame(self, img: Image.Image, box: Tuple[int, int, int, int], title: str, subtitle: str = "", border_color = None) -> Tuple[int, int, int, int]:
        draw = ImageDraw.Draw(img)
        bcol = border_color or self.accent_color
        x1, y1, x2, y2 = box
        draw.rectangle(box, fill=self.card_bg, outline=bcol, width=2)
        
        head_h = 56 if not subtitle else 76
        draw.line([(x1, y1 + head_h), (x2, y1 + head_h)], fill=bcol, width=1)
        
        fta_t, fen_t = get_fonts(22, bold=True)
        draw_mixed_line(draw, x1 + 20, y1 + 14, title[:50], (255, 255, 255), fta_t, fen_t)
        if subtitle:
            fta_sub, fen_sub = get_fonts(15, bold=False)
            draw_mixed_line(draw, x1 + 20, y1 + 46, subtitle[:65], (130, 160, 200), fta_sub, fen_sub)
        return (x1 + 20, y1 + head_h + 16, x2 - 20, y2 - 16)

    def render_scene(self, scene: Dict[str, Any], video_title: str, out_path: Path):
        img, draw = self.create_canvas(video_title)
        
        heading = scene.get("heading", "OVERVIEW")
        subheading = scene.get("subheading", "")
        
        cards = scene.get("cards", [])
        has_card_content = any(c.get("bullets") or c.get("badge") for c in cards)
        # The designed layouts are drawn in fixed 1080p coordinates; other frames use the scalable card.
        native_frame = (self.width, self.height) in ((1920, 1080), (1080, 1920))
        if not native_frame or scene.get("layout_type") == "text_card" or not has_card_content:
            self._render_text_card(img, heading, subheading, cards)
        elif self.is_shorts:
            self._render_vertical_shorts(img, scene, heading, subheading)
        else:
            fta_h, fen_h = get_fonts(44, bold=True)
            fta_sub, fen_sub = get_fonts(22, bold=False)
            draw_mixed_line(draw, 100, 50, heading[:65], (255, 255, 255), fta_h, fen_h)
            draw_mixed_line(draw, 100, 105, subheading[:95], self.accent_color, fta_sub, fen_sub)

            l_type = scene.get("layout_type", "pillars")

            if l_type == "comparison" or len(cards) == 2:
                self._render_comparison(img, cards)
            elif l_type == "code_or_terminal":
                self._render_terminal(img, cards, heading)
            elif l_type == "stack_list" or len(cards) >= 4:
                self._render_stack_list(img, cards)
            elif l_type == "hero_metric":
                self._render_hero_metric(img, cards)
            else:
                self._render_pillars(img, cards)

        img.save(out_path)

    # --- SCALABLE TEXT CARD (ANY FRAME SIZE) ---
    def _render_text_card(self, img: Image.Image, heading: str, subheading: str, cards: List[Dict[str, Any]]):
        draw = ImageDraw.Draw(img)
        unit = min(self.width, self.height) / 1080
        max_w = int(self.width * 0.84)
        margin = (self.width - max_w) // 2

        fta_h, fen_h = get_fonts(int(76 * unit), bold=True)
        fta_s, fen_s = get_fonts(int(38 * unit), bold=False)
        fta_b, fen_b = get_fonts(int(32 * unit), bold=False)
        h_step, s_step, b_step = int(92 * unit), int(52 * unit), int(46 * unit)

        h_lines = wrap_text(heading, fta_h, fen_h, max_w, draw)[:3]
        s_lines = wrap_text(subheading, fta_s, fen_s, max_w, draw)[:3] if subheading else []
        b_lines = []
        for card in cards[:3]:
            for bullet in card.get("bullets", [])[:4]:
                b_lines.extend(wrap_text(f"• {bullet}", fta_b, fen_b, max_w, draw))
        b_lines = b_lines[:8]

        rule_gap = int(36 * unit)
        total = len(h_lines) * h_step + rule_gap * 2 + len(s_lines) * s_step + (rule_gap + len(b_lines) * b_step if b_lines else 0)
        y = max(int(40 * unit), (self.height - total) // 2)

        for line in h_lines:
            line_w = get_mixed_width(line, fta_h, fen_h, draw)
            draw_mixed_line(draw, (self.width - line_w) // 2, y, line, (255, 255, 255), fta_h, fen_h)
            y += h_step

        y += rule_gap // 2
        rule_w = int(120 * unit)
        draw.rectangle(((self.width - rule_w) // 2, y, (self.width + rule_w) // 2, y + max(3, int(5 * unit))), fill=self.accent_color)
        y += rule_gap

        for line in s_lines:
            line_w = get_mixed_width(line, fta_s, fen_s, draw)
            draw_mixed_line(draw, (self.width - line_w) // 2, y, line, self.sec_color, fta_s, fen_s)
            y += s_step

        if b_lines:
            y += rule_gap
            for line in b_lines:
                draw_mixed_line(draw, margin, y, line, (215, 225, 240), fta_b, fen_b)
                y += b_step

    # --- VERTICAL YOUTUBE SHORTS (9:16) LAYOUT ---
    def _render_vertical_shorts(self, img: Image.Image, scene: Dict[str, Any], heading: str, subheading: str):
        draw = ImageDraw.Draw(img)
        fta_h, fen_h = get_fonts(64, bold=True)
        fta_sub, fen_sub = get_fonts(34, bold=False)

        draw_mixed_line(draw, 60, 110, heading[:48], (255, 255, 255), fta_h, fen_h)
        wrapped_sub = wrap_text(subheading, fta_sub, fen_sub, 960, draw)
        sy = 195
        for s in wrapped_sub[:2]:
            draw_mixed_line(draw, 60, sy, s, self.accent_color, fta_sub, fen_sub)
            sy += 44

        cards = scene.get("cards", [])
        card_w = 960
        start_y = 290

        if len(cards) <= 1:
            # Single prominent card + Interactive Terminal Simulation Window
            card = cards[0] if cards else {}
            card_h = 420
            col = self.accent_color
            ib = self.draw_card_frame(img, (60, start_y, 60 + card_w, start_y + card_h), card.get("title", ""), card.get("subtitle", ""), border_color=col)
            cdraw = ImageDraw.Draw(img)

            badge = card.get("badge")
            by = ib[1]
            if badge:
                fta_b, fen_b = get_fonts(28, bold=True)
                cdraw.rectangle((ib[0], by, ib[0] + 200, by + 44), fill=(25, 38, 60), outline=col, width=1)
                draw_mixed_line(cdraw, ib[0] + 16, by + 8, badge, col, fta_b, fen_b)
                by += 58

            fta_bullet, fen_bullet = get_fonts(26, bold=False)
            for bullet in card.get("bullets", [])[:2]:
                wrapped = wrap_text(bullet, fta_bullet, fen_bullet, card_w - 40, cdraw)
                for w in wrapped:
                    draw_mixed_line(cdraw, ib[0], by, f"• {w}", (190, 215, 240), fta_bullet, fen_bullet)
                    by += 36
                by += 16

            # Terminal window only for scenes that really show commands
            if scene.get("layout_type") == "code_or_terminal":
                term_y = start_y + card_h + 35
                term_h = 440
                draw.rectangle([(60, term_y), (60 + card_w, term_y + term_h)], fill=(15, 23, 42), outline=(51, 65, 85), width=2)
                draw.rectangle([(60, term_y), (60 + card_w, term_y + 44)], fill=(30, 41, 59))
                draw.line([(60, term_y + 44), (60 + card_w, term_y + 44)], fill=(51, 65, 85), width=1)

                ty = term_y + 70
                fta_cmd, fen_cmd = get_fonts(24, bold=False)
                for cmd_text in [scene.get("code"), scene.get("command")]:
                    if cmd_text:
                        for code_line in str(cmd_text).splitlines()[:8]:
                            draw_mixed_line(draw, 85, ty, code_line, (56, 189, 248), fta_cmd, fen_cmd)
                            ty += 40
        else:
            num_cards = min(2, len(cards))
            total_avail_h = 1000
            gap = 35
            card_h = (total_avail_h - (num_cards - 1) * gap) // num_cards

            for i, card in enumerate(cards[:num_cards]):
                y = start_y + i * (card_h + gap)
                col = self.accent_color if i % 2 == 0 else self.sec_color
                ib = self.draw_card_frame(img, (60, y, 60 + card_w, y + card_h), card.get("title", ""), card.get("subtitle", ""), border_color=col)
                cdraw = ImageDraw.Draw(img)

                badge = card.get("badge")
                by = ib[1]
                if badge:
                    fta_b, fen_b = get_fonts(28, bold=True)
                    cdraw.rectangle((ib[0], by, ib[0] + 200, by + 44), fill=(25, 38, 60), outline=col, width=1)
                    draw_mixed_line(cdraw, ib[0] + 16, by + 8, badge, col, fta_b, fen_b)
                    by += 58

                fta_bullet, fen_bullet = get_fonts(26, bold=False)
                for bullet in card.get("bullets", [])[:2]:
                    wrapped = wrap_text(bullet, fta_bullet, fen_bullet, card_w - 40, cdraw)
                    for w in wrapped:
                        draw_mixed_line(cdraw, ib[0], by, f"• {w}", (190, 215, 240), fta_bullet, fen_bullet)
                        by += 36
                    by += 16

    # --- LANDSCAPE 16:9 METHODS ---
    def _render_pillars(self, img: Image.Image, cards: List[Dict[str, Any]]):
        num = max(1, min(3, len(cards)))
        card_w = (1720 - (num - 1) * 40) // num
        card_y, card_h = 180, 700
        start_x = 100

        for i, card in enumerate(cards[:3]):
            x = start_x + i * (card_w + 40)
            col = self.accent_color if i % 2 == 0 else self.sec_color
            ib = self.draw_card_frame(img, (x, card_y, x + card_w, card_y + card_h), card.get("title", ""), card.get("subtitle", ""), border_color=col)
            cdraw = ImageDraw.Draw(img)
            
            badge = card.get("badge")
            by = ib[1]
            if badge:
                fta_b, fen_b = get_fonts(15, bold=True)
                cdraw.rectangle((ib[0], by, ib[0] + 160, by + 34), fill=(25, 38, 60), outline=col, width=1)
                draw_mixed_line(cdraw, ib[0] + 12, by + 6, badge, col, fta_b, fen_b)
                by += 50
                
            fta_bullet, fen_bullet = get_fonts(17, bold=False)
            for bullet in card.get("bullets", []):
                wrapped = wrap_text(bullet, fta_bullet, fen_bullet, card_w - 40, cdraw)
                for w in wrapped:
                    draw_mixed_line(cdraw, ib[0], by, f"• {w}", (190, 215, 240), fta_bullet, fen_bullet)
                    by += 25
                by += 12

    def _render_comparison(self, img: Image.Image, cards: List[Dict[str, Any]]):
        col_w = 830
        card_y, card_h = 180, 700
        cols = [self.accent_color, self.sec_color]
        positions = [100, 990]

        for i, card in enumerate(cards[:2]):
            x = positions[i]
            col = cols[i]
            ib = self.draw_card_frame(img, (x, card_y, x + col_w, card_y + card_h), card.get("title", ""), card.get("subtitle", ""), border_color=col)
            cdraw = ImageDraw.Draw(img)
            by = ib[1]
            fta_b, fen_b = get_fonts(18, bold=False)
            for bullet in card.get("bullets", []):
                draw_mixed_line(cdraw, ib[0], by, "✓", col, fta_b, fen_b)
                wrapped = wrap_text(bullet, fta_b, fen_b, col_w - 50, cdraw)
                for w in wrapped:
                    draw_mixed_line(cdraw, ib[0] + 28, by, w, (195, 215, 240), fta_b, fen_b)
                    by += 26
                by += 16

    def _render_terminal(self, img: Image.Image, cards: List[Dict[str, Any]], heading: str):
        ib = self.draw_card_frame(img, (100, 180, self.width - 100, 900), "Terminal / Code Simulation", heading, border_color=(51, 65, 85, 200))
        tdraw = ImageDraw.Draw(img)
        ty = ib[1] + 10
        fta_t, fen_t = get_fonts(20, bold=True)
        fta_term, fen_term = get_fonts(18, bold=False)
        
        for card in cards:
            title = card.get("title", "")
            if title:
                draw_mixed_line(tdraw, ib[0] + 10, ty, f"$ {title}", (56, 189, 248), fta_t, fen_t)
                ty += 34
            for b in card.get("bullets", []):
                draw_mixed_line(tdraw, ib[0] + 25, ty, f"> {b}", (200, 225, 255), fta_term, fen_term)
                ty += 28
            ty += 16

    def _render_stack_list(self, img: Image.Image, cards: List[Dict[str, Any]]):
        y = 180
        card_h = 155
        fta_desc, fen_desc = get_fonts(18, bold=False)
        for i, card in enumerate(cards[:4]):
            col = self.accent_color if i % 2 == 0 else self.sec_color
            ib = self.draw_card_frame(img, (100, y, self.width - 100, y + card_h), card.get("title", ""), card.get("subtitle", ""), border_color=col)
            sdraw = ImageDraw.Draw(img)
            bullets_text = "  |  ".join(card.get("bullets", []))
            wrapped = wrap_text(bullets_text, fta_desc, fen_desc, self.width - 260, sdraw)
            dy = ib[1] + 6
            for w in wrapped:
                draw_mixed_line(sdraw, ib[0], dy, w, (195, 215, 240), fta_desc, fen_desc)
                dy += 26
            y += 175

    def _render_hero_metric(self, img: Image.Image, cards: List[Dict[str, Any]]):
        card1 = cards[0] if cards else {}
        # A single card takes the full width rather than sitting beside an empty box
        right_edge = 720 if len(cards) > 1 else self.width - 100
        ib1 = self.draw_card_frame(img, (100, 180, right_edge, 880), card1.get("title", ""), "", border_color=self.accent_color)
        c1_draw = ImageDraw.Draw(img)
        fta_hero, fen_hero = get_fonts(60, bold=True)
        hy = ib1[1] + 40
        if card1.get("badge"):
            draw_mixed_line(c1_draw, ib1[0] + 20, hy, card1["badge"], self.accent_color, fta_hero, fen_hero)
            hy += 120
        fta_b, fen_b = get_fonts(18 if len(cards) > 1 else 34, bold=False)
        for b in card1.get("bullets", []):
            wrapped = wrap_text(b, fta_b, fen_b, right_edge - 180, c1_draw)
            for w in wrapped:
                draw_mixed_line(c1_draw, ib1[0] + 20, hy, f"• {w}", (190, 215, 240), fta_b, fen_b)
                hy += 26 if len(cards) > 1 else 48
            hy += 14

        if len(cards) < 2:
            return
        card2 = cards[1]
        ib2 = self.draw_card_frame(img, (760, 180, self.width - 100, 880), card2.get("title", ""), card2.get("subtitle", ""), border_color=self.sec_color)
        c2_draw = ImageDraw.Draw(img)
        ry = ib2[1]
        for b in card2.get("bullets", []):
            wrapped = wrap_text(b, fta_b, fen_b, 980, c2_draw)
            for w in wrapped:
                draw_mixed_line(c2_draw, ib2[0] + 20, ry, f"✓ {w}", (190, 215, 240), fta_b, fen_b)
                ry += 26
            ry += 16
