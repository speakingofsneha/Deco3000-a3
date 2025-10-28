from typing import List, Dict, Any, Tuple
import logging

from .models import OutlineItem, BulletPoint, Chunk
from .chunking_embedding import ChunkingEmbeddingService
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self):
        self.llm_service = get_llm_service()
        self.chunking_service = ChunkingEmbeddingService()
    
    def generate_bullets_for_outline_item(
        self, 
        outline_item: OutlineItem, 
        vector_store, 
        top_k: int = 5,
        max_bullets: int = 5
    ) -> List[BulletPoint]:
        """Generate bullet points for an outline item using RAG"""
        
        # Search for relevant chunks
        query = f"{outline_item.title} {outline_item.description}"
        similar_chunks = self.chunking_service.search_similar_chunks(query, top_k)
        
        if not similar_chunks:
            logger.warning(f"No similar chunks found for outline item: {outline_item.title}")
            return []
        
        # Prepare context from retrieved chunks
        context = self._prepare_context(similar_chunks)
        chunk_ids = [chunk.id for chunk, _ in similar_chunks]
        
        # Generate bullet points using LLM
        bullets = self._generate_bullets_with_llm(
            outline_item, 
            context, 
            max_bullets
        )
        
        # Add provenance information
        bullets_with_provenance = []
        for bullet in bullets:
            bullet_with_provenance = BulletPoint(
                text=bullet,
                provenance=chunk_ids,
                confidence=0.8  # Default confidence
            )
            bullets_with_provenance.append(bullet_with_provenance)
        
        return bullets_with_provenance
    
    def _prepare_context(self, similar_chunks: List[Tuple[Chunk, float]]) -> str:
        """Prepare context from retrieved chunks"""
        context_parts = []
        
        for chunk, score in similar_chunks:
            context_part = f"Source: {chunk.metadata.get('section_title', 'Unknown')} (Page {chunk.page_number})\n"
            context_part += f"Content: {chunk.text}\n"
            context_part += f"Relevance Score: {score:.3f}\n"
            context_part += "---\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _generate_bullets_with_llm(
        self, 
        outline_item: OutlineItem, 
        context: str, 
        max_bullets: int
    ) -> List[str]:
        """Generate bullet points using LLM"""
        
        prompt = self._create_bullet_generation_prompt(
            outline_item, 
            context, 
            max_bullets
        )
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You are an expert at creating concise, informative bullet points for presentations. Focus on key facts, findings, and important information."
                },
                {"role": "user", "content": prompt}
            ]
            
            bullets_text = self.llm_service.generate_chat_completion(
                messages, 
                max_tokens=1000, 
                temperature=0.3
            )
            
            bullets = self._parse_bullets_response(bullets_text)
            
            return bullets[:max_bullets]  # Limit to max_bullets
            
        except Exception as e:
            logger.error(f"Error generating bullets: {str(e)}")
            return [f"Key information about {outline_item.title.lower()}"]
    
    def _create_bullet_generation_prompt(
        self, 
        outline_item: OutlineItem, 
        context: str, 
        max_bullets: int
    ) -> str:
        """Create prompt for bullet point generation"""
        return f"""
Based on the following context, create {max_bullets} concise bullet points for a presentation slide about:

Title: {outline_item.title}
Description: {outline_item.description}

Context:
{context}

Requirements:
1. Each bullet point should be 1-2 sentences maximum
2. Focus on the most important and relevant information
3. Use clear, professional language suitable for a presentation
4. Avoid repetition
5. Include specific facts, numbers, or key findings when available
6. Make each bullet point actionable or informative

Format as a simple list with bullet points using "-" or "•" symbols.
Do not include any additional text or explanations.
"""
    
    def _parse_bullets_response(self, response_text: str) -> List[str]:
        """Parse bullet points from LLM response"""
        lines = response_text.split('\n')
        bullets = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                # Remove bullet symbol and clean up
                bullet = line[1:].strip()
                if bullet:
                    bullets.append(bullet)
            elif line and not line.startswith('Title:') and not line.startswith('Description:'):
                # Sometimes bullets don't have symbols
                if len(line) > 10:  # Avoid very short lines
                    bullets.append(line)
        
        return bullets
    
    def generate_comprehensive_bullets(
        self, 
        outline_items: List[OutlineItem], 
        vector_store,
        top_k: int = 5,
        max_bullets_per_item: int = 5
    ) -> Dict[str, List[BulletPoint]]:
        """Generate bullets for all outline items"""
        
        results = {}
        
        for outline_item in outline_items:
            logger.info(f"Generating bullets for: {outline_item.title}")
            
            bullets = self.generate_bullets_for_outline_item(
                outline_item,
                vector_store,
                top_k,
                max_bullets_per_item
            )
            
            results[outline_item.title] = bullets
        
        return results