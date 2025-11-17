# fastapi web api for pdf to slides conversion
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
import logging
from pathlib import Path
from typing import Optional
import subprocess
import tempfile

from .processing_service import PDFProcessingService
from .models import (
    PDFProcessingRequest, PDFProcessingResponse,
    OutlineContentResponse, RegenerateContentRequest
)
from .slide_generator import SlideGenerator

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# initialize fastapi application
app = FastAPI(
    title="PDF to Slide Deck API",
    description="Convert PDF documents to structured slide decks using AI",
    version="1.0.0"
)

# add cors middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom StaticFiles class that adds no-cache headers for development
class NoCacheStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def __call__(self, scope, receive, send):
        # StaticFiles only handles GET/HEAD by default, but we'll let it handle method checking
        # and just wrap the response to add no-cache headers
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Add no-cache headers for all static files in development
                headers = list(message.get("headers", []))
                # Remove existing cache headers
                headers = [(k, v) for k, v in headers if k.lower() not in (b"cache-control", b"pragma", b"expires", b"etag", b"last-modified")]
                # Add no-cache headers
                headers.append((b"cache-control", b"no-cache, no-store, must-revalidate"))
                headers.append((b"pragma", b"no-cache"))
                headers.append((b"expires", b"0"))
                message["headers"] = headers
            await send(message)
        
        # Call parent - it will handle method checking and only process GET/HEAD
        # For POST/PUT/etc, it will raise a 405 Method Not Allowed, which is fine
        # because those should be handled by API routes before reaching here
        try:
            await super().__call__(scope, receive, send_wrapper)
        except Exception:
            # If StaticFiles can't handle it (e.g., POST request), let it propagate
            # This should not happen if routes are defined before static mounts
            raise

# Add no-cache middleware for static files in development
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Add no-cache headers for CSS, JS, HTML, SCSS, and JSX files
        if request.url.path.endswith(('.css', '.js', '.html', '.scss', '.jsx')):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            # Remove ETag and Last-Modified headers if they exist
            if "ETag" in response.headers:
                del response.headers["ETag"]
            if "Last-Modified" in response.headers:
                del response.headers["Last-Modified"]
        return response

