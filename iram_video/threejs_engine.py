"""
IRAM Video Three.js 3D WebGL Engine
Generates interactive, hardware-accelerated 3D motion graphics, kinetic titles,
holographic tech backdrops, and code matrices for YouTube documentaries and cinema trailers.
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

THREEJS_CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
ORBIT_CONTROLS_CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"

THEME_PALETTES = {
    "tokyo_storm": {"bg": "#07090e", "primary": "#00f0ff", "secondary": "#7000ff", "accent": "#ff006e"},
    "cyberpunk_neon": {"bg": "#05050a", "primary": "#00f0ff", "secondary": "#ffe600", "accent": "#ff0055"},
    "catppuccin": {"bg": "#1e1e2e", "primary": "#cba6f7", "secondary": "#89b4fa", "accent": "#f38ba8"},
    "matrix_green": {"bg": "#020804", "primary": "#00ff66", "secondary": "#05ffa1", "accent": "#003b15"}
}

def generate_3d_kinetic_title_html(
    title: str = "IRAM OS SOVEREIGN ENGINE",
    subtitle: str = "Hardware-Accelerated Autonomous Multimedia OS",
    preset: str = "neon_kinetic",
    palette_name: str = "tokyo_storm",
    aspect_ratio: str = "16:9"
) -> str:
    """Generates a complete standalone Three.js WebGL 3D animation HTML page."""
    palette = THEME_PALETTES.get(palette_name, THEME_PALETTES["tokyo_storm"])
    is_vertical = (aspect_ratio in ["9:16", "vertical", "shorts"])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 3D Motion Title</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; user-select:none; }}
        body {{
            background: {palette['bg']};
            color: #ffffff;
            font-family: "JetBrains Mono", -apple-system, BlinkMacSystemFont, monospace;
            overflow: hidden;
            width: 100vw;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        #canvas-container {{
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
            z-index: 1;
        }}
        .title-overlay {{
            position: absolute;
            z-index: 10;
            text-align: center;
            pointer-events: none;
            padding: 20px;
            max-width: {'85%' if is_vertical else '75%'};
        }}
        .badge {{
            display: inline-block;
            background: rgba(0, 240, 255, 0.15);
            border: 1px solid {palette['primary']};
            color: {palette['primary']};
            font-size: 11px;
            font-weight: 800;
            padding: 4px 14px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 16px;
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
            animation: fadeInDown 0.8s ease-out;
        }}
        .main-title {{
            font-size: {'28px' if is_vertical else '48px'};
            font-weight: 900;
            letter-spacing: {'2px' if is_vertical else '4px'};
            text-transform: uppercase;
            color: #ffffff;
            text-shadow: 0 0 30px {palette['primary']}, 0 0 60px {palette['secondary']};
            margin-bottom: 12px;
            line-height: 1.2;
            animation: zoomIn 1s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        .subtitle {{
            font-size: {'13px' if is_vertical else '18px'};
            font-weight: 500;
            color: #a6adc8;
            letter-spacing: 1px;
            line-height: 1.5;
            animation: fadeInUp 1.2s ease-out;
        }}
        @keyframes fadeInDown {{ from {{ opacity:0; transform:translateY(-20px); }} to {{ opacity:1; transform:translateY(0); }} }}
        @keyframes fadeInUp {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
        @keyframes zoomIn {{ from {{ opacity:0; transform:scale(0.85); }} to {{ opacity:1; transform:scale(1); }} }}
    </style>
    <script src="{THREEJS_CDN}"></script>
    <script src="{ORBIT_CONTROLS_CDN}"></script>
</head>
<body>
    <div id="canvas-container"></div>
    <div class="title-overlay">
        <div class="badge">IRAM OS Sovereign Studio</div>
        <div class="main-title">{title}</div>
        <div class="subtitle">{subtitle}</div>
    </div>

    <script>
        let scene, camera, renderer, controls;
        let coreGroup, torusMesh, particles;

        function init() {{
            const container = document.getElementById('canvas-container');
            scene = new THREE.Scene();
            scene.fog = new THREE.FogExp2('{palette['bg']}', 0.025);

            camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(0, 0, 28);

            renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            container.appendChild(renderer.domElement);

            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.autoRotate = true;
            controls.autoRotateSpeed = 1.2;

            // Lights
            scene.add(new THREE.AmbientLight(0xffffff, 0.4));
            const pLight1 = new THREE.PointLight(0x{palette['primary'].replace('#', '')}, 3, 50);
            pLight1.position.set(12, 12, 12);
            scene.add(pLight1);

            const pLight2 = new THREE.PointLight(0x{palette['accent'].replace('#', '')}, 2, 50);
            pLight2.position.set(-12, -12, 10);
            scene.add(pLight2);

            // Core 3D Geometry
            coreGroup = new THREE.Group();

            const torusGeo = new THREE.TorusGeometry(8.5, 0.8, 30, 200);
            const torusMat = new THREE.MeshStandardMaterial({{
                color: 0x{palette['primary'].replace('#', '')},
                wireframe: true,
                emissive: 0x{palette['primary'].replace('#', '')},
                emissiveIntensity: 0.6
            }});
            torusMesh = new THREE.Mesh(torusGeo, torusMat);
            coreGroup.add(torusMesh);

            const innerGeo = new THREE.IcosahedronGeometry(4.5, 2);
            const innerMat = new THREE.MeshStandardMaterial({{
                color: 0x{palette['secondary'].replace('#', '')},
                wireframe: true,
                emissive: 0x{palette['secondary'].replace('#', '')},
                emissiveIntensity: 0.4
            }});
            const innerMesh = new THREE.Mesh(innerGeo, innerMat);
            coreGroup.add(innerMesh);

            // Particle Field
            const pCount = 1800;
            const pGeo = new THREE.BufferGeometry();
            const pPos = new Float32Array(pCount * 3);
            for (let i = 0; i < pCount * 3; i += 3) {{
                pPos[i] = (Math.random() - 0.5) * 80;
                pPos[i+1] = (Math.random() - 0.5) * 80;
                pPos[i+2] = (Math.random() - 0.5) * 80;
            }}
            pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
            const pMat = new THREE.PointsMaterial({{
                color: 0x{palette['primary'].replace('#', '')},
                size: 0.28,
                transparent: true,
                opacity: 0.8
            }});
            particles = new THREE.Points(pGeo, pMat);
            scene.add(particles);

            scene.add(coreGroup);

            window.addEventListener('resize', onWindowResize, false);
            animate();
        }}

        function onWindowResize() {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }}

        function animate() {{
            requestAnimationFrame(animate);
            if (controls) controls.update();
            if (coreGroup) {{
                coreGroup.rotation.x += 0.005;
                coreGroup.rotation.y += 0.008;
            }}
            if (particles) {{
                particles.rotation.y -= 0.001;
            }}
            renderer.render(scene, camera);
        }}

        window.onload = init;
    </script>
</body>
</html>"""
    return html

