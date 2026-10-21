"""Original API plus an isolated, wallet-free playground."""
from legacy import *
from playground import router
from payments import router as payments_router
from pilot import router as pilot_router
from mainnet import router as mainnet_router
from reporting import router as reporting_router
from negotiation import router as negotiation_router, page_router as negotiation_page_router
from ai_review import router as ai_review_router

app.include_router(router)
app.include_router(payments_router)
app.include_router(pilot_router)
app.include_router(mainnet_router)
app.include_router(reporting_router)
app.include_router(negotiation_router)
app.include_router(negotiation_page_router)
app.include_router(ai_review_router)

PUBLIC_ORIGIN = "https://agent-notary-5.onrender.com"


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
        f"Sitemap: {PUBLIC_ORIGIN}/sitemap.xml",
        "",
    ])
    return PlainTextResponse(body)


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    from fastapi.responses import Response
    urls = [
        ("/mainnet", "1.0"),
        ("/mainnet/founding50", "0.8"),
        ("/play", "0.8"),
        ("/terms", "0.4"),
        ("/privacy", "0.4"),
    ]
    entries = "".join(
        f"<url><loc>{PUBLIC_ORIGIN}{path}</loc><lastmod>2026-10-21</lastmod><priority>{priority}</priority></url>"
        for path, priority in urls
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{entries}</urlset>'
    return Response(xml, media_type="application/xml")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
