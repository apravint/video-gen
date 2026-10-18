"""
Autonomous 3D CAD Exploded-View Video Engine for ShortsCreator AI.
Recreates high-end hardware engineering showcase animations matching Google Antigravity / Gemini Argon workflows.

Features:
- Procedural multi-layer 3D CAD exploded perspective animation with orbital turntable camera choreography.
- Hardware architecture presets (Google Pixel / Tensor G5, Quantum Chip, GPU Architecture, Neural Engine).
- High-fidelity studio lighting with obsidian matte environment, edge specularity, and depth occlusion.
- Real-time animated technical HUD telemetry, leader lines, coordinate grids, and engineering callouts.
- Procedural mechanical Foley sound design (stepper servos, pneumatic slides, magnetic latch clicks, sub-bass impacts).
- Standalone Blender MCP / CLI Python script exporter for native Cycles/Eevee 3D rendering.
"""

import os
import math
import random
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from .sfx import SoundEffectsSynthesizer
from .voice import generate_voiceover


# Default Hardware Presets
PIXEL_TENSOR_HARDWARE_PRESET = {
    "title": "GOOGLE PIXEL 9 PRO // HARDWARE ARCHITECTURE",
    "subtitle": "AUTONOMOUS CAD EXPLODED VIEW • GEMINI ARGON WORKFLOW",
    "layers": [
        {
            "id": "back_glass",
            "name": "GORILLA GLASS VICTUS 2 BACKPLATE",
            "spec": "Matte Obsidian Finish • Anti-Fingerprint Oleophobic Coating",
            "badge": "MOHS: 8.5 • 0.8mm ULTRA-THIN",
            "color": (26, 28, 34),
            "edge_color": (90, 100, 120),
            "z_rest": 3.5,
            "z_explode": 6.5,
            "type": "glass",
            "callout_side": "right"
        },
        {
            "id": "camera_visor",
            "name": "TRIPLE PRO OPTICS VISOR",
            "spec": "50MP Octa PD Main + 48MP Quad PD 5X Periscope Prism + 48MP Ultrawide",
            "badge": "1/1.31\" SENSOR • OIS / EIS DUAL GIMBAL",
            "color": (18, 20, 24),
            "edge_color": (160, 180, 220),
            "z_rest": 3.0,
            "z_explode": 5.2,
            "type": "camera_bar",
            "callout_side": "left"
        },
        {
            "id": "wireless_coil",
            "name": "QI2 COPPER INDUCTION COIL",
            "spec": "High-Purity Oxygen-Free Copper Winding Matrix + Ferrite Shield",
            "badge": "15W FAST INDUCTIVE • NFC DUAL-BAND",
            "color": (180, 95, 45),
            "edge_color": (230, 140, 70),
            "z_rest": 2.2,
            "z_explode": 3.6,
            "type": "coil",
            "callout_side": "right"
        },
        {
            "id": "battery_pack",
            "name": "5060 mAh GRAPHENE DUAL-CELL",
            "spec": "High-Density Silicon-Carbon Anode with Integrated BMS Safety Circuit",
            "badge": "37W FAST CHARGING • 19.5 Wh DENSITY",
            "color": (35, 40, 48),
            "edge_color": (80, 160, 240),
            "z_rest": 1.2,
            "z_explode": 2.1,
            "type": "battery",
            "callout_side": "left"
        },
        {
            "id": "logic_board",
            "name": "MAIN LOGIC BOARD & TENSOR G5",
            "spec": "3nm GAAFET Architecture • Google TPU Gen 4 • Titan M2 Security",
            "badge": "48 TOPS ON-DEVICE AI • 16GB LPDDR5X",
            "color": (15, 30, 24),
            "edge_color": (40, 200, 140),
            "z_rest": 0.2,
            "z_explode": 0.6,
            "type": "pcb",
            "callout_side": "right"
        },
        {
            "id": "vapor_chamber",
            "name": "3D COPPER VAPOR CHAMBER",
            "spec": "Vacuum-Sealed Deionized Fluid Capillary Mesh for High-TDP Dissipation",
            "badge": "4500 mm² AREA • -8.5°C CORE DELTA",
            "color": (170, 85, 35),
            "edge_color": (220, 130, 60),
            "z_rest": -0.8,
            "z_explode": -1.2,
            "type": "copper_plate",
            "callout_side": "left"
        },
        {
            "id": "aluminum_chassis",
            "name": "AEROSPACE GRADE 7000 ALUMINUM FRAME",
            "spec": "100% Recycled CNC Unibody Chassis with Ceramic-Infused Antenna Isolators",
            "badge": "IP68 WATER/DUST • HIGH TORSIONAL RIGIDITY",
            "color": (55, 60, 68),
            "edge_color": (180, 190, 205),
            "z_rest": -1.8,
            "z_explode": -2.8,
            "type": "chassis",
            "callout_side": "right"
        },
        {
            "id": "display_panel",
            "name": "SUPER ACTUA LTPO OLED DISPLAY",
            "spec": "6.8\" 1-120Hz Variable Refresh • 3000 Nits Peak HDR • 24-bit True Color",
            "badge": "486 PPI • GORILLA GLASS VICTUS 2",
            "color": (12, 14, 18),
            "edge_color": (60, 140, 255),
            "z_rest": -2.8,
            "z_explode": -4.6,
            "type": "display",
            "callout_side": "left"
        }
    ]
}


