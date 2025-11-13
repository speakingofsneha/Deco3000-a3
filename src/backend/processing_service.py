import os
import shutil
import time
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from .pdf_parser import PDFParser
from .chunking_embedding import ChunkingEmbeddingService
from .outline_generator import OutlineGenerator
from .rag_system import RAGSystem
from .slide_generator import SlideGenerator
from .llm_service import get_llm_service
from .models import (
    PDFProcessingRequest, PDFProcessingResponse, SlideDeck,
    OutlineContentResponse, RegenerateContentRequest
)

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
    
    def generate_outline_and_content(self, request: PDFProcessingRequest) -> OutlineContentResponse:
        """Generate outline and content without creating slides"""
        start_time = time.time()
        
        try:
            logger.info(f"Generating outline and content: {request.pdf_path}")
            
            # Step 1: Parse PDF
            pdf_structure = self.pdf_parser.extract_text_and_structure(request.pdf_path)
            
            # Step 2: Chunk and embed
            chunk_size = min(request.chunk_size, 400)
            overlap = max(request.overlap, 100)
            
            chunks = self.chunking_service.chunk_text(
                pdf_structure, 
                chunk_size, 
                overlap
            )
            
            if len(chunks) > request.max_chunks:
                chunks = chunks[:request.max_chunks]
            
            vector_store = self.chunking_service.create_embeddings(chunks)
            
            # Step 3: Generate initial narrative plan first (without needing an outline)
            # This will be a structured narrative that the user can edit
            narrative_plan = self._generate_narrative_plan(
                None,  # No outline needed - generate from PDF content directly
                pdf_structure.title,
                vector_store,
                chunks
            )
            
            # Step 4: Generate outline FROM the narrative
            # The outline structure should reflect the narrative's story beats
            outline_items = self.outline_generator.generate_outline_from_narrative(
                narrative_plan,
                pdf_structure.title
            )
            
            # Save vector store for later use (will be used when generating bullets)
            pdf_name = Path(request.pdf_path).stem
            vector_store_path = self.vector_store_dir / pdf_name
            self.chunking_service.save_vector_store(str(vector_store_path))
            
            processing_time = time.time() - start_time
            
            return OutlineContentResponse(
                success=True,
                message="Outline and narrative plan generated successfully",
                pdf_title=pdf_structure.title,
                outline=outline_items,
                narrative_plan=narrative_plan,
                bullets_data={},  # Will be generated after user edits narrative
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error generating outline and content: {str(e)}", exc_info=True)
            return OutlineContentResponse(
                success=False,
                message=f"Error: {str(e)}",
                pdf_title="",
                outline=[],
                narrative_plan="",
                bullets_data={},
                processing_time=time.time() - start_time
            )
    
    def _generate_narrative_plan(self, outline_items: List, pdf_title: str, vector_store, chunks: List) -> str:
        """Generate a compelling storytelling narrative plan from PDF content"""
        llm_service = get_llm_service()
        
        # Build outline summary if outline_items provided, otherwise skip
        outline_summary = ""
        if outline_items:
            outline_summary = "\n".join([
                f"{idx + 1}. {item.title}: {item.description or ''}"
                for idx, item in enumerate(outline_items)
            ])
        
        # Set vector store temporarily for searching
        original_vector_store = self.chunking_service.vector_store
        self.chunking_service.vector_store = vector_store
        
        try:
            # Get relevant chunks for narrative generation using a broad query
            query = f"{pdf_title} case study user research design process problem solution"
            similar_chunks_results = self.chunking_service.search_similar_chunks(query, top_k=15)
            
            # Prepare context from chunks - clean and filter
            context_parts = []
            for chunk_tuple in similar_chunks_results:
                # Extract chunk from tuple (chunk, score)
                chunk = chunk_tuple[0] if isinstance(chunk_tuple, tuple) else chunk_tuple
                
                # Extract text from Chunk model
                chunk_text = chunk.text if hasattr(chunk, 'text') else str(chunk)
                
                # Remove page numbers, random numbers, and incomplete sentences
                chunk_text = self._clean_chunk_text(chunk_text)
                if chunk_text and len(chunk_text.strip()) > 50:  # Only use substantial chunks
                    context_parts.append(chunk_text)
            
            source_context = "\n\n".join(context_parts[:10])  # Use top 10 chunks
            
            if not source_context or len(source_context.strip()) < 100:
                # Fallback: use chunks directly if search didn't work
                logger.warning("Search didn't return enough context, using chunks directly")
                context_parts = []
                for chunk in chunks[:15]:
                    chunk_text = chunk.text if hasattr(chunk, 'text') else str(chunk)
                    chunk_text = self._clean_chunk_text(chunk_text)
                    if chunk_text and len(chunk_text.strip()) > 50:
                        context_parts.append(chunk_text)
                source_context = "\n\n".join(context_parts[:10])
        finally:
            # Restore original vector store
            self.chunking_service.vector_store = original_vector_store
        
        # Build prompt based on whether we have an outline or not
        if outline_summary:
            outline_section = f"""
OUTLINE SECTIONS:
{outline_summary}
"""
        else:
            outline_section = """
NOTE: Generate the narrative directly from the source material below. Do not rely on a predefined outline structure - let the story emerge naturally from the content.
"""
        
        prompt = f"""You are an expert UX case study writer. Create a compelling, complete narrative for a UX case study based EXCLUSIVELY on the source material provided below.

CASE STUDY TITLE: {pdf_title}
{outline_section}

SOURCE MATERIAL FROM THE ACTUAL CASE STUDY (YOU MUST USE THIS CONTENT):
{source_context}

CRITICAL REQUIREMENTS - READ CAREFULLY:
1. You MUST base your narrative ONLY on the source material provided above
2. DO NOT invent, imagine, or create fictional scenarios (e.g., "busy single parent managing finances")
3. DO NOT use generic examples - extract the ACTUAL user, problem, and context from the source material
4. If the source material mentions "Carnatic music", write about Carnatic music - NOT banking apps or finances
5. If the source material mentions specific research methods, users, or findings, reference those EXACTLY
6. Write a COMPLETE, COHERENT narrative - every sentence must be finished and make sense
7. Follow the exact 5-part storytelling structure below
8. Write in flowing paragraphs, not bullet points or fragments
9. DO NOT include page numbers, random numbers like "4-10", "55-59", or incomplete sentences ending with "...."
10. DO NOT copy text verbatim - synthesize and rewrite in a narrative style
11. Connect each section naturally to create a cohesive story

STRUCTURE YOUR NARRATIVE AS FOLLOWS:

**1. Define the Hero (The User)**
Read the source material carefully to identify:
- Who is the actual user mentioned in the case study?
- What is the actual problem they face (as described in the source material)?
- What is the actual context or domain (e.g., Carnatic music education, not banking)?

Write 2-3 complete paragraphs that describe the REAL user and problem from the source material. Do NOT invent fictional users or scenarios.

**2. Set the Stage**
From the source material, identify:
- What was the actual project scope mentioned?
- What were the actual goals stated?
- What research methods were actually used (as mentioned in source material)?
- What constraints existed?

Write 1-2 complete paragraphs using ONLY information from the source material.

**3. Show the Conflict**
From the source material, identify:
- What actual challenges or obstacles were discovered?
- What unexpected insights came from the actual research?
- What hurdles had to be overcome (as mentioned in source material)?

Write 2-3 complete paragraphs using ONLY challenges and insights from the source material.

**4. The Turning Point**
From the source material, identify:
- What actual design decisions were made?
- What actual breakthrough moments or iterations occurred?
- What actual processes or methods were used?

Write 2-3 complete paragraphs using ONLY design decisions and processes from the source material.

**5. Deliver the Resolution**
From the source material, identify:
- What actual results or outcomes were mentioned?
- What actual impact or metrics were reported?
- What actual conclusions were drawn?

Write 1-2 complete paragraphs using ONLY results and outcomes from the source material.

ABSOLUTE PROHIBITIONS:
- DO NOT invent fictional users, scenarios, or examples
- DO NOT use generic examples like "busy single parent" or "banking app" unless they appear in the source material
- DO NOT include page numbers, ranges like "4-10", "55-59", or any random numbers
- DO NOT leave sentences incomplete or end with "...."
- DO NOT use fragmented phrases or disconnected words
- DO NOT copy chunks verbatim - synthesize and rewrite
- DO NOT include methodology names as standalone items without context
- DO NOT reference domains, apps, or contexts that are NOT in the source material

VALIDATION CHECKLIST (before submitting):
- [ ] Every user, problem, and context mentioned comes from the source material
- [ ] No fictional scenarios or invented examples
- [ ] All research methods mentioned are from the source material
- [ ] All design decisions referenced are from the source material
- [ ] All results/outcomes are from the source material
- [ ] The narrative matches the domain/topic of the case study title

Now write the complete narrative following this structure, using EXCLUSIVELY the source material provided above:"""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert UX case study writer who creates compelling, story-driven narratives based EXCLUSIVELY on provided source material. You NEVER invent fictional users, scenarios, or examples. You extract actual users, problems, research findings, design decisions, and outcomes from the source material and synthesize them into engaging narratives. You write complete, coherent narratives that flow naturally. You never leave sentences incomplete, use fragmented phrases, or include page numbers or random ranges. You are strictly factual and base everything on the provided source material."
                },
                {"role": "user", "content": prompt}
            ]
            
            response = llm_service.generate_chat_completion(
                messages,
                max_tokens=3000,
                temperature=0.7
            )
            
            if response and response.strip():
                narrative = response.strip()
                # Clean the narrative to remove any remaining issues
                narrative = self._clean_narrative(narrative)
                
                # Validate that the narrative is based on actual content
                narrative_lower = narrative.lower()
                source_lower = source_context.lower()
                
                # Check for common hallucination patterns
                hallucination_patterns = [
                    "busy single parent",
                    "manage their finances",
                    "banking app",
                    "manage their money",
                    "financial management"
                ]
                
                # Check if narrative contains hallucinated content
                has_hallucination = any(pattern in narrative_lower for pattern in hallucination_patterns)
                
                # Check if narrative references actual content from source
                # Extract key terms from source (first 500 chars)
                source_key_terms = set(source_lower[:500].split())
                narrative_terms = set(narrative_lower.split())
                overlap = len(source_key_terms.intersection(narrative_terms))
                
                # If narrative has hallucination patterns and low overlap with source, regenerate
                if has_hallucination and overlap < 5:
                    logger.warning(f"Narrative contains hallucinated content. Overlap with source: {overlap}. Regenerating...")
                    # Try once more with stronger emphasis
                    retry_prompt = prompt + "\n\nCRITICAL REMINDER: The examples in the structure above are JUST examples of style, NOT content to copy. You MUST use ONLY the actual content from the source material provided. If the source material is about Carnatic music, write about Carnatic music. If it's about a different domain, use that domain. DO NOT use the example scenarios."
                    retry_messages = [
                        {
                            "role": "system",
                            "content": "You are an expert UX case study writer who creates compelling, story-driven narratives based EXCLUSIVELY on provided source material. You NEVER invent fictional users, scenarios, or examples. You extract actual users, problems, research findings, design decisions, and outcomes from the source material and synthesize them into engaging narratives. You write complete, coherent narratives that flow naturally. You never leave sentences incomplete, use fragmented phrases, or include page numbers or random ranges. You are strictly factual and base everything on the provided source material."
                        },
                        {"role": "user", "content": retry_prompt}
                    ]
                    response = llm_service.generate_chat_completion(
                        retry_messages,
                        max_tokens=3000,
                        temperature=0.5  # Lower temperature for more factual output
                    )
                    if response and response.strip():
                        narrative = response.strip()
                        narrative = self._clean_narrative(narrative)
                
                # Validate that the narrative is complete (has all 5 sections)
                sections = ["Define the Hero", "Set the Stage", "Show the Conflict", "Turning Point", "Resolution"]
                has_structure = any(section.lower() in narrative.lower() for section in sections)
                
                if not has_structure or len(narrative) < 500:
                    logger.warning("Generated narrative may be incomplete, using fallback")
                    return self._generate_fallback_narrative(outline_items, pdf_title, source_context)
                
                return narrative
            else:
                # Fallback to simple structure if LLM fails
                return self._generate_fallback_narrative(outline_items, pdf_title, source_context)
                
        except Exception as e:
            logger.error(f"Error generating narrative plan: {str(e)}")
            # Fallback to simple structure
            return self._generate_fallback_narrative(outline_items, pdf_title, source_context)
    
    def _clean_chunk_text(self, text: str) -> str:
        """Clean chunk text to remove page numbers, random numbers, and incomplete sentences"""
        import re
        # Remove page number patterns like "4-10", "55-59", standalone numbers
        text = re.sub(r'\b\d+-\d+\b', '', text)  # Remove ranges
        text = re.sub(r'\b\d{1,2}\s*=\s*\d+', '', text)  # Remove patterns like "4 = 10"
        # Remove incomplete sentences ending with "...."
        text = re.sub(r'\.{3,}\s*$', '.', text, flags=re.MULTILINE)
        # Remove standalone methodology words without context
        text = re.sub(r'\b(think aloud|heuristic evaluation|interviews|understand|empathise|define|ideate)\b(?=\s|$)', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def _clean_narrative(self, narrative: str) -> str:
        """Clean the generated narrative to remove any issues"""
        import re
        # Remove page number patterns
        narrative = re.sub(r'\b\d+-\d+\b', '', narrative)
        narrative = re.sub(r'\b\d{1,2}\s*=\s*\d+', '', narrative)
        # Fix incomplete sentences ending with "...."
        narrative = re.sub(r'\.{3,}\s*', '. ', narrative)
        # Remove sentences that are just methodology names
        lines = narrative.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and len(line) > 20:  # Only keep substantial lines
                cleaned_lines.append(line)
        return '\n\n'.join(cleaned_lines)
    
    def _generate_fallback_narrative(self, outline_items: List, pdf_title: str, source_context: str = "") -> str:
        """Fallback narrative generation if LLM fails"""
        narrative = f"""Case Study: {pdf_title}

**1. Define the Hero (The User)**

Every compelling UX case study begins with the user. In this project, we focused on understanding who our users are and what challenges they face. The hero of our story is not the designer, but the people who will use and benefit from our design solution.

Based on our research, we identified key user needs and pain points that drove our design decisions. Understanding their context, motivations, and frustrations was essential to creating a solution that truly serves them.

**2. Set the Stage**

This project was undertaken with specific goals and constraints in mind. We worked within defined parameters including timeline, resources, and stakeholder requirements. Understanding these constraints helped shape our approach and ensured we delivered a solution that was both innovative and feasible.

The project scope encompassed multiple phases of research, design, and testing, each building upon the previous to create a comprehensive solution.

**3. Show the Conflict**

During our research phase, we discovered several unexpected challenges and obstacles. These findings revealed gaps between initial assumptions and actual user needs. Some insights challenged our preconceptions and required us to rethink our approach.

These conflicts and challenges became opportunities to demonstrate our problem-solving abilities and create a more robust solution.

**4. The Turning Point**

Through iterative design and testing, we identified key breakthrough moments that transformed our understanding of the problem. These "aha" moments led to design decisions that fundamentally improved the user experience.

By focusing on these critical insights, we were able to create solutions that addressed core user needs in innovative ways.

**5. Deliver the Resolution**

The final solution delivered measurable impact on the user experience. Through our design process, we achieved outcomes that directly addressed the challenges identified at the beginning of the project.

The results demonstrate how thoughtful design can transform user experiences and create meaningful value.

**Outline Sections:**
"""
        for idx, item in enumerate(outline_items):
            narrative += f"\n{idx + 1}. {item.title}\n"
            if item.description:
                narrative += f"   {item.description}\n"
        
        return narrative
    
    def regenerate_content_with_focus(
        self, 
        request: RegenerateContentRequest
    ) -> OutlineContentResponse:
        """Regenerate content with narrative and tone"""
        start_time = time.time()
        
        try:
            logger.info(f"Regenerating content with narrative: {request.narrative[:100] if request.narrative else 'None'}..., tone: {request.tone}")
            
            # Load or recreate vector store
            pdf_name = Path(request.pdf_path).stem
            vector_store_path = self.vector_store_dir / pdf_name
            
            if vector_store_path.with_suffix(".index").exists():
                # Load existing vector store
                vector_store = self.chunking_service.load_vector_store(str(vector_store_path))
            else:
                # Recreate vector store
                pdf_structure = self.pdf_parser.extract_text_and_structure(request.pdf_path)
                chunk_size = min(request.chunk_size, 400)
                overlap = max(request.overlap, 100)
                chunks = self.chunking_service.chunk_text(pdf_structure, chunk_size, overlap)
                if len(chunks) > request.max_chunks:
                    chunks = chunks[:request.max_chunks]
                vector_store = self.chunking_service.create_embeddings(chunks)
                self.chunking_service.save_vector_store(str(vector_store_path))
            
            # Regenerate outline from the edited narrative (if narrative provided)
            # This ensures the outline structure matches the narrative
            if request.narrative:
                outline_items = self.outline_generator.generate_outline_from_narrative(
                    request.narrative,
                    Path(request.pdf_path).stem
                )
                logger.info(f"Regenerated outline from narrative: {len(outline_items)} items")
            else:
                outline_items = request.outline
            
            # Set narrative and tone in RAG system
            self.rag_system.chunking_service = self.chunking_service
            self.rag_system.narrative = request.narrative
            self.rag_system.tone = request.tone
            self.rag_system.all_seen_bullets = []  # Reset for regeneration
            
            # Regenerate bullets with new parameters using the regenerated outline
            bullets_data = self.rag_system.generate_comprehensive_bullets(
                outline_items, 
                vector_store,
                top_k=8,
                max_bullets_per_item=5
            )
            
            # Get PDF title
            pdf_structure = self.pdf_parser.extract_text_and_structure(request.pdf_path)
            
            processing_time = time.time() - start_time
            
            return OutlineContentResponse(
                success=True,
                message="Content regenerated successfully",
                pdf_title=pdf_structure.title,
                outline=outline_items,  # Use regenerated outline
                narrative_plan=request.narrative or "",
                bullets_data=bullets_data,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error regenerating content: {str(e)}", exc_info=True)
            return OutlineContentResponse(
                success=False,
                message=f"Error: {str(e)}",
                pdf_title="",
                outline=request.outline,
                narrative_plan=request.narrative or "",
                bullets_data={},
                processing_time=time.time() - start_time
            )
    
    def generate_slides_from_outline(
        self,
        pdf_path: str,
        outline: List,
        bullets_data: Dict[str, List],
        pdf_metadata: Optional[Dict[str, Any]] = None
    ) -> PDFProcessingResponse:
        """Generate slides from edited outline and content"""
        start_time = time.time()
        
        try:
            logger.info(f"Generating slides from outline: {len(outline)} items, {len(bullets_data)} sections with bullets")
            
            if not outline or len(outline) == 0:
                raise ValueError("Outline is empty")
            
            pdf_structure = self.pdf_parser.extract_text_and_structure(pdf_path)
            if pdf_metadata is None:
                pdf_metadata = self.pdf_parser.extract_metadata(pdf_path)
            
            # Generate slide deck
            slide_deck = self.slide_generator.generate_slide_deck(
                pdf_structure.title,
                outline,
                bullets_data,
                pdf_path,
                pdf_metadata
            )
            
            if not slide_deck:
                raise ValueError("Failed to generate slide deck")
            
            # Save outputs
            try:
                self._save_outputs(slide_deck, None, pdf_path)
            except Exception as save_error:
                logger.warning(f"Error saving outputs (continuing anyway): {str(save_error)}")
            
            processing_time = time.time() - start_time
            
            return PDFProcessingResponse(
                success=True,
                message="Slides generated successfully",
                slide_deck=slide_deck,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error generating slides: {str(e)}", exc_info=True)
            return PDFProcessingResponse(
                success=False,
                message=f"Error: {str(e)}",
                processing_time=time.time() - start_time
            )