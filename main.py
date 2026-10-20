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
