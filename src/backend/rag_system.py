# retrieval-augmented generation system for creating slide content
from typing import List, Dict, Any, Tuple, Set
import logging
import re
from difflib import SequenceMatcher

from .models import OutlineItem, BulletPoint, Chunk
from .chunking_embedding import ChunkingEmbeddingService
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)

# system that uses rag to generate bullet points for slides from pdf content
class RAGSystem:
    # initialize rag system with llm and chunking services
    def __init__(self):
        self.llm_service = get_llm_service()
        self.chunking_service = ChunkingEmbeddingService()
        self.all_seen_bullets = []  # track all bullets to check for duplicates
        self.narrative = None
        self.tone = None
        self._is_research_section = False  # track if current section is research
    
    # determine section type and return query keywords
    def _determine_section_type(self, outline_item: OutlineItem) -> tuple[str, str]:
        """Determine section type and return query keywords"""
        if not self.narrative:
            return "general", ""
        
        outline_lower = outline_item.title.lower()
        description_lower = (outline_item.description or "").lower()
        text = f"{outline_lower} {description_lower}"
        
        # section type mappings
        section_mappings = {
            "problem_statement": (['problem statement', 'how might we', 'hmw'], ""),
            "research": (['research', 'themes', 'findings', 'early findings', 'interview', 'survey', 'observation', 'ethnography'], "research methods findings themes insights"),
            "problem": (['problem', 'overview', 'user', "what's the problem", 'challenge'], "user problem challenge"),
            "context": (['context', 'setting', 'assignment', 'brief', 'scope'], "project scope constraints context assignment"),
            "ideation": (['ideation', 'brainstorm', 'concept', 'direction', 'ideation methods'], "ideation concepts brainstorming directions sketches early concepts"),
            "wireframes": (['wireframe', 'wireframes', 'wireframing', 'early designs', 'low-fidelity'], "wireframes wireframe early designs low-fidelity sketches interactions flows"),
            "mockups": (['mockup', 'mockups', 'visual design', 'color palette', 'typography', 'spacing', 'layout'], "mockups mockup visual design color palette typography spacing layout design elements"),
            "iterations": (['design process', 'iterations', 'iterative', 'evolution', 'rounds'], "design process iterations iterative evolution rounds changes modifications"),
            "prototyping": (['prototype', 'prototyping', 'interactive', 'clickable'], "prototyping prototype tools interface decisions interactive clickable"),
            "design": (['design', 'solution'], "design decisions solution"),
            "testing": (['test', 'evaluation', 'feedback', 'testing', 'usability testing', 'test rounds'], "testing evaluation feedback usability test rounds participants observations"),
            "outcome": (['outcome', 'final', 'result', 'impact'], "results impact outcomes final solution"),
            "reflection": (["didn't go as planned", "what didn't", "learned", "reflection", "challenges", "adaptations", "compromises"], "challenges adaptations compromises lessons learned reflections what didn't work"),
        }
        
        for section_type, (keywords, query_keywords) in section_mappings.items():
            if any(word in text for word in keywords):
                if section_type == "research":
                    self._is_research_section = True
                return section_type, query_keywords
        
        return "general", ""
    
    # extract exact text from narrative for a given section
    def _extract_section_text_from_narrative(self, outline_item: OutlineItem) -> str:
        """Extract the exact text from the narrative that corresponds to this outline section"""
        if not self.narrative:
            return ""
        
        import re
        
        # try to match the outline title to a section in the narrative
        outline_title_lower = outline_item.title.lower().strip()
        narrative = self.narrative
        
        # look for markdown headings like **title** or ## title
        # also look for the title text directly
        patterns = [
            rf'\*\*{re.escape(outline_item.title)}\*\*',  # **exact title**
            rf'\*\*{re.escape(outline_item.title.lower())}\*\*',  # **exact title lower**
            rf'##\s+{re.escape(outline_item.title)}',  # ## exact title
            rf'##\s+{re.escape(outline_item.title.lower())}',  # ## exact title lower
        ]
        
        # also try partial matches for common variations
        title_words = outline_title_lower.split()
        if len(title_words) > 2:
            # try matching first few words
            partial_title = ' '.join(title_words[:3])
            patterns.extend([
                rf'\*\*.*?{re.escape(partial_title)}.*?\*\*',
                rf'##\s+.*?{re.escape(partial_title)}.*?',
            ])
        
        section_text = ""
        section_start = -1
        
        # find the section start
        for pattern in patterns:
            match = re.search(pattern, narrative, re.IGNORECASE)
            if match:
                section_start = match.end()
                break
        
        # if no markdown heading found, try to find the title text directly
        if section_start == -1:
            title_pattern = re.escape(outline_item.title)
            match = re.search(title_pattern, narrative, re.IGNORECASE)
            if match:
                section_start = match.end()
        
        if section_start == -1:
            # try matching by description keywords
            if outline_item.description:
                desc_words = outline_item.description.lower().split()[:3]
                for word in desc_words:
                    if len(word) > 4:  # only meaningful words
                        match = re.search(rf'\*\*.*?{re.escape(word)}.*?\*\*', narrative, re.IGNORECASE)
                        if match:
                            section_start = match.end()
                            break
        
        if section_start == -1:
            return ""
        
        # find the next section (next markdown heading) or end of narrative
        next_section_pattern = r'\*\*[^*]+\*\*|##\s+[^\n]+'
        next_match = re.search(next_section_pattern, narrative[section_start:])
        
        if next_match:
            section_text = narrative[section_start:section_start + next_match.start()].strip()
        else:
            section_text = narrative[section_start:].strip()
        
        # clean up the text - remove extra whitespace, keep paragraphs
        section_text = re.sub(r'\n{3,}', '\n\n', section_text)
        section_text = section_text.strip()
        
        # if we got a good chunk of text, return it
        if len(section_text) > 20:
            return section_text
        
        return ""
    
    # generate bullet points for an outline section using rag
    def generate_bullets_for_outline_item(
        self, 
        outline_item: OutlineItem, 
        vector_store, 
        top_k: int = 20,
        max_bullets: int = 15
    ) -> List[BulletPoint]:
        """Generate bullet points for an outline item using RAG, following the narrative"""
        
        # reset section type flag for this item
        self._is_research_section = False
        
        # extract exact text from narrative for this section
        exact_narrative_text = self._extract_section_text_from_narrative(outline_item)
        
        # build search query from outline description and title
        query_parts = []
        if outline_item.description:
            # add description twice to increase weight in semantic search
            query_parts.append(outline_item.description)
            query_parts.append(outline_item.description)
        query_parts.append(outline_item.title)
        
        # identify section type and add relevant keywords to query
        section_type, query_keywords = self._determine_section_type(outline_item)
        if query_keywords:
            query_parts.append(query_keywords)
        
        # if we have exact narrative text, use it as-is and add intelligent expansion
        if exact_narrative_text:
            # use the entire exact narrative text as-is (don't truncate or modify it)
            base_text = exact_narrative_text.strip()
            
            # problem statement sections should remain exactly as-is, no expansion
            if section_type == "problem_statement":
                bullets = [base_text] if base_text else []
                return self._create_bullets_with_provenance(bullets, [], base_text, outline_item.title, "using exact narrative text as-is (problem statement)")
            
            # search for similar chunks to add intelligent expansion based on section type
            query = " ".join(query_parts)
            similar_chunks = self.chunking_service.search_similar_chunks(query, top_k)
            
            expansion_text = ""
            if similar_chunks:
                # sort chunks by page and position to maintain chronological order
                similar_chunks = sorted(similar_chunks, key=lambda x: (
                    x[0].page_number if hasattr(x[0], 'page_number') else 0,
                    x[0].chunk_index if hasattr(x[0], 'chunk_index') else 0
                ))
                
                # prepare context string from chunks
                context = self._prepare_context(similar_chunks)
                
                # generate intelligent expansion based on section type and outline (max 2-3 sentences)
                expansion_text = self._generate_intelligent_expansion(
                    outline_item,
                    base_text,
                    context,
                    section_type
                )
            
            # combine base text and expansion
            bullets = [base_text] if base_text else []
            if expansion_text and expansion_text.strip():
                bullets.append(expansion_text.strip())
            
            # create bullet points with provenance
            return self._create_bullets_with_provenance(bullets, similar_chunks if similar_chunks else [], base_text, outline_item.title, "using exact narrative text with intelligent expansion")
        
        # fallback: if no exact narrative text found, use original generation method
        # for problem statement sections, use exact text from outline description without any changes
        if section_type == "problem_statement" and outline_item.description:
            exact_text = outline_item.description.strip()
            if exact_text:
                return [BulletPoint(
                    text=exact_text,
                    provenance=[],
                    confidence=1.0
                )]
        
        # search for similar chunks using vector similarity
        query = " ".join(query_parts)
        similar_chunks = self.chunking_service.search_similar_chunks(query, top_k)
        
        if not similar_chunks:
            logger.warning(f"No chunks found for: {outline_item.title}")
            return []
        
        # sort chunks by page and position to maintain chronological order
        similar_chunks = sorted(similar_chunks, key=lambda x: (
            x[0].page_number if hasattr(x[0], 'page_number') else 0,
            x[0].chunk_index if hasattr(x[0], 'chunk_index') else 0
        ))
        
        # prepare context string from chunks
        context = self._prepare_context(similar_chunks)
        
        # generate bullets using llm
        bullets_text = self._generate_bullets_with_llm(
            outline_item, 
            context, 
            max_bullets,
            section_type
        )
        
        # parse bullets from llm response
        bullets = self._parse_bullets(bullets_text)
        
        # filter out duplicates and low quality bullets
        bullets = self._filter_bullets(bullets)
        
        # remove repeated phrases
        bullets = self._deduplicate_phrases(bullets)
        
        # merge outline description into bullets if needed
        bullets = self._merge_outline_description(outline_item.description, bullets, max_bullets)
        
        # create bullet points with provenance
        return self._create_bullets_with_provenance(bullets, similar_chunks, None, outline_item.title)
    
    # create bullet point objects with provenance
    def _create_bullets_with_provenance(
        self, 
        bullets: List[str], 
        similar_chunks: List[Tuple[Chunk, float]], 
        base_text: str = None,
        section_title: str = "",
        log_suffix: str = ""
    ) -> List[BulletPoint]:
        """Create bullet point objects with provenance"""
        # get page provenance
        page_numbers = []
        if similar_chunks:
            page_numbers = sorted(list(set([chunk.page_number for chunk, _ in similar_chunks])))
        provenance_pages = [f"Page {page}" for page in page_numbers] if page_numbers else []
        
        # create bullet point objects
        bullets_with_provenance = []
        for bullet_text in bullets:
            if bullet_text and len(bullet_text.strip()) > 10:
                confidence = 1.0 if base_text and bullet_text == base_text else 0.85
                bullet_with_provenance = BulletPoint(
                    text=bullet_text.strip(),
                    provenance=provenance_pages,
                    confidence=confidence
                )
                bullets_with_provenance.append(bullet_with_provenance)
                self.all_seen_bullets.append(bullet_text.lower())
        
        suffix = f" ({log_suffix})" if log_suffix else ""
        logger.info(f"  Generated {len(bullets_with_provenance)} bullets for: {section_title}{suffix}")
        return bullets_with_provenance
    
    # prepare context string from chunks for llm
    def _prepare_context(self, similar_chunks: List[Tuple[Chunk, float]]) -> str:
        """Prepare context from chunks, maintaining chronological order"""
        context_parts = []
        
        # process top chunks in chronological order
        for i, (chunk, score) in enumerate(similar_chunks[:14], 1):
            section = chunk.metadata.get('section_title', 'Unknown')
            page = chunk.page_number
            chunk_index = chunk.chunk_index if hasattr(chunk, 'chunk_index') else i
            
            # clean chunk text before adding to context
            chunk_text = self._clean_chunk_for_context(chunk.text)
            
            if chunk_text and len(chunk_text.strip()) > 30:
                # format chunk with order info to maintain chronology
                context_part = f"[Source {i}, Page {page}, Order {chunk_index}] {section}:\n{chunk_text}\n---\n"
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    # clean chunk text by removing artifacts and incomplete sentences
    def _clean_chunk_for_context(self, text: str) -> str:
        """Clean chunk text for context preparation"""
        import re
        # remove page number patterns like "4-10"
        text = re.sub(r'\b\d+-\d+\b', '', text)
        text = re.sub(r'\b\d{1,2}\s*=\s*\d+', '', text)
        # fix incomplete sentences ending with multiple dots
        text = re.sub(r'\.{3,}\s*$', '.', text, flags=re.MULTILINE)
        # remove standalone methodology words without context
        text = re.sub(r'\b(think aloud|heuristic evaluation|interviews|understand|empathise|define|ideate|conceptualise)\b(?=\s|$)', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    # build narrative instruction for llm prompt
    def _build_narrative_instruction(self, outline_item: OutlineItem, section_restrictions: str) -> str:
        """Build narrative instruction string for LLM prompt"""
        return f"""
CRITICAL: CASE STUDY NARRATIVE AND OUTLINE (USE AS YOUR GUIDE):
{self.narrative}

OUTLINE SECTION INFORMATION:
- Section Title: "{outline_item.title}"
- Section Description: "{outline_item.description or 'No description provided'}"

NARRATIVE AND OUTLINE REQUIREMENTS:
- The narrative provides story structure - USE IT AS A GUIDE
- The OUTLINE SECTION tells you EXACTLY what content belongs in THIS section - USE IT AS YOUR PRIMARY GUIDE
- CRITICAL: ONLY EXPAND the narrative by 1-2 sentences per section. Do not add extensive new content.
- CRITICAL: DO NOT mention appendices, appendixes, or "see appendix" - keep everything self-contained.
- Use simple, clear, human language - write like you're talking to a friend. Avoid complex words, jargon, or convoluted sentences. Keep it straightforward and easy to understand.
- Be SPECIFIC about problems, users, methods, and outcomes.
- DO NOT append meta notes or explanations.

{section_restrictions}
"""
    
    # generate intelligent expansion based on section type and outline meaning
    def _generate_intelligent_expansion(self, outline_item: OutlineItem, base_text: str, context: str, section_type: str = None) -> str:
        """Generate intelligent expansion that stays grounded in the outline and is guided by section type"""
        
        # determine what kind of expansion to add based on section type
        expansion_guidance = {
            "research": "Add 2-3 sentences about the research methods used and what they revealed. Be specific about methods, participants, and findings.",
            "ideation": "Add 2-3 sentences about how ideas were developed or refined. Describe the ideation process and concept evolution.",
            "testing": "Add 2-3 sentences about what was tested and what was learned. Include specific testing methods and key findings.",
            "wireframes": "Add 2-3 sentences about the wireframing process, key design decisions, or how wireframes evolved.",
            "mockups": "Add 2-3 sentences about visual design choices, color palette, typography, or layout decisions.",
            "prototyping": "Add 2-3 sentences about the prototyping process, tools used, or interactive decisions made.",
            "iterations": "Add 2-3 sentences about how the design changed between iterations and why.",
            "problem": "Add 2-3 sentences about specific user problems or challenges identified.",
            "outcome": "Add 2-3 sentences about the final results, impact, or how goals were met.",
            "reflection": "Add 2-3 sentences about specific challenges faced or lessons learned.",
        }
        
        guidance = expansion_guidance.get(section_type, "Add 2-3 sentences that expand on the outline with relevant details from the source material.")
        
        prompt = f"""Expand this case study section with 2-3 sentences that stay grounded in the outline.

OUTLINE SECTION:
- Title: "{outline_item.title}"
- Description: "{outline_item.description or ''}"

EXACT OUTLINE TEXT (DO NOT REPEAT THIS):
{base_text}

SOURCE MATERIAL:
{context}

YOUR TASK:
{guidance}

CRITICAL REQUIREMENTS:
1. Add ONLY 2-3 sentences maximum that expand on the outline meaning
2. Stay grounded in the outline - don't add irrelevant or made-up content
3. Don't repeat what's already in the outline text
4. Use simple, clear, human language - write like you're talking to a friend
5. Be SPECIFIC: include numbers, participant counts, method names, exact findings from source material
6. Write in FIRST PERSON (I, we, my, our)
7. DO NOT mention appendices
8. Make sure the expansion aligns with the intended meaning of the outline section
9. MAXIMUM 2-3 sentences - do not exceed this limit

Output ONLY the 2-3 expansion sentences. No explanations."""
        
        try:
            messages = [
                {"role": "system", "content": "You expand case study content intelligently. You stay grounded in the outline meaning and add only relevant details. Use simple, clear language. Don't repeat outline text. Don't add irrelevant content. Maximum 2-3 sentences only."},
                {"role": "user", "content": prompt}
            ]
            response = self.llm_service.generate_chat_completion(messages, max_tokens=150, temperature=0.5)
            expansion = re.sub(r'^[-•*]\s+', '', response.strip())
            if expansion and not expansion.endswith(('.', '!', '?')):
                expansion = expansion.rstrip('.') + '.'
            return expansion
        except Exception as e:
            logger.error(f"Error generating expansion: {str(e)}")
            return ""
    
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
            
            narrative_instruction = self._build_narrative_instruction(outline_item, section_restrictions)
        
        tone_instruction = ""
        if self.tone:
            tone_instruction = f"\nTONE: {self.tone}\n- Write in a {self.tone} tone\n- Adjust language and style accordingly\n"
        
        prompt = f"""You are writing content for a slide in a UX case study presentation. 

OUTLINE SECTION:
- Title: "{outline_item.title}"
- Description: "{outline_item.description or 'No description provided'}"

CASE STUDY NARRATIVE (USE AS YOUR GUIDE):
{self.narrative if self.narrative else "No narrative provided"}

SOURCE MATERIAL:
{context}

YOUR TASK:
Generate ONLY 1-2 bullet points. Use the OUTLINE SECTION DESCRIPTION to identify relevant chunks. CRITICAL: ONLY LIGHTLY EXPAND the narrative by 1-2 bullet points per section.

CRITICAL REQUIREMENTS:
1. Generate ONLY 1-2 bullet points per section
2. Use simple, clear, human language - write like you're talking to a friend. Avoid complex words, jargon, or convoluted sentences. Keep sentences short and straightforward.
3. BE SPECIFIC AND PRECISE - Include exact details: numbers, participant counts, method names, findings
4. Write in FIRST PERSON (I, we, my, our) to match narrative style
5. Write complete, finished sentences - never incomplete
6. Each bullet 30-80 words - concise and focused
7. DO NOT use vague statements
8. DO NOT mention appendices or supplementary materials
9. DO NOT include meta-commentary

{tone_instruction if self.tone else ""}

Output ONLY bullet points, one per line, starting with "- ". No explanations.
"""
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You create presentation slides that tell compelling stories. Use OUTLINE SECTION DESCRIPTION as your PRIMARY GUIDE. Generate ONLY 1-2 bullet points per section. Use simple, clear, human language - write like you're talking to a friend. Avoid complex words, jargon, or convoluted sentences. Write in CLEAR, CONVERSATIONAL style. Extract SPECIFIC, PRECISE details from source material. Write in FIRST PERSON. NEVER use vague statements. NEVER include meta-commentary. Keep expansion minimal - 1-2 bullet points only."
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
    
    # parse bullet points from llm response text
    def _parse_bullets(self, response_text: str) -> List[str]:
        """Parse bullets from LLM response"""
        import re
        lines = response_text.strip().split('\n')
        bullets = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # remove any mentions of appendices
            line = re.sub(r'\b(appendix|appendices|appendixes|see appendix|refer to appendix|appendix \d+|appendix [a-z])\b', '', line, flags=re.IGNORECASE)
            line = re.sub(r'\b(supplementary materials?|see supplementary|refer to supplementary)\b', '', line, flags=re.IGNORECASE)
            line = line.strip()
            
            if not line:
                continue
            
            # remove bullet symbols like "-", "•", "*", etc
            for symbol in ['-', '•', '*', '○', '1.', '2.', '3.', '4.', '5.']:
                if line.startswith(symbol):
                    line = line[len(symbol):].strip()
                    break
            
            # skip headers or very short lines
            if ':' in line[:20] or len(line) < 15:
                continue
            
            # skip meta-text that references the process
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
            
            # skip incomplete sentences
            if line.strip().endswith('....') or line.strip().endswith('...'):
                continue
            
            # skip very short lines
            if len(line.strip()) < 20:
                continue
            
            # add valid bullet point
            if len(line) > 15 and len(line) < 300:
                bullets.append(line)
        
        return bullets
    
    def _deduplicate_phrases(self, bullets: List[str]) -> List[str]:
        """Remove bullets that repeat common subphrases; keep the first occurrence."""
        if not bullets:
            return bullets
        phrases = ['pen and paper', 'current system', 'as mentioned', 'as discussed', 'online ethnography', 'user generated content', 'ethnography', 'research method', 'research finding', 'participant']
        seen_keys: Set[str] = set()
        result: List[str] = []
        for b in bullets:
            b_norm = ' '.join(b.lower().split())
            key = next((p for p in phrases if p in b_norm), None)
            if key and key in seen_keys:
                continue
            if key:
                seen_keys.add(key)
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
        bullet_words = bullet.lower().split()
        bullet_phrases = [' '.join(bullet_words[i:i+3]) for i in range(len(bullet_words) - 2) if len(' '.join(bullet_words[i:i+3])) > 10]
        for existing in existing_bullets:
            if sum(1 for phrase in bullet_phrases if phrase in existing.lower()) >= 3:
                return True
        return False
    
    def _contains_research_methods(self, bullet: str) -> bool:
        """Check if bullet contains research-specific methods or content"""
        research_keywords = ['online ethnography', 'ethnography', 'user generated content', 'interview', 'survey', 'observation', 'focus group', 'participant', 'research method', 'research finding', 'thematic analysis', 'affinity mapping', 'user research']
        return any(keyword in bullet.lower() for keyword in research_keywords)
    
    def _is_good_bullet(self, bullet: str) -> bool:
        """Check if bullet is good quality"""
        bullet_lower = bullet.lower()
        bad_phrases = ['key information', 'main points', 'this section', 'the following', 'as mentioned', 'provides information', 'based on the', 'i\'ve extracted', 'i have extracted', 'according to the', 'as discussed', 'the above', 'case study narrative', 'source material', 'provided narrative', 'based on the provided', 'extracted insights', 'following insights']
        good_words = ['user', 'task', 'design', 'application', 'feature', 'research', 'problem', 'solution', 'interface', 'experience', 'specific', 'focused', 'simple', 'easy', 'quick']
        
        if any(phrase in bullet_lower for phrase in bad_phrases):
                return False
        if bullet.strip().endswith(('....', '...')):
            return False
        if not (20 <= len(bullet) <= 600):
            return False
        return any(word in bullet_lower for word in good_words)
    
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
        """lightly expand the user's outline description into 1-2 sentences maximum"""
        import re
        desc = description.strip()
        if not desc:
            return desc
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', desc) if s.strip()]
        if len(sentences) >= 2:
            return ' '.join(sentences[:2])
        if len(sentences) == 1:
            return sentences[0] + " This section expands on that with relevant details from the project."
        return desc
    
    # generate bullets for all outline items
    def generate_comprehensive_bullets(
        self, 
        outline_items: List[OutlineItem], 
        vector_store,
        top_k: int = 20,
        max_bullets_per_item: int = 15
    ) -> Dict[str, List[BulletPoint]]:
        """Generate bullets for all outline items"""
        
        # reset seen bullets list for new deck
        self.all_seen_bullets = []
        
        results = {}
        
        # generate bullets for each outline section in the exact order provided
        for outline_item in outline_items:
            logger.info(f"Generating bullets for: {outline_item.title}")
            
            bullets = self.generate_bullets_for_outline_item(
                outline_item,
                vector_store,
                top_k,
                max_bullets_per_item
            )
            
            # ensure we only keep 1-2 bullets per section
            bullets = bullets[:max_bullets_per_item]
            results[outline_item.title] = bullets
        
        return results