# pdf_tools.py
from flask import Flask, request, render_template_string, send_file
from io import BytesIO
from base64 import b64decode
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rlcanvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw, ImageFont
import json
import datetime
import os, uuid, tempfile, time

app = Flask(__name__)

# === Direktori hasil sementara (buat preview stabil) ===
RESULT_DIR = os.path.join(tempfile.gettempdir(), "pdf_tools_results")
os.makedirs(RESULT_DIR, exist_ok=True)

def cleanup_old_results(max_age_hours=12):
    cutoff = time.time() - max_age_hours * 3600
    try:
        for name in os.listdir(RESULT_DIR):
            if not name.endswith(".pdf"):
                continue
            path = os.path.join(RESULT_DIR, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except Exception:
                pass
    except Exception:
        pass

def save_result_pdf(pdf_bytes: bytes, suggest_name: str = "output.pdf"):
    cleanup_old_results()
    token = uuid.uuid4().hex
    path = os.path.join(RESULT_DIR, f"{token}.pdf")
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    size_kb = round(len(pdf_bytes) / 1024, 1)
    return f"/result/{token}.pdf", suggest_name, size_kb

@app.route("/result/<token>.pdf")
def serve_result_pdf(token):
    path = os.path.join(RESULT_DIR, f"{token}.pdf")
    if os.path.exists(path):
        return send_file(path, mimetype="application/pdf", as_attachment=False, download_name="result.pdf")
    return "Not found", 404

HTML = r"""
<!doctype html>
<html lang="id" x-data="ui()" x-init="init()" :class="dark ? 'dark' : ''">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>PDF Tools Mini — Notion Theme + Sign (Drag & Drop)</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <!-- PDF.js v2.16.105 (kompatibel, tanpa private fields) -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
  <script>
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js";
  </script>
  <meta name="theme-color" content="#ffffff">
  <style>
    :root{
      --bg:#fbfbfa; --card:#fff; --border:#e7e7e5; --text:#1f2328; --dim:#5b5f66;
      --btn:#111827; --btn2:#2b2f36; --ring:#6b7280;
    }
    .dark:root{
      --bg:#191919; --card:#1f1f1f; --border:#2a2a2a; --text:#e6e6e6; --dim:#a7a7a7;
      --btn:#e6e6e6; --btn2:#d1d1d1; --ring:#94a3b8;
    }
    html,body{background:var(--bg);color:var(--text)}
    .wrap{max-width:1100px;margin-inline:auto}
    .appbar{position:sticky;top:0;z-index:40;background:color-mix(in oklab,var(--bg),transparent 8%);backdrop-filter:blur(6px);border-bottom:1px solid var(--border)}
    .brand{width:26px;height:26px;border-radius:6px;background:#111827;color:#fff;display:grid;place-items:center;font-weight:700}
    .dark .brand{background:#e6e6e6;color:#111827}
    .card{background:var(--card);border:1px solid var(--border);border-radius:12px}
    .label{font-size:13px;color:var(--dim);font-weight:600}
    .inpt{width:100%;background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);outline:none}
    .inpt:focus{border-color:var(--ring);box-shadow:0 0 0 2px color-mix(in oklab,var(--ring),transparent 70%)}
    .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:10px 14px;border-radius:10px;font-weight:600;border:1px solid var(--border);background:var(--btn);color:#fff;transition:transform .1s,box-shadow .15s,background .15s}
    .btn:hover{transform:translateY(-1px);box-shadow:0 6px 14px rgba(0,0,0,.08);background:var(--btn2)}
    .btn-sec{background:transparent;color:var(--text)}
    .muted{font-size:12px;color:var(--dim)}
    .tabs{display:flex;gap:8px;flex-wrap:wrap}
    .tab{padding:8px 12px;border:1px solid var(--border);border-radius:10px;background:transparent;cursor:pointer}
    .tab[aria-selected="true"]{background:color-mix(in oklab,var(--card),transparent 90%);border-color:var(--ring)}
    .checker{background-image:linear-gradient(45deg,#eaeaea 25%,transparent 25%),linear-gradient(-45deg,#eaeaea 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#eaeaea 75%),linear-gradient(-45deg,transparent 75%,#eaeaea 75%);background-size:14px 14px}
    .dark .checker{background-image:linear-gradient(45deg,#242424 25%,transparent 25%),linear-gradient(-45deg,#242424 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#242424 75%),linear-gradient(-45deg,transparent 75%,#242424 75%)}
    .pdfStage{position:relative;border:1px solid var(--border);border-radius:10px;overflow:hidden;background:#fff;min-height:200px}
    .dark .pdfStage{background:#0f0f0f}
    .pdfStage canvas{display:block;width:100%;height:auto}
    .sigGhost{
      position:absolute; left:10px; top:10px;
      background-size:contain; background-repeat:no-repeat; background-position:center;
      transform-origin:top left; user-select:none; touch-action:none; cursor:grab;
      filter: drop-shadow(0 3px 6px rgba(0,0,0,.2));
      border-radius:6px;
    }
    .sigGhost:active{cursor:grabbing}
    .sigText{
      font-style:italic; font-weight:600; color:var(--text);
      display:flex;align-items:center;justify-content:center;width:100%;height:100%;
      background:transparent; text-shadow:0 0 0 rgba(0,0,0,.1);
    }
    .chips{display:flex;flex-wrap:wrap;gap:6px}
    .chip{font-size:12px;border:1px solid var(--border);border-radius:999px;padding:4px 8px;background:color-mix(in oklab,var(--card),transparent 92%)}
  </style>
</head>
<body>
  <header class="appbar">
    <div class="wrap px-5 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="brand">PDF</div>
        <div>
          <div class="text-[13px]" style="color:var(--dim)">Workspace</div>
          <div class="font-semibold leading-tight">PDF Tools Mini — Notion Theme + Sign (Drag & Drop)</div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button @click="toggle()" class="btn btn-sec px-3 py-2 text-sm"><span x-show="!dark">🌙</span><span x-show="dark">☀️</span></button>
      </div>
    </div>
  </header>

  <main class="wrap px-5 py-6 grid lg:grid-cols-3 gap-6">
    <section class="lg:col-span-2 space-y-6">
      <div class="tabs">
        <button class="tab" :aria-selected="tab==='merge'"  @click="tab='merge'">🔗 Gabung</button>
        <button class="tab" :aria-selected="tab==='split'"  @click="tab='split'">✂️ Pisah</button>
        <button class="tab" :aria-selected="tab==='rotate'" @click="tab='rotate'">🌀 Rotasi</button>
        <button class="tab" :aria-selected="tab==='sign'"   @click="tab='sign'">✍️ Sign (Drag & Drop)</button>
      </div>

      <!-- MERGE -->
      <div class="card p-5" x-show="tab==='merge'">
        <form method="POST" enctype="multipart/form-data">
          <input type="hidden" name="action" value="merge">
          <label class="label block mb-1">Pilih beberapa PDF</label>
          <input class="inpt" type="file" name="files" accept="application/pdf" multiple required>
          <div class="mt-4 flex gap-2">
            <button class="btn">Gabungkan</button>
            <button class="btn btn-sec" type="reset">Reset</button>
          </div>
        </form>
      </div>

      <!-- SPLIT -->
      <div class="card p-5" x-show="tab==='split'">
        <form method="POST" enctype="multipart/form-data">
          <input type="hidden" name="action" value="split">
          <label class="label block mb-1">PDF</label>
          <input class="inpt" type="file" name="file" accept="application/pdf" required>
          <label class="label block mt-4">Halaman: contoh <code>1,3-5,8</code></label>
          <input class="inpt" type="text" name="ranges" placeholder="1-3,5,8-10" required>
          <div class="mt-4 flex gap-2">
            <button class="btn">Ekstrak</button>
            <button class="btn btn-sec" type="reset">Reset</button>
          </div>
        </form>
      </div>

      <!-- ROTATE -->
      <div class="card p-5" x-show="tab==='rotate'">
        <form method="POST" enctype="multipart/form-data">
          <input type="hidden" name="action" value="rotate">
          <label class="label block mb-1">PDF</label>
          <input class="inpt" type="file" name="file" accept="application/pdf" required>
          <label class="label block mt-4">Halaman: <code>all</code> atau <code>2,5-7</code></label>
          <input class="inpt" type="text" name="ranges" placeholder="all / 1,3-4">
          <label class="label block mt-4">Derajat</label>
          <select name="deg" class="inpt"><option value="90">90°</option><option value="180">180°</option><option value="270">270°</option></select>
          <div class="mt-4 flex gap-2">
            <button class="btn">Putar</button>
            <button class="btn btn-sec" type="reset">Reset</button>
          </div>
        </form>
      </div>

      <!-- SIGN (Drag & Drop) -->
      <div class="card p-5 space-y-4" x-show="tab==='sign'">
        <form method="POST" enctype="multipart/form-data" @submit="beforeSubmit($event)">
          <input type="hidden" name="action" value="sign-dnd">
          <input type="hidden" name="placements" x-ref="placements">
          <input type="hidden" name="drawn_data" x-ref="drawndata">

          <div class="grid md:grid-cols-2 gap-4">
            <div>
              <label class="label block mb-1">PDF untuk ditandatangani</label>
              <input class="inpt" type="file" name="file" accept="application/pdf" @change="loadPDF($event)" required>
              <div class="muted mt-1" x-show="!pdfDoc">Preview muncul setelah PDF dipilih.</div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="label block mb-1">Halaman</label>
                <div class="flex gap-2">
                  <button class="btn btn-sec px-3" type="button" @click="prevPage()" :disabled="!pdfDoc || pageNum<=1">◀</button>
                  <input class="inpt" type="number" min="1" :max="pageCount||1" x-model.number="pageNum" @change="renderPage()">
                  <button class="btn btn-sec px-3" type="button" @click="nextPage()" :disabled="!pdfDoc || pageNum>=pageCount">▶</button>
                </div>
              </div>
              <div>
                <label class="label block mb-1">Lebar tanda tangan (%)</label>
                <input class="inpt" type="number" min="10" max="60" x-model.number="widthPct">
              </div>
              <div class="col-span-2">
                <label class="inline-flex items-center gap-2 text-xs px-3 py-2 rounded-lg border" style="border-color:var(--border);">
                  <input type="checkbox" name="with_date" checked> Tambah tanggal kecil di samping
                </label>
                <input class="inpt mt-2" type="text" name="date_fmt" value="%d %b %Y" placeholder="%d %b %Y">
              </div>
            </div>
          </div>

          <div class="grid md:grid-cols-3 gap-4 mt-2">
            <div>
              <div class="label">Metode</div>
              <label class="inline-flex items-center gap-2"><input type="radio" name="sig_mode" value="draw" x-model="mode" checked> Gambar</label><br>
              <label class="inline-flex items-center gap-2"><input type="radio" name="sig_mode" value="upload" x-model="mode"> Upload</label><br>
              <label class="inline-flex items-center gap-2"><input type="radio" name="sig_mode" value="typed" x-model="mode"> Ketik</label>
            </div>

            <div x-show="mode==='draw'">
              <div class="label mb-1">Pad tanda tangan</div>
              <div style="border:1px dashed var(--border);border-radius:10px;overflow:hidden">
                <canvas x-ref="pad" width="700" height="220" class="w-full h-36"></canvas>
              </div>
              <div class="mt-2 flex gap-2">
                <button type="button" class="btn btn-sec" @click="clearPad()">Bersihkan</button>
                <label class="inline-flex items-center gap-2 text-xs px-3 py-2 rounded-lg border" style="border-color:var(--border);">
                  <input type="checkbox" x-model="thin"> Garis tipis
                </label>
              </div>
            </div>

            <div x-show="mode==='upload'">
              <div class="label mb-1">Upload gambar tanda tangan</div>
              <input class="inpt" type="file" name="sig_image" accept="image/*" @change="previewUpload($event)">
              <div class="muted mt-1">PNG transparan disarankan.</div>
            </div>

            <div x-show="mode==='typed'">
              <div class="label mb-1">Ketik nama</div>
              <input class="inpt" type="text" name="typed_text" x-model="typedText" placeholder="Nama kamu">
              <div class="muted mt-1">Preview huruf miring ala tanda tangan.</div>
            </div>
          </div>

          <!-- Stage: PDF + draggable signature -->
          <div class="mt-3">
            <div class="label mb-1">Preview halaman <span x-text="pageNum"></span> / <span x-text="pageCount||'—'"></span></div>
            <div class="pdfStage" x-ref="stage">
              <canvas x-ref="pdfcanvas"></canvas>
              <div x-ref="ghost" class="sigGhost" :style="ghostStyle" @mousedown="startDrag" @touchstart="startDrag">
                <div class="sigText" x-show="mode==='typed'"><span x-text="typedText||'Tanda Tangan'"></span></div>
              </div>
            </div>
            <div class="mt-2 flex items-center gap-2">
              <button class="btn btn-sec" type="button" @click="applyPlacement()">+ Apply ke halaman ini</button>
              <button class="btn btn-sec" type="button" @click="removePlacement()">Hapus placement halaman ini</button>
              <div class="muted">Geser kotak tanda tangan lalu klik Apply.</div>
            </div>
            <div class="chips mt-2">
              <template x-for="p in placements" :key="p.page">
                <div class="chip">Hal. <span x-text="p.page"></span> — x:<span x-text="p.x_pct.toFixed(1)"></span>% y:<span x-text="p.y_pct.toFixed(1)"></span>% w:<span x-text="p.width_pct"></span>%</div>
              </template>
            </div>
          </div>

          <div class="mt-5 flex gap-2">
            <button class="btn" type="submit" :disabled="!pdfDoc || placements.length===0">Tandatangani</button>
            <button class="btn btn-sec" type="reset" @click="resetSign()">Reset</button>
          </div>
        </form>
      </div>

      {% if result_url %}
      <div class="card p-5">
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div><div class="font-semibold">Berhasil diproses</div><div class="muted">Ukuran: {{ size_kb }} KB</div></div>
          <a class="btn" download="{{ filename }}" href="{{ result_url }}">⬇️ Download</a>
        </div>
        <div class="mt-4 p-3 checker rounded-lg">
          <iframe src="{{ result_url }}" class="w-full" style="height:60vh;border:1px solid var(--border);border-radius:8px;"></iframe>
        </div>
      </div>
      {% endif %}
    </section>

    <aside class="space-y-6">
      <div class="card p-5">
        <div class="font-semibold mb-2">Tips Drag & Drop</div>
        <ul class="list-disc pl-5 space-y-2 text-sm" style="color:var(--dim)">
          <li>Lebar tanda tangan diatur dari angka “%”.</li>
          <li>Geser kotak ke posisi yang diinginkan, lalu klik “Apply ke halaman ini”.</li>
          <li>Ulangi ke halaman lain, baru klik “Tandatangani”.</li>
        </ul>
      </div>
    </aside>
  </main>

  <footer class="wrap px-5 py-8 muted">
    © 2025 andartelolat — MIT. (Visual signature, bukan sertifikat digital PKI)
  </footer>

  <script>
    function ui(){
      return {
        dark:(() => { const s=localStorage.getItem('theme'); if(s==='dark') return true; if(s==='light') return false; return window.matchMedia('(prefers-color-scheme: dark)').matches; })(),
        tab:'{{ active_tab or "sign" }}',

        pdfDoc:null, pageNum:1, pageCount:null, scale:1, fileArrayBuffer:null,
        mode:'draw', typedText:'', thin:false,
        widthPct:35, placements:[],
        dragging:false, dragOffsetX:0, dragOffsetY:0,
        sigAR:4.0, // aspect ratio agar ghost selalu punya tinggi

        toggle(){
          this.dark=!this.dark;
          localStorage.setItem('theme', this.dark?'dark':'light');
          const m=document.querySelector('meta[name="theme-color"]');
          if(m) m.setAttribute('content', this.dark ? '#191919' : '#ffffff');
        },

        // ===== PDF handling =====
        async loadPDF(ev){
          const file = ev.target.files?.[0];
          if(!file) return;
          this.fileArrayBuffer = await file.arrayBuffer();
          try{
            this.pdfDoc = await pdfjsLib.getDocument({data: this.fileArrayBuffer}).promise;
            this.pageCount = this.pdfDoc.numPages;
            this.pageNum = 1;
            await this.renderPage();
          }catch(err){
            alert('Gagal memuat PDF: ' + err);
          }
        },
        async renderPage(){
          if(!this.pdfDoc) return;
          const page = await this.pdfDoc.getPage(this.pageNum);
          const stage = this.$refs.stage;
          const targetWidth = Math.max(320, stage.clientWidth || 800);
          const vp1 = page.getViewport({ scale: 1 });
          const scale = targetWidth / vp1.width;
          this.scale = scale;
          const viewport = page.getViewport({ scale });

          const canvas = this.$refs.pdfcanvas;
          const ctx = canvas.getContext('2d', {alpha:false});
          canvas.width  = Math.floor(viewport.width);
          canvas.height = Math.floor(viewport.height);
          await page.render({ canvasContext: ctx, viewport }).promise;

          this.layoutGhost();
        },

        prevPage(){ if(this.pdfDoc && this.pageNum>1){ this.pageNum--; this.renderPage(); } },
        nextPage(){ if(this.pdfDoc && this.pageNum<this.pageCount){ this.pageNum++; this.renderPage(); } },

        // ===== Signature ghost =====
        get ghostStyle(){
          const st = {};
          const canvas = this.$refs.pdfcanvas;
          const cw = canvas?.width || 800;
          const ch = canvas?.height || 600;
          const gw = Math.max(10, Math.floor(cw * (this.widthPct/100)));
          const gh = Math.max(24, Math.round(gw / (this.sigAR||4.0)));
          st.width  = gw + 'px';
          st.height = gh + 'px';

          if(this.mode==='draw' && this.$refs.pad){
            try{ st.backgroundImage = `url(${this.$refs.pad.toDataURL('image/png')})`; }catch(e){}
          } else if (this.mode==='upload' && this._uploadPreviewURL){
            st.backgroundImage = `url(${this._uploadPreviewURL})`;
          } else {
            st.backgroundImage = 'none';
          }

          const p = this.placements.find(x=>x.page===this.pageNum);
          if(p){
            const xpx = Math.round((p.x_pct/100)*cw);
            const ypx_from_bottom = Math.round((p.y_pct/100)*ch);
            const top_from_top = ch - ypx_from_bottom - gh;
            st.left = xpx+'px';
            st.top  = Math.max(0, top_from_top) + 'px';
          }
          return st;
        },
        layoutGhost(){
          const g=this.$refs.ghost, c=this.$refs.pdfcanvas;
          if(!g||!c) return;
          const p = this.placements.find(x=>x.page===this.pageNum);
          if(!p){
            const margin = Math.floor(c.width*0.03);
            const gw = Math.max(10, Math.floor(c.width*(this.widthPct/100)));
            const gh = Math.max(24, Math.round(gw/(this.sigAR||4.0)));
            g.style.left = (c.width - gw - margin) + 'px';
            g.style.top  = (c.height - gh - margin) + 'px';
          }
        },
        startDrag(e){
          const g=this.$refs.ghost; if(!g) return;
          this.dragging=true; g.style.cursor='grabbing';
          const rect = g.getBoundingClientRect();
          const clientX = e.touches?e.touches[0].clientX:e.clientX;
          const clientY = e.touches?e.touches[0].clientY:e.clientY;
          this.dragOffsetX = clientX - rect.left;
          this.dragOffsetY = clientY - rect.top;
          window.addEventListener('mousemove', this.onDrag, {passive:false});
          window.addEventListener('mouseup', this.endDrag);
          window.addEventListener('touchmove', this.onDrag, {passive:false});
          window.addEventListener('touchend', this.endDrag);
        },
        onDrag(e){
          if(!this.dragging) return;
          e.preventDefault?.();
          const stageRect = this.$refs.stage.getBoundingClientRect();
          const g=this.$refs.ghost, c=this.$refs.pdfcanvas;
          const clientX = e.touches?e.touches[0].clientX:e.clientX;
          const clientY = e.touches?e.touches[0].clientY:e.clientY;
          let x = clientX - stageRect.left - this.dragOffsetX;
          let y = clientY - stageRect.top  - this.dragOffsetY;
          const maxX = (c.width  - g.offsetWidth);
          const maxY = (c.height - g.offsetHeight);
          x = Math.max(0, Math.min(x, maxX));
          y = Math.max(0, Math.min(y, maxY));
          g.style.left = x + 'px';
          g.style.top  = y + 'px';
        },
        endDrag(){
          this.dragging=false;
          const g=this.$refs.ghost; if(g) g.style.cursor='grab';
          window.removeEventListener('mousemove', this.onDrag);
          window.removeEventListener('mouseup', this.endDrag);
          window.removeEventListener('touchmove', this.onDrag);
          window.removeEventListener('touchend', this.endDrag);
        },

        // ===== Upload preview + aspect ratio =====
        _uploadPreviewURL:null,
        previewUpload(ev){
          const f = ev.target.files?.[0];
          if(!f) return;
          const r = new FileReader();
          r.onload = ()=>{
            this._uploadPreviewURL = r.result;
            const im = new Image();
            im.onload = ()=>{ this.sigAR = (im.naturalWidth||1)/(im.naturalHeight||1); };
            im.src = this._uploadPreviewURL;
          };
          r.readAsDataURL(f);
        },

        // ===== Signature pad =====
        init(){
          const m=document.querySelector('meta[name="theme-color"]');
          if(m) m.setAttribute('content', this.dark ? '#191919' : '#ffffff');

          const c=this.$refs.pad; if(!c) return;
          const ctx=c.getContext('2d');
          const setStyle=()=>{
            ctx.lineCap='round'; ctx.lineJoin='round';
            ctx.lineWidth=this.thin?2:3;
            ctx.strokeStyle=getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#111827';
          };
          const scale=window.devicePixelRatio||1;
          const resize=()=>{
            const rect=c.getBoundingClientRect();
            c.width=Math.floor(rect.width*scale);
            c.height=Math.floor(rect.height*scale);
            ctx.setTransform(scale,0,0,scale,0,0);
            setStyle();
            // FIX: gunakan '||' (bukan 'or') agar tidak error JS
            this.sigAR = (c.width||700)/(c.height||220);
          };
          new ResizeObserver(resize).observe(c); resize();

          let drawing=false, lastX=0,lastY=0;
          const pos=e=>{
            const r=c.getBoundingClientRect();
            const x=(e.touches?e.touches[0].clientX:e.clientX)-r.left;
            const y=(e.touches?e.touches[0].clientY:e.clientY)-r.top;
            return {x,y};
          };
          const start=e=>{drawing=true; const p=pos(e); lastX=p.x; lastY=p.y;};
          const move =e=>{
            if(!drawing) return;
            const p=pos(e); setStyle();
            ctx.beginPath(); ctx.moveTo(lastX,lastY); ctx.lineTo(p.x,p.y); ctx.stroke();
            lastX=p.x; lastY=p.y;
          };
          const end  =()=>{drawing=false};
          c.addEventListener('mousedown',start);
          c.addEventListener('mousemove',move);
          window.addEventListener('mouseup',end);
          c.addEventListener('touchstart',start,{passive:true});
          c.addEventListener('touchmove',move,{passive:true});
          c.addEventListener('touchend',end);
        },
        clearPad(){ const c=this.$refs.pad; if(!c) return; c.getContext('2d').clearRect(0,0,c.width,c.height); },

        // ===== Placements =====
        applyPlacement(){
          const canvas = this.$refs.pdfcanvas, ghost=this.$refs.ghost;
          if(!canvas || !ghost) return;
          const cw = canvas.width, ch = canvas.height;
          const left = parseFloat(ghost.style.left||'0');
          const top  = parseFloat(ghost.style.top||'0');
          const gh   = ghost.offsetHeight || Math.round((canvas.width*(this.widthPct/100))/(this.sigAR||4));
          const x_pct = (left / cw) * 100.0;
          const y_from_bottom = (ch - (top + gh));
          const y_pct = (y_from_bottom / ch) * 100.0;
          const w_pct = this.widthPct;

          const idx = this.placements.findIndex(p=>p.page===this.pageNum);
          const rec = {page:this.pageNum, x_pct:x_pct, y_pct:y_pct, width_pct:w_pct};
          if(idx>=0) this.placements.splice(idx,1,rec); else this.placements.push(rec);
        },
        removePlacement(){
          const idx = this.placements.findIndex(p=>p.page===this.pageNum);
          if(idx>=0) this.placements.splice(idx,1);
          this.layoutGhost();
        },
        resetSign(){
          this.placements=[]; this.typedText=''; this.widthPct=35; this.clearPad(); this.layoutGhost();
        },

        // ===== Submit =====
        beforeSubmit(e){
          if(!this.pdfDoc){ e.preventDefault(); alert('Pilih PDF terlebih dulu.'); return; }
          if(this.placements.length===0){ e.preventDefault(); alert('Belum ada placement. Klik "Apply ke halaman ini".'); return; }
          this.$refs.placements.value = JSON.stringify(this.placements);
          if(this.mode==='draw' && this.$refs.pad){
            this.$refs.drawndata.value = this.$refs.pad.toDataURL('image/png');
          }
        }
      }
    }
    (function(){
      const s=localStorage.getItem('theme');
      const d = s ? s==='dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
      const m=document.querySelector('meta[name="theme-color"]');
      if(m) m.setAttribute('content', d ? '#191919' : '#ffffff');
    })();
  </script>
</body>
</html>
"""

# ---------- Helpers ----------
def parse_ranges(spec: str, total_pages: int):
    if not spec:
        return []
    s = spec.strip().lower()
    if s in ("all", "last"):
        return list(range(total_pages)) if s == "all" else [total_pages - 1]
    pages = set()
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if part == "last":
            pages.add(total_pages - 1)
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                start = max(1, int(a))
                end = min(total_pages, int(b))
                if start <= end:
                    for p in range(start, end + 1):
                        pages.add(p - 1)
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= total_pages:
                    pages.add(p - 1)
            except ValueError:
                continue
    return sorted(pages)

def decode_data_url_png(data_url: str) -> BytesIO | None:
    if not data_url or not data_url.startswith("data:image"):
        return None
    try:
        _, b64data = data_url.split(",", 1)
        raw = b64decode(b64data)
        return BytesIO(raw)
    except Exception:
        return None

def render_typed_signature(text: str, color=(17, 24, 39, 255)) -> BytesIO | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        font = ImageFont.truetype("ariali.ttf", 140)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Oblique.ttf", 140)
        except Exception:
            font = ImageFont.load_default()
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((20, 20), text, fill=color, font=font)
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio

def add_signature_to_pdf_points(
    pdf_in: BytesIO,
    placements: list,  # [{page:1-based, x_pct,y_pct,width_pct}]
    sig_mode: str,
    sig_image_file,
    drawn_data_url: str,
    typed_text: str,
    with_date: bool,
    date_fmt: str,
) -> bytes:
    reader = PdfReader(pdf_in)
    total = len(reader.pages)

    # siapkan gambar tanda tangan
    sig_img_bio = None
    if sig_mode == "draw":
        sig_img_bio = decode_data_url_png(drawn_data_url)
    elif sig_mode == "upload" and sig_image_file and getattr(sig_image_file, "filename", ""):
        sig_img_bio = BytesIO(sig_image_file.read())
    elif sig_mode == "typed":
        sig_img_bio = render_typed_signature(typed_text or "")
    if not sig_img_bio:
        raise ValueError("Tanda tangan tidak tersedia.")
    sig_img = Image.open(sig_img_bio).convert("RGBA")
    sig_w, sig_h = sig_img.size

    # normalisasi placements
    norm = []
    for p in placements or []:
        try:
            page = int(p.get("page", 1)) - 1
            if 0 <= page < total:
                norm.append({
                    "page": page,
                    "x_pct": float(p.get("x_pct", 0.0)),
                    "y_pct": float(p.get("y_pct", 0.0)),
                    "width_pct": float(p.get("width_pct", 35.0)),
                })
        except Exception:
            continue

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        page_w = float(page.mediabox.width)
        page_h = float(page.mediabox.height)
        pp = [x for x in norm if x["page"] == i]
        if pp:
            overlay_bio = BytesIO()
            can = rlcanvas.Canvas(overlay_bio, pagesize=(page_w, page_h))
            for item in pp:
                w_pct = max(5.0, min(100.0, item["width_pct"]))
                target_w = page_w * (w_pct / 100.0)
                scale = target_w / sig_w
                target_h = sig_h * scale
                x = (item["x_pct"] / 100.0) * page_w
                y = (item["y_pct"] / 100.0) * page_h  # y dari bawah (koordinat PDF)
                can.drawImage(ImageReader(sig_img), x, y, width=target_w, height=target_h, mask='auto')

                if with_date:
                    try:
                        label = datetime.datetime.now().strftime(date_fmt or "%d %b %Y")
                    except Exception:
                        label = datetime.datetime.now().strftime("%d %b %Y")
                    can.setFont("Helvetica", max(8, int(target_h * 0.18)))
                    can.setFillGray(0.15)
                    can.drawString(x, max(6, y - (target_h * 0.22)), label)
            can.save()
            overlay_bio.seek(0)
            overlay_reader = PdfReader(overlay_bio)
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    writer.close()
    return out.getvalue()

# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def index():
    result_url = None
    filename = None
    size_kb = None
    active_tab = "sign"

    if request.method == "POST":
        action = request.form.get("action")

        if action == "merge":
            active_tab = "merge"
            files = request.files.getlist("files")
            merger = PdfWriter()
            for f in files:
                if not f or not f.filename:
                    continue
                reader = PdfReader(BytesIO(f.read()))
                for page in reader.pages:
                    merger.add_page(page)
            out = BytesIO()
            merger.write(out)
            merger.close()
            result_url, filename, size_kb = save_result_pdf(out.getvalue(), "merged.pdf")

        elif action == "split":
            active_tab = "split"
            f = request.files.get("file")
            ranges = request.form.get("ranges", "")
            if f and f.filename:
                reader = PdfReader(BytesIO(f.read()))
                pages = parse_ranges(ranges, len(reader.pages))
                writer = PdfWriter()
                for i in pages:
                    writer.add_page(reader.pages[i])
                out = BytesIO()
                writer.write(out)
                writer.close()
                result_url, filename, size_kb = save_result_pdf(out.getvalue(), "extracted.pdf")

        elif action == "rotate":
            active_tab = "rotate"
            f = request.files.get("file")
            ranges = request.form.get("ranges", "all")
            deg = int(request.form.get("deg", "90"))
            if f and f.filename:
                reader = PdfReader(BytesIO(f.read()))
                total = len(reader.pages)
                target_idx = parse_ranges(ranges, total)
                writer = PdfWriter()
                for idx, page in enumerate(reader.pages):
                    if idx in target_idx or ranges.lower() == "all":
                        page.rotate(deg)
                    writer.add_page(page)
                out = BytesIO()
                writer.write(out)
                writer.close()
                result_url, filename, size_kb = save_result_pdf(out.getvalue(), "rotated.pdf")

        elif action == "sign-dnd":
            active_tab = "sign"
            pdf_file = request.files.get("file")
            if pdf_file and pdf_file.filename:
                try:
                    placements = json.loads(request.form.get("placements", "[]"))
                except Exception:
                    placements = []
                sig_mode = request.form.get("sig_mode", "draw")
                sig_image_file = request.files.get("sig_image")
                drawn_data = request.form.get("drawn_data", "")
                typed_text = request.form.get("typed_text", "")
                with_date = request.form.get("with_date") == "on"
                date_fmt = request.form.get("date_fmt", "%d %b %Y")

                pdf_bytes = pdf_file.read()
                final_bytes = add_signature_to_pdf_points(
                    pdf_in=BytesIO(pdf_bytes),
                    placements=placements,
                    sig_mode=sig_mode,
                    sig_image_file=sig_image_file,
                    drawn_data_url=drawn_data,
                    typed_text=typed_text,
                    with_date=with_date,
                    date_fmt=date_fmt,
                )
                result_url, filename, size_kb = save_result_pdf(final_bytes, "signed.pdf")

    return render_template_string(
        HTML,
        result_url=result_url,
        filename=filename,
        size_kb=size_kb,
        active_tab=active_tab
    )

if __name__ == "__main__":
    # pip install flask pypdf reportlab pillow
    # python pdf_tools.py  ->  http://localhost:5002/
    app.run(debug=True, host="0.0.0.0", port=5002)
