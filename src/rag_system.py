from typing import List, Dict, Any, Tuple, Set
import logging
import re
from difflib import SequenceMatcher

from .models import OutlineItem, BulletPoint, Chunk
from .chunking_embedding import ChunkingEmbeddingService
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self):
        self.llm_service = get_llm_service()
        self.chunking_service = ChunkingEmbeddingService()
        self.all_seen_bullets = []  # Track all bullets to check for duplicates
    
    def generate_bullets_for_outline_item(
        self, 
        outline_item: OutlineItem, 
        vector_store, 
        top_k: int = 8,
        max_bullets: int = 5
    ) -> List[BulletPoint]:
        """Generate bullet points for an outline item using RAG"""
        
        # Search for relevant chunks
        extra_query = ""
        if 'problem' in (outline_item.title or '').lower():
            extra_query = " context background understand why issue"
        query = f"{outline_item.title} {outline_item.description}{extra_query}"
        similar_chunks = self.chunking_service.search_similar_chunks(query, top_k)
        
        if not similar_chunks:
            logger.warning(f"No chunks found for: {outline_item.title}")
            return []
        
        # Prepare context
        context = self._prepare_context(similar_chunks)
        
        # Generate bullets with LLM
        bullets_text = self._generate_bullets_with_llm(
            outline_item, 
            context, 
            max_bullets
        )
        
        # Parse and clean bullets
        bullets = self._parse_bullets(bullets_text)
        
        # Remove duplicates and low quality
        bullets = self._filter_bullets(bullets)
        
        # Suppress repeated phrases and near-duplicates more aggressively
        bullets = self._deduplicate_phrases(bullets)
        
        # Limit to max
        bullets = bullets[:max_bullets]
        
        # Add provenance
        page_numbers = sorted(list(set([chunk.page_number for chunk, _ in similar_chunks])))
        provenance_pages = [f"Page {page}" for page in page_numbers]
        
        bullets_with_provenance = []
        for bullet_text in bullets:
            bullet_with_provenance = BulletPoint(
                text=bullet_text,
                provenance=provenance_pages,
                confidence=0.85
            )
            bullets_with_provenance.append(bullet_with_provenance)
            self.all_seen_bullets.append(bullet_text.lower())
        
        logger.info(f"  Generated {len(bullets_with_provenance)} bullets for: {outline_item.title}")
        return bullets_with_provenance
    
    def _prepare_context(self, similar_chunks: List[Tuple[Chunk, float]]) -> str:
        """Prepare context from chunks"""
        context_parts = []
        
        for i, (chunk, score) in enumerate(similar_chunks[:5], 1):  # Use top 5
            section = chunk.metadata.get('section_title', 'Unknown')
            page = chunk.page_number
            
            context_part = f"[Source {i}] {section} (Page {page}):\n{chunk.text}\n---\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _generate_bullets_with_llm(
        self, 
        outline_item: OutlineItem, 
        context: str, 
        max_bullets: int
    ) -> str:
        """Generate bullets using LLM"""
        
        prompt = f"""Create {max_bullets} bullet points for a slide titled "{outline_item.title}".

SOURCE MATERIAL:
{context}

INSTRUCTIONS:
1. Extract 3-5 specific insights from the source material
2. Each bullet should be 20-50 words (can be longer if needed for clarity)
3. Focus on concrete details, user insights, or design decisions
4. Avoid generic statements
5. Each bullet must provide unique information
6. Use clear, professional language
7. Be comprehensive - include sufficient detail to convey the full meaning

Format each bullet on a new line starting with "- "
"""
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You are an expert at creating presentation slides. Extract specific, concrete information and present it clearly."
                },
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_service.generate_chat_completion(
                messages, 
                max_tokens=1500, 
                temperature=0.5
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating bullets: {str(e)}")
            return ""
    
    def _parse_bullets(self, response_text: str) -> List[str]:
        """Parse bullets from LLM response"""
        lines = response_text.strip().split('\n')
        bullets = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # Remove bullet symbols
            for symbol in ['-', '•', '*', '○', '1.', '2.', '3.', '4.', '5.']:
                if line.startswith(symbol):
                    line = line[len(symbol):].strip()
                    break
            
            # Skip headers or instructions
            if ':' in line[:20] or len(line) < 15:
                continue
            
            # Skip meta-text
            skip_words = ['bullet point', 'slide', 'here are', 'following']
            if any(word in line.lower()[:30] for word in skip_words):
                continue
            
            if len(line) > 15 and len(line) < 300:
                bullets.append(line)
        
        return bullets
    
    def _deduplicate_phrases(self, bullets: List[str]) -> List[str]:
        """Remove bullets that repeat common subphrases; keep the first occurrence."""
        if not bullets:
            return bullets
        phrases = [
            'pen and paper', 'current system', 'as mentioned', 'as discussed'
        ]
        seen_keys: Set[str] = set()
        result: List[str] = []
        for b in bullets:
            b_norm = ' '.join(b.lower().split())
            key = None
            for p in phrases:
                if p in b_norm:
                    key = p
                    break
            if key:
                if key in seen_keys:
                    continue
                seen_keys.add(key)
            # Do not trim sentences; preserve full bullet text
            result.append(b.strip())
        return result

    def _filter_bullets(self, bullets: List[str]) -> List[str]:
        """Filter out duplicates and low quality bullets"""
        filtered = []
        
        for bullet in bullets:
            bullet_lower = bullet.lower()
            
            # Check if too similar to already seen bullets
            is_duplicate = False
            for seen in self.all_seen_bullets:
                similarity = SequenceMatcher(None, bullet_lower, seen).ratio()
                if similarity > 0.75:  # 75% similar
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # Check if too similar to bullets in current list
            is_duplicate_local = False
            for existing in filtered:
                similarity = SequenceMatcher(None, bullet_lower, existing.lower()).ratio()
                if similarity > 0.75:
                    is_duplicate_local = True
                    break
            
            if is_duplicate_local:
                continue
            
            # Check quality
            if self._is_good_bullet(bullet):
                filtered.append(bullet)
        
        return filtered
    
    def _is_good_bullet(self, bullet: str) -> bool:
        """Check if bullet is good quality"""
        
        bullet_lower = bullet.lower()
        
        # Reject generic phrases
        bad_phrases = [
            'key information', 'main points', 'this section', 
            'the following', 'as mentioned', 'provides information'
        ]
        
        for phrase in bad_phrases:
            if phrase in bullet_lower:
                return False
        
        # Length check
        if len(bullet) < 20 or len(bullet) > 600:
            return False
        
        # Should have some specific content
        good_words = [
            'user', 'task', 'design', 'application', 'feature',
            'research', 'problem', 'solution', 'interface', 'experience',
            'specific', 'focused', 'simple', 'easy', 'quick'
        ]
        
        has_content = any(word in bullet_lower for word in good_words)
        
        return has_content
    
    def generate_comprehensive_bullets(
        self, 
        outline_items: List[OutlineItem], 
        vector_store,
        top_k: int = 8,
        max_bullets_per_item: int = 7
    ) -> Dict[str, List[BulletPoint]]:
        """Generate bullets for all outline items"""
        
        # Reset for new deck
        self.all_seen_bullets = []
        
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