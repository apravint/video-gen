import os
import re
import sys
import json
import base64
import mimetypes
import threading
import subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from iram_video.soundscape import SoundscapeAdvisor

RESOURCES_DIR = Path(os.getenv("IRAM_RESOURCES_DIR", Path.home() / "resources"))
OUTPUTS_DIR = Path(os.getenv("IRAM_OUTPUTS_DIR", Path.home()))
UPLOAD_DIR = Path(os.getenv("IRAM_UPLOAD_DIR", "/tmp/iram_uploads"))

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>IRAM Video Studio — Autonomous AI Cinema & Animation Engine</title>
  <style>
    :root {
      --bg: #0b0f17;
      --card: #131b2a;
      --card-hover: #172235;
      --border: #233045;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --accent-glow: rgba(59, 130, 246, 0.2);
      --sky: #38bdf8;
      --text: #f8fafc;
      --muted: #94a3b8;
      --card-inner: #0d1422;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "JetBrains Mono", sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
    header { background: rgba(19, 27, 42, 0.88); backdrop-filter: blur(14px); border-bottom: 1px solid var(--border); padding: 18px 36px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; }
    .brand { display: flex; align-items: center; gap: 14px; font-weight: 700; font-size: 20px; letter-spacing: -0.4px; }
    .badge { font-size: 11px; padding: 4px 10px; border-radius: 6px; background: rgba(59, 130, 246, 0.12); color: var(--sky); border: 1px solid rgba(59, 130, 246, 0.3); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }
    main { max-width: 1440px; margin: 0 auto; padding: 32px 24px; width: 100%; display: grid; grid-template-columns: 1.18fr 0.82fr; gap: 32px; }
    @media (max-width: 1024px) { main { grid-template-columns: 1fr; } }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 26px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35); }
    h2 { font-size: 17px; font-weight: 600; margin-bottom: 18px; color: #fff; display: flex; align-items: center; gap: 10px; }
    .form-group { margin-bottom: 20px; }
    label { display: block; font-size: 13px; font-weight: 500; color: var(--muted); margin-bottom: 8px; }
    textarea, select, input[type="text"] { width: 100%; background: var(--card-inner); border: 1px solid var(--border); border-radius: 8px; padding: 12px 14px; color: var(--text); font-size: 14px; transition: border 0.2s; outline: none; }
    textarea:focus, select:focus, input[type="text"]:focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }
    textarea { resize: vertical; min-height: 95px; line-height: 1.5; }
    
    .chip-section { margin-top: 10px; }
    .chip-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); margin-bottom: 6px; font-weight: 600; }
    .chips { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 10px; }
    .chip { font-size: 12px; padding: 5px 12px; border-radius: 16px; background: #182335; border: 1px solid var(--border); color: #cbd5e1; cursor: pointer; transition: all 0.2s; user-select: none; }
    .chip:hover { border-color: var(--accent); color: var(--sky); background: rgba(59, 130, 246, 0.1); }
    
    .radio-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .radio-card { border: 1px solid var(--border); border-radius: 8px; padding: 12px; background: var(--card-inner); cursor: pointer; display: flex; align-items: center; gap: 10px; transition: all 0.2s; }
    .radio-card input { width: auto; accent-color: var(--accent); }
    .radio-card.active { border-color: var(--accent); background: rgba(59, 130, 246, 0.08); }
    
    .btn-generate { width: 100%; padding: 14px; border-radius: 8px; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: #fff; font-weight: 600; font-size: 15px; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px; box-shadow: 0 4px 18px rgba(59, 130, 246, 0.3); transition: opacity 0.2s; }
    .btn-generate:hover { opacity: 0.94; }
    .btn-generate:disabled { opacity: 0.45; cursor: not-allowed; }
    
    .btn-secondary { background: #1e293b; color: #cbd5e1; border: 1px solid var(--border); padding: 8px 14px; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; }
    .btn-secondary:hover { background: #27354a; color: #fff; border-color: var(--accent); }

    .video-preview-wrapper { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 10px; overflow: hidden; border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; position: relative; }
    .video-preview-wrapper.shorts-mode { aspect-ratio: 9/16; max-height: 520px; margin: 0 auto; }
    video { width: 100%; height: 100%; object-fit: contain; }
    
    .status-box { margin-top: 16px; padding: 13px; border-radius: 8px; background: var(--card-inner); border: 1px solid var(--border); font-size: 13px; font-family: monospace; color: var(--sky); min-height: 48px; display: flex; align-items: center; gap: 10px; }
    .spinner { border: 2px solid rgba(59, 130, 246, 0.2); border-top-color: var(--accent); border-radius: 50%; width: 16px; height: 16px; animation: spin 0.8s linear infinite; display: none; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .dropzone { border: 1px dashed var(--border); border-radius: 8px; padding: 16px; text-align: center; background: var(--card-inner); cursor: pointer; transition: all 0.2s; }
    .dropzone:hover { border-color: var(--accent); background: rgba(59, 130, 246, 0.04); }
    .dropzone-text { font-size: 12px; color: var(--muted); }

    .recent-reel { margin-top: 24px; }
    .recent-list { display: flex; flex-direction: column; gap: 8px; max-height: 250px; overflow-y: auto; margin-top: 10px; }
    .recent-item { background: var(--card-inner); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; font-size: 13px; cursor: pointer; transition: all 0.2s; }
    .recent-item:hover { border-color: var(--accent); background: var(--card-hover); }
    .recent-name { color: #e2e8f0; font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 280px; }
    .recent-size { font-size: 11px; color: var(--muted); }

    .soundscape-box { margin-top: 16px; background: var(--card-inner); border: 1px solid var(--border); border-radius: 8px; padding: 14px; font-size: 12px; line-height: 1.6; display: none; }
    .soundscape-box h3 { font-size: 13px; color: var(--sky); margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span>🎬 IRAM Video Studio</span>
      <span class="badge">Modern Cinema • Steady-Cam • AI Soundscape • MCP Ready</span>
    </div>
    <div style="font-size: 13px; color: var(--muted);">IRAM OS Local Studio</div>
  </header>

  <main>
    <div class="card">
      <h2>⚙️ Director & Production Console</h2>
      
      <div class="form-group">
        <label>Import from Structured JSON Blueprint:</label>
        <select id="jsonSelect">
          <option value="">-- Direct Text Prompt Only --</option>
        </select>
      </div>

      <div class="form-group">
        <label>Screenplay Premise / Directorial Vision (English or தமிழ்):</label>
        <textarea id="promptInput" placeholder="Describe the video narrative, documentary focus, or technical concept...">How AI is transforming software engineering and modern coding workflows</textarea>
        
        <div class="chip-section">
          <div class="chip-title">🎥 Cinematography & Camera Movement</div>
          <div class="chips">
            <span class="chip" onclick="addChip('subtle steady-cam micro-drift')">📹 Steady Micro-Drift</span>
            <span class="chip" onclick="addChip('slow orbital 360 degree pan')">🔄 Orbital 360</span>
            <span class="chip" onclick="addChip('smooth tracking dolly shot')">🛤️ Tracking Dolly</span>
            <span class="chip" onclick="addChip('FPV drone flyover')">🛸 FPV Flyover</span>
            <span class="chip" onclick="addChip('macro close-up detail')">🔍 Macro Detail</span>
            <span class="chip" onclick="addChip('wide architectural establishing shot')">🏛️ Wide Establishing</span>
          </div>

          <div class="chip-title">💡 Lighting & Atmosphere</div>
          <div class="chips">
            <span class="chip" onclick="addChip('soft diffused studio lighting')">🛋️ Soft Studio</span>
            <span class="chip" onclick="addChip('golden hour natural sunlight')">🌅 Golden Hour</span>
            <span class="chip" onclick="addChip('high-contrast chiaroscuro shadows')">🌓 Chiaroscuro</span>
            <span class="chip" onclick="addChip('moody volumetric fog')">🌫️ Volumetric Fog</span>
            <span class="chip" onclick="addChip('clean natural daylight')">☀️ Natural Daylight</span>
          </div>

          <div class="chip-title">🎨 Visual Style & Texture</div>
          <div class="chips">
            <span class="chip" onclick="addChip('photorealistic 8k cinematic texture')">🎞️ 8k Cinematic</span>
            <span class="chip" onclick="addChip('minimalist tech editorial style')">📐 Tech Editorial</span>
            <span class="chip" onclick="addChip('vintage 35mm film grain')">🎞️ 35mm Film</span>
            <span class="chip" onclick="addChip('clean documentary realism')">📽️ Documentary</span>
            <span class="chip" onclick="addChip('executive corporate design')">🏢 Executive</span>
          </div>
        </div>
      </div>

      <div class="form-group">
        <label>Production Format:</label>
        <div class="radio-grid">
          <label class="radio-card active"><input type="radio" name="mode" value="real" checked> 🎥 Real YouTube Video (B-Roll, Steady-Cam)</label>
          <label class="radio-card"><input type="radio" name="mode" value="film"> 🎭 Animated Feature Film</label>
          <label class="radio-card"><input type="radio" name="mode" value="cinema"> 🎬 Cinema Blockbuster Trailer</label>
          <label class="radio-card"><input type="radio" name="mode" value="shorts"> 📱 YouTube Shorts (9:16)</label>
        </div>
      </div>

      <div class="form-group">
        <label>Image-to-Video Starter Frame (Optional):</label>
        <div class="dropzone" id="imageDropzone" onclick="document.getElementById('fileInput').click()">
          <span class="dropzone-text" id="dropzoneText">📁 Click or drop image here for Image-to-Video storyboarding</span>
          <input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFileSelect(event)">
        </div>
        <input type="text" id="startImagePath" placeholder="Or enter local image path..." style="margin-top: 8px;">
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;" class="form-group">
        <div>
          <label>Animated Mascot Cast (Film / Cinema):</label>
          <select id="charSelect">
            <option value="auto">Auto Selection</option>
            <option value="robot">Unit-7 (Engineering Robot)</option>
            <option value="presenter">Nova (Lead Architect)</option>
            <option value="ferris">Ferris (Rust Mascot)</option>
            <option value="gopher">Gopher (Go Mascot)</option>
          </select>
        </div>
        <div>
          <label>Broadcast Language:</label>
          <select id="langSelect">
            <option value="en">English (Editorial Commentary)</option>
            <option value="ta">தமிழ் (Tamil Cinema)</option>
          </select>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;" class="form-group">
        <div>
          <label>Genre Blueprint / Template:</label>
          <select id="templateSelect">
            <option value="">-- Freeform Editorial (Default) --</option>
            <option value="explainer">💡 Deep-Dive Explainer</option>
            <option value="tutorial">🛠️ Step-by-Step Tutorial</option>
            <option value="listicle">🔢 Ranked Listicle / Countdown</option>
            <option value="comparison">⚖️ Head-to-Head Comparison</option>
            <option value="news">📰 Tech News / Product Release</option>
            <option value="promo">🚀 SaaS / Startup Promo</option>
            <option value="podcast">🎙️ Dual-Voice Studio Podcast</option>
          </select>
        </div>
        <div>
          <label>Aspect Ratio & Framing:</label>
          <select id="ratioSelect">
            <option value="auto">Auto (Matches Format)</option>
            <option value="16:9">16:9 Landscape (YouTube / Desktop)</option>
            <option value="9:16">9:16 Vertical (Shorts / Reels)</option>
            <option value="1:1">1:1 Square (Instagram / LinkedIn)</option>
            <option value="2.39:1">2.39:1 Cinema Scope (Widescreen)</option>
          </select>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;" class="form-group">
        <div>
          <label>Cinematic Scene Transition:</label>
          <select id="transitionSelect">
            <option value="fade">Dissolve / Crossfade</option>
            <option value="wipeleft">Wipe Left</option>
            <option value="slideleft">Slide Left</option>
            <option value="circlecrop">Iris / Circle Crop</option>
            <option value="smoothleft">Smooth Left Push</option>
            <option value="fadeblack">Dip to Black</option>
          </select>
        </div>
        <div>
          <label>Cinematic Color Grade:</label>
          <select id="gradeSelect">
            <option value="auto">Auto Grade</option>
            <option value="clean">Clean Enterprise</option>
            <option value="documentary">Documentary Realism</option>
            <option value="cinematic">Cinematic 35mm</option>
            <option value="vintage">Vintage Film</option>
            <option value="noir">Moody Noir</option>
            <option value="vibrant">Vibrant Tech</option>
          </select>
        </div>
      </div>

      <div style="display: flex; gap: 12px; margin-bottom: 20px;">
        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; font-size: 13px; color: var(--text);">
          <input type="checkbox" id="steadyToggle" checked style="accent-color: var(--accent);"> Steady Camera (Disable lateral pan swings)
        </label>
        <button type="button" class="btn-secondary" onclick="planSoundscape()" style="margin-left: auto;">🎧 Plan AI Soundscape</button>
      </div>

      <button id="btnGen" class="btn-generate" onclick="startGeneration()">
        <span>🚀 Direct & Render Master Video</span>
      </button>

      <div class="status-box">
        <div class="spinner" id="spinner"></div>
        <span id="statusText">Ready to direct. Select options and click Render.</span>
      </div>
    </div>

    <div class="card">
      <h2>📽️ Master Broadcast Monitor</h2>
      <div class="video-preview-wrapper" id="previewWrap">
        <video id="videoPlayer" controls playsinline></video>
      </div>
      <div style="margin-top: 18px; display: flex; justify-content: space-between; align-items: center;">
        <span id="videoMeta" style="font-size: 13px; color: var(--muted);">No video loaded</span>
        <a id="downloadBtn" href="#" download style="font-size: 13px; color: var(--sky); text-decoration: none; display: none; font-weight: 500;">⬇️ Download Master MP4</a>
      </div>

      <div class="soundscape-box" id="soundscapeBox">
        <h3>🎼 AI Soundscape & Foley Blueprint</h3>
        <div id="soundscapeContent"></div>
      </div>

      <div class="recent-reel">
        <h2>🎞️ Recent Production Reel</h2>
        <div class="recent-list" id="recentList">
          <div style="font-size: 12px; color: var(--muted); padding: 8px;">Loading recent videos...</div>
        </div>
      </div>
    </div>
  </main>

  <script>
    function escapeHtml(str) {
      if (!str) return '';
      const div = document.createElement('div');
      div.textContent = String(str);
      return div.innerHTML;
    }

    async function loadResources() {
      try {
        const res = await fetch('/api/resources');
        const files = await res.json();
        const sel = document.getElementById('jsonSelect');
        files.forEach(f => {
          const opt = document.createElement('option');
          opt.value = f.name;
          opt.textContent = f.name + (f.title && f.title !== f.name ? ' (' + f.title + ')' : '');
          sel.appendChild(opt);
        });
      } catch (e) {
        console.error("Failed to load resources", e);
      }
    }

    async function loadRecentVideos() {
      try {
        const res = await fetch('/api/recent_videos');
        const list = await res.json();
        const container = document.getElementById('recentList');
        if (!list || list.length === 0) {
          container.innerHTML = '<div style="font-size: 12px; color: var(--muted); padding: 8px;">No recent videos found.</div>';
          return;
        }
        container.innerHTML = '';
        list.forEach(v => {
          const item = document.createElement('div');
          item.className = 'recent-item';
          const safeName = escapeHtml(v.filename);
          const safeSize = Number(v.size_mb || 0).toFixed(2);
          item.innerHTML = `
            <div class="recent-name" title="${safeName}">🎬 ${safeName}</div>
            <div class="recent-size">${safeSize} MB</div>
          `;
          item.onclick = () => {
            const vp = document.getElementById('videoPlayer');
            vp.src = '/video/' + encodeURIComponent(v.filename);
            vp.play();
            document.getElementById('videoMeta').textContent = v.filename + ' (' + safeSize + ' MB)';
            const dl = document.getElementById('downloadBtn');
            dl.href = '/video/' + encodeURIComponent(v.filename);
            dl.style.display = 'inline';
          };
          container.appendChild(item);
        });
      } catch (e) {
        console.error("Failed to load recent videos", e);
      }
    }

    loadResources();
    loadRecentVideos();

    document.querySelectorAll('.radio-card').forEach(rc => {
      rc.addEventListener('click', () => {
        document.querySelectorAll('.radio-card').forEach(c => c.classList.remove('active'));
        rc.classList.add('active');
        rc.querySelector('input').checked = true;
        const mode = rc.querySelector('input').value;
        const wrap = document.getElementById('previewWrap');
        if (mode === 'shorts') {
          wrap.classList.add('shorts-mode');
        } else {
          wrap.classList.remove('shorts-mode');
        }
      });
    });

    function addChip(text) {
      const el = document.getElementById('promptInput');
      el.value = el.value.trim() ? el.value.trim() + ', ' + text : text;
    }

    function handleFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;
      uploadImageFile(file);
    }

    const dropzone = document.getElementById('imageDropzone');
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.style.borderColor = '#3b82f6'; });
    dropzone.addEventListener('dragleave', () => { dropzone.style.borderColor = 'var(--border)'; });
    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--border)';
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        uploadImageFile(e.dataTransfer.files[0]);
      }
    });

    async function uploadImageFile(file) {
      const dropText = document.getElementById('dropzoneText');
      dropText.textContent = "Uploading " + file.name + "...";
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const res = await fetch('/api/upload_image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data: e.target.result, name: file.name })
          });
          const d = await res.json();
          if (d.status === 'success') {
            document.getElementById('startImagePath').value = d.path;
            dropText.textContent = "✓ Image Loaded: " + file.name;
          } else {
            dropText.textContent = "❌ Upload failed";
          }
        } catch (err) {
          dropText.textContent = "❌ Error uploading";
        }
      };
      reader.readAsDataURL(file);
    }

    async function planSoundscape() {
      const prompt = document.getElementById('promptInput').value;
      const box = document.getElementById('soundscapeBox');
      const content = document.getElementById('soundscapeContent');
      box.style.display = 'block';
      content.innerHTML = '<span style="color:var(--muted)">Consulting AI Soundscape Director...</span>';
      try {
        const res = await fetch('/api/soundscape', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        if (data.status === 'success' && data.soundscape) {
          const s = data.soundscape;
          content.innerHTML = `
            <div><strong>Style:</strong> ${s.bgm_style || 'Cinematic Documentary'}</div>
            <div><strong>Mood:</strong> ${s.bgm_mood || 'Inspirational'} (BPM: ${s.tempo_bpm || 105})</div>
            <div><strong>Instrumentation:</strong> ${(s.instruments || []).join(', ')}</div>
            <div style="margin-top: 6px;"><strong>Foley Cues:</strong> ${(s.foley_cues || []).map(f => f.effect_type + ' (' + f.description + ')').join(' • ') || 'Ambient Room Tone'}</div>
          `;
        } else {
          content.innerHTML = '<span style="color:#ef4444">Failed to generate soundscape plan</span>';
        }
      } catch (err) {
        content.innerHTML = '<span style="color:#ef4444">Error: ' + err.message + '</span>';
      }
    }

    async function startGeneration() {
      const btn = document.getElementById('btnGen');
      const spinner = document.getElementById('spinner');
      const statusText = document.getElementById('statusText');
      const prompt = document.getElementById('promptInput').value;
      const jsonDoc = document.getElementById('jsonSelect').value;
      const mode = document.querySelector('input[name="mode"]:checked').value;
      const character = document.getElementById('charSelect').value;
      const language = document.getElementById('langSelect').value;
      const startImage = document.getElementById('startImagePath').value;
      const steadyCamera = document.getElementById('steadyToggle').checked;
      const template = document.getElementById('templateSelect').value;
      const aspectRatio = document.getElementById('ratioSelect').value;
      const transition = document.getElementById('transitionSelect').value;
      const colorGrade = document.getElementById('gradeSelect').value;

      btn.disabled = true;
      spinner.style.display = 'block';
      statusText.textContent = "Directing screenplay, synthesizing audio & rendering cinematic master...";

      try {
        const res = await fetch('/api/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, jsonDoc, mode, character, language, startImage, steadyCamera, template, aspectRatio, transition, colorGrade })
        });
        const data = await res.json();
        if (data.status === 'success') {
          statusText.textContent = "✓ Master Render Complete: " + data.filename;
          const vp = document.getElementById('videoPlayer');
          vp.src = '/video/' + encodeURIComponent(data.filename);
          vp.play();
          document.getElementById('videoMeta').textContent = data.filename + ' (' + data.duration + ')';
          const dl = document.getElementById('downloadBtn');
          dl.href = '/video/' + encodeURIComponent(data.filename);
          dl.style.display = 'inline';
          loadRecentVideos();
        } else {
          statusText.textContent = "❌ Generation failed: " + (data.error || "Unknown error");
        }
      } catch (err) {
        statusText.textContent = "❌ Network error: " + err.message;
      } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
      }
    }
  </script>
