"""Original API plus an isolated, wallet-free playground."""
from legacy import *
from playground import router
from payments import router as payments_router
from pilot import router as pilot_router

app.include_router(router)
app.include_router(payments_router)
app.include_router(pilot_router)

@app.get("/founding50", include_in_schema=False)
def founding50():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).resolve().parent / "static" / "founding50.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
