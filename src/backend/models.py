# pydantic models for data validation and structure
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum

# enum for different types of slides
class SlideType(str, Enum):
    TITLE = "title"
    CONTENT = "content"
    BULLET = "bullet"
    IMAGE = "image"

# model for a text chunk from the pdf
class Chunk(BaseModel):
    id: str
    text: str
    page_number: int
    chunk_index: int
    metadata: Dict[str, Any] = {}

# model for an outline section
class OutlineItem(BaseModel):
    title: str
    description: str
    level: int
    order: int

# model for a bullet point on a slide
class BulletPoint(BaseModel):
    text: str
    provenance: List[str]  # list of chunk IDs that support this bullet
    confidence: float = 0.0

# model for a single slide
class Slide(BaseModel):
    id: str
    type: SlideType
    title: str
    content: List[BulletPoint]
    provenance: List[str] = []  # page numbers for the entire slide
    metadata: Dict[str, Any] = {}

# model for a complete slide deck
class SlideDeck(BaseModel):
    title: str
    slides: List[Slide]
    metadata: Dict[str, Any] = {}
    created_at: str
    source_pdf: str

# request model for processing a pdf
class PDFProcessingRequest(BaseModel):
    pdf_path: str
    max_chunks: int = 1500
    chunk_size: int = 2000 
    overlap: int = 200  # reduced overlap since we want fewer chunks

# response model for pdf processing
class PDFProcessingResponse(BaseModel):
    success: bool
    message: str
    slide_deck: Optional[SlideDeck] = None
    processing_time: float = 0.0

# response model for outline and content generation
class OutlineContentResponse(BaseModel):
    success: bool
    message: str
    pdf_title: str
    outline: List[OutlineItem]
    narrative_plan: str  # initial narrative plan for user to edit
    bullets_data: Dict[str, List[BulletPoint]] = {}  # will be generated after user edits outline
    processing_time: float = 0.0

# request model for regenerating content with narrative and tone
class RegenerateContentRequest(BaseModel):
    pdf_path: str
    outline: List[OutlineItem]
    narrative: Optional[str] = None
    tone: Optional[str] = None
    max_chunks: int = 1500
    chunk_size: int = 2000  # larger chunks for better context (hopefully)
    overlap: int = 200  