</body>
</html>
"""

class VideoStudioHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Inject standard security headers into every response
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; media-src 'self' blob:; img-src 'self' data:;"
        )
        super().end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
            return

        if path == "/api/resources":
            items = []
            if RESOURCES_DIR.exists():
                for f in sorted(RESOURCES_DIR.glob("*.json")):
                    try:
                        with open(f, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                            title = data.get("title", f.name)
                    except Exception:
                        title = f.name
                    # Never leak internal absolute paths to the client
                    items.append({"name": f.name, "id": f.name, "title": title})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(items).encode("utf-8"))
            return

        if path == "/api/templates":
            from iram_video.templates import VIDEO_TEMPLATES
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(VIDEO_TEMPLATES).encode("utf-8"))
            return

        if path == "/api/recent_videos":
            recent = []
            seen = set()
            scan_dirs = [OUTPUTS_DIR, Path.cwd()]
            for sdir in scan_dirs:
                if sdir.exists():
                    for mp4 in sdir.glob("*.mp4"):
                        if mp4.name in seen:
                            continue
                        seen.add(mp4.name)
                        try:
                            st = mp4.stat()
                            recent.append({
                                "filename": mp4.name,
                                "size_mb": round(st.st_size / (1024 * 1024), 2),
                                "mtime": st.st_mtime
                            })
                        except Exception:
                            pass
            recent.sort(key=lambda x: x["mtime"], reverse=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(recent[:15]).encode("utf-8"))
            return

        if path.startswith("/video/"):
            raw_filename = path.replace("/video/", "")
            safe_name = Path(raw_filename).name
            if not safe_name or not (safe_name.endswith(".mp4") or safe_name.endswith(".webm")):
                self.send_response(400)
                self.end_headers()
                return

            # HIGH QUALITY SECURITY FIX: Use explicit relative path containment anchors
            try:
                candidate1 = (OUTPUTS_DIR / safe_name).resolve()
                candidate2 = (Path.cwd() / safe_name).resolve()
                target_file = None
                
                if candidate1.is_file() and candidate1.is_relative_to(OUTPUTS_DIR.resolve()):
                    target_file = candidate1
                elif candidate2.is_file() and candidate2.is_relative_to(Path.cwd().resolve()):
                    target_file = candidate2
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            if not target_file:
                self.send_response(404)
                self.end_headers()
                return

            file_size = target_file.stat().st_size
            range_header = self.headers.get("Range")
            if range_header and range_header.startswith("bytes="):
                try:
                    bytes_range = range_header.replace("bytes=", "").split("-")
                    start = int(bytes_range[0])
                    end = int(bytes_range[1]) if (len(bytes_range) > 1 and bytes_range[1]) else file_size - 1
                    if start < 0 or start >= file_size or end < start:
                        raise ValueError()
                    end = min(end, file_size - 1)
                    length = end - start + 1
                    self.send_response(206)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.send_header("Content-Length", str(length))
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    with open(target_file, "rb") as vf:
                        vf.seek(start)
                        self.wfile.write(vf.read(length))
                except Exception:
                    self.send_response(416)
                    self.end_headers()
                return
            else:
                self.send_response(200)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(target_file, "rb") as vf:
                    self.wfile.write(vf.read())
                return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        content_len = self.headers.get("Content-Length")
        if not content_len:
            self.send_response(411)
            self.end_headers()
            return
        try:
            length = int(content_len)
        except ValueError:
            self.send_response(400)
            self.end_headers()
            return

        max_limit = 50 * 1024 * 1024 if self.path == "/api/upload_image" else 2 * 1024 * 1024
        if length > max_limit or length < 0:
            self.send_response(413)
            self.end_headers()
            return

        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "error": "Invalid JSON payload"}).encode("utf-8"))
            return

        if self.path == "/api/upload_image":
            data_url = payload.get("data", "")
            fname = payload.get("name", "starter.png")
            safe_fname = Path(fname).name or "starter.png"
            ext = Path(safe_fname).suffix.lower()
            if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
                safe_fname = f"{Path(safe_fname).stem}.png"

            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            if "," in data_url:
                data_url = data_url.split(",", 1)[1]
            try:
                raw_bytes = base64.b64decode(data_url)
            except Exception:
                self.send_response(400)
                self.end_headers()
                return

            save_path = UPLOAD_DIR / safe_fname
            with open(save_path, "wb") as f:
                f.write(raw_bytes)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "path": safe_fname}).encode("utf-8"))
            return

        if self.path == "/api/soundscape":
            prompt = payload.get("prompt", "AI Future Documentary")
            advisor = SoundscapeAdvisor()
            plan = advisor.advise_soundscape(prompt)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "soundscape": plan}).encode("utf-8"))
            return

        if self.path == "/api/generate":
            prompt = payload.get("prompt", "AI Future")
            json_doc = payload.get("jsonDoc")
            mode = payload.get("mode", "real")
            char = payload.get("character", "auto")
            lang = payload.get("language", "en")
            start_image = payload.get("startImage")
            extend_video = payload.get("extendVideo")
            steady_camera = payload.get("steadyCamera", True)
            template = payload.get("template")
            aspect_ratio = payload.get("aspectRatio", "auto")
            transition = payload.get("transition", "fade")
            color_grade = payload.get("colorGrade", "auto")

            # Build command line
            cmd = [sys.executable, "-m", "iram_video.cli"]

            if template:
                cmd.extend(["--template", template])
            if aspect_ratio and aspect_ratio != "auto":
                cmd.extend(["--aspect-ratio", aspect_ratio])
            if transition and transition != "fade":
                cmd.extend(["--transition", transition])
            if color_grade and color_grade != "auto":
                cmd.extend(["--grade", color_grade])

            if mode == "real":
                cmd.append("--real")
            elif mode == "film":
                cmd.append("--film")
            elif mode == "cinema":
                cmd.append("--cinema")
            elif mode == "shorts":
                cmd.append("--shorts")

            if char and char != "auto":
                cmd.extend(["--character", char])
            if lang:
                cmd.extend(["--lang", lang])

            if start_image:
                si_name = Path(start_image).name
                si_path = (UPLOAD_DIR / si_name).resolve()
                if si_path.exists() and str(si_path).startswith(str(UPLOAD_DIR.resolve())):
                    cmd.extend(["--start-image", str(si_path)])

            if extend_video:
                ev_name = Path(extend_video).name
                ev_path = (OUTPUTS_DIR / ev_name).resolve()
                if ev_path.exists() and str(ev_path).startswith(str(OUTPUTS_DIR.resolve())):
                    cmd.extend(["--extend", str(ev_path)])

            if not steady_camera:
                cmd.append("--dynamic-cam")

            slug = re.sub(r"[^\w\s-]", "", prompt, flags=re.UNICODE).strip().lower()
            slug = re.sub(r"[-\s]+", "_", slug)[:35] or "web_render"
            out_name = f"{slug}_{mode}.mp4"
            out_file = OUTPUTS_DIR / out_name
            cmd.extend(["-o", str(out_file)])

            if json_doc:
                jd_name = Path(json_doc).name
                jd_path = (RESOURCES_DIR / jd_name).resolve()
                if jd_path.exists() and str(jd_path).startswith(str(RESOURCES_DIR.resolve())):
                    cmd.extend(["--from-json", str(jd_path)])
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "error": "Invalid resource document path"}).encode("utf-8"))
                    return
            else:
                cmd.extend(["--", prompt])

            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "filename": out_name,
                    "duration": "Broadcast Ready"
                }).encode("utf-8"))
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "error": e.stderr or str(e)
                }).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def start_server(port: int = 7860):
    host = os.getenv("IRAM_HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, port), VideoStudioHandler)
    print(f"\n🌐 [IRAM Video Studio] Running at http://{host}:{port}")
    print(f"🎬 Ready for browser-based video directing, mascot selection, and live playback.\n")
    server.serve_forever()
