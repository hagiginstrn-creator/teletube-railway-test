""" وب‌سرور FastAPI: مسیر دانلود مستقیم فایل‌ها + پنل مدیریت ساده.
با uvicorn، همزمان با بات (توی همون event loop) اجرا می‌شه — به bot.py نگاه کن. """
import os
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
    if not entry:
        raise HTTPException(status_code=404, detail="لینک پیدا نشد یا منقضی شده")
    
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
    """مسیر جدید برای نمایش عکس تامبنیل در پنل مدیریت"""
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
    
    cards_html = ""
    for entry in links:
        token = entry['token']
        dl_link = f"{base_url}/files/{token}" if base_url else f"/files/{token}"
        urldl_link = entry.get('urldl_link') or ''
        tg_link = entry.get('tg_link') or ''
        
        # مقادیر امن برای جاوا اسکریپت
        safe_title = entry['title'].replace("'", "\\'").replace('"', '&quot;')
        
        cards_html += f'''
        <div class="col">
            <div class="glass video-card h-100" onclick="showModal('{token}', '{safe_title}', '{dl_link}', '{urldl_link}', '{tg_link}')">
                <div class="thumb-container">
                    <img src="/thumbs/{token}" alt="Thumbnail">
                    <div class="play-overlay"><i class="bi bi-play-circle-fill"></i></div>
                </div>
                <div class="card-body p-3">
                    <h6 class="video-title" title="{entry['title']}">{entry['title']}</h6>
                    <div class="video-meta mt-3">
                        <div class="d-flex justify-content-between mb-1">
                            <span><i class="bi bi-hdd-fill me-1"></i> {format_size(entry['size_bytes']) or '-'}</span>
                            <span><i class="bi bi-cloud-arrow-down-fill me-1"></i> {entry['downloads']}</span>
                        </div>
                        <div><i class="bi bi-hourglass-split me-1"></i> {_fmt_time(entry['expires_at'])}</div>
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
                <h5 class="mt-3 text-muted">هیچ ویدیوی فعالی وجود ندارد</h5>
            </div>
        </div>'''

    return f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TeleTube Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
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
            }}

            /* Ambient Glowing Orbs */
            .bg-orb {{
                position: fixed;
                border-radius: 50%;
                filter: blur(100px);
                z-index: -1;
                animation: float 12s infinite ease-in-out alternate;
            }}
            .orb-1 {{ width: 400px; height: 400px; background: rgba(99, 102, 241, 0.3); top: -10%; left: -10%; }}
            .orb-2 {{ width: 500px; height: 500px; background: rgba(236, 72, 153, 0.2); bottom: -20%; right: -10%; animation-delay: -5s; }}
            .orb-3 {{ width: 350px; height: 350px; background: rgba(56, 189, 248, 0.2); top: 30%; left: 40%; animation-duration: 18s; }}

            @keyframes float {{
                0% {{ transform: translateY(0) scale(1); }}
                100% {{ transform: translateY(-40px) scale(1.1); }}
            }}

            /* Glassmorphism Core Class */
            .glass {{
                background: var(--glass-bg);
                backdrop-filter: var(--glass-blur);
                -webkit-backdrop-filter: var(--glass-blur);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}

            .navbar-glass {{
                background: rgba(15, 23, 42, 0.6);
                backdrop-filter: blur(20px);
                border-bottom: 1px solid var(--glass-border);
            }}

            /* Video Cards */
            .video-card {{
                cursor: pointer;
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s;
                display: flex;
                flex-direction: column;
                position: relative;
                overflow: hidden;
            }}
            .video-card:hover {{
                transform: translateY(-8px);
                background: rgba(30, 41, 59, 0.6);
                border-color: rgba(56, 189, 248, 0.3);
            }}
            
            .thumb-container {{
                position: relative;
                width: 100%;
                padding-top: 56.25%; /* 16:9 Aspect Ratio */
                background: #000;
                overflow: hidden;
                border-bottom: 1px solid var(--glass-border);
            }}
            .thumb-container img {{
                position: absolute;
                top: 0; left: 0;
                width: 100%; height: 100%;
                object-fit: cover;
                opacity: 0.85;
                transition: opacity 0.3s, transform 0.5s;
            }}
            .video-card:hover .thumb-container img {{
                opacity: 1;
                transform: scale(1.05);
            }}
            .play-overlay {{
                position: absolute;
                top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                font-size: 3rem;
                color: rgba(255, 255, 255, 0.7);
                opacity: 0;
                transition: opacity 0.3s, transform 0.3s;
            }}
            .video-card:hover .play-overlay {{
                opacity: 1;
                transform: translate(-50%, -50%) scale(1.1);
            }}

            .video-title {{
                font-size: 0.95rem;
                line-height: 1.5;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                font-weight: 600;
                color: #f1f5f9;
            }}
            .video-meta {{
                font-size: 0.8rem;
                color: #94a3b8;
            }}
            .video-meta i {{ color: var(--accent-color); }}

            /* Forms & Inputs */
            .form-check-label {{ color: #cbd5e1; }}
            .form-control, .input-group-text {{
                background: rgba(0, 0, 0, 0.2) !important;
                border: 1px solid var(--glass-border) !important;
                color: #f8fafc !important;
            }}
            .form-control:focus {{
                box-shadow: 0 0 0 0.25rem rgba(56, 189, 248, 0.2) !important;
                border-color: var(--accent-color) !important;
            }}

            /* Modal Styling */
            .modal-content {{
                background: rgba(15, 23, 42, 0.85);
                backdrop-filter: blur(24px);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 24px;
                color: #e2e8f0;
            }}
            .modal-header {{ border-bottom: 1px solid var(--glass-border); }}
            .btn-close {{ filter: invert(1); opacity: 0.7; }}
            .btn-close:hover {{ opacity: 1; }}

            /* Glass Buttons */
            .btn-glass-primary {{
                background: rgba(56, 189, 248, 0.15);
                border: 1px solid rgba(56, 189, 248, 0.4);
                color: var(--accent-color);
                transition: all 0.3s;
                border-radius: 12px;
            }}
            .btn-glass-primary:hover {{
                background: rgba(56, 189, 248, 0.3);
                color: #fff;
                box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
            }}
            
            .btn-glass-danger {{
                background: rgba(244, 63, 94, 0.15);
                border: 1px solid rgba(244, 63, 94, 0.4);
                color: #fb7185;
                transition: all 0.3s;
                border-radius: 12px;
            }}
            .btn-glass-danger:hover {{
                background: rgba(244, 63, 94, 0.3);
                color: #fff;
                box-shadow: 0 0 15px rgba(244, 63, 94, 0.3);
            }}

            .copy-btn {{
                background: rgba(255, 255, 255, 0.05) !important;
                color: #cbd5e1 !important;
                border-color: var(--glass-border) !important;
                transition: background 0.2s;
            }}
            .copy-btn:hover {{ background: rgba(255, 255, 255, 0.15) !important; color: #fff !important; }}

            /* Switch Toggles */
            .form-switch .form-check-input {{
                background-color: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.1);
            }}
            .form-switch .form-check-input:checked {{
                background-color: var(--accent-color);
                border-color: var(--accent-color);
            }}

            /* Scrollbar */
            ::-webkit-scrollbar {{ width: 8px; }}
            ::-webkit-scrollbar-track {{ background: #0f172a; }}
            ::-webkit-scrollbar-thumb {{ background: rgba(255, 255, 255, 0.2); border-radius: 10px; }}
            ::-webkit-scrollbar-thumb:hover {{ background: rgba(255, 255, 255, 0.4); }}
        </style>
    </head>
    <body>

    <!-- Animated Background Elements -->
    <div class="bg-orb orb-1"></div>
    <div class="bg-orb orb-2"></div>
    <div class="bg-orb orb-3"></div>

    <nav class="navbar navbar-glass sticky-top py-3 mb-5">
        <div class="container">
            <a class="navbar-brand fw-bold text-white d-flex align-items-center" href="#">
                <i class="bi bi-youtube text-danger fs-3 me-2"></i> 
                <span style="letter-spacing: 1px;">TELETUBE <span class="fw-light text-muted">ADMIN</span></span>
            </a>
        </div>
    </nav>

    <div class="container mb-5 pb-5">
        <!-- Settings Panel -->
        <div class="glass p-4 mb-5">
            <h5 class="mb-4 text-white"><i class="bi bi-sliders text-info me-2"></i> پیکربندی سیستم</h5>
            <form action="/admin/settings" method="post">
                <div class="row g-4">
                    <div class="col-md-4">
                        <div class="form-check form-switch fs-5">
                            <input class="form-check-input" type="checkbox" name="enable_direct_links" id="c1" value="true" {checked_direct}>
                            <label class="form-check-label fs-6 mt-1 ms-2" for="c1">لینک مستقیم سرور</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check form-switch fs-5">
                            <input class="form-check-input" type="checkbox" name="enable_channel_delivery" id="c2" value="true" {checked_channel}>
                            <label class="form-check-label fs-6 mt-1 ms-2" for="c2">آپلود در تلگرام</label>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="form-check form-switch fs-5">
                            <input class="form-check-input" type="checkbox" name="enable_urldl" id="c3" value="true" {checked_urldl}>
                            <label class="form-check-label fs-6 mt-1 ms-2" for="c3">مسیر داخلی urldl.ir</label>
                        </div>
                    </div>
                </div>
                <div class="mt-4 pt-2 border-top border-secondary border-opacity-25">
                    <button type="submit" class="btn btn-glass-primary px-5 py-2">
                        <i class="bi bi-hdd-network me-2"></i> اعمال تنظیمات
                    </button>
                </div>
            </form>
        </div>

        <!-- Video Grid -->
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h4 class="m-0 text-white"><i class="bi bi-collection-play me-2 text-info"></i> آرشیو ویدیوها</h4>
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
                    <h5 class="modal-title fw-bold text-truncate w-100 pe-3" id="modalTitle">عنوان ویدیو</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body px-4 pb-4 mt-3">
                    
                    <div class="mb-4">
                        <label class="form-label text-info small fw-bold mb-2"><i class="bi bi-globe2"></i> لینک مستقیم سرور</label>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalDirect" readonly dir="ltr">
                            <button class="btn copy-btn px-3" type="button" onclick="copyToClipboard('modalDirect')"><i class="bi bi-clipboard"></i></button>
                        </div>
                    </div>

                    <div class="mb-4" id="urldlBox">
                        <label class="form-label text-info small fw-bold mb-2"><i class="bi bi-lightning-charge-fill text-warning"></i> ترافیک داخلی (urldl)</label>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalUrldl" readonly dir="ltr">
                            <button class="btn copy-btn px-3" type="button" onclick="copyToClipboard('modalUrldl')"><i class="bi bi-clipboard"></i></button>
                        </div>
                    </div>

                    <div class="mb-5" id="tgBox">
                        <label class="form-label text-info small fw-bold mb-2"><i class="bi bi-telegram text-primary"></i> پست ذخیره تلگرام</label>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalTg" readonly dir="ltr">
                            <button class="btn copy-btn px-3" type="button" onclick="copyToClipboard('modalTg')"><i class="bi bi-clipboard"></i></button>
                        </div>
                    </div>

                    <form id="deleteForm" method="post" action="">
                        <button type="submit" class="btn btn-glass-danger w-100 py-2 fs-6">
                            <i class="bi bi-trash3-fill me-2"></i> حذف کامل از سرور
                        </button>
                    </form>

                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const myModal = new bootstrap.Modal(document.getElementById('linkModal'));

        function showModal(token, title, direct, urldl, tg) {{
            document.getElementById('modalTitle').innerText = title;
            document.getElementById('modalDirect').value = direct;
            
            // مدیریت نمایش باکسی که لینک نداره
            const urldlBox = document.getElementById('urldlBox');
            if(urldl && urldl !== 'None') {{ urldlBox.style.display = 'block'; document.getElementById('modalUrldl').value = urldl; }} 
            else {{ urldlBox.style.display = 'none'; }}

            const tgBox = document.getElementById('tgBox');
            if(tg && tg !== 'None') {{ tgBox.style.display = 'block'; document.getElementById('modalTg').value = tg; }} 
            else {{ tgBox.style.display = 'none'; }}

            document.getElementById('deleteForm').action = "/admin/links/" + token + "/delete";
            myModal.show();
        }}

        function copyToClipboard(elementId) {{
            var copyText = document.getElementById(elementId);
            copyText.select();
            document.execCommand("copy");
            
            // انیمیشن تیک کپی
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
    links = store.list_links()
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
