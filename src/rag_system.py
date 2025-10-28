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
        top_k: int = 6,
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
        
        # Let the LLM determine how many bullets based on content
        bullets = self._generate_bullets_with_llm(
            outline_item, 
            context, 
            max_bullets  # This is now a maximum, not a fixed number
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
                    "content": "You are an expert at creating compelling slide deck content. Your task is to transform source material into crisp, impactful bullet points that work perfectly for presentations. Focus on clarity, impact, and delivering the key message effectively."
                },
                {"role": "user", "content": prompt}
            ]
            
            bullets_text = self.llm_service.generate_chat_completion(
                messages, 
                max_tokens=1000, 
                temperature=0.5
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
Create compelling bullet points for a design presentation slide about "{outline_item.title}".

Source Material:
{context}

Instructions:
1. Create 3-5 concise, impactful bullet points that capture the key insights
2. Each bullet should be 1 sentence maximum - clear and punchy
3. Focus on the most important findings, decisions, or insights from the design process
4. Use professional language suitable for a design presentation
5. Highlight key user insights, design decisions, or technical details
6. Make each bullet point informative and engaging
7. Prioritize actionable insights and concrete findings
8. Each bullet should stand alone and be easily readable
9. Focus on what matters most for understanding the design process

Create bullet points that effectively communicate the design story and key insights.

Format as a simple list with bullet points using "-" or "•" symbols.
Do not include any introductory text, explanations, or meta-commentary.
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
                if bullet and self._is_valid_bullet(bullet):
                    bullets.append(bullet)
            elif line and not line.startswith('Title:') and not line.startswith('Description:'):
                # Sometimes bullets don't have symbols
                if len(line) > 10 and self._is_valid_bullet(line):  # Avoid very short lines
                    bullets.append(line)
        
        return bullets
    
    def _is_valid_bullet(self, bullet: str) -> bool:
        """Check if a bullet point is valid (not generic placeholder text)"""
        # Generic phrases to filter out
        generic_phrases = [
            "here are the",
            "key information about",
            "important points",
            "this section covers",
            "main topics include",
            "key concepts",
            "the following",
            "based on the",
            "as mentioned",
            "as discussed",
            "in summary",
            "to summarize",
            "bullet points for",
            "presentation slide",
            "concise bullet points"
        ]
        
        bullet_lower = bullet.lower()
        
        # Check if it's too generic
        for phrase in generic_phrases:
            if phrase in bullet_lower:
                return False
        
        # Check if it's too short or too long
        if len(bullet) < 15 or len(bullet) > 300:
            return False
        
        # Check if it contains specific content indicators
        specific_indicators = [
            "specific", "example", "data", "result", "finding", "study", "research",
            "analysis", "method", "approach", "technique", "process", "system",
            "application", "implementation", "development", "design", "model",
            "framework", "algorithm", "protocol", "standard", "guideline",
            "user", "task", "interface", "feature", "function", "clicking", "checkbox",
            "completed", "focused", "mapping", "frictionless", "chiming", "accomplishment",
            "pending", "notes", "field", "status", "list", "create", "type", "enter",
            "swipe", "mobile", "desktop", "wireframe", "testing", "iteration"
        ]
        
        # If it contains specific indicators, it's likely good content
        if any(indicator in bullet_lower for indicator in specific_indicators):
            return True
        
        # If it's a reasonable length and doesn't contain generic phrases, accept it
        return True
    
    def generate_comprehensive_bullets(
        self, 
        outline_items: List[OutlineItem], 
        vector_store,
        top_k: int = 6,
        max_bullets_per_item: int = 5
    ) -> Dict[str, List[BulletPoint]]:
        """Generate bullets for all outline items based on content availability"""
        
        results = {}
        
        for outline_item in outline_items:
            logger.info(f"Generating bullets for: {outline_item.title}")
            
            # Let the system determine how many bullets based on content
            bullets = self.generate_bullets_for_outline_item(
                outline_item,
                vector_store,
                top_k,
                max_bullets_per_item  # This is now a maximum, not a fixed number
            )
            
            results[outline_item.title] = bullets
            logger.info(f"Generated {len(bullets)} bullets for {outline_item.title}")
        
        return results