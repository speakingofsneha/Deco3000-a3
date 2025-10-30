import os
import shutil
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
            logger.info("="*60)
            
            # Step 1: Parse PDF
            logger.info("Step 1: Parsing PDF...")
            pdf_structure = self.pdf_parser.extract_text_and_structure(request.pdf_path)
            pdf_metadata = self.pdf_parser.extract_metadata(request.pdf_path)
            
            logger.info(f"  ✓ Title: {pdf_structure.title}")
            logger.info(f"  ✓ Sections found: {len(pdf_structure.sections)}")
            logger.info(f"  ✓ Total pages: {pdf_structure.total_pages}")
            
            # Step 2: Chunk and embed
            logger.info("\nStep 2: Chunking and embedding...")
            
            # Use optimized chunk settings
            chunk_size = min(request.chunk_size, 400)
            overlap = max(request.overlap, 100)
            
            logger.info(f"  Using chunk_size={chunk_size}, overlap={overlap}")
            
            chunks = self.chunking_service.chunk_text(
                pdf_structure, 
                chunk_size, 
                overlap
            )
            
            logger.info(f"  ✓ Created {len(chunks)} chunks")
            
            if len(chunks) > request.max_chunks:
                chunks = chunks[:request.max_chunks]
                logger.warning(f"  ! Limited to {request.max_chunks} chunks")
            
            vector_store = self.chunking_service.create_embeddings(chunks)
            logger.info(f"  ✓ Created vector store")
            
            # Step 3: Generate outline
            logger.info("\nStep 3: Generating outline...")
            outline_items = self.outline_generator.generate_outline(
                pdf_structure.title, 
                chunks,
                max_sections=8
            )
            
            logger.info(f"  ✓ Created {len(outline_items)} sections")
            
            # Step 4: Generate bullets with RAG
            logger.info("\nStep 4: Generating bullets...")
            self.rag_system.chunking_service = self.chunking_service
            bullets_data = self.rag_system.generate_comprehensive_bullets(
                outline_items, 
                vector_store,
                top_k=8,
                max_bullets_per_item=5
            )
            
            total_bullets = sum(len(bullets) for bullets in bullets_data.values())
            logger.info(f"  ✓ Generated {total_bullets} total bullets")
            
            # Step 5: Generate slide deck
            logger.info("\nStep 5: Generating slide deck...")
            slide_deck = self.slide_generator.generate_slide_deck(
                pdf_structure.title,
                outline_items,
                bullets_data,
                request.pdf_path,
                pdf_metadata
            )
            
            logger.info(f"  ✓ Created {len(slide_deck.slides)} slides")
            
            # Save outputs
            self._save_outputs(slide_deck, vector_store, request.pdf_path)
            
            processing_time = time.time() - start_time
            
            logger.info("="*60)
            logger.info(f"✓ SUCCESS! Completed in {processing_time:.2f} seconds")
            logger.info(f"  - Total slides: {len(slide_deck.slides)}")
            logger.info(f"  - Total bullets: {sum(len(s.content) for s in slide_deck.slides)}")
            logger.info("="*60)
            
            return PDFProcessingResponse(
                success=True,
                message="PDF processed successfully",
                slide_deck=slide_deck,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"✗ ERROR: {str(e)}", exc_info=True)
            
            return PDFProcessingResponse(
                success=False,
                message=f"Error processing PDF: {str(e)}",
                processing_time=processing_time
            )
    
    def _save_outputs(self, slide_deck: SlideDeck, vector_store, pdf_path: str):
        """Save processing outputs"""
        pdf_name = Path(pdf_path).stem
        
        # Save slide deck JSON as <name>.json
        json_path = self.output_dir / f"{pdf_name}.json"
        self.slide_generator.export_to_json(slide_deck, str(json_path))
        logger.info(f"\n  ✓ Saved: {json_path}")
        
        # Update latest.json pointer for the viewer default
        try:
            latest_path = self.output_dir / "latest.json"
            shutil.copyfile(str(json_path), str(latest_path))
            logger.info(f"  ✓ Updated: {latest_path}")
        except Exception as e:
            logger.warning(f"  ! Could not update latest.json: {e}")
        
        # Save vector store
        vector_store_path = self.vector_store_dir / pdf_name
        self.chunking_service.save_vector_store(str(vector_store_path))
        logger.info(f"  ✓ Saved: {vector_store_path}")
    
    def load_existing_slide_deck(self, pdf_name: str) -> Optional[SlideDeck]:
        """Load existing slide deck if available"""
        json_path = self.output_dir / f"{pdf_name}.json"
        
        if json_path.exists():
            try:
                return self.slide_generator.load_from_json(str(json_path))
            except Exception as e:
                logger.error(f"Error loading existing slide deck: {str(e)}")
        
        return None
    
    def get_processing_status(self, pdf_name: str) -> Dict[str, Any]:
        """Get processing status for a PDF"""
        json_path = self.output_dir / f"{pdf_name}.json"
        vector_store_path = self.vector_store_dir / pdf_name
        
        return {
            "slide_deck_exists": json_path.exists(),
            "vector_store_exists": vector_store_path.with_suffix(".index").exists(),
            "slide_deck_path": str(json_path) if json_path.exists() else None,
            "vector_store_path": str(vector_store_path) if vector_store_path.with_suffix(".index").exists() else None
        }