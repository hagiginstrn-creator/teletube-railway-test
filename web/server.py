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
# پنل مدیریت
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
            <div class="card video-card h-100 shadow-sm" onclick="showModal('{token}', '{safe_title}', '{dl_link}', '{urldl_link}', '{tg_link}')">
                <div class="thumb-container">
                    <img src="/thumbs/{token}" alt="Thumbnail">
                </div>
                <div class="card-body">
                    <h6 class="card-title video-title" title="{entry['title']}">{entry['title']}</h6>
                    <div class="video-meta mt-2 text-muted">
                        <div><i class="bi bi-hdd"></i> {format_size(entry['size_bytes']) or '-'}</div>
                        <div><i class="bi bi-clock"></i> انقضا: {_fmt_time(entry['expires_at'])}</div>
                        <div><i class="bi bi-download"></i> دفعات دانلود: {entry['downloads']}</div>
                    </div>
                </div>
            </div>
        </div>
        '''
        
    if not cards_html:
        cards_html = '<div class="col-12 text-center text-muted my-5"><i class="bi bi-inbox fs-1"></i><p>هیچ ویدیوی فعالی وجود ندارد</p></div>'

    return f"""
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>پنل مدیریت TeleTube</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
        <style>
            body {{ background-color: #f8f9fa; font-family: Tahoma, Arial, sans-serif; }}
            .navbar {{ box-shadow: 0 2px 4px rgba(0,0,0,.08); }}
            .video-card {{ cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; border: none; border-radius: 12px; overflow: hidden; }}
            .video-card:hover {{ transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,.1) !important; }}
            .thumb-container {{ position: relative; width: 100%; padding-top: 56.25%; background: #e9ecef; }}
            .thumb-container img {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
            .video-title {{ font-size: 0.95rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; }}
            .video-meta {{ font-size: 0.8rem; line-height: 1.8; }}
            .modal-content {{ border-radius: 16px; border: none; }}
            .copy-btn {{ border-top-right-radius: 0; border-bottom-right-radius: 0; }}
        </style>
    </head>
    <body>

    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container">
            <a class="navbar-brand fw-bold" href="#"><i class="bi bi-youtube text-danger"></i> TeleTube Admin</a>
        </div>
    </nav>

    <div class="container mb-5">
        <!-- بخش تنظیمات -->
        <div class="card shadow-sm mb-5 border-0" style="border-radius: 12px;">
            <div class="card-body">
                <h5 class="card-title mb-4"><i class="bi bi-gear-fill text-primary"></i> تنظیمات ربات</h5>
                <form action="/admin/settings" method="post">
                    <div class="row g-3">
                        <div class="col-md-4">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" name="enable_direct_links" id="c1" value="true" {checked_direct}>
                                <label class="form-check-label" for="c1">لینک مستقیم دانلود</label>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" name="enable_channel_delivery" id="c2" value="true" {checked_channel}>
                                <label class="form-check-label" for="c2">ارسال به کانال تلگرام</label>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-check form-switch">
                                <input class="form-check-input" type="checkbox" name="enable_urldl" id="c3" value="true" {checked_urldl}>
                                <label class="form-check-label" for="c3">لینک داخلی urldl.ir</label>
                            </div>
                        </div>
                    </div>
                    <div class="mt-4">
                        <button type="submit" class="btn btn-primary px-4"><i class="bi bi-save"></i> ذخیره تنظیمات</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- گرید ویدیوها -->
        <h5 class="mb-4"><i class="bi bi-collection-play"></i> فایل‌های فعال</h5>
        <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 row-cols-lg-4 g-4">
            {cards_html}
        </div>
    </div>

    <!-- Modal نمایش لینک‌ها -->
    <div class="modal fade" id="linkModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content shadow">
                <div class="modal-header border-0 pb-0">
                    <h5 class="modal-title fw-bold text-truncate w-100 pe-3" id="modalTitle">عنوان ویدیو</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    
                    <div class="mb-3">
                        <label class="form-label text-muted small mb-1"><i class="bi bi-cloud-arrow-down"></i> لینک دانلود مستقیم</label>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalDirect" readonly dir="ltr">
                            <button class="btn btn-outline-secondary copy-btn" type="button" onclick="copyToClipboard('modalDirect')"><i class="bi bi-copy"></i></button>
                        </div>
                    </div>

                    <div class="mb-3" id="urldlBox">
                        <label class="form-label text-muted small mb-1"><i class="bi bi-lightning-charge"></i> لینک نیم‌بها (urldl)</label>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalUrldl" readonly dir="ltr">
                            <button class="btn btn-outline-secondary copy-btn" type="button" onclick="copyToClipboard('modalUrldl')"><i class="bi bi-copy"></i></button>
                        </div>
                    </div>

                    <div class="mb-4" id="tgBox">
                        <label class="form-label text-muted small mb-1"><i class="bi bi-telegram"></i> لینک پست کانال</label>
                        <div class="input-group">
                            <input type="text" class="form-control text-start" id="modalTg" readonly dir="ltr">
                            <button class="btn btn-outline-secondary copy-btn" type="button" onclick="copyToClipboard('modalTg')"><i class="bi bi-copy"></i></button>
                        </div>
                    </div>

                    <form id="deleteForm" method="post" action="">
                        <button type="submit" class="btn btn-danger w-100"><i class="bi bi-trash3"></i> حذف فایل از سرور</button>
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
            
            // مدیریت نمایش فیلدهای خالی
            const urldlBox = document.getElementById('urldlBox');
            if(urldl) {{ urldlBox.style.display = 'block'; document.getElementById('modalUrldl').value = urldl; }} 
            else {{ urldlBox.style.display = 'none'; }}

            const tgBox = document.getElementById('tgBox');
            if(tg) {{ tgBox.style.display = 'block'; document.getElementById('modalTg').value = tg; }} 
            else {{ tgBox.style.display = 'none'; }}

            // ست کردن اکشن دکمه حذف
            document.getElementById('deleteForm').action = "/admin/links/" + token + "/delete";

            myModal.show();
        }}

        function copyToClipboard(elementId) {{
            var copyText = document.getElementById(elementId);
            copyText.select();
            document.execCommand("copy");
            
            // تغییر آیکون برای فیدبک بصری
            const btn = copyText.nextElementSibling;
            const originalIcon = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-check2 text-success"></i>';
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
