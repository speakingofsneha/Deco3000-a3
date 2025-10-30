import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PDFStructure:
    title: str
    sections: List[Dict[str, Any]]
    paragraphs: List[str]
    total_pages: int

class PDFParser:
    def __init__(self):
        self.section_patterns = [
            r'^\d+\.?\s+[A-Z][^.]*$',  # 1. Title or 1 Title
            r'^\d{2}\s+[a-z]+$',       # 01 empathise, 02 conceptualise
            r'^[A-Z][A-Z\s]+$',        # ALL CAPS TITLES
            r'^\d+\.\d+\.?\s+[A-Z]',   # 1.1. Subtitle
        ]
    
    def extract_text_and_structure(self, pdf_path: str) -> PDFStructure:
        """Extract text and basic structure from PDF"""
        try:
            doc = fitz.open(pdf_path)
            text_content = []
            sections = []
            current_section = None
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                
                # Split page into lines for structure analysis
                lines = page_text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if line is a section header
                    if self._is_section_header(line):
                        if current_section and len(current_section['content']) > 0:
                            sections.append(current_section)
                        current_section = {
                            'title': line,
                            'page': page_num + 1,
                            'content': []
                        }
                    else:
                        if current_section:
                            current_section['content'].append(line)
                        text_content.append(line)
            
            # Add the last section
            if current_section and len(current_section['content']) > 0:
                sections.append(current_section)
            
            # Extract title (first section or first meaningful line)
            title = self._extract_title(sections, text_content)
            
            # Store page count before closing
            total_pages = doc.page_count
            doc.close()
            
            logger.info(f"Extracted {len(sections)} sections, title: '{title}'")
            
            return PDFStructure(
                title=title,
                sections=sections,
                paragraphs=text_content,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
            raise
    
    def _is_section_header(self, line: str) -> bool:
        """Check if a line is likely a section header"""
        if len(line) < 3 or len(line) > 100:
            return False
        
        # Check against patterns
        for pattern in self.section_patterns:
            if re.match(pattern, line):
                return True
        
        # Additional heuristics
        # All caps and short
        if line.isupper() and len(line.split()) <= 5:
            return True
        
        # Numbered sections (01, 02, etc.)
        if re.match(r'^\d{2}\s+[a-z]+', line):
            return True
        
        # Common section keywords
        design_keywords = [
            'general purpose', 'target audience', 'design goal', 
            'data model', 'user flow', 'paper sketch', 'wireframe',
            'introduction', 'overview', 'problem', 'solution',
            'research', 'testing', 'prototype'
        ]
        
        line_lower = line.lower()
        for keyword in design_keywords:
            if keyword in line_lower and len(line.split()) <= 5:
                return True
        
        # Title case with 2-4 words
        if line.istitle() and 2 <= len(line.split()) <= 4:
            return True
        
        return False
    
    def _extract_title(self, sections: List[Dict[str, Any]], text_content: List[str]) -> str:
        """Extract document title"""
        
        # Try first section if it exists and looks like a title
        if sections:
            first_title = sections[0]['title']
            # Must be reasonable length and not too short
            if 10 < len(first_title) < 100:
                # Clean common prefixes
                title = re.sub(r'^(Title:|Report:|Project:)\s*', '', first_title, flags=re.IGNORECASE)
                if len(title) > 5:
                    return title
        
        # Try to find a title-like line in first page of text
        for line in text_content[:20]:  # Check more lines
            # Look for title characteristics
            if 15 < len(line) < 100:  # Not too short, not too long
                # Check if it looks like a title
                words = line.split()
                if 2 <= len(words) <= 8:  # Reasonable number of words
                    # Title case or all caps
                    if line.istitle() or line.isupper():
                        return line
        
        # Last resort: use PDF filename without extension
        if text_content and len(text_content) > 0:
            # But make sure it's not a fragment
            first_line = text_content[0]
            if len(first_line) > 15:
                return first_line[:80]
        
        return "Design Report"
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            page_count = doc.page_count
            doc.close()
            
            return {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', ''),
                'page_count': page_count
            }
        except Exception as e:
            logger.error(f"Error extracting metadata from {pdf_path}: {str(e)}")
            return {}