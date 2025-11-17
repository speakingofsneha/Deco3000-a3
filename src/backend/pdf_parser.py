# pdf parsing using pymupdf
import fitz  # PyMuPDF
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# data structure for parsed pdf content
@dataclass
class PDFStructure:
    title: str
    sections: List[Dict[str, Any]]
    paragraphs: List[str]
    total_pages: int

# class for extracting text and structure from pdf files
class PDFParser:
    # initialize parser with patterns to identify section headers
    def __init__(self):
        # regex patterns to detect section headers in pdf text
        self.section_patterns = [
            r'^\d+\.?\s+[A-Z][^.]*$',  # 1. Title or 1 Title
            r'^\d{2}\s+[a-z]+$',       # 01 empathise, 02 conceptualise
            r'^[A-Z][A-Z\s]+$',        # ALL CAPS TITLES
            r'^\d+\.\d+\.?\s+[A-Z]',   # 1.1. Subtitle
        ]
    
    # extract all text and identify sections from pdf
    def extract_text_and_structure(self, pdf_path: str) -> PDFStructure:
        """Extract text and basic structure from PDF"""
        try:
            # open pdf document
            doc = fitz.open(pdf_path)
            text_content = []
            sections = []
            current_section = None
            
            # process each page
            for page_num in range(doc.page_count):
                page = doc[page_num]
                page_text = page.get_text()
                
                # split page into lines for analysis
                lines = page_text.split('\n')
                
                # process each line
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # check if this line is a section header
                    if self._is_section_header(line):
                        # save previous section if it has content
                        if current_section and len(current_section['content']) > 0:
                            sections.append(current_section)
                        # start new section
                        current_section = {
                            'title': line,
                            'page': page_num + 1,
                            'content': []
                        }
                    else:
                        # add line to current section or general content
                        if current_section:
                            current_section['content'].append(line)
                        text_content.append(line)
            
            # add the last section if it exists
            if current_section and len(current_section['content']) > 0:
                sections.append(current_section)
            
            # extract document title
            title = self._extract_title(sections, text_content)
            
            # store page count before closing
            total_pages = doc.page_count
            doc.close()
            
            logger.info(f"Extracted {len(sections)} sections, title: '{title}'")
            
            # return structured pdf data
            return PDFStructure(
                title=title,
                sections=sections,
                paragraphs=text_content,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
            raise
    
    # check if a line looks like a section header
    def _is_section_header(self, line: str) -> bool:
        """Check if a line is likely a section header"""
        # reject lines that are too short or too long
        if len(line) < 3 or len(line) > 100:
            return False
        
        # check against regex patterns
        for pattern in self.section_patterns:
            if re.match(pattern, line):
                return True
        
        # check if all caps and short (likely a header)
        if line.isupper() and len(line.split()) <= 5:
            return True
        
        # check for numbered sections like "01 empathise"
        if re.match(r'^\d{2}\s+[a-z]+', line):
            return True
        
        # check for common design report keywords
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
        
        # check if title case with 2-4 words (likely a header)
        if line.istitle() and 2 <= len(line.split()) <= 4:
            return True
        
        return False
    
    # extract the document title from sections or text content
    def _extract_title(self, sections: List[Dict[str, Any]], text_content: List[str]) -> str:
        """Extract document title"""
        
        # try using first section title if it looks reasonable
        if sections:
            first_title = sections[0]['title']
            if 10 < len(first_title) < 100:
                # remove common prefixes like "Title:" or "Report:"
                title = re.sub(r'^(Title:|Report:|Project:)\s*', '', first_title, flags=re.IGNORECASE)
                if len(title) > 5:
                    return title
        
        # search through first lines of text for title-like content
        for line in text_content[:20]:
            # look for lines with title characteristics
            if 15 < len(line) < 100:
                words = line.split()
                # check if reasonable word count and title case
                if 2 <= len(words) <= 8:
                    if line.istitle() or line.isupper():
                        return line
        
        # fallback: use first line of text if substantial
        if text_content and len(text_content) > 0:
            first_line = text_content[0]
            if len(first_line) > 15:
                return first_line[:80]
        
        # default title if nothing found
        return "Design Report"
    
    # extract metadata like author, creation date, etc from pdf
    def extract_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        try:
            # open pdf and get metadata
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            page_count = doc.page_count
            doc.close()
            
            # return structured metadata dictionary
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