class ExplodedCADVideoEngine:
    """High-performance 3D CAD Exploded-View video renderer and sound designer."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self.aspect_ratio = "16:9" if width > height else "9:16"

    @classmethod
    def _get_font(cls, size: int = 14, bold: bool = False) -> ImageFont.ImageFont:
        """Cached high-resolution TrueType monospace font loader."""
        if not hasattr(cls, "_font_cache"):
            cls._font_cache = {}
        key = (size, bold)
        if key in cls._font_cache:
            return cls._font_cache[key]
        candidates = [
            "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf" if bold else "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSansMono.ttf",
            "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/system/fonts/DroidSansMono.ttf",
            "/system/fonts/Roboto-Regular.ttf"
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    f = ImageFont.truetype(path, size)
                    cls._font_cache[key] = f
                    return f
                except Exception:
                    pass
        f = ImageFont.load_default()
        cls._font_cache[key] = f
        return f

    # 3D Math & Projection Utilities
    # -------------------------------------------------------------------------
    @staticmethod
    def project_3d_to_2d(
        point3d: Tuple[float, float, float],
        yaw_rad: float,
        pitch_rad: float,
        scale: float,
        center_x: float,
        center_y: float
    ) -> Tuple[float, float, float]:
        """
        Rotates point (x, y, z) by yaw around Y-axis, pitch around X-axis,
        and projects to 2D screen coordinates with perspective depth.
        Returns: (screen_x, screen_y, depth_z)
        """
        x, y, z = point3d

        # Yaw rotation (around Y axis)
        cos_y, sin_y = math.cos(yaw_rad), math.sin(yaw_rad)
        x1 = x * cos_y + z * sin_y
        y1 = y
        z1 = -x * sin_y + z * cos_y

        # Pitch rotation (around X axis)
        cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)
        x2 = x1
        y2 = y1 * cos_p - z1 * sin_p
        z2 = y1 * sin_p + z1 * cos_p

        # Perspective camera projection (focal distance D = 14.0)
        camera_dist = 14.0
        persp = camera_dist / (camera_dist + z2)
        sx = center_x + x2 * scale * persp
        sy = center_y + y2 * scale * persp

        return sx, sy, z2

    @staticmethod
    def ease_in_out_cubic(t: float) -> float:
        """Standard smooth ease-in-out cubic interpolation."""
        t = max(0.0, min(1.0, t))
        return 4.0 * t * t * t if t < 0.5 else 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0

    # -------------------------------------------------------------------------
    # Procedural Frame Rendering
    # -------------------------------------------------------------------------
    def render_frame(
        self,
        time_sec: float,
        total_duration: float,
        preset: Dict[str, Any],
        render_pass_num: int = 942
    ) -> Image.Image:
        """Renders an individual frame of the exploded CAD animation."""
        img = Image.new("RGB", (self.width, self.height), (8, 10, 14))
        draw = ImageDraw.Draw(img)

        # 1. Background studio gradient & isometric engineering grid
        self._draw_studio_background(draw, self.width, self.height)

        # 2. Compute animation phase & camera angles
        # Phase 1: 0.0 -> 0.28: Exploded separation
        # Phase 2: 0.28 -> 0.72: Orbital turntable inspection
        # Phase 3: 0.72 -> 0.90: Reassembly docking
        # Phase 4: 0.90 -> 1.00: Hero lock hold & final specular sheen
        t_norm = time_sec / total_duration

        if t_norm < 0.28:
            # Separation easing
            sub_t = t_norm / 0.28
            explode_factor = self.ease_in_out_cubic(sub_t)
            yaw_rad = math.radians(-22.0 + 8.0 * sub_t)
            pitch_rad = math.radians(24.0 + 3.0 * sub_t)
        elif t_norm < 0.72:
            # Full exploded orbital turntable sweep
            sub_t = (t_norm - 0.28) / (0.72 - 0.28)
            explode_factor = 1.0
            yaw_rad = math.radians(-14.0 + 36.0 * sub_t)
            pitch_rad = math.radians(27.0 - 5.0 * math.sin(math.pi * sub_t))
        elif t_norm < 0.90:
            # Reassembly docking
            sub_t = (t_norm - 0.72) / (0.90 - 0.72)
            explode_factor = 1.0 - self.ease_in_out_cubic(sub_t)
            yaw_rad = math.radians(22.0 - 10.0 * sub_t)
            pitch_rad = math.radians(22.0)
        else:
            # Final Hero lock
            explode_factor = 0.0
            yaw_rad = math.radians(12.0)
            pitch_rad = math.radians(20.0)

        # Scale & Center
        center_x = self.width * 0.48
        center_y = self.height * 0.52
        base_scale = min(self.width, self.height) * 0.11

        layers = preset.get("layers", [])

        # 3. Sort layers by depth (Back-to-front rendering)
        # Compute layer 3D centers
        layer_render_data = []
        for i, layer in enumerate(layers):
            z_curr = layer["z_rest"] + (layer["z_explode"] - layer["z_rest"]) * explode_factor
            # 3D bounding box for phone layer: W=3.2, H=6.5, Thickness=0.18
            w, h, th = 3.2, 6.5, 0.16
            center_3d = (0.0, 0.0, z_curr)
            _, _, depth = self.project_3d_to_2d(center_3d, yaw_rad, pitch_rad, base_scale, center_x, center_y)
            layer_render_data.append({
                "layer": layer,
                "index": i,
                "z_curr": z_curr,
                "depth": depth,
                "w": w,
                "h": h,
                "th": th
            })

        # Sort layers from furthest depth to closest depth
        layer_render_data.sort(key=lambda d: d["depth"], reverse=True)

        # 4. Render 3D layers
        callout_pins = []
        for ldata in layer_render_data:
            pin = self._render_3d_layer(
                draw, ldata, yaw_rad, pitch_rad, base_scale, center_x, center_y, explode_factor, t_norm
            )
            if pin:
                callout_pins.append(pin)

        # 5. Render Technical HUD Telemetry & Leader Lines
        self._render_hud_telemetry(
            draw, preset, callout_pins, time_sec, total_duration, explode_factor, render_pass_num
        )

        return img

    def _draw_studio_background(self, draw: ImageDraw.ImageDraw, w: int, h: int):
        """Draws dark obsidian studio environment with millimeter CAD grid & corner crosshairs."""
        # Engineering grid lines
        grid_step = 60
        grid_color = (18, 22, 30)
        sub_grid_color = (13, 16, 22)

        for x in range(0, w, grid_step // 2):
            c = grid_color if x % grid_step == 0 else sub_grid_color
            draw.line([(x, 0), (x, h)], fill=c, width=1)

        for y in range(0, h, grid_step // 2):
            c = grid_color if y % grid_step == 0 else sub_grid_color
            draw.line([(0, y), (w, y)], fill=c, width=1)

        # Subtle radial center vignette illumination
        cx, cy = w // 2, h // 2
        for r, alpha in [(300, (14, 18, 26)), (550, (11, 14, 20))]:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=alpha, width=1)

        # Corner technical CAD brackets
        margin = 35
        bracket_len = 25
        b_color = (45, 60, 85)

        # Top-Left
        draw.line([(margin, margin), (margin + bracket_len, margin)], fill=b_color, width=2)
        draw.line([(margin, margin), (margin, margin + bracket_len)], fill=b_color, width=2)
        # Top-Right
        draw.line([(w - margin, margin), (w - margin - bracket_len, margin)], fill=b_color, width=2)
        draw.line([(w - margin, margin), (w - margin, margin + bracket_len)], fill=b_color, width=2)
        # Bottom-Left
        draw.line([(margin, h - margin), (margin + bracket_len, h - margin)], fill=b_color, width=2)
        draw.line([(margin, h - margin), (margin, h - margin - bracket_len)], fill=b_color, width=2)
        # Bottom-Right
        draw.line([(w - margin, h - margin), (w - margin - bracket_len, h - margin)], fill=b_color, width=2)
        draw.line([(w - margin, h - margin), (w - margin, h - margin - bracket_len)], fill=b_color, width=2)

    def _render_3d_layer(
        self,
        draw: ImageDraw.ImageDraw,
        ldata: Dict[str, Any],
        yaw_rad: float,
        pitch_rad: float,
        scale: float,
        center_x: float,
        center_y: float,
        explode_factor: float,
        t_norm: float
    ) -> Optional[Dict[str, Any]]:
        """Renders a single 3D component layer with shading, bevels, and specular highlights."""
        layer = ldata["layer"]
        w = ldata["w"]
        h = ldata["h"]
        th = ldata["th"]
        z = ldata["z_curr"]

        hw = w / 2.0
        hh = h / 2.0
        hth = th / 2.0

        # 8 vertices of the rectangular slab in local 3D space
        # Front face (+Z):
        v_f_tl = (-hw, -hh, z + hth)
        v_f_tr = (hw, -hh, z + hth)
        v_f_br = (hw, hh, z + hth)
        v_f_bl = (-hw, hh, z + hth)
        # Back face (-Z):
        v_b_tl = (-hw, -hh, z - hth)
        v_b_tr = (hw, -hh, z - hth)
        v_b_br = (hw, hh, z - hth)
        v_b_bl = (-hw, hh, z - hth)

        all_v = [v_f_tl, v_f_tr, v_f_br, v_f_bl, v_b_tl, v_b_tr, v_b_br, v_b_bl]
        proj_2d = [
            self.project_3d_to_2d(v, yaw_rad, pitch_rad, scale, center_x, center_y)
            for v in all_v
        ]
        p_pts = [(p[0], p[1]) for p in proj_2d]

        # Faces with vertex indices:
        # Front: [0, 1, 2, 3]
        # Back: [4, 7, 6, 5]
        # Top: [4, 5, 1, 0]
        # Bottom: [3, 2, 6, 7]
        # Left: [4, 0, 3, 7]
        # Right: [1, 5, 6, 2]

        color = layer["color"]
        edge_col = layer["edge_color"]
        l_type = layer["type"]

        # Drop shadow underneath layer on floor
        if explode_factor > 0.1:
            shadow_poly = [
                (p[0] + 15 * explode_factor, p[1] + 25 * explode_factor)
                for p in [p_pts[4], p_pts[5], p_pts[6], p_pts[7]]
            ]
            draw.polygon(shadow_poly, fill=(5, 6, 9))

        # Determine surface illumination based on normal angle
        # Side face (Right or Left depending on yaw)
        if math.sin(yaw_rad) > 0:
            # Right face visible
            side_pts = [p_pts[1], p_pts[5], p_pts[6], p_pts[2]]
            side_col = tuple(max(0, int(c * 0.75)) for c in color)
            draw.polygon(side_pts, fill=side_col, outline=edge_col)
        else:
            # Left face visible
            side_pts = [p_pts[4], p_pts[0], p_pts[3], p_pts[7]]
            side_col = tuple(max(0, int(c * 0.65)) for c in color)
            draw.polygon(side_pts, fill=side_col, outline=edge_col)

        # Top face (due to positive pitch tilt)
        top_pts = [p_pts[4], p_pts[5], p_pts[1], p_pts[0]]
        top_col = tuple(min(255, int(c * 1.35 + 15)) for c in color)
        draw.polygon(top_pts, fill=top_col, outline=edge_col)

        # Front Face
        front_pts = [p_pts[0], p_pts[1], p_pts[2], p_pts[3]]
        draw.polygon(front_pts, fill=color, outline=edge_col)

        # Component specific internal graphics & texture details
        self._draw_component_details(draw, l_type, p_pts, edge_col, t_norm)

        # Pin coordinate for technical callout
        pin_3d = (hw * 0.8 if layer["callout_side"] == "right" else -hw * 0.8, -hh * 0.2, z)
        pin_x, pin_y, _ = self.project_3d_to_2d(pin_3d, yaw_rad, pitch_rad, scale, center_x, center_y)

        return {
            "layer": layer,
            "pin_x": pin_x,
            "pin_y": pin_y,
            "side": layer["callout_side"],
            "index": ldata["index"]
        }

    def _draw_component_details(
        self,
        draw: ImageDraw.ImageDraw,
        l_type: str,
        p_pts: List[Tuple[float, float]],
        edge_col: Tuple[int, int, int],
        t_norm: float
    ):
        """Draws realistic micro-textures and internal hardware silicon/copper structures."""
        # p_pts: 0=TL, 1=TR, 2=BR, 3=BL on front face
        tl, tr, br, bl = p_pts[0], p_pts[1], p_pts[2], p_pts[3]

        def lerp_pt(p1, p2, alpha):
            return (p1[0] + (p2[0] - p1[0]) * alpha, p1[1] + (p2[1] - p1[1]) * alpha)

        def quad_pt(u, v):
            top = lerp_pt(tl, tr, u)
            bot = lerp_pt(bl, br, u)
            return lerp_pt(top, bot, v)

        if l_type == "pcb":
            # Tensor G5 Silicon Die in center + RAM chip
            chip_tl = quad_pt(0.32, 0.35)
            chip_tr = quad_pt(0.68, 0.35)
            chip_br = quad_pt(0.68, 0.65)
            chip_bl = quad_pt(0.32, 0.65)
            # Silicon mirrored die
            draw.polygon([chip_tl, chip_tr, chip_br, chip_bl], fill=(22, 24, 28), outline=(60, 220, 160))

            # Gold wire bonds and micro-traces
            for trace_idx in range(5):
                u = 0.36 + trace_idx * 0.07
                p_a = quad_pt(u, 0.35)
                p_b = quad_pt(u, 0.22)
                draw.line([p_a, p_b], fill=(210, 175, 70), width=1)

            # Center Tensor G logo mark or microcode badge
            c_die = quad_pt(0.50, 0.50)
            draw.ellipse([c_die[0] - 6, c_die[1] - 6, c_die[0] + 6, c_die[1] + 6], outline=(70, 240, 180), width=1)

        elif l_type == "coil":
            # Concentric copper induction coils
            c_coil = quad_pt(0.50, 0.50)
            for r_factor in [0.15, 0.25, 0.35]:
                c_tl = quad_pt(0.50 - r_factor, 0.50 - r_factor)
                c_br = quad_pt(0.50 + r_factor, 0.50 + r_factor)
                draw.ellipse([c_tl[0], c_tl[1], c_br[0], c_br[1]], outline=(230, 130, 50), width=1)

        elif l_type == "camera_bar":
            # Three circular camera lenses: Main, Periscope rectangular prism, Ultrawide
            for pos_v in [0.28, 0.50, 0.72]:
                c_lens = quad_pt(0.50, pos_v)
                draw.ellipse([c_lens[0] - 8, c_lens[1] - 8, c_lens[0] + 8, c_lens[1] + 8], fill=(10, 12, 16), outline=(100, 140, 220), width=2)
                # Glass refraction glint
                draw.ellipse([c_lens[0] - 3, c_lens[1] - 3, c_lens[0] + 1, c_lens[1] + 1], fill=(200, 230, 255))

        elif l_type == "battery":
            # Battery cell safety wrapper with technical warnings
            b_box_tl = quad_pt(0.20, 0.15)
            b_box_br = quad_pt(0.80, 0.85)
            draw.rectangle([b_box_tl[0], b_box_tl[1], b_box_br[0], b_box_br[1]], outline=(60, 100, 150), width=1)
            # Battery trace contact terminals
            t_a = quad_pt(0.40, 0.15)
            t_b = quad_pt(0.60, 0.15)
            draw.line([(t_a[0], t_a[1] - 5), t_a], fill=(200, 170, 60), width=2)
            draw.line([(t_b[0], t_b[1] - 5), t_b], fill=(200, 170, 60), width=2)

        elif l_type == "display":
            # Subtle bezel border & front camera punch-hole
            hole = quad_pt(0.50, 0.08)
            draw.ellipse([hole[0] - 3, hole[1] - 3, hole[0] + 3, hole[1] + 3], fill=(5, 5, 8), outline=(50, 70, 100), width=1)

    def _render_hud_telemetry(
        self,
        draw: ImageDraw.ImageDraw,
        preset: Dict[str, Any],
        callout_pins: List[Dict[str, Any]],
        time_sec: float,
        total_duration: float,
        explode_factor: float,
        render_pass_num: int
    ):
        """Draws glowing technical HUD cards, leader lines, and status telemetry."""
        w, h = self.width, self.height

        font_title = self._get_font(18, bold=True)
        font_sub = self._get_font(11, bold=False)
        font_status = self._get_font(11, bold=True)
        font_status_sub = self._get_font(10, bold=False)
        font_box_title = self._get_font(11, bold=True)
        font_box_spec = self._get_font(9, bold=False)
        font_box_badge = self._get_font(9, bold=True)

        # Header Title & Workflow Info (Top Left)
        draw.text((45, 45), preset.get("title", "CAD EXPLODED VIEW"), fill=(225, 235, 250), font=font_title)
        draw.text((45, 72), preset.get("subtitle", "ARGON AUTONOMOUS HARDWARE ENGINE"), fill=(110, 135, 170), font=font_sub)

        # Top Right Live Telemetry Status
        status_line_1 = f"PASS: {render_pass_num:04d}/1000  |  FPS: {self.fps}  |  STATUS: NOMINAL"
        status_line_2 = f"ROTATION: {time_sec * 18.5:.1f}°  |  ZOOM: 1.00X  |  ELEVATION: 24.2°"
        draw.text((w - 440, 45), status_line_1, fill=(80, 200, 240), font=font_status)
        draw.text((w - 440, 68), status_line_2, fill=(110, 135, 170), font=font_status_sub)

        # Bottom Progress Telemetry Bar
        bar_w = w - 90
        bar_x = 45
        bar_y = h - 45
        prog = min(1.0, max(0.0, time_sec / total_duration))
        draw.line([(bar_x, bar_y), (bar_x + bar_w, bar_y)], fill=(30, 40, 55), width=2)
        draw.line([(bar_x, bar_y), (bar_x + int(bar_w * prog), bar_y)], fill=(60, 180, 240), width=2)
        draw.text((bar_x, bar_y - 20), f"ITERATIVE BLENDER MCP LOOP // T+{time_sec:.2f}s", fill=(90, 115, 145), font=font_sub)

        # Only draw exploded callouts if exploded separation is active
        if explode_factor < 0.25:
            return

        callout_alpha = min(1.0, (explode_factor - 0.25) / 0.5)

        # Draw technical leader lines & cards for key components
        highlight_layers = {"camera_visor", "logic_board", "battery_pack", "wireless_coil", "display_panel"}

        for pin in callout_pins:
            layer = pin["layer"]
            l_id = layer["id"]
            if l_id not in highlight_layers:
                continue

            px, py = pin["pin_x"], pin["pin_y"]
            side = pin["side"]

            # Anchor box coordinates
            box_w = 340
            box_h = 58
            if side == "right":
                box_x = w - box_w - 45
                box_y = py - 20
                elbow_x = px + 40
            else:
                box_x = 45
                box_y = py - 20
                elbow_x = px - 40

            # Leader pin point circle
            p_col = (70, 220, 255)
            draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=p_col)

            # Leader line: [Pin] -> [Elbow] -> [Box Anchor]
            line_end_x = box_x if side == "right" else box_x + box_w
            draw.line([(px, py), (elbow_x, py)], fill=(60, 140, 190), width=1)
            draw.line([(elbow_x, py), (line_end_x, box_y + 15)], fill=(60, 140, 190), width=1)

            # Technical Callout Box
            # Background plate
            draw.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=(12, 16, 24), outline=(40, 65, 95))
            # Left accent stripe
            draw.rectangle([box_x, box_y, box_x + 4, box_y + box_h], fill=(60, 200, 240))

            # Text content
            draw.text((box_x + 12, box_y + 6), layer["name"][:32], fill=(230, 240, 255), font=font_box_title)
            draw.text((box_x + 12, box_y + 24), layer["spec"][:48], fill=(140, 160, 185), font=font_box_spec)
            draw.text((box_x + 12, box_y + 40), layer["badge"], fill=(70, 215, 170), font=font_box_badge)

    # -------------------------------------------------------------------------
    # Blender MCP & Python Script Exporter
    # -------------------------------------------------------------------------
    @staticmethod
    def generate_blender_script(
        output_script_path: str,
        output_render_mp4: str = "pixel_exploded_render.mp4",
        fps: int = 30,
        duration_sec: float = 18.0
    ) -> str:
        """
        Generates a complete standalone Python script to be executed in Blender
        (`blender -b -P run_blender_exploded.py`) or via Blender MCP.
        Sets up true 3D meshes, PBR materials, keyframed exploded translation,
        orbital camera, 3-point lighting, and Eevee/Cycles render pipeline.
        """
        script_content = f'''import bpy
import math

# Clear existing objects
bpy.ops.wm.read_factory_settings(use_empty=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES' if bpy.context.preferences.addons.get('cycles') else 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.fps = {fps}
total_frames = int({duration_sec} * {fps})
scene.frame_start = 1
scene.frame_end = total_frames
scene.render.filepath = "{output_render_mp4}"

# Dark matte obsidian background
world = bpy.data.worlds.new("ObsidianStudio")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = (0.015, 0.018, 0.024, 1.0)
    bg_node.inputs[1].default_value = 0.8

# Camera Setup with Orbital Turntable Empty
cam_data = bpy.data.cameras.new("CAD_Camera")
cam_data.lens = 85.0
cam_obj = bpy.data.objects.new("CAD_Camera", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

empty = bpy.data.objects.new("CamTarget", None)
scene.collection.objects.link(empty)
empty.location = (0, 0, 0)

cam_obj.location = (0, -7.5, 3.2)
constraint = cam_obj.constraints.new(type='TRACK_TO')
constraint.target = empty
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'

# Animate Camera Turntable
empty.rotation_euler = (0, 0, math.radians(-25))
empty.keyframe_insert(data_path="rotation_euler", frame=1)
empty.rotation_euler = (0, 0, math.radians(25))
empty.keyframe_insert(data_path="rotation_euler", frame=total_frames)

# Studio 3-Point Lighting
# Key Light
key_light = bpy.data.lights.new("KeyLight", 'AREA')
key_light.energy = 350.0
key_light.size = 3.0
key_obj = bpy.data.objects.new("KeyLight", key_light)
key_obj.location = (4.0, -4.0, 5.0)
scene.collection.objects.link(key_obj)

# Rim Specular Light
rim_light = bpy.data.lights.new("RimLight", 'SPOT')
rim_light.energy = 500.0
rim_light.color = (0.6, 0.8, 1.0)
rim_obj = bpy.data.objects.new("RimLight", rim_light)
rim_obj.location = (-3.5, 4.5, 4.0)
scene.collection.objects.link(rim_obj)

# Helper function to create materials
def make_mat(name, color, metallic=0.0, roughness=0.3, transmission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = transmission
    return mat

mat_chassis = make_mat("AluChassis", (0.35, 0.38, 0.42, 1.0), metallic=0.92, roughness=0.25)
mat_pcb = make_mat("PCB", (0.05, 0.15, 0.10, 1.0), metallic=0.2, roughness=0.5)
mat_copper = make_mat("Copper", (0.85, 0.45, 0.20, 1.0), metallic=0.98, roughness=0.18)
mat_battery = make_mat("Battery", (0.12, 0.14, 0.18, 1.0), metallic=0.4, roughness=0.4)
mat_glass = make_mat("GorillaGlass", (0.08, 0.10, 0.14, 1.0), metallic=0.1, roughness=0.05, transmission=0.85)

# Layer definitions (Name, dims, z_rest, z_exploded, material)
layers = [
    ("Display_Assembly", (1.8, 3.8, 0.04), -1.2, -3.2, mat_glass),
    ("Alu_Chassis_7000", (1.85, 3.85, 0.08), -0.8, -1.8, mat_chassis),
    ("Vapor_Chamber", (1.4, 2.5, 0.02), -0.3, -0.7, mat_copper),
    ("Logic_Board_TensorG5", (1.6, 2.2, 0.04), 0.1, 0.3, mat_pcb),
    ("Battery_5060mAh", (1.3, 2.4, 0.08), 0.5, 1.3, mat_battery),
    ("Qi2_Induction_Coil", (1.1, 1.1, 0.02), 0.9, 2.1, mat_copper),
    ("Camera_Visor_Optics", (1.75, 0.8, 0.12), 1.2, 2.9, mat_chassis),
    ("Gorilla_Glass_Back", (1.8, 3.8, 0.04), 1.5, 3.8, mat_glass),
]

for name, dims, z_r, z_e, mat in layers:
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (dims[0], dims[1], dims[2])
    obj.data.materials.append(mat)

    # Keyframe Explosion Animation
    # Frame 1: Resting assembled
    obj.location = (0, 0, z_r)
    obj.keyframe_insert(data_path="location", frame=1)

    # Frame 60: Fully exploded
    f_open = int(total_frames * 0.28)
    obj.location = (0, 0, z_e)
    obj.keyframe_insert(data_path="location", frame=f_open)

    # Frame 150: Hold exploded inspection
    f_hold = int(total_frames * 0.72)
    obj.location = (0, 0, z_e)
    obj.keyframe_insert(data_path="location", frame=f_hold)

    # Frame 200: Reassembled docking
    f_dock = int(total_frames * 0.90)
    obj.location = (0, 0, z_r)
    obj.keyframe_insert(data_path="location", frame=f_dock)

print("Argon Exploded CAD Scene configured successfully.")
'''
        Path(output_script_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        return output_script_path

    # -------------------------------------------------------------------------
    # Full Autonomous Video Pipeline
    # -------------------------------------------------------------------------
    def generate_exploded_video(
        self,
        output_video_path: str,
        duration: float = 18.0,
        preset: Optional[Dict[str, Any]] = None,
        script_text: Optional[str] = None,
        voice: Optional[str] = None,
        lang: str = "en"
    ) -> Dict[str, Any]:
        """
        Renders the entire exploded CAD video with synchronized procedural mechanical Foley audio.
        Optionally mixes neural voiceover if script_text is provided.
        """
        output_video_path = Path(output_video_path).resolve()
        output_video_path.parent.mkdir(parents=True, exist_ok=True)

        if preset is None:
            preset = PIXEL_TENSOR_HARDWARE_PRESET

        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)
            frames_dir = temp_dir / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)

            total_frames = int(duration * self.fps)
            print(f"[CAD Engine] Rendering {total_frames} frames at {self.width}x{self.height} ({self.fps} fps)...")

            # 1. Render all procedural frames
            # Batch render with progress reporting
            for frame_idx in range(total_frames):
                t_sec = frame_idx / self.fps
                frame_img = self.render_frame(
                    time_sec=t_sec,
                    total_duration=duration,
                    preset=preset,
                    render_pass_num=940 + (frame_idx % 60)
                )
                frame_path = frames_dir / f"frame_{frame_idx:05d}.jpg"
                frame_img.save(frame_path, quality=94)

            # 2. Synthesize Mechanical Foley Audio Track
            sfx_wav_path = temp_dir / "mechanical_sfx.wav"
            print("[CAD Engine] Synthesizing synchronized mechanical Foley audio (pneumatics, servos, latches)...")
            SoundEffectsSynthesizer.generate_mechanical_exploded_soundtrack(
                sfx_wav_path, total_duration=duration, sample_rate=44100
            )

            # 3. Optional Voiceover Generation
            final_audio_path = sfx_wav_path
            if script_text:
                print(f"[CAD Engine] Synthesizing neural voiceover in {lang.upper()}...")
                v_target = voice or ("ta-IN-PallaviNeural" if lang == "ta" else "en-US-AvaNeural")
                tts_wav_path = temp_dir / "voiceover.wav"
                generate_voiceover(script_text, str(tts_wav_path), voice=v_target)

                # Mix voiceover with mechanical Foley
                mixed_audio_path = temp_dir / "mixed_master.wav"
                mix_cmd = [
                    "ffmpeg", "-y",
                    "-i", str(tts_wav_path),
                    "-i", str(sfx_wav_path),
                    "-filter_complex",
                    "[0:a]volume=1.0[voice];[1:a]volume=0.45[foley];[voice][foley]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                    "-map", "[aout]",
                    "-ac", "2",
                    str(mixed_audio_path)
                ]
                subprocess.run(mix_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                final_audio_path = mixed_audio_path

            # 4. Assemble video with FFmpeg
            raw_video_path = temp_dir / "raw_video.mp4"
            print("[CAD Engine] Assembling master MP4...")
            v_cmd = [
                "ffmpeg", "-y",
                "-framerate", str(self.fps),
                "-i", str(frames_dir / "frame_%05d.jpg"),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                str(raw_video_path)
            ]
            subprocess.run(v_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # Mux video with audio
            mux_cmd = [
                "ffmpeg", "-y",
                "-i", str(raw_video_path),
                "-i", str(final_audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                str(output_video_path)
            ]
            subprocess.run(mux_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Also generate companion Blender script for power users
        blender_script_path = str(output_video_path).replace(".mp4", "_blender.py")
        self.generate_blender_script(blender_script_path, output_render_mp4=output_video_path.name, fps=self.fps, duration_sec=duration)

        return {
            "video_path": str(output_video_path),
            "blender_script": blender_script_path,
            "duration": duration,
            "resolution": f"{self.width}x{self.height}",
            "fps": self.fps,
            "preset": preset["title"]
        }