# SCSS compilation middleware
class SCSSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Check if this is a request for a .scss file
        if request.url.path.endswith('.scss'):
            # Handle SCSS files from src/styles/ directory
            # Paths like /styles/base.scss should map to src/styles/base.scss
            path_parts = request.url.path.strip('/').split('/')
            
            if path_parts[0] == 'styles' and len(path_parts) == 2:
                scss_filename = path_parts[1]
                scss_path = styles_dir / scss_filename
            else:
                # Try to find in styles directory by filename
                scss_filename = path_parts[-1] if path_parts else request.url.path.lstrip('/')
                scss_path = styles_dir / scss_filename
            
            logger.info(f"SCSS request: {request.url.path} -> {scss_path}")
            
            if scss_path.exists() and scss_path.suffix == '.scss':
                try:
                    logger.info(f"Compiling SCSS: {scss_path}")
                    result = subprocess.run(
                        ['sass', '--load-path', str(styles_dir), str(scss_path), '--style', 'expanded'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        logger.info(f"SCSS compiled successfully: {scss_path}")
                        return Response(
                            content=result.stdout,
                            media_type="text/css",
                            headers={
                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                "Pragma": "no-cache",
                                "Expires": "0"
                            }
                        )
                    else:
                        logger.error(f"SCSS compilation error for {scss_path}: {result.stderr}")
                        raise HTTPException(status_code=500, detail=f"SCSS compilation failed: {result.stderr}")
                except subprocess.TimeoutExpired:
                    logger.error("SCSS compilation timeout")
                    raise HTTPException(status_code=500, detail="SCSS compilation timeout")
                except Exception as e:
                    logger.error(f"SCSS compilation error: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"SCSS compilation error: {str(e)}")
            else:
                logger.warning(f"SCSS file not found: {scss_path}")
        
        return await call_next(request)

# initialize processing services
processing_service = PDFProcessingService()
slide_generator = SlideGenerator()

# create directories for uploads and outputs
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# Define directories (needed for middleware)
base_dir = Path(__file__).parent.parent.parent
public_dir = base_dir / "public"
src_dir = base_dir / "src"
styles_dir = src_dir / "styles"
outputs_dir = base_dir / "outputs"

# Add middleware (after directories are defined)
app.add_middleware(SCSSMiddleware)
app.add_middleware(NoCacheMiddleware)

# ============================================================================
# API ROUTES - Must be defined BEFORE static file mounts
# ============================================================================

# endpoint to upload pdf files
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file"""
    try:
        # validate file is pdf
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # save uploaded file to uploads directory
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

# endpoint to generate outline and narrative without creating slides
@app.post("/generate-outline")
async def generate_outline(
    pdf_path: str = Form(...),
    max_chunks: int = Form(1000),
    chunk_size: int = Form(500),
    overlap: int = Form(50)
):
    """Generate outline and content without creating slides"""
    try:
        # validate pdf exists
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        # create processing request
        request = PDFProcessingRequest(
            pdf_path=pdf_path,
            max_chunks=max_chunks,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        # generate outline and narrative
        response = processing_service.generate_outline_and_content(request)
        
        if response.success:
            # return response as dict
            try:
                return response.model_dump()
            except AttributeError:
                return response.dict()
        else:
            raise HTTPException(status_code=500, detail=response.message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating outline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")

@app.post("/regenerate-content")
async def regenerate_content(request: RegenerateContentRequest):
    """Regenerate content with case study focus and tone"""
    try:
        if not os.path.exists(request.pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        response = processing_service.regenerate_content_with_focus(request)
        
        if response.success:
            # Use model_dump() for Pydantic v2 or dict() for v1
            try:
                return response.model_dump()
            except AttributeError:
                return response.dict()
        else:
            raise HTTPException(status_code=500, detail=response.message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")

@app.post("/generate-slides")
async def generate_slides_from_outline(
    pdf_path: str = Form(...),
    outline: str = Form(...),  # JSON string
    bullets_data: str = Form(...)  # JSON string
):
    """Generate slides from edited outline and content"""
    try:
        import json
        from .models import OutlineItem, BulletPoint
        
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        # Parse JSON and convert to Pydantic models
        try:
            outline_json = json.loads(outline)
            outline_list = [OutlineItem(**item) for item in outline_json]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Error parsing outline JSON: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid outline JSON: {str(e)}")
        
        try:
            bullets_json = json.loads(bullets_data)
            bullets_dict = {}
            for title, bullets_list in bullets_json.items():
                if bullets_list and len(bullets_list) > 0:
                    bullets_dict[title] = [BulletPoint(**bullet) for bullet in bullets_list]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Error parsing bullets_data JSON: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid bullets_data JSON: {str(e)}")
        
        # Validate that we have bullets data
        if not bullets_dict:
            logger.warning("No bullets data provided, generating slides with empty content")
        
        response = processing_service.generate_slides_from_outline(
            pdf_path,
            outline_list,
            bullets_dict
        )
        
        if response.success:
            # Use model_dump() for Pydantic v2 or dict() for v1
            try:
                result = response.model_dump()
            except AttributeError:
                try:
                    result = response.dict()
                except Exception as e:
                    logger.error(f"Error serializing response: {str(e)}")
                    # Fallback: manually construct response
                    slide_deck_dict = None
                    if response.slide_deck:
                        try:
                            slide_deck_dict = response.slide_deck.model_dump()
                        except AttributeError:
                            try:
                                slide_deck_dict = response.slide_deck.dict()
                            except Exception:
                                logger.error("Failed to serialize slide_deck")
                    result = {
                        "success": response.success,
                        "message": response.message,
                        "slide_deck": slide_deck_dict,
                        "processing_time": response.processing_time
                    }
            return result
        else:
            raise HTTPException(status_code=500, detail=response.message)
            
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating slides: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")

# endpoint to process pdf and generate complete slide deck
@app.post("/process")
async def process_pdf(
    pdf_path: str = Form(...),
    max_chunks: int = Form(1000),
    chunk_size: int = Form(500),
    overlap: int = Form(50)
):
    """Process a PDF file and generate slide deck"""
    try:
        # validate pdf exists
        if not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        # create processing request
        request = PDFProcessingRequest(
            pdf_path=pdf_path,
            max_chunks=max_chunks,
            chunk_size=chunk_size,
            overlap=overlap
        )
        
        # run full processing pipeline
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

# Serve favicon
@app.get("/favicon.png", include_in_schema=False)
async def serve_favicon():
    """Serve the favicon"""
    favicon_path = base_dir / "favicon.png"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    raise HTTPException(status_code=404)

# Serve index.html at root (fallback if static mount doesn't work)
@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the main UI"""
    index_path = public_dir / "index.html"
    if index_path.exists():
        response = FileResponse(str(index_path))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
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

# ============================================================================
# STATIC FILE MOUNTS - Must be AFTER all API routes
# ============================================================================

# Mount static files with no-cache for development
# Mount src/ directory at /src/ for React components, utils, services
if src_dir.exists():
    app.mount("/src", NoCacheStaticFiles(directory=str(src_dir), html=False), name="src")
    logger.info(f"Mounted src files from {src_dir} at /src")

# Mount public/ directory at root for HTML and other static assets
# This must be LAST to avoid intercepting API routes
if public_dir.exists():
    app.mount("/", NoCacheStaticFiles(directory=str(public_dir), html=True), name="public")
    logger.info(f"Mounted static files from {public_dir} at /")

if outputs_dir.exists():
    app.mount("/outputs", NoCacheStaticFiles(directory=str(outputs_dir)), name="outputs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)