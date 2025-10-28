from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum

class SlideType(str, Enum):
    TITLE = "title"
    CONTENT = "content"
    BULLET = "bullet"
    IMAGE = "image"

class Chunk(BaseModel):
    id: str
    text: str
    page_number: int
    chunk_index: int
    metadata: Dict[str, Any] = {}

class OutlineItem(BaseModel):
    title: str
    description: str
    level: int
    order: int

class BulletPoint(BaseModel):
    text: str
    provenance: List[str]  # List of chunk IDs that support this bullet
    confidence: float = 0.0

class Slide(BaseModel):
    id: str
    type: SlideType
    title: str
    content: List[BulletPoint]
    metadata: Dict[str, Any] = {}

class SlideDeck(BaseModel):
    title: str
    slides: List[Slide]
    metadata: Dict[str, Any] = {}
    created_at: str
    source_pdf: str

class PDFProcessingRequest(BaseModel):
    pdf_path: str
    max_chunks: int = 1000
    chunk_size: int = 500
    overlap: int = 50

class PDFProcessingResponse(BaseModel):
    success: bool
    message: str
    slide_deck: Optional[SlideDeck] = None
    processing_time: float = 0.0