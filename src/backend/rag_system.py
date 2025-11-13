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
        self.narrative = None
        self.tone = None
    
    def generate_bullets_for_outline_item(
        self, 
        outline_item: OutlineItem, 
        vector_store, 
        top_k: int = 8,
        max_bullets: int = 5
    ) -> List[BulletPoint]:
        """Generate bullet points for an outline item using RAG, following the narrative"""
        
        # Build query based on narrative themes, not just outline title
        # This ensures we search for content that aligns with the narrative
        query_parts = [outline_item.title, outline_item.description]
        
        # If narrative exists, extract relevant themes for this section
        if self.narrative:
            # Try to match outline item to narrative sections
            narrative_lower = self.narrative.lower()
            outline_lower = outline_item.title.lower()
            
            # Add narrative context to query
            if any(word in outline_lower for word in ['problem', 'overview', 'hero', 'user']):
                query_parts.append("user problem challenge")
            elif any(word in outline_lower for word in ['research', 'stage', 'context']):
                query_parts.append("project scope constraints context")
            elif any(word in outline_lower for word in ['insight', 'conflict', 'challenge']):
                query_parts.append("challenges obstacles research findings")
            elif any(word in outline_lower for word in ['direction', 'solution', 'design', 'turning', 'wireframe']):
                query_parts.append("design decisions solution breakthrough")
            elif any(word in outline_lower for word in ['test', 'evaluation', 'result', 'outcome', 'next']):
                query_parts.append("results impact outcomes testing")
        
        query = " ".join(query_parts)
        similar_chunks = self.chunking_service.search_similar_chunks(query, top_k)
        
        if not similar_chunks:
            logger.warning(f"No chunks found for: {outline_item.title}")
            return []
        
        # Sort chunks chronologically (by page_number, then chunk_index)
        similar_chunks = sorted(similar_chunks, key=lambda x: (
            x[0].page_number if hasattr(x[0], 'page_number') else 0,
            x[0].chunk_index if hasattr(x[0], 'chunk_index') else 0
        ))
        
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
        """Prepare context from chunks, maintaining chronological order"""
        context_parts = []
        
        # Chunks are already sorted chronologically, so process in order
        for i, (chunk, score) in enumerate(similar_chunks[:8], 1):  # Use top 8 for better context
            section = chunk.metadata.get('section_title', 'Unknown')
            page = chunk.page_number
            chunk_index = chunk.chunk_index if hasattr(chunk, 'chunk_index') else i
            
            # Clean chunk text
            chunk_text = self._clean_chunk_for_context(chunk.text)
            
            if chunk_text and len(chunk_text.strip()) > 30:
                # Include order information to help LLM maintain chronology
                context_part = f"[Source {i}, Page {page}, Order {chunk_index}] {section}:\n{chunk_text}\n---\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _clean_chunk_for_context(self, text: str) -> str:
        """Clean chunk text for context preparation"""
        import re
        # Remove page number patterns
        text = re.sub(r'\b\d+-\d+\b', '', text)
        text = re.sub(r'\b\d{1,2}\s*=\s*\d+', '', text)
        # Remove incomplete sentences ending with "...."
        text = re.sub(r'\.{3,}\s*$', '.', text, flags=re.MULTILINE)
        # Remove standalone methodology words
        text = re.sub(r'\b(think aloud|heuristic evaluation|interviews|understand|empathise|define|ideate|conceptualise)\b(?=\s|$)', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def _generate_bullets_with_llm(
        self, 
        outline_item: OutlineItem, 
        context: str, 
        max_bullets: int
    ) -> str:
        """Generate bullets using LLM"""
        
        # Build narrative and tone instructions
        narrative_instruction = ""
        if self.narrative:
            narrative_instruction = f"""
CRITICAL: CASE STUDY NARRATIVE (MUST FOLLOW STRICTLY):
{self.narrative}

NARRATIVE REQUIREMENTS:
- The narrative above defines the EXACT story structure and flow for this case study
- You MUST align your bullet points with the narrative's structure and themes
- The narrative tells a story focused on the user's journey (the hero)
- Each bullet point MUST support and reflect the narrative's themes:
  * The user's problem and journey (hero)
  * The context and constraints (setting the stage)
  * The challenges and obstacles (conflict)
  * The design decisions and breakthroughs (turning point)
  * The impact and results (resolution)
- Make bullet points tell part of the story as defined in the narrative, not just list facts
- Connect bullet points to the overall narrative arc and ensure they flow chronologically
- If the narrative mentions specific themes, problems, or solutions, your bullets MUST reflect those
- The narrative is the PRIMARY guide - source material should be used to support the narrative, not replace it
"""
        
        tone_instruction = ""
        if self.tone:
            tone_instruction = f"\nTONE: {self.tone}\n- Write in a {self.tone} tone\n- Adjust language and style accordingly\n"
        
        prompt = f"""You are writing content for a slide in a UX case study presentation. The slide title is "{outline_item.title}".

CASE STUDY NARRATIVE (THIS IS YOUR PRIMARY GUIDE):
{self.narrative if self.narrative else "No narrative provided"}

SOURCE MATERIAL (ordered chronologically - use to support the narrative):
{context}

YOUR TASK:
Write {max_bullets} bullet points that tell the case study story as defined in the narrative above. The narrative defines the EXACT story structure, themes, and flow you must follow.

CRITICAL REQUIREMENTS:
1. The narrative is your PRIMARY guide - align every bullet with the narrative's story structure and themes
2. Use the source material to find specific details that support the narrative's story, not to replace it
3. Write complete, finished sentences - never leave sentences incomplete
4. Each bullet should be 20-50 words (can be longer if needed for clarity)
5. Focus on concrete details, user insights, or design decisions that support the narrative's story
6. Avoid generic statements - be specific and story-driven as the narrative is
7. Each bullet must provide unique information - avoid repeating concepts
8. Ensure bullets follow chronological order (source material is already ordered)
9. Write in the same engaging, story-driven style as the narrative

ABSOLUTE PROHIBITIONS:
- DO NOT include meta-commentary like "Based on the narrative", "I've extracted", "Here are", etc.
- DO NOT reference the narrative or your process - just write the content
- DO NOT leave sentences incomplete or end with "...."
- DO NOT repeat concepts already covered in other bullets
- DO NOT use the slide title as a template - use the narrative structure instead

{tone_instruction if self.tone else ""}

Output ONLY the bullet points, one per line, starting with "- ". No explanations, no meta-text, just the content.
"""
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You are an expert at creating presentation slides that tell compelling stories. You strictly follow the provided narrative structure and ensure content flows chronologically. You extract specific, concrete information from source material and present it in a way that supports the narrative's story arc. You NEVER include meta-commentary, explanations, or references to your process. You ONLY write the actual content for the slides - complete, finished sentences that tell the story."
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
            
            # Skip meta-text and incomplete sentences
            skip_phrases = [
                'bullet point', 'slide', 'here are', 'following', 
                'based on', 'i\'ve extracted', 'i have extracted',
                'provided case study', 'narrative', 'source material',
                'according to', 'as mentioned in', 'as discussed in',
                'the above', 'the following', 'these insights'
            ]
            line_lower = line.lower()
            if any(phrase in line_lower[:50] for phrase in skip_phrases):
                continue
            
            # Skip incomplete sentences ending with "...."
            if line.strip().endswith('....') or line.strip().endswith('...'):
                continue
            
            # Skip sentences that are too short or incomplete
            if len(line.strip()) < 20:
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
            
            # Skip incomplete sentences
            if bullet.strip().endswith('....') or bullet.strip().endswith('...'):
                continue
            
            # Check if too similar to already seen bullets
            is_duplicate = False
            for seen in self.all_seen_bullets:
                similarity = SequenceMatcher(None, bullet_lower, seen).ratio()
                if similarity > 0.70:  # 70% similar (more aggressive)
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # Check if too similar to bullets in current list
            is_duplicate_local = False
            for existing in filtered:
                similarity = SequenceMatcher(None, bullet_lower, existing.lower()).ratio()
                if similarity > 0.70:
                    is_duplicate_local = True
                    break
            
            if is_duplicate_local:
                continue
            
            # Check for concept repetition (same key concepts)
            if self._has_repeated_concept(bullet, filtered):
                continue
            
            # Check quality
            if self._is_good_bullet(bullet):
                filtered.append(bullet)
        
        return filtered
    
    def _has_repeated_concept(self, bullet: str, existing_bullets: List[str]) -> bool:
        """Check if bullet repeats the same concept as existing bullets"""
        bullet_lower = bullet.lower()
        
        # Extract key phrases (3-4 word phrases)
        bullet_words = bullet_lower.split()
        bullet_phrases = []
        for i in range(len(bullet_words) - 2):
            phrase = ' '.join(bullet_words[i:i+3])
            if len(phrase) > 10:  # Only meaningful phrases
                bullet_phrases.append(phrase)
        
        # Check against existing bullets
        for existing in existing_bullets:
            existing_lower = existing.lower()
            # Count overlapping phrases
            overlap_count = sum(1 for phrase in bullet_phrases if phrase in existing_lower)
            if overlap_count >= 2:  # If 2+ key phrases overlap, likely same concept
                return True
        
        return False
    
    def _is_good_bullet(self, bullet: str) -> bool:
        """Check if bullet is good quality"""
        
        bullet_lower = bullet.lower()
        
        # Reject generic phrases and meta-text
        bad_phrases = [
            'key information', 'main points', 'this section', 
            'the following', 'as mentioned', 'provides information',
            'based on the', 'i\'ve extracted', 'i have extracted',
            'according to the', 'as discussed', 'the above',
            'case study narrative', 'source material', 'provided narrative',
            'based on the provided', 'extracted insights', 'following insights'
        ]
        
        for phrase in bad_phrases:
            if phrase in bullet_lower:
                return False
        
        # Reject incomplete sentences
        if bullet.strip().endswith('....') or bullet.strip().endswith('...'):
            return False
        
        # Reject very short bullets
        if len(bullet.strip()) < 20:
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