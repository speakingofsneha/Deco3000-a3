import os
import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .pdf_parser import PDFParser
from .chunking_embedding import ChunkingEmbeddingService
from .outline_generator import OutlineGenerator
from .rag_system import RAGSystem
from .slide_generator import SlideGenerator
from .models import PDFProcessingRequest, PDFProcessingResponse, SlideDeck

logger = logging.getLogger(__name__)

class PDFProcessingService:
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.chunking_service = ChunkingEmbeddingService()
        self.outline_generator = OutlineGenerator()
        self.rag_system = RAGSystem()
        self.slide_generator = SlideGenerator()
        
        # Create output directories
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
        
        self.vector_store_dir = Path("faiss_index")
        self.vector_store_dir.mkdir(exist_ok=True)
    
    def process_pdf(self, request: PDFProcessingRequest) -> PDFProcessingResponse:
        """Main processing pipeline"""
        start_time = time.time()
        
        try:
            logger.info(f"Starting PDF processing: {request.pdf_path}")
            
            # Step 1: Parse PDF
            logger.info("Step 1: Parsing PDF...")
            pdf_structure = self.pdf_parser.extract_text_and_structure(request.pdf_path)
            pdf_metadata = self.pdf_parser.extract_metadata(request.pdf_path)
            
            # Step 2: Chunk and embed
            logger.info("Step 2: Chunking and embedding...")
            chunks = self.chunking_service.chunk_text(
                pdf_structure, 
                request.chunk_size, 
                request.overlap
            )
            
            if len(chunks) > request.max_chunks:
                chunks = chunks[:request.max_chunks]
                logger.warning(f"Limited chunks to {request.max_chunks}")
            
            vector_store = self.chunking_service.create_embeddings(chunks)
            
            # Step 3: Generate outline
            logger.info("Step 3: Generating outline...")
            outline_items = self.outline_generator.generate_outline(
                pdf_structure.title, 
                chunks
            )
            
            # Step 4: Generate bullets with RAG
            logger.info("Step 4: Generating bullets with RAG...")
            # Ensure RAG system uses the same chunking service
            self.rag_system.chunking_service = self.chunking_service
            bullets_data = self.rag_system.generate_comprehensive_bullets(
                outline_items, 
                vector_store
            )
            
            # Step 5: Generate slide deck
            logger.info("Step 5: Generating slide deck...")
            slide_deck = self.slide_generator.generate_slide_deck(
                pdf_structure.title,
                outline_items,
                bullets_data,
                request.pdf_path,
                pdf_metadata
            )
            
            # Save outputs
            self._save_outputs(slide_deck, vector_store, request.pdf_path)
            
            processing_time = time.time() - start_time
            
            logger.info(f"PDF processing completed in {processing_time:.2f} seconds")
            
            return PDFProcessingResponse(
                success=True,
                message="PDF processed successfully",
                slide_deck=slide_deck,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error processing PDF: {str(e)}")
            
            return PDFProcessingResponse(
                success=False,
                message=f"Error processing PDF: {str(e)}",
                processing_time=processing_time
            )
    
    def _save_outputs(self, slide_deck: SlideDeck, vector_store, pdf_path: str):
        """Save processing outputs"""
        pdf_name = Path(pdf_path).stem
        
        # Save slide deck JSON
        json_path = self.output_dir / f"{pdf_name}_slides.json"
        self.slide_generator.export_to_json(slide_deck, str(json_path))
        
        # Save vector store
        vector_store_path = self.vector_store_dir / pdf_name
        self.chunking_service.save_vector_store(str(vector_store_path))
        
        logger.info(f"Outputs saved: {json_path}, {vector_store_path}")
    
    def load_existing_slide_deck(self, pdf_name: str) -> Optional[SlideDeck]:
        """Load existing slide deck if available"""
        json_path = self.output_dir / f"{pdf_name}_slides.json"
        
        if json_path.exists():
            try:
                return self.slide_generator.load_from_json(str(json_path))
            except Exception as e:
                logger.error(f"Error loading existing slide deck: {str(e)}")
        
        return None
    
    def get_processing_status(self, pdf_name: str) -> Dict[str, Any]:
        """Get processing status for a PDF"""
        json_path = self.output_dir / f"{pdf_name}_slides.json"
        vector_store_path = self.vector_store_dir / pdf_name
        
        return {
            "slide_deck_exists": json_path.exists(),
            "vector_store_exists": vector_store_path.with_suffix(".index").exists(),
            "slide_deck_path": str(json_path) if json_path.exists() else None,
            "vector_store_path": str(vector_store_path) if vector_store_path.with_suffix(".index").exists() else None
        }