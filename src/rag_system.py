from typing import List, Dict, Any, Tuple, Set
import logging
import re
from difflib import SequenceMatcher
from collections import Counter
import numpy as np

from .models import OutlineItem, BulletPoint, Chunk
from .chunking_embedding import ChunkingEmbeddingService
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)

class RAGSystem:
    def __init__(self):
        self.llm_service = get_llm_service()
        self.chunking_service = ChunkingEmbeddingService()
        self.all_seen_bullets = []
        self.all_generated_texts = []
        self.covered_ngrams = Counter()  # Track n-grams dynamically
        self.semantic_fingerprints = []  # Track semantic signatures
    
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
        
        # Generate paragraphs with LLM
        paragraphs_text = self._generate_bullets_with_llm(
            outline_item, 
            context, 
            max_bullets
        )
        
        # Parse and clean paragraphs
        paragraphs = self._parse_bullets(paragraphs_text)
        
        # Remove duplicates and low quality
        paragraphs = self._filter_bullets(paragraphs)
        
        # Aggressive deduplication
        paragraphs = self._deduplicate_advanced(paragraphs)
        
        # Limit to max
        paragraphs = paragraphs[:max_bullets]
        
        # Add provenance
        page_numbers = sorted(list(set([chunk.page_number for chunk, _ in similar_chunks])))
        provenance_pages = [f"Page {page}" for page in page_numbers]
        
        paragraphs_with_provenance = []
        for paragraph_text in paragraphs:
            paragraph_with_provenance = BulletPoint(
                text=paragraph_text,
                provenance=provenance_pages,
                confidence=0.85
            )
            paragraphs_with_provenance.append(paragraph_with_provenance)
            
            # Track this content globally
            self.all_seen_bullets.append(paragraph_text.lower())
            self.all_generated_texts.append(paragraph_text.lower())
            
            # Track n-grams dynamically
            self._update_ngram_tracker(paragraph_text)
            
            # Store semantic fingerprint
            self.semantic_fingerprints.append(self._create_semantic_fingerprint(paragraph_text))
        
        logger.info(f"  Generated {len(paragraphs_with_provenance)} paragraphs for: {outline_item.title}")
        return paragraphs_with_provenance
    
    def _prepare_context(self, similar_chunks: List[Tuple[Chunk, float]]) -> str:
        """Prepare context from chunks"""
        context_parts = []
        
        for i, (chunk, score) in enumerate(similar_chunks[:5], 1):
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
        """Generate paragraphs using LLM with improved anti-repetition"""
        
        # Build dynamic avoidance list from tracked n-grams
        avoidance_text = ""
        if self.covered_ngrams:
            # Get top repeated phrases
            common_phrases = [phrase for phrase, count in self.covered_ngrams.most_common(20) if count >= 2]
            if common_phrases:
                phrases_list = ", ".join(common_phrases)
                avoidance_text = f"\n\nCRITICAL - AVOID REPETITION:\nThese phrases/concepts have already been used multiple times:\n{phrases_list}\n\nYou MUST NOT repeat these phrases or their synonyms. Find completely new angles and different vocabulary."
        
        # Add examples of what's already been covered
        recent_content = ""
        if len(self.all_generated_texts) > 0:
            recent_samples = self.all_generated_texts[-3:] if len(self.all_generated_texts) >= 3 else self.all_generated_texts
            recent_content = f"\n\nPREVIOUSLY COVERED CONTENT (DO NOT REPEAT):\n" + "\n---\n".join(recent_samples[:2])
        
        prompt = f"""Create EXACTLY {max_bullets} complete paragraphs for a slide titled "{outline_item.title}".

SOURCE MATERIAL:
{context}
{avoidance_text}
{recent_content}

CRITICAL REQUIREMENTS:
1. Each paragraph MUST be 50-150 words (2-4 complete sentences)
2. Each paragraph MUST be completely finished - no cut-off text
3. Extract UNIQUE insights that haven't been mentioned before
4. Use DIFFERENT vocabulary and phrasing from previous slides
5. Focus on concrete, specific details from the source material
6. NO generic statements or filler language
7. Write in natural, flowing prose - NOT bullet points
8. Each paragraph must provide NEW information specific to "{outline_item.title}"
9. NEVER repeat phrases, concepts, or vocabulary from previously covered content
10. Finish every sentence completely - do not truncate

FORMAT:
- Write each paragraph as a complete block of text
- Separate paragraphs with exactly one blank line
- Do NOT use bullet points, dashes, numbers, or any symbols
- Ensure every paragraph is self-contained and complete

IMPORTANT: You must generate exactly {max_bullets} fully complete paragraphs. If you cannot find {max_bullets} unique points, generate fewer rather than repeating content.
"""
        
        try:
            messages = [
                {
                    "role": "system", 
                    "content": "You are an expert at creating presentation slides from design research documents. Your core skill is extracting UNIQUE, specific insights and presenting them in clear, complete paragraphs. You NEVER repeat vocabulary, phrases, or concepts that have been used before. You preserve the authentic language style of source material while ensuring each paragraph provides genuinely new information. Most importantly: you always complete your thoughts - never cut off mid-sentence."
                },
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_service.generate_chat_completion(
                messages, 
                max_tokens=2500,  # Increased to prevent cutoff
                temperature=0.7  # Slightly higher for more variety
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return ""
    
    def _parse_bullets(self, response_text: str) -> List[str]:
        """Parse paragraphs from LLM response with better handling"""
        # Split by double newlines to get paragraphs
        paragraphs = response_text.strip().split('\n\n')
        parsed_paragraphs = []
        
        for para in paragraphs:
            # Clean up the paragraph
            para = para.strip()
            
            # Remove any remaining bullet symbols or numbering at the start
            para_lines = para.split('\n')
            cleaned_lines = []
            for line in para_lines:
                line = line.strip()
                if not line:
                    continue
                # Remove bullet symbols or numbering
                line = re.sub(r'^[\-•*●○■□▪▫][\s]*', '', line)
                line = re.sub(r'^\d+[\.\)][\s]*', '', line)
                cleaned_lines.append(line)
            
            para = ' '.join(cleaned_lines).strip()
            
            # Skip empty paragraphs
            if not para:
                continue
            
            # Skip headers or meta-instructions
            if ':' in para[:40] and any(word in para.lower()[:60] for word in ['instruction', 'format', 'requirement', 'critical', 'important', 'note']):
                continue
            
            # Skip meta-text
            skip_phrases = ['bullet point', 'paragraph', 'here are', 'the following', 'the paragraphs', 'the content', 'exactly', 'must be']
            if any(phrase in para.lower()[:60] for phrase in skip_phrases):
                continue
            
            # Check if paragraph is incomplete (ends abruptly)
            if self._is_incomplete_text(para):
                logger.warning(f"Detected incomplete paragraph: {para[-50:]}")
                # Try to salvage if it's just missing a period
                if len(para) > 100 and para[-1] not in '.!?':
                    para = para + '.'
                elif len(para) < 100:
                    continue  # Skip incomplete short paragraphs
            
            # Length check - paragraphs should be substantial
            if 50 <= len(para) <= 800:
                parsed_paragraphs.append(para)
            elif len(para) > 800:
                logger.warning(f"Paragraph too long ({len(para)} chars), truncating")
                # Find last complete sentence within 800 chars
                truncated = para[:800]
                last_period = truncated.rfind('.')
                if last_period > 400:  # Keep it if we have at least 400 chars
                    parsed_paragraphs.append(truncated[:last_period + 1])
        
        return parsed_paragraphs
    
    def _is_incomplete_text(self, text: str) -> bool:
        """Check if text appears to be cut off or incomplete"""
        # Check for common indicators of incomplete text
        last_chars = text[-20:].lower()
        
        # Ends with incomplete word patterns
        if re.search(r'\b\w+$', text) and not text[-1] in '.!?':
            # Check if it's a complete sentence structure
            if not any(text.endswith(word) for word in ['app', 'apps', 'design', 'user', 'task', 'goal', 'work']):
                return True
        
        # Ends with connector words (indicates continuation)
        connector_endings = ['and', 'but', 'or', 'with', 'from', 'to', 'of', 'for', 'in', 'on', 'at', 'by']
        words = text.split()
        if len(words) > 0 and words[-1].lower().rstrip('.,!?') in connector_endings:
            return True
        
        # Ends with "..." which is sometimes used by LLMs for truncation
        if text.endswith('...') or text.endswith('..'):
            return True
        
        return False
    
    def _update_ngram_tracker(self, text: str):
        """Extract and track significant n-grams dynamically"""
        text_lower = text.lower()
        words = text_lower.split()
        
        # Track meaningful 2-grams, 3-grams, and 4-grams
        for n in [2, 3, 4]:
            for i in range(len(words) - n + 1):
                ngram = ' '.join(words[i:i+n])
                # Filter out ngrams with common stop words
                if not self._is_stopword_ngram(ngram):
                    self.covered_ngrams[ngram] += 1
    
    def _is_stopword_ngram(self, ngram: str) -> bool:
        """Check if ngram is mostly stop words"""
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'of', 'for', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'this', 'that', 'these', 'those', 'with', 'from', 'by'}
        words = ngram.split()
        stop_count = sum(1 for w in words if w in stop_words)
        return stop_count >= len(words) - 1  # Allow only one non-stop word
    
    def _create_semantic_fingerprint(self, text: str) -> Dict[str, float]:
        """Create a semantic fingerprint of text using key term frequencies"""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        # Filter stop words
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'of', 'for', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'this', 'that', 'these', 'those', 'with', 'from', 'by', 'it', 'as', 'can', 'will', 'would', 'their', 'them', 'they'}
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Count frequencies
        word_counts = Counter(meaningful_words)
        total = len(meaningful_words)
        
        if total == 0:
            return {}
        
        # Normalize to frequencies
        return {word: count / total for word, count in word_counts.items()}
    
    def _semantic_fingerprint_similarity(self, fp1: Dict[str, float], fp2: Dict[str, float]) -> float:
        """Calculate similarity between two semantic fingerprints"""
        if not fp1 or not fp2:
            return 0.0
        
        # Get all words
        all_words = set(fp1.keys()) | set(fp2.keys())
        
        # Calculate cosine similarity
        dot_product = sum(fp1.get(word, 0) * fp2.get(word, 0) for word in all_words)
        norm1 = sum(v**2 for v in fp1.values()) ** 0.5
        norm2 = sum(v**2 for v in fp2.values()) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _deduplicate_advanced(self, bullets: List[str]) -> List[str]:
        """Advanced deduplication using multiple strategies"""
        if not bullets:
            return bullets
        
        result = []
        
        for bullet in bullets:
            bullet_norm = ' '.join(bullet.lower().split())
            
            # Strategy 1: Check for high n-gram overlap with previous content
            bullet_ngrams = self._extract_ngrams(bullet_norm, [2, 3, 4])
            overlap_ratio = self._calculate_ngram_overlap(bullet_ngrams)
            
            if overlap_ratio > 0.3:  # More than 30% n-gram overlap
                logger.info(f"Skipping due to high n-gram overlap ({overlap_ratio:.2f}): {bullet[:50]}...")
                continue
            
            # Strategy 2: Check semantic fingerprint similarity
            current_fingerprint = self._create_semantic_fingerprint(bullet)
            is_semantically_duplicate = False
            
            for prev_fingerprint in self.semantic_fingerprints:
                similarity = self._semantic_fingerprint_similarity(current_fingerprint, prev_fingerprint)
                if similarity > 0.65:  # High semantic similarity
                    is_semantically_duplicate = True
                    logger.info(f"Skipping due to semantic similarity ({similarity:.2f}): {bullet[:50]}...")
                    break
            
            if is_semantically_duplicate:
                continue
            
            # Strategy 3: Check for local duplicates within current batch
            is_local_duplicate = False
            for existing in result:
                similarity = self._check_semantic_similarity(bullet_norm, existing.lower())
                if similarity > 0.50:
                    is_local_duplicate = True
                    break
            
            if is_local_duplicate:
                continue
            
            # Passed all checks
            result.append(bullet)
        
        return result
    
    def _extract_ngrams(self, text: str, n_values: List[int]) -> Set[str]:
        """Extract n-grams of specified sizes"""
        words = text.split()
        ngrams = set()
        
        for n in n_values:
            for i in range(len(words) - n + 1):
                ngram = ' '.join(words[i:i+n])
                if not self._is_stopword_ngram(ngram):
                    ngrams.add(ngram)
        
        return ngrams
    
    def _calculate_ngram_overlap(self, current_ngrams: Set[str]) -> float:
        """Calculate how much the current n-grams overlap with previously seen content"""
        if not current_ngrams:
            return 0.0
        
        overlap_count = sum(1 for ngram in current_ngrams if self.covered_ngrams.get(ngram, 0) >= 1)
        return overlap_count / len(current_ngrams)
    
    def _check_semantic_similarity(self, text1: str, text2: str) -> float:
        """Check semantic similarity between two texts"""
        # Normalize texts
        t1_words = set(text1.lower().split())
        t2_words = set(text2.lower().split())
        
        # Simple word overlap ratio
        if not t1_words or not t2_words:
            return 0.0
        
        intersection = t1_words.intersection(t2_words)
        union = t1_words.union(t2_words)
        
        jaccard = len(intersection) / len(union) if union else 0.0
        
        # Also check sequence similarity
        seq_similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        # Return weighted average
        return (jaccard * 0.4 + seq_similarity * 0.6)
    
    def _filter_bullets(self, bullets: List[str]) -> List[str]:
        """Filter out duplicates and low quality bullets"""
        filtered = []
        
        for bullet in bullets:
            bullet_lower = bullet.lower()
            
            # Check quality first
            if not self._is_good_bullet(bullet):
                continue
            
            # Check semantic similarity to all previously seen content
            is_duplicate = False
            for seen in self.all_generated_texts:
                similarity = self._check_semantic_similarity(bullet_lower, seen)
                if similarity > 0.50:  # Stricter threshold
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue
            
            # Check if too similar to bullets in current list
            is_duplicate_local = False
            for existing in filtered:
                similarity = self._check_semantic_similarity(bullet_lower, existing.lower())
                if similarity > 0.50:
                    is_duplicate_local = True
                    break
            
            if is_duplicate_local:
                continue
            
            filtered.append(bullet)
        
        return filtered
    
    def _is_good_bullet(self, bullet: str) -> bool:
        """Check if paragraph is good quality"""
        bullet_lower = bullet.lower()
        
        # Reject generic phrases
        bad_phrases = [
            'key information', 'main points', 'this section', 
            'the following', 'as mentioned', 'provides information',
            'in conclusion', 'to summarize', 'it is important to note',
            'this paragraph', 'this content', 'these paragraphs'
        ]
        
        for phrase in bad_phrases:
            if phrase in bullet_lower:
                return False
        
        # Length check
        if len(bullet) < 50 or len(bullet) > 800:
            return False
        
        # Should have specific content markers
        good_indicators = [
            'user', 'task', 'design', 'application', 'feature',
            'research', 'problem', 'solution', 'interface', 'experience',
            'study', 'findings', 'method', 'approach', 'system',
            'prototype', 'iteration', 'feedback', 'testing'
        ]
        
        has_content = any(word in bullet_lower for word in good_indicators)
        
        # Should have some sentence structure
        has_structure = '.' in bullet or '!' in bullet or '?' in bullet
        
        return has_content and has_structure
    
    def generate_comprehensive_bullets(
        self, 
        outline_items: List[OutlineItem], 
        vector_store,
        top_k: int = 8,
        max_bullets_per_item: int = 5
    ) -> Dict[str, List[BulletPoint]]:
        """Generate paragraphs for all outline items"""
        
        # Reset for new deck
        self.all_seen_bullets = []
        self.all_generated_texts = []
        self.covered_ngrams = Counter()
        self.semantic_fingerprints = []
        
        results = {}
        
        for outline_item in outline_items:
            logger.info(f"Generating paragraphs for: {outline_item.title}")
            
            paragraphs = self.generate_bullets_for_outline_item(
                outline_item,
                vector_store,
                top_k,
                max_bullets_per_item
            )
            
            results[outline_item.title] = paragraphs
        
        logger.info(f"Total unique n-grams tracked: {len(self.covered_ngrams)}")
        logger.info(f"Most common phrases: {self.covered_ngrams.most_common(10)}")
        return results