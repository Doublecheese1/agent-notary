"""Original API plus an isolated, wallet-free playground."""
import asyncio
import contextlib
import os

from legacy import *
from playground import router
from payments import router as payments_router
from pilot import router as pilot_router
from mainnet import router as mainnet_router
from reporting import router as reporting_router, reporting_enabled
from negotiation import router as negotiation_router, page_router as negotiation_page_router
from ai_review import router as ai_review_router
from discovery import router as discovery_router
from international import LOCALES, localized_landing
from launch_analytics import router as launch_analytics_router
from founding50 import router as founding50_router
from outreach_crm import router as outreach_crm_router
from email_archive import router as email_archive_router
from agent_coordination import router as agent_coordination_router

app.include_router(router)
app.include_router(payments_router)
app.include_router(pilot_router)
app.include_router(mainnet_router)
app.include_router(reporting_router)
app.include_router(negotiation_router)
app.include_router(negotiation_page_router)
app.include_router(ai_review_router)
app.include_router(discovery_router)
app.include_router(launch_analytics_router)
app.include_router(founding50_router)
app.include_router(outreach_crm_router)
app.include_router(email_archive_router)
app.include_router(agent_coordination_router)


_email_archive_task: asyncio.Task | None = None


async def _email_archive_loop() -> None:
    """Run the read-only IMAP archive in the existing web service process."""
    from email_archive import sync_imap

    interval = max(3600, int(os.getenv("OUTREACH_IMAP_SYNC_INTERVAL_SECONDS", "86400")))
    while True:
        try:
            await asyncio.to_thread(sync_imap)
        except Exception as exc:  # pragma: no cover - runtime safety net
            print(f"[email-archive] sync failed: {exc}", flush=True)
        await asyncio.sleep(interval)


@app.on_event("startup")
async def start_email_archive_loop() -> None:
    global _email_archive_task
    enabled = os.getenv("OUTREACH_IMAP_BACKGROUND_SYNC", "false").strip().lower() == "true"
    if enabled and _email_archive_task is None:
        _email_archive_task = asyncio.create_task(_email_archive_loop())


@app.on_event("shutdown")
async def stop_email_archive_loop() -> None:
    global _email_archive_task
    if _email_archive_task is not None:
        _email_archive_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _email_archive_task
        _email_archive_task = None

PUBLIC_ORIGIN = "https://agentsolis.solists.com.tr"


class BodySizeLimitMiddleware:
    """Reject oversized request bodies even when Content-Length is absent."""
    def __init__(self, app, max_bytes: int = 1_048_576):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body = message.get("body", b"")
            total += len(body)
            if total > self.max_bytes:
                from fastapi.responses import JSONResponse
                response = JSONResponse({"detail": "Request body is too large."}, status_code=413)
                return await response(scope, receive, send)
            chunks.append(body)
            if not message.get("more_body", False):
                break
        complete = b"".join(chunks)
        delivered = False

        async def replay():
            nonlocal delivered
            if delivered:
                return {"type": "http.request", "body": b"", "more_body": False}
            delivered = True
            return {"type": "http.request", "body": complete, "more_body": False}

        return await self.app(scope, replay, send)


app.add_middleware(BodySizeLimitMiddleware)


@app.middleware("http")
async def security_headers(request, call_next):
    if request.url.hostname == "agent-notary-5.onrender.com":
        from fastapi.responses import RedirectResponse
        destination = f"{PUBLIC_ORIGIN}{request.url.path}"
        if request.url.query:
            destination += f"?{request.url.query}"
        return RedirectResponse(destination, status_code=308)
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > 1_048_576:
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"detail": "Request body is too large."}, status_code=413)
            except ValueError:
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Invalid Content-Length header."}, status_code=400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'; "
        "form-action 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'self' https://*.arbitrum.io https://*.arbiscan.io"
    )
    return response


@app.get("/robots.txt", include_in_schema=False)
def robots():
    from fastapi.responses import PlainTextResponse
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        "Disallow: /internal/",
        "Disallow: /private-report/",
        "Disallow: /mainnet/setup",
        "Disallow: /mainnet/operations",
        "Disallow: /mainnet/validator",
        "Disallow: /mainnet/deal/",
        "Disallow: /mainnet/negotiate/",
        "Disallow: /pilot/admin",
        "Disallow: /pilot/deal/",
        "Allow: /.well-known/agent-card.json",
        "Allow: /.well-known/security.txt",
        "Allow: /llms.txt",
        f"Sitemap: {PUBLIC_ORIGIN}/sitemap.xml",
        "",
    ])
    return PlainTextResponse(body)


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    from fastapi.responses import Response
    urls = [
        ("/", "1.0"),
        ("/mainnet", "1.0"),
        ("/mainnet/founding50", "0.8"),
        ("/ai-agent-escrow", "0.8"),
        ("/x402-vs-agent-escrow", "0.8"),
        ("/ai-agent-job-evidence", "0.8"),
        ("/play", "0.8"),
        ("/start", "0.7"),
        ("/faq", "0.7"),
        ("/contact", "0.4"),
        ("/terms", "0.4"),
        ("/privacy", "0.4"),
    ]
    urls.extend((f"/{locale}", "0.7") for locale in LOCALES)
    entries = "".join(
        f"<url><loc>{PUBLIC_ORIGIN}{path}</loc><priority>{priority}</priority></url>"
        for path, priority in urls
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'
    return Response(xml, media_type="application/xml")

@app.get("/indexnow-key.txt", include_in_schema=False)
def indexnow_key():
    import os
    import re
    from fastapi import HTTPException
    from fastapi.responses import PlainTextResponse
    key = os.getenv("INDEXNOW_KEY", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9-]{8,128}", key):
        raise HTTPException(status_code=404, detail="IndexNow is not configured")
    return PlainTextResponse(key)

@app.get("/ai-agent-escrow", include_in_schema=False)
def ai_agent_escrow_guide():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "ai-agent-escrow.html")