def export_3d_title_scene(output_file: str, title: str, subtitle: str = "", palette: str = "tokyo_storm", aspect_ratio: str = "16:9") -> str:
    """Exports a 3D WebGL motion scene HTML file ready to view or capture."""
    out_path = Path(output_file).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_3d_kinetic_title_html(title=title, subtitle=subtitle, palette_name=palette, aspect_ratio=aspect_ratio)
    out_path.write_text(content, encoding="utf-8")
    print(f"🪐 [THREE.JS] 3D Motion Graphics Scene exported to: {out_path}")
    return str(out_path)

def launch_3d_studio(port: int = 8995):
    """Launches the dedicated Three.js 3D Motion Graphics Studio GUI."""
    if shutil.which("iram-video-3d"):
        subprocess.Popen(["iram-video-3d"])
        print("🪐 [THREE.JS] Launched IRAM OS 3D Motion Graphics Studio on Wayland.")
    elif shutil.which("iram-3d"):
        subprocess.Popen(["iram-3d"])
        print("🪐 [THREE.JS] Launched IRAM 3D CAD & Mesh Inspector.")
    else:
        # Fallback to local viewer
        import tempfile
        tmp_html = Path(tempfile.gettempdir()) / "iram_video_3d_studio.html"
        export_3d_title_scene(str(tmp_html), "IRAM OS THREE.JS STUDIO", "Interactive WebGL 3D Motion Graphics Engine")
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(tmp_html)])
        print(f"🪐 [THREE.JS] Opened 3D WebGL scene at: {tmp_html}")
