from typing import List, Dict, Any
import logging
import json
import re

from .models import OutlineItem, Chunk
from .chunking_embedding import VectorStore
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)

class OutlineGenerator:
    def __init__(self):
        self.llm_service = get_llm_service()
    
    def generate_outline(self, pdf_title: str, chunks: List[Chunk], max_sections: int = 8) -> List[OutlineItem]:
        """Generate outline by analyzing content and creating meaningful slide titles"""
        
        # Group chunks by section and page
        sections = {}
        for chunk in chunks:
            section_title = chunk.metadata.get('section_title', 'General')
            page_num = chunk.page_number
            
            # Create a key that groups by section
            if section_title not in sections:
                sections[section_title] = {
                    'title': section_title,
                    'chunks': [],
                    'page': page_num,
                    'total_length': 0
                }
            sections[section_title]['chunks'].append(chunk)
            sections[section_title]['total_length'] += len(chunk.text)
        
        # Sort sections by page number
        sorted_sections = sorted(sections.items(), key=lambda x: x[1]['page'])
        
        # Filter: Remove sections that are too small
        meaningful_sections = []
        for section_title, section_data in sorted_sections:
            # Keep sections with at least 150 characters of content
            if section_data['total_length'] >= 150:
                meaningful_sections.append((section_title, section_data))
        
        # If we filtered out everything, be more lenient
        if not meaningful_sections and sorted_sections:
            meaningful_sections = sorted_sections[:max_sections]
        
        # Limit to max_sections
        sections_to_use = meaningful_sections[:max_sections]
        
        logger.info(f"Creating outline from {len(sections_to_use)} sections")
        
        # Create outline items
        outline_items = []
        order = 1
        seen_titles = set()
        
        for section_title, section_data in sections_to_use:
            section_chunks = section_data['chunks']
            section_text = " ".join([chunk.text for chunk in section_chunks[:3]])
            
            # Clean the title
            cleaned_title = self._clean_title(section_title)
            
            # Make sure title is unique
            original_cleaned = cleaned_title
            counter = 1
            while cleaned_title.lower() in seen_titles:
                cleaned_title = f"{original_cleaned} ({counter})"
                counter += 1
            seen_titles.add(cleaned_title.lower())
            
            # Create description
            description = self._create_description(section_text)
            
            outline_item = OutlineItem(
                title=cleaned_title,
                description=description,
                level=1,
                order=order
            )
            outline_items.append(outline_item)
            logger.info(f"  Section {order}: {cleaned_title}")
            order += 1
        
        return outline_items
    
    def _clean_title(self, title: str) -> str:
        """Clean and improve title"""
        
        # Remove leading numbers: "01 ", "1. ", etc.
        title = re.sub(r'^\d+\.?\s+', '', title)
        title = re.sub(r'^\d{2}\s+', '', title)
        
        # If it's all lowercase, capitalize it properly
        if title.islower():
            title = title.title()
        
        # Clean formatting
        title = title.replace('_', ' ')
        title = ' '.join(title.split())
        
        # Limit length
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title.strip()
    
    def _create_description(self, text: str) -> str:
        """Create description from text"""
        # Take first sentence or 150 chars
        sentences = text.split('.')
        if sentences and len(sentences[0]) > 20:
            desc = sentences[0].strip() + '.'
        else:
            desc = text[:150].strip()
        
        # Clean up
        desc = desc.replace('\n', ' ')
        desc = ' '.join(desc.split())
        
        if len(text) > len(desc):
            desc += '...'
        
        return desc