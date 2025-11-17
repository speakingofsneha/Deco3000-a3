from typing import List, Dict, Any, Tuple, Set
import logging
import re
from difflib import SequenceMatcher

from .models import OutlineItem, BulletPoint, Chunk
from .chunking_embedding import ChunkingEmbeddingService
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)

# rag system wraps retrieval-augmented generation for per-section slide content
class RAGSystem:
    def __init__(self):
        self.llm_service = get_llm_service()
        self.chunking_service = ChunkingEmbeddingService()
        self.all_seen_bullets = []  # Track all bullets to check for duplicates
        self.narrative = None
        self.tone = None
        self._is_research_section = False  # Track if current section is research
    
    def generate_bullets_for_outline_item(
        self, 
        outline_item: OutlineItem, 
        vector_store, 
        top_k: int = 20,
        max_bullets: int = 15
    ) -> List[BulletPoint]:
        """Generate bullet points for an outline item using RAG, following the narrative"""
        
        # reset flags so each section can decide whether it is research/process/etc
        # Reset research section flag for this item
        self._is_research_section = False
        
        # Build query based on outline description and title to find relevant chunks
        # The outline description tells us what content belongs in this section - prioritize it heavily
        query_parts = []
        if outline_item.description:
            # Add description multiple times to increase its weight in semantic search
            query_parts.append(outline_item.description)
            query_parts.append(outline_item.description)  # Double weight for description
        query_parts.append(outline_item.title)
        
        # If narrative exists, extract relevant themes for this section and identify section type
        section_type = None
        if self.narrative:
            # Try to match outline item to narrative sections
            narrative_lower = self.narrative.lower()
            outline_lower = outline_item.title.lower()
            description_lower = (outline_item.description or "").lower()
            
            # Identify section type based on narrative structure
            if any(word in outline_lower or word in description_lower for word in ['research', 'themes', 'findings', 'early findings', 'interview', 'survey', 'observation', 'ethnography']):
                section_type = "research"
                self._is_research_section = True
                query_parts.append("research methods findings themes insights")
            elif any(word in outline_lower or word in description_lower for word in ['problem', 'overview', 'user', "what's the problem", 'challenge']):
                section_type = "problem"
                query_parts.append("user problem challenge")
            elif any(word in outline_lower or word in description_lower for word in ['context', 'setting', 'assignment', 'brief', 'scope']):
                section_type = "context"
                query_parts.append("project scope constraints context assignment")
            elif any(word in outline_lower or word in description_lower for word in ['ideation', 'brainstorm', 'concept', 'direction', 'ideation methods']):
                section_type = "ideation"
                query_parts.append("ideation concepts brainstorming directions sketches early concepts")
            elif any(word in outline_lower or word in description_lower for word in ['wireframe', 'wireframes', 'wireframing', 'early designs', 'low-fidelity']):
                section_type = "wireframes"
                query_parts.append("wireframes wireframe early designs low-fidelity sketches interactions flows")
            elif any(word in outline_lower or word in description_lower for word in ['mockup', 'mockups', 'visual design', 'color palette', 'typography', 'spacing', 'layout']):
                section_type = "mockups"
                query_parts.append("mockups mockup visual design color palette typography spacing layout design elements")
            elif any(word in outline_lower or word in description_lower for word in ['design process', 'iterations', 'iterative', 'evolution', 'rounds']):
                section_type = "iterations"
                query_parts.append("design process iterations iterative evolution rounds changes modifications")
            elif any(word in outline_lower or word in description_lower for word in ['prototype', 'prototyping', 'interactive', 'clickable']):
                section_type = "prototyping"
                query_parts.append("prototyping prototype tools interface decisions interactive clickable")
            elif any(word in outline_lower or word in description_lower for word in ['design', 'solution']):
                section_type = "design"
                query_parts.append("design decisions solution")
            elif any(word in outline_lower or word in description_lower for word in ['test', 'evaluation', 'feedback', 'testing', 'usability testing', 'test rounds']):
                section_type = "testing"
                query_parts.append("testing evaluation feedback usability test rounds participants observations")
            elif any(word in outline_lower or word in description_lower for word in ['outcome', 'final', 'result', 'impact']):
                section_type = "outcome"
                query_parts.append("results impact outcomes final solution")
            else:
                section_type = "general"
        
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
            max_bullets,
            section_type
        )
        
        # Parse and clean bullets
        bullets = self._parse_bullets(bullets_text)
        
        # Remove duplicates and low quality
        bullets = self._filter_bullets(bullets)
        
        # Suppress repeated phrases and near-duplicates more aggressively
        bullets = self._deduplicate_phrases(bullets)
        
        # Inject outline description as anchor if provided
        bullets = self._merge_outline_description(outline_item.description, bullets, max_bullets)
        
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
        # Use more chunks to provide comprehensive context
        for i, (chunk, score) in enumerate(similar_chunks[:14], 1):  # use top 14 for context to reduce token count
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
        max_bullets: int,
        section_type: str = None
    ) -> str:
        """Generate bullets using LLM"""
        
        # build guardrails for this specific section before calling the model
        # Build narrative and tone instructions
        narrative_instruction = ""
        section_restrictions = ""
        
        if self.narrative:
            # Identify which narrative section this outline item corresponds to
            narrative_lower = self.narrative.lower()
            outline_lower = outline_item.title.lower()
            description_lower = (outline_item.description or "").lower()
            
            # Determine if this is a research section
            is_research_section = (
                section_type == "research" or
                any(word in outline_lower or word in description_lower for word in [
                    'research', 'themes', 'findings', 'early findings', 'interview', 
                    'survey', 'observation', 'ethnography', 'user research'
                ])
            )
            
            # Add section-specific restrictions
            if is_research_section:
                section_restrictions = """
SECTION-SPECIFIC REQUIREMENTS (CRITICAL):
- This is a RESEARCH section. ONLY include content about research methods, research findings, research themes, and research insights.
- Research-specific content (like "online ethnography", "user generated content", specific research methods, participant counts, research findings) should ONLY appear in research sections.
- DO NOT include research methods or findings in non-research sections.
"""
            else:
                section_restrictions = f"""
SECTION-SPECIFIC REQUIREMENTS (CRITICAL):
- This is a {section_type.upper() if section_type else "GENERAL"} section. ONLY include content relevant to this section type.
- DO NOT include research methods (like "online ethnography", "user generated content") unless this is explicitly a research section.
- Research-specific content should ONLY appear in research sections, not in {section_type if section_type else "other"} sections.
- Focus on content that matches this section's purpose as defined in the narrative.
"""
            
            narrative_instruction = f"""
CRITICAL: CASE STUDY NARRATIVE AND OUTLINE (USE AS YOUR GUIDE):
{self.narrative}

OUTLINE SECTION INFORMATION:
- Section Title: "{outline_item.title}"
- Section Description: "{outline_item.description or 'No description provided'}"

NARRATIVE AND OUTLINE REQUIREMENTS:
- The narrative above provides the story structure and flow for this case study - USE IT AS A GUIDE to understand the overall story
- The OUTLINE SECTION (title and description) tells you EXACTLY what content belongs in THIS specific section - USE IT AS YOUR PRIMARY GUIDE for determining what chunks/content should go here
- The outline section description defines the scope and purpose of this section - extract ALL relevant content from the source material that matches this description
- Use the narrative to understand the section's purpose within the overall story, then use the OUTLINE DESCRIPTION to determine which specific chunks and content from the source material belong in this section
- GENERATE COMPREHENSIVE, DETAILED content from the source material that matches the outline section's description - don't be minimal or sparse
- The narrative follows a structured case study format covering: project title, description, team/role, context, problem, research, problem statement, constraints, design goals, ideation, wireframes, mockups, design process and iterations, prototyping, testing, final outcome, and reflections
- CRITICAL: Pay special attention to process sections: ideation, wireframes, mockups, design process/iterations, prototyping, and testing. These sections should contain DETAILED information about the design process.
- Each bullet point should support the narrative's themes for this section AND match the outline section's description - be DETAILED and COMPREHENSIVE
- Make bullet points tell part of the story as defined in the narrative, using rich details from the source material that align with the outline section
- Connect bullet points to the overall narrative arc and ensure they flow chronologically
- If the narrative mentions specific themes, problems, or solutions, your bullets should reflect those, but EXPAND on them with details from the source material
- The narrative guides WHAT to include and WHERE - the OUTLINE SECTION DESCRIPTION tells you which specific content belongs here - the source material provides the DETAILS and SPECIFICS
- CRITICAL: Generate FULL, DETAILED content for this section. The outline section description is your guide for what content should go here - use it to extract ALL relevant information from the source material. Don't be minimal - create comprehensive bullets that fully cover what the outline section describes
- Content should primarily appear in the section where it's most relevant according to the outline description, but you can include supporting details as needed
- IMPORTANT: Use the outline section description to identify which chunks from the source material are relevant to this section, then generate comprehensive content from those chunks
- DO NOT mention appendices, supplemental materials, or instructions to "see appendix"—keep every statement self-contained within the slide content
- DO NOT introduce new section headings. Reuse the exact headings from the student's narrative (e.g., "**tldr;**", "**Team and Constraints**", etc.) and ensure the content you generate fits within those sections.
- The final narrative that the student will submit must stay between 500 and 700 words. Keep bullets information-rich but concise so that the total prose stays within that limit. Remove redundancy and avoid repeating details across sections.
- Use clear, concise, human-sounding language—avoid robotic phrasing or generic filler. Be SPECIFIC about problems, users, methods, and outcomes.
- DO NOT append meta notes or explanations (e.g., “Note: this section...”); end once the actual content is complete.

{section_restrictions}
"""
        
        tone_instruction = ""
        if self.tone:
            tone_instruction = f"\nTONE: {self.tone}\n- Write in a {self.tone} tone\n- Adjust language and style accordingly\n"
        
        prompt = f"""You are writing content for a slide in a UX case study presentation. 

OUTLINE SECTION:
- Title: "{outline_item.title}"
- Description: "{outline_item.description or 'No description provided'}"

CASE STUDY NARRATIVE (USE AS YOUR GUIDE FOR STORY STRUCTURE):
{self.narrative if self.narrative else "No narrative provided"}

SOURCE MATERIAL (ordered chronologically - extract content that matches the outline section description):
{context}

YOUR TASK:
Write {max_bullets} bullet points (or more if needed to fully cover the outline section) that tell the case study story. The OUTLINE SECTION DESCRIPTION above tells you EXACTLY what content belongs in this section - use it to identify which chunks from the source material are relevant, then extract ALL relevant information from those chunks to generate comprehensive content.

CRITICAL: You must extract information from MULTIPLE chunks. Do not just use one or two chunks - go through ALL the source material chunks provided and extract EVERY piece of information that matches the outline section description. Generate multiple bullets from each relevant chunk if needed. The goal is to create COMPREHENSIVE content that fully covers what the outline section describes.

CRITICAL REQUIREMENTS:
1. The OUTLINE SECTION DESCRIPTION is your PRIMARY GUIDE - it tells you what content belongs in this section. Use it to identify which chunks from the source material are relevant, then extract ALL relevant information from those chunks.
2. The narrative provides context for the overall story structure - use it to understand how this section fits into the bigger picture, but let the OUTLINE DESCRIPTION guide what specific content goes here.
3. Use the source material to find SPECIFIC, DETAILED information that matches the outline section description - be THOROUGH and COMPREHENSIVE, not minimal. Generate FULL content for this section.
4. Write complete, finished sentences - never leave sentences incomplete
5. Each bullet should be 30-100 words (can be longer if needed for clarity and detail) - prioritize being DETAILED and COMPREHENSIVE over being brief
6. BE SPECIFIC AND PRECISE - Include exact details: numbers, participant counts, specific method names, exact findings, specific quotes or insights, exact statistics
7. DO NOT use vague statements - extract SPECIFIC problems, SPECIFIC findings, SPECIFIC methods from source material
8. Write in FIRST PERSON when appropriate (I, we, my, our) to match the narrative style
9. For research methods: include exact method names, participant numbers, duration, specific findings
10. Focus on concrete details, user insights, or design decisions that match the outline section description - GENERATE FULL CONTENT, not sparse summaries
11. Each bullet must provide unique information - avoid repeating concepts, but be COMPREHENSIVE within each bullet
12. Ensure bullets follow chronological order (source material is already ordered)
13. Write in the same engaging, story-driven style as the narrative
14. CRITICAL: Generate FULL, DETAILED content for this section. The outline section description tells you what content belongs here - use it to extract ALL relevant information from the source material. Create RICH, COMPREHENSIVE bullets that fully cover what the outline section describes. Don't be minimal or sparse - generate substantial content.
15. Only include research methods (like "online ethnography", "user generated content") in research sections. Research content should appear in the research section, but other sections should have their own comprehensive content from the source material.
16. DO NOT repeat the exact same information across sections, but each section should be FULL and DETAILED with content relevant to its purpose as defined by the outline description.
17. IMPORTANT: Use the outline section description to guide which chunks from the source material are relevant to this section. Then generate comprehensive, detailed bullets from ALL relevant chunks - don't skip content that matches the outline description.
18. CRITICAL: Extract information from MULTIPLE chunks. Review ALL chunks provided and extract information from each one that matches the outline section description. If a chunk contains multiple relevant pieces of information, create multiple bullets from it. Do not limit yourself to just a few chunks - be thorough and extract from as many relevant chunks as possible.
19. The outline section description is your filter - if content in a chunk matches what the outline describes, extract it. Generate enough bullets to fully cover what the outline section describes - aim for comprehensive coverage, not minimal summaries.

ABSOLUTE PROHIBITIONS:
- DO NOT include meta-commentary like "Based on the narrative", "I've extracted", "Here are", etc.
- DO NOT reference the narrative or your process - just write the content
- DO NOT leave sentences incomplete or end with "...."
- DO NOT repeat concepts already covered in other bullets
- DO NOT use the slide title as a template - use the narrative structure instead
- DO NOT append summarising notes such as "Note: this content..."—finish with the final bullet content only

{tone_instruction if self.tone else ""}

Output ONLY the bullet points, one per line, starting with "- ". No explanations, no meta-text, just the content.
"""
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You are an expert at creating presentation slides that tell compelling stories. You use the OUTLINE SECTION DESCRIPTION as your PRIMARY GUIDE to determine what content belongs in each section, then use the narrative to understand the overall story structure. You generate COMPREHENSIVE, DETAILED content from the source material that matches the outline section description. You write in a CLEAR, CONVERSATIONAL, and COMPELLING style - use simple, direct language, avoid convoluted sentences. Write like a student telling their story. You extract SPECIFIC, PRECISE, DETAILED information from source material - exact numbers, participant counts, specific method names, exact findings, specific quotes. You generate FULL, RICH content - don't be minimal or sparse. You use the outline section description to identify which chunks from the source material are relevant, then extract ALL relevant information from MULTIPLE chunks to create comprehensive bullets. You go through ALL provided chunks and extract information from each one that matches the outline description. You generate multiple bullets from each relevant chunk if needed. You write in FIRST PERSON when appropriate. You NEVER use vague statements - always be specific and precise. You present information in a way that supports the narrative's story arc with comprehensive details. You NEVER include meta-commentary, explanations, or references to your process. You ONLY write the actual content for the slides - complete, finished sentences that tell the story with precise, detailed information in a clear, conversational style. Generate COMPREHENSIVE content that fully covers what the outline section describes by extracting from MULTIPLE chunks, not minimal summaries from just one or two chunks."
                },
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_service.generate_chat_completion(
                messages, 
                max_tokens=4000,  # Increased to allow for more comprehensive content
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
            'pen and paper', 'current system', 'as mentioned', 'as discussed',
            'online ethnography', 'user generated content', 'ethnography',
            'research method', 'research finding', 'participant'
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
            
            # Check if too similar to already seen bullets (less aggressive to allow more content)
            is_duplicate = False
            for seen in self.all_seen_bullets:
                similarity = SequenceMatcher(None, bullet_lower, seen).ratio()
                if similarity > 0.8:
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # Check if too similar to bullets in current list (less aggressive)
            is_duplicate_local = False
            for existing in filtered:
                similarity = SequenceMatcher(None, bullet_lower, existing.lower()).ratio()
                if similarity > 0.8:
                    is_duplicate_local = True
                    break
            
            if is_duplicate_local:
                continue
            
            # Check for concept repetition (same key concepts)
            if self._has_repeated_concept(bullet, filtered):
                continue
            
            # Check for research-specific content in non-research sections
            # This is handled in the LLM prompt, but add extra filtering here
            if self._contains_research_methods(bullet) and not self._is_research_section:
                # Skip research methods in non-research sections
                logger.debug(f"Filtered out research content from non-research section: {bullet[:50]}...")
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
        
        # Check against existing bullets (less aggressive - allow more content)
        for existing in existing_bullets:
            existing_lower = existing.lower()
            # Count overlapping phrases
            overlap_count = sum(1 for phrase in bullet_phrases if phrase in existing_lower)
            if overlap_count >= 3:
                return True
        
        return False
    
    def _contains_research_methods(self, bullet: str) -> bool:
        """Check if bullet contains research-specific methods or content"""
        bullet_lower = bullet.lower()
        research_keywords = [
            'online ethnography', 'ethnography', 'user generated content',
            'interview', 'survey', 'observation', 'focus group',
            'participant', 'research method', 'research finding',
            'thematic analysis', 'affinity mapping', 'user research'
        ]
        return any(keyword in bullet_lower for keyword in research_keywords)
    
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
    
    def _merge_outline_description(self, description: str, bullets: List[str], max_bullets: int) -> List[str]:
        """ensure the outline description anchors the section content"""
        if not description:
            return bullets[:max_bullets]
        
        desc_text = description.strip()
        if not desc_text:
            return bullets[:max_bullets]
        
        expanded_desc = self._expand_outline_description(desc_text)
        desc_lower = expanded_desc.lower()
        for bullet in bullets:
            if SequenceMatcher(None, desc_lower, bullet.lower()).ratio() > 0.9:
                trimmed = bullets[:max_bullets]
                return trimmed
        
        allowance = max(0, max_bullets - 1)
        trimmed = bullets[:allowance]
        return [expanded_desc] + trimmed

    def _expand_outline_description(self, description: str) -> str:
        """lightly expand the user's outline description into 2-3 sentences"""
        import re
        desc = description.strip()
        if not desc:
            return desc
        
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', desc) if s.strip()]
        
        if len(sentences) >= 3:
            return ' '.join(sentences[:3])
        if len(sentences) == 2:
            return ' '.join(sentences)
        
        # only one sentence available; add two gentle follow-ups to keep context
        base = sentences[0]
        follow_up = " This section keeps exactly to that intention, echoing the edits you made to the outline."
        bridge = " It simply adds a touch more clarity so the case study reads smoothly while staying true to your wording."
        return base + follow_up + bridge
    
    def generate_comprehensive_bullets(
        self, 
        outline_items: List[OutlineItem], 
        vector_store,
        top_k: int = 20,
        max_bullets_per_item: int = 15
    ) -> Dict[str, List[BulletPoint]]:
        """Generate bullets for all outline items"""
        
        # reset cache so duplicates are only filtered within this deck
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