@app.get("/x402-vs-agent-escrow", include_in_schema=False)
def x402_vs_agent_escrow_guide():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "x402-vs-agent-escrow.html")

@app.get("/ai-agent-job-evidence", include_in_schema=False)
def ai_agent_job_evidence_guide():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "ai-agent-job-evidence.html")

@app.get("/founding50", include_in_schema=False)
def founding50():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "founding50.html")

@app.get("/terms", include_in_schema=False)
def terms():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "terms.html")

@app.get("/privacy", include_in_schema=False)
def privacy():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "privacy.html")

@app.get("/assets/brand.css", include_in_schema=False)
def brand_styles():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "brand.css", media_type="text/css")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "favicon.ico", media_type="image/x-icon")


@app.get("/assets/launch-analytics.js", include_in_schema=False)
def launch_analytics_script():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "launch-analytics.js", media_type="text/javascript")

@app.get("/assets/language-menu.js", include_in_schema=False)
def language_menu_script():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "language-menu.js", media_type="text/javascript")


@app.get("/assets/video-guide.js", include_in_schema=False)
def video_guide_script():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "video-guide.js", media_type="text/javascript")


@app.get("/assets/localized-status.js", include_in_schema=False)
def localized_status_script():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "localized-status.js", media_type="text/javascript")


@app.get("/assets/videos/{filename}", include_in_schema=False)
def explainer_video_asset(filename: str):
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    allowed = {
        "01-overview.mp4", "02-wallet.mp4", "03-buyer.mp4", "04-seller.mp4", "05-founding50.mp4",
        "01-poster.png", "02-poster.png", "03-poster.png", "04-poster.png", "05-poster.png",
    }
    allowed.update(
        f"{chapter}.{language}.vtt"
        for chapter in ("01", "02", "03", "04", "05")
        for language in ("en", "tr", "es", "pt-br", "ru", "zh-cn")
    )
    if filename not in allowed:
        raise HTTPException(status_code=404, detail="Video asset not found")
    media_type = "video/mp4" if filename.endswith(".mp4") else "text/vtt" if filename.endswith(".vtt") else "image/png"
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "videos" / filename,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/assets/flags/{code}.svg", include_in_schema=False)
def language_flag(code: str):
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    if code not in {"gb", "tr", "es", "br", "ru", "cn"}:
        raise HTTPException(status_code=404, detail="Flag not found")
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "flags" / f"{code}.svg",
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )

@app.get("/assets/agentsolis-social-card.png", include_in_schema=False)
def social_card():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "agentsolis-social-card.png", media_type="image/png")

@app.get("/assets/fonts/Manrope-Variable.ttf", include_in_schema=False)
def manrope_font():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "fonts" / "Manrope-Variable.ttf", media_type="font/ttf")

@app.get("/assets/fonts/IBMPlexMono-Regular.ttf", include_in_schema=False)
def plex_mono_font():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "fonts" / "IBMPlexMono-Regular.ttf", media_type="font/ttf")

@app.get("/private-report/{access_key}", include_in_schema=False)
def founder_reports(access_key: str):
    import os
    import secrets
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    expected = os.getenv("REPORT_DASHBOARD_PATH", "").strip()
    if (
        not reporting_enabled()
        or len(expected) < 24
        or not secrets.compare_digest(access_key, expected)
    ):
        raise HTTPException(404, "Not found")
    return FileResponse(
        Path(__file__).resolve().parent / "static" / "reports.html",
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex, nofollow, noarchive",
        },
    )

@app.get('/start', include_in_schema=False)
def start_page():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / 'static' / 'start.html')


@app.get('/faq', include_in_schema=False)
def faq_page():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / 'static' / 'faq.html')


@app.get('/contact', include_in_schema=False)
def contact_page():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / 'static' / 'contact.html')


@app.get('/.well-known/security.txt', include_in_schema=False)
def security_contact():
    from datetime import datetime, timedelta, timezone
    from fastapi.responses import PlainTextResponse
    expires = (datetime.now(timezone.utc) + timedelta(days=180)).strftime('%Y-%m-%dT%H:%M:%SZ')
    body = '\n'.join([
        'Contact: mailto:agentsolis@solists.com.tr',
        'Canonical: https://agentsolis.solists.com.tr/.well-known/security.txt',
        'Preferred-Languages: en, tr',
        f'Expires: {expires}',
        '',
    ])
    return PlainTextResponse(body, headers={'Cache-Control': 'public, max-age=86400'})


@app.get("/{locale}", include_in_schema=False)
def international_landing(locale: str):
    from fastapi import HTTPException
    from fastapi.responses import HTMLResponse
    if locale not in LOCALES:
        raise HTTPException(status_code=404, detail="Language not found")
    return HTMLResponse(localized_landing(locale))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
