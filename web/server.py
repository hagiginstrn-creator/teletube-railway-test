""" وب‌سرور FastAPI: مسیر دانلود مستقیم فایل‌ها + پنل مدیریت ساده. """
import os
import time
from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

from config import LINK_TTL_HOURS, PUBLIC_BASE_URL
from utils.helpers import format_size
from web import store
from web.settings import get_settings, update_settings
from web.auth import require_admin

app = FastAPI(title="TeleTube", docs_url=None, redoc_url=None)

@app.get("/")
async def root():
    return {"service": "TeleTube", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/files/{token}")
async def download_file(token: str):
    entry = store.get_link(token)
    if not entry or entry.get("is_deleted"):
        raise HTTPException(status_code=404, detail="لینک پیدا نشد یا فایل از سرور حذف شده است")
    
    if not os.path.exists(entry["file_path"]):
        raise HTTPException(status_code=404, detail="فایل دیگه روی سرور موجود نیست")
        
    store.record_download(token)
    filename = f"{entry['title']}.mp4"
    return FileResponse(
        entry["file_path"],
        media_type="video/mp4",
        filename=filename,
    )

@app.get("/thumbs/{token}")
async def get_thumbnail(token: str):
    entry = store.get_link(token)
    if entry and entry.get("thumb_path") and os.path.exists(entry["thumb_path"]):
        return FileResponse(entry["thumb_path"])
    return Response(content=b"", media_type="image/jpeg")

# ---------------------------------------------------------------------------
# پنل مدیریت (Glassmorphism UI)
# ---------------------------------------------------------------------------
def _fmt_time(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

def _render_admin_page(settings: dict, links: list, base_url: str) -> str:
    checked_direct = "checked" if settings.get("enable_direct_links", True) else ""
    checked_channel = "checked" if settings.get("enable_channel_delivery", True) else ""
    checked_urldl = "checked" if settings.get("enable_urldl", False) else ""
    install_time = settings.get("install_time", time.time())
    
    cards_html = ""
    for entry in links:
        token = entry['token']
        dl_link = f"{base_url}/files/{token}" if base_url else f"/files/{token}"
        urldl_link = entry.get('urldl_link') or ''
        tg_link = entry.get('tg_link') or ''
        is_deleted = entry.get('is_deleted', False)
        is_del_js = 'true' if is_deleted else 'false'
        
        safe_title = entry['title'].replace("'", "\\'").replace('"', '&quot;')
        
        # برچسب و تصویر
        if is_deleted:
            badge_html = '<span class="position-absolute top-0 start-0 m-2 badge bg-danger opacity-75" style="z-index:2;" data-fa="حذف شده" data-en="Deleted">حذف شده</span>'
            thumb_html = '<div class="w-100 h-100 d-flex justify-content-center align-items-center" style="background: rgba(0,0,0,0.6); position:absolute; top:0; left:0;"><i class="bi bi-trash3 text-secondary" style="font-size: 3rem;"></i></div>'
        else:
            badge_html = '<span class="position-absolute top-0 start-0 m-2 badge bg-success opacity-75" style="z-index:2;" data-fa="موجود" data-en="Active">موجود</span>'
            thumb_html = f'<img src="/thumbs/{token}" alt="">'
        
        cards_html += f'''
        <div class="col">
            <div class="glass video-card h-100" onclick="showModal('{token}', '{safe_title}', '{dl_link}', '{urldl_link}', '{tg_link}', {entry['created_at']}, {entry['expires_at']}, {is_del_js})">
                <div class="thumb-container">
                    {badge_html}
                    {thumb_html}
                    <div class="play-overlay"><i class="bi bi-play-circle-fill"></i></div>
                </div>
                <div class="card-body p-3">
                    <h6 class="video-title" title="{entry['title']}">{entry['title']}</h6>
                    <div class="video-meta mt-3">
                        <div class="d-flex justify-content-between mb-1">
                            <span><i class="bi bi-hdd-fill me-1"></i> {format_size(entry['size_bytes']) or '-'}</span>
                            <span><i class="bi bi-cloud-arrow-down-fill me-1"></i> {entry['downloads']}</span>
                        </div>
                        <div><i class="bi bi-calendar3 me-1"></i> <span data-fa="ساخت:" data-en="Created:">ساخت:</span> {_fmt_time(entry['created_at'])}</div>
                    </div>
                </div>
            </div>
        </div>
        '''
        
    if not cards_html:
        cards_html = '''
        <div class="col-12 text-center my-5">
            <div class="glass p-5 d-inline-block" style="border-radius: 24px;">
                <i class="bi bi-camera-reels text-muted" style="font-size: 4rem;"></i>
                <h5 class="mt-3 text-muted" data-fa="هیچ ویدیویی در آرشیو وجود ندارد" data-en="No videos in archive">هیچ ویدیویی در آرشیو وجود ندارد</h5>
            </div>
        </div>'''

    return f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TeleTube Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet" id="bs-css">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <style>
            :root {{
                --glass-bg: rgba(30, 41, 59, 0.4);
                --glass-border: rgba(255, 255, 255, 0.08);
                --glass-blur: blur(16px);
                --accent-color: #38bdf8;
            }}
            
            body {{
                background-color: #0f172a;
                color: #f8fafc;
                font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
                min-height: 100vh;
                overflow-x: hidden;
                position: relative;
                transition: direction 0.3s;
            }}

            body[dir="ltr"] {{ text-align: left; }}
            body[dir="rtl"] {{ text-align: right; }}

            .bg-orb {{ position: fixed; border-radius: 50%; filter: blur(100px); z-index: -1; animation: float 12s infinite ease-in-out alternate; }}
            .orb-1 {{ width: 400px; height: 400px; background: rgba(99, 102, 241, 0.3); top: -10%; left: -10%; }}
            .orb-2 {{ width: 500px; height: 500px; background: rgba(236, 72, 153, 0.2); bottom: -20%; right: -10%; animation-delay: -5s; }}
            .orb-3 {{ width: 350px; height: 350px; background: rgba(56, 189, 248, 0.2); top: 30%; left: 40%; animation-duration: 18s; }}

            @keyframes float {{ 0% {{ transform: translateY(0) scale(1); }} 100% {{ transform: translateY(-40px) scale(1.1); }} }}

            .glass {{
                background: var(--glass-bg);
                backdrop-filter: var(--glass-blur);
                -webkit-backdrop-filter: var(--glass-blur);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}

            .navbar-glass {{ background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(20px); border-bottom: 1px solid var(--glass-border); }}

            .video-card {{ cursor: pointer; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s; display: flex; flex-direction: column; position: relative; overflow: hidden; }}
            .video-card:hover {{ transform: translateY(-8px); background: rgba(30, 41, 59, 0.6); border-color: rgba(56, 189, 248, 0.3); }}
            
            .thumb-container {{ position: relative; width: 100%; padding-top: 56.25%; background: #000; overflow: hidden; border-bottom: 1px solid var(--glass-border); }}
            .thumb-container img {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.85; transition: opacity 0.3s, transform 0.5s; }}
            .video-card:hover .thumb-container img {{ opacity: 1; transform: scale(1.05); }}
            
            .play-overlay {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 3rem; color: rgba(255, 255, 255, 0.7); opacity: 0; transition: opacity 0.3s, transform 0.3s; z-index:3; }}
            .video-card:hover .play-overlay {{ opacity: 1; transform: translate(-50%, -50%) scale(1.1); }}

            .video-title {{ font-size: 0.95rem; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; font-weight: 600; color: #f1f5f9; }}
            .video-meta {{ font-size: 0.8rem; color: #94a3b8; }}
            .video-meta i {{ color: var(--accent-color); }}

            .form-check-label {{ color: #cbd5e1; }}
            .form-control, .input-group-text {{ background: rgba(0, 0, 0, 0.2) !important; border: 1px solid var(--glass-border) !important; color: #f8fafc !important; }}
            .form-control:focus {{ box-shadow: 0 0 0 0.25rem rgba(56, 189, 248, 0.2) !important; border-color: var(--accent-color) !important; }}

            .modal-content {{ background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(24px); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 24px; color: #e2e8f0; }}
            .modal-header {{ border-bottom: 1px solid var(--glass-border); }}
            .btn-close {{ filter: invert(1); opacity: 0.7; }}
            .btn-close:hover {{ opacity: 1; }}

            .btn-glass-primary {{ background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.4); color: var(--accent-color); transition: all 0.3s; border-radius: 12px; }}
            .btn-glass-primary:hover {{ background: rgba(56, 189, 248, 0.3); color: #fff; box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }}
            
            .btn-glass-danger {{ background: rgba(244, 63, 94, 0.15); border: 1px solid rgba(244, 63, 94, 0.4); color: #fb7185; transition: all 0.3s; border-radius: 12px; }}
            .btn-glass-danger:hover {{ background: rgba(244, 63, 94, 0.3); color: #fff; box-shadow: 0 0 15px rgba(244, 63, 94, 0.3); }}

            .copy-btn {{ background: rgba(255, 255, 255, 0.05) !important; color: #cbd5e1 !important; border-color: var(--glass-border) !important; transition: background 0.2s; }}
            .copy-btn:hover {{ background: rgba(255, 255, 255, 0.15) !important; color: #fff !important; }}

            .form-switch .form-check-input {{ background-color: rgba(255, 255, 255, 0.2); border-color: rgba(255, 255, 255, 0.1); cursor: pointer; }}
            .form-switch .form-check-input:checked {{ background-color: var(--accent-color); border-color: var(--accent-color); }}

            ::-webkit-scrollbar {{ width: 8px; }}
            ::-webkit-scrollbar-track {{ background: #0f172a; }}
            ::-webkit-scrollbar-thumb {{ background: rgba(255, 255, 255, 0.2); border-radius: 10px; }}
            ::-webkit-scrollbar-thumb:hover {{ background: rgba(255, 255, 255, 0.4); }}
        </style>
    </head>
    <body>

    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-orb orb-3"></div>

    <nav class="navbar navbar-glass sticky-top py-3 mb-4">
        <div class="container d-flex justify-content-between">
            <a class="navbar-brand fw-bold text-white d-flex align-items-center" href="#">
                <i class="bi bi-youtube text-danger fs-3 me-2"></i> 
                <span style="letter-spacing: 1px;">TELETUBE <span class="fw-light text-muted">DASHBOARD</span></span>
            </a>
            <div>
                <button id="langBtn" class="btn btn-outline-info btn-sm rounded-pill px-3" onclick="toggleLanguage()">EN</button>
            </div>
        </div>
    </nav>

    <div class="container mb-5 pb-5">
    
        <!-- تایمر Railway (30 روزه) -->
        <div class="glass p-3 mb-4 d-flex flex-column flex-md-row justify-content-between align-items-center shadow-sm" style="border-radius: 16px;">
            <div class="d-flex align-items-center mb-2 mb-md-0">
                <i class="bi bi-rocket-takeoff fs-2 text-warning me-3"></i>
                <div>
                    <h6 class="mb-1 fw-bold text-white" data-fa="زمان پایان پلن سرور (۳۰ روزه)" data-en="Server Plan Expiration (30 Days)">زمان پایان پلن سرور (۳۰ روزه)</h6>
                    <small class="text-info" id="railwayTimer" data-fa="در حال محاسبه..." data-en="Calculating...">در حال محاسبه...</small>
                </div>
            </div>
            <div class="spinner-grow text-warning opacity-75" role="status" style="width: 1.5rem; height: 1.5rem;">
              <span class="visually-hidden">Loading...</span>
            </div>
        </div>

        <div class="row">
            <!-- Settings Panel -->
            <div class="col-lg-6 mb-4">
                <div class="glass p-4 h-100">
                    <h5 class="mb-4 text-white" data-fa="پیکربندی سیستم" data-en="System Configuration"><i class="bi bi-sliders text-info me-2"></i> پیکربندی سیستم</h5>
                    <form action="/admin/settings" method="post">
                        <div class="d-flex flex-column gap-3">
                            <div class="form-check form-switch fs-5">
                                <input class="form-check-input" type="checkbox" name="enable_direct_links" id="c1" value="true" {checked_direct}>
                                <label class="form-check-label fs-6 mt-1 mx-2" for="c1" data-fa="لینک مستقیم سرور" data-en="Direct Server Link">لینک مستقیم سرور</label>
                            </div>
                            <div class="form-check form-switch fs-5">
                                <input class="form-check-input" type="checkbox" name="enable_channel_delivery" id="c2" value="true" {checked_channel}>
                                <label class="form-check-label fs-6 mt-1 mx-2" for="c2" data-fa="آپلود در کانال تلگرام" data-en="Upload to Telegram Channel">آپلود در کانال تلگرام</label>
                            </div>
                            <div class="form-check form-switch fs-5">
                                <input class="form-check-input" type="checkbox" name="enable_urldl" id="c3" value="true" {checked_urldl}>
                                <label class="form-check-label fs-6 mt-1 mx-2" for="c3" data-fa="مسیر داخلی urldl.ir" data-en="Internal urldl.ir Route">مسیر داخلی urldl.ir</label>
                            </div>
                        </div>
                        <div class="mt-4 pt-3 border-top border-secondary border-opacity-25">
                            <button type="submit" class="btn btn-glass-primary px-4 py-2 w-100">
                                <i class="bi bi-hdd-network me-2"></i> <span data-fa="اعمال تنظیمات" data-en="Apply Settings">اعمال تنظیمات</span>
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Bot Control Panel -->
            <div class="col-lg-6 mb-4">
                <div class="glass p-4 h-100">
                    <h5 class="mb-4 text-white" data-fa="کنترل ربات تلگرام" data-en="Telegram Bot Control"><i class="bi bi-robot text-primary me-2"></i> کنترل ربات تلگرام</h5>
                    
                    <!-- محتوای خالی برای آینده -->
                    <div class="d-flex flex-column justify-content-center align-items-center h-75 opacity-50">
                        <i class="bi bi-tools fs-1 mb-2"></i>
                        <span data-fa="امکانات این بخش به زودی اضافه خواهد شد..." data-en="Features will be added soon...">امکانات این بخش به زودی اضافه خواهد شد...</span>
                    </div>

                </div>
            </div>
        </div>

        <div class="d-flex justify-content-between align-items-center mt-3 mb-4 border-bottom border-secondary border-opacity-25 pb-2">
            <h4 class="m-0 text-white" data-fa="آرشیو ویدیوها" data-en="Video Archive"><i class="bi bi-archive me-2 text-info"></i> آرشیو ویدیوها</h4>
        </div>
        
        <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4 g-4">
            {cards_html}
        </div>
    </div>

    <!-- Modal (پاپ‌آپ لینک‌ها) -->
    <div class="modal fade" id="linkModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content shadow-lg">
                <div class="modal-header border-0 pb-0 mt-2 px-4">
                    <h5 class="modal-title fw-bold text-truncate w-100 pe-3" id="modalTitle" dir="auto">عنوان ویدیو</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body px-4 pb-4 mt-3">
                    
                    <div class="mb-4">
                        <div class="d-flex justify-content-between align-items-end mb-2">
                            <label class="form-label text-info small fw-bold mb-0" data-fa="لینک مستقیم سرور" data-en="Direct Server Link"><i class="bi bi-globe2"></i> لینک مستقیم سرور</label>
                            <span id="modalDirectTime" class="badge"></span>
                        </div>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalDirect" readonly dir="ltr">
                            <button class="btn copy-btn px-3" type="button" onclick="copyToClipboard('modalDirect')"><i class="bi bi-clipboard"></i></button>
                        </div>
                    </div>

                    <div class="mb-4" id="urldlBox">
                        <div class="d-flex justify-content-between align-items-end mb-2">
                            <label class="form-label text-info small fw-bold mb-0" data-fa="ترافیک داخلی (urldl)" data-en="Internal Traffic (urldl)"><i class="bi bi-lightning-charge-fill text-warning"></i> ترافیک داخلی (urldl)</label>
                            <span id="modalUrldlTime" class="badge"></span>
                        </div>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalUrldl" readonly dir="ltr">
                            <button class="btn copy-btn px-3" type="button" onclick="copyToClipboard('modalUrldl')"><i class="bi bi-clipboard"></i></button>
                        </div>
                    </div>

                    <div class="mb-5" id="tgBox">
                        <div class="d-flex justify-content-between align-items-end mb-2">
                            <label class="form-label text-info small fw-bold mb-0" data-fa="پست ذخیره تلگرام" data-en="Telegram Post"><i class="bi bi-telegram text-primary"></i> پست ذخیره تلگرام</label>
                            <span id="modalTgTime" class="badge"></span>
                        </div>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalTg" readonly dir="ltr">
                            <button class="btn copy-btn px-3" type="button" onclick="copyToClipboard('modalTg')"><i class="bi bi-clipboard"></i></button>
                        </div>
                    </div>

                    <form id="deleteForm" method="post" action="">
                        <button type="submit" class="btn btn-glass-danger w-100 py-2 fs-6">
                            <i class="bi bi-trash3-fill me-2"></i> <span data-fa="حذف فایل از سرور (باقی‌ماندن در آرشیو)" data-en="Delete File (Keep in Archive)">حذف فایل از سرور (باقی‌ماندن در آرشیو)</span>
                        </button>
                    </form>

                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Language Toggle System
        let currentLang = 'fa';
        
        function toggleLanguage() {{
            currentLang = currentLang === 'fa' ? 'en' : 'fa';
            document.body.setAttribute('dir', currentLang === 'fa' ? 'rtl' : 'ltr');
            document.getElementById('langBtn').innerText = currentLang === 'fa' ? 'EN' : 'FA';
            
            // Switch CSS
            const bsLink = document.getElementById('bs-css');
            if(currentLang === 'fa') {{
                bsLink.href = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css";
            }} else {{
                bsLink.href = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css";
            }}

            // Update all elements with data attributes
            document.querySelectorAll('[data-fa]').forEach(el => {{
                el.innerText = el.getAttribute(`data-${{currentLang}}`);
            }});
        }}

        // 30 Days Railway Timer Logic
        const installTimeMs = {install_time} * 1000;
        const expireTimeMs = installTimeMs + (30 * 24 * 60 * 60 * 1000);

        function updateRailwayTimer() {{
            const now = Date.now();
            const diff = expireTimeMs - now;
            
            if (diff <= 0) {{
                const msg = currentLang === 'fa' ? 'پلن منقضی شده است' : 'Plan Expired';
                document.getElementById('railwayTimer').innerText = msg;
                document.getElementById('railwayTimer').className = 'text-danger fw-bold';
                return;
            }}
            
            const d = Math.floor(diff / (1000 * 60 * 60 * 24));
            const h = Math.floor((diff / (1000 * 60 * 60)) % 24);
            const m = Math.floor((diff / 1000 / 60) % 60);
            
            const msg = currentLang === 'fa' 
                ? `${{d}} روز و ${{h}} ساعت و ${{m}} دقیقه دیگر` 
                : `${{d}}d ${{h}}h ${{m}}m remaining`;
                
            document.getElementById('railwayTimer').innerText = msg;
        }}
        setInterval(updateRailwayTimer, 60000);
        updateRailwayTimer(); // Run once immediately

        // Modal Logic
        const myModal = new bootstrap.Modal(document.getElementById('linkModal'));

        function showModal(token, title, direct, urldl, tg, createdAt, expiresAt, isDeleted) {{
            document.getElementById('modalTitle').innerText = title;
            document.getElementById('modalDirect').value = direct;
            
            const nowSecs = Math.floor(Date.now() / 1000);

            // 1. Direct Link (24 hours)
            if (isDeleted || expiresAt < nowSecs) {{
                document.getElementById('modalDirectTime').innerText = currentLang === 'fa' ? 'حذف شده' : 'Deleted';
                document.getElementById('modalDirectTime').className = 'badge bg-danger';
            }} else {{
                const diff = expiresAt - nowSecs;
                const h = Math.floor(diff / 3600);
                const m = Math.floor((diff % 3600) / 60);
                document.getElementById('modalDirectTime').innerText = currentLang === 'fa' ? `${{h}}ساعت و ${{m}}دقیقه مانده` : `${{h}}h ${{m}}m left`;
                document.getElementById('modalDirectTime').className = 'badge bg-success';
            }}

            // 2. urldl Link (7 days)
            const urldlBox = document.getElementById('urldlBox');
            if(urldl && urldl !== 'None') {{ 
                urldlBox.style.display = 'block'; 
                document.getElementById('modalUrldl').value = urldl; 
                
                const urldlExpire = createdAt + (7 * 24 * 3600);
                if (urldlExpire < nowSecs) {{
                    document.getElementById('modalUrldlTime').innerText = currentLang === 'fa' ? 'منقضی شده' : 'Expired';
                    document.getElementById('modalUrldlTime').className = 'badge bg-danger';
                }} else {{
                    const diffU = urldlExpire - nowSecs;
                    const dU = Math.floor(diffU / 86400);
                    const hU = Math.floor((diffU % 86400) / 3600);
                    document.getElementById('modalUrldlTime').innerText = currentLang === 'fa' ? `${{dU}}روز و ${{hU}}ساعت مانده` : `${{dU}}d ${{hU}}h left`;
                    document.getElementById('modalUrldlTime').className = 'badge bg-warning text-dark';
                }}
            }} else {{ urldlBox.style.display = 'none'; }}

            // 3. Telegram Post (Permanent)
            const tgBox = document.getElementById('tgBox');
            if(tg && tg !== 'None') {{ 
                tgBox.style.display = 'block'; 
                document.getElementById('modalTg').value = tg; 
                document.getElementById('modalTgTime').innerText = currentLang === 'fa' ? 'دائمی' : 'Permanent';
                document.getElementById('modalTgTime').className = 'badge bg-primary';
            }} else {{ tgBox.style.display = 'none'; }}

            document.getElementById('deleteForm').action = "/admin/links/" + token + "/delete";
            myModal.show();
        }}

        function copyToClipboard(elementId) {{
            var copyText = document.getElementById(elementId);
            copyText.select();
            document.execCommand("copy");
            
            const btn = copyText.nextElementSibling;
            const originalIcon = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-check2-all text-success"></i>';
            setTimeout(() => {{ btn.innerHTML = originalIcon; }}, 1500);
        }}
    </script>
    </body>
    </html>
    """

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(_user: str = Depends(require_admin)):
    settings = get_settings()
    
    # ثبت زمان اولین اجرای پنل (به عنوان تاریخ شروع پلن 30 روزه سرور)
    if "install_time" not in settings:
        settings["install_time"] = time.time()
        update_settings({"install_time": settings["install_time"]})
        
    links = store.list_links(include_expired=True)
    return _render_admin_page(settings, links, PUBLIC_BASE_URL)

@app.post("/admin/settings")
async def admin_update_settings(
    enable_direct_links: bool = Form(False),
    enable_channel_delivery: bool = Form(False),
    enable_nimbaha: bool = Form(False),
    enable_urldl: bool = Form(False),
    _user: str = Depends(require_admin),
):
    if not enable_direct_links and not enable_channel_delivery:
        enable_channel_delivery = True

    update_settings({
        "enable_direct_links": enable_direct_links,
        "enable_channel_delivery": enable_channel_delivery,
        "enable_nimbaha": enable_nimbaha,
        "enable_urldl": enable_urldl,
    })
    
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/links/{token}/delete")
async def admin_delete_link(token: str, _user: str = Depends(require_admin)):
    store.delete_link(token, delete_file=True)
    return RedirectResponse(url="/admin", status_code=303)
