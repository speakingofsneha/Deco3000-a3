from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import os
import logging
from pathlib import Path
from typing import Optional

from .processing_service import PDFProcessingService
from .models import PDFProcessingRequest, PDFProcessingResponse
from .slide_generator import SlideGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PDF to Slide Deck API",
    description="Convert PDF documents to structured slide decks using AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add no-cache middleware for static files in development
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Add no-cache headers for CSS, JS, and HTML files
        if request.url.path.endswith(('.css', '.js', '.html')):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

app.add_middleware(NoCacheMiddleware)

# Initialize services
processing_service = PDFProcessingService()
slide_generator = SlideGenerator()

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Mount static files
base_dir = Path(__file__).parent.parent
ui_dir = base_dir / "ui"
outputs_dir = base_dir / "outputs"

if ui_dir.exists():
    # Mount static files with no cache headers for development
    static_files = StaticFiles(directory=str(ui_dir), html=True)
    app.mount("/ui", static_files, name="ui")
if outputs_dir.exists():
    app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")

# Serve favicon
@app.get("/favicon.png", include_in_schema=False)
async def serve_favicon():
    """Serve the favicon"""
    favicon_path = base_dir / "favicon.png"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    raise HTTPException(status_code=404)

# Serve index.html at root
@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the main UI"""
    index_path = ui_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "PDF to Slide Deck API", "version": "1.0.0"}

@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "message": "PDF to Slide Deck API",
        "version": "1.0.0",
        "endpoints": {
            "upload": "/upload",
            "process": "/process",
            "status": "/status/{pdf_name}",
            "download": "/download/{pdf_name}",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "pdf-to-slides"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file"""
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Save uploaded file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"File uploaded: {file.filename}")
        
        return {
            "message": "File uploaded successfully",
            "filename": file.filename,
            "file_path": file_path,
            "file_size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/process")
async def process_pdf(
    pdf_path: str = Form(...),
    max_chunks: int = Form(1000),
    chunk_size: int = Form(500),
    overlap: int = Form(50)
):
    """Process a PDF file and generate slide deck"""
    try:
        # Check if file exists
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        # Create processing request
        request = PDFProcessingRequest(
            pdf_path=pdf_path,
            max_chunks=max_chunks,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        # Process PDF
        response = processing_service.process_pdf(request)
        
        if response.success:
            return response.dict()
        else:
            raise HTTPException(status_code=500, detail=response.message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/status/{pdf_name}")
async def get_processing_status(pdf_name: str):
    """Get processing status for a PDF"""
    try:
        status = processing_service.get_processing_status(pdf_name)
        return status
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.get("/download/{pdf_name}")
async def download_slide_deck(pdf_name: str):
    """Download the generated slide deck JSON"""
    try:
        json_path = f"outputs/{pdf_name}_slides.json"
        
        if not os.path.exists(json_path):
            raise HTTPException(status_code=404, detail="Slide deck not found")
        
        return FileResponse(
            path=json_path,
            filename=f"{pdf_name}_slides.json",
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading slide deck: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.get("/slides/{pdf_name}")
async def get_slide_deck(pdf_name: str):
    """Get slide deck data as JSON"""
    try:
        json_path = f"outputs/{pdf_name}_slides.json"
        
        if not os.path.exists(json_path):
            raise HTTPException(status_code=404, detail="Slide deck not found")
        
        slide_deck = slide_generator.load_from_json(json_path)
        return slide_deck.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading slide deck: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Load failed: {str(e)}")

@app.get("/slides/{pdf_name}/stats")
async def get_slide_deck_stats(pdf_name: str):
    """Get slide deck statistics"""
    try:
        json_path = f"outputs/{pdf_name}_slides.json"
        
        if not os.path.exists(json_path):
            raise HTTPException(status_code=404, detail="Slide deck not found")
        
        slide_deck = slide_generator.load_from_json(json_path)
        stats = slide_generator.get_slide_statistics(slide_deck)
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)