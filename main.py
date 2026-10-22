"""Original API plus an isolated, wallet-free playground."""
from legacy import *
from playground import router
from payments import router as payments_router
from pilot import router as pilot_router
from mainnet import router as mainnet_router
from reporting import router as reporting_router
from negotiation import router as negotiation_router, page_router as negotiation_page_router
from ai_review import router as ai_review_router
from discovery import router as discovery_router
from international import LOCALES, localized_landing

app.include_router(router)
app.include_router(payments_router)
app.include_router(pilot_router)
app.include_router(mainnet_router)
app.include_router(reporting_router)
app.include_router(negotiation_router)
app.include_router(negotiation_page_router)
app.include_router(ai_review_router)
app.include_router(discovery_router)

PUBLIC_ORIGIN = "https://agentsolis.solists.com.tr"


@app.middleware("http")
async def security_headers(request, call_next):
    if request.url.hostname == "agent-notary-5.onrender.com":
        from fastapi.responses import RedirectResponse
        destination = f"{PUBLIC_ORIGIN}{request.url.path}"
        if request.url.query:
            destination += f"?{request.url.query}"
        return RedirectResponse(destination, status_code=308)
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
        "Disallow: /reports",
        "Disallow: /internal/",
        "Disallow: /mainnet/setup",
        "Disallow: /mainnet/operations",
        "Disallow: /mainnet/validator",
        "Disallow: /mainnet/deal/",
        "Disallow: /mainnet/negotiate/",
        "Disallow: /pilot/admin",
        "Disallow: /pilot/deal/",
        "Allow: /.well-known/agent-card.json",
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
        ("/terms", "0.4"),
        ("/privacy", "0.4"),
    ]
    urls.extend((f"/{locale}", "0.7") for locale in LOCALES)
    entries = "".join(
        f"<url><loc>{PUBLIC_ORIGIN}{path}</loc><lastmod>2026-10-22</lastmod><priority>{priority}</priority></url>"
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

@app.get("/reports", include_in_schema=False)
def founder_reports():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "reports.html")

@app.get("/mainnet/founding50", include_in_schema=False)
def mainnet_founding50():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "founding50-mainnet.html")


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
