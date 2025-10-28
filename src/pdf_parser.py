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
            r'^[A-Z][A-Z\s]+$',        # ALL CAPS TITLES
            r'^\d+\.\d+\.?\s+[A-Z]',   # 1.1. Subtitle
            r'^Chapter\s+\d+',         # Chapter 1
            r'^Section\s+\d+',         # Section 1
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
                        if current_section:
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
            if current_section:
                sections.append(current_section)
            
            # Extract title (first section or first line)
            title = sections[0]['title'] if sections else text_content[0][:100] if text_content else "Untitled"
            
            # Store page count before closing
            total_pages = doc.page_count
            doc.close()
            
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
        
        for pattern in self.section_patterns:
            if re.match(pattern, line):
                return True
        
        # Additional heuristics
        if line.isupper() and len(line.split()) <= 5:
            return True
        
        return False
    
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