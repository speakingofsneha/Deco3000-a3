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
    
    def generate_outline(self, pdf_title: str, chunks: List[Chunk], max_sections: int = 6) -> List[OutlineItem]:
        """Generate outline by analyzing content and creating meaningful slide titles"""
        
        # Group chunks by section and page order
        sections = {}
        for chunk in chunks:
            section_title = chunk.metadata.get('section_title', 'General')
            page_num = chunk.page_number
            
            if section_title not in sections:
                sections[section_title] = {
                    'title': section_title,
                    'chunks': [],
                    'page': page_num
                }
            sections[section_title]['chunks'].append(chunk)
        
        # Sort sections by page number to follow PDF order
        sorted_sections = sorted(sections.items(), key=lambda x: x[1]['page'])
        
        # Filter out 'General' sections and prioritize meaningful sections
        meaningful_sections = []
        for section_title, section_data in sorted_sections:
            if section_title != 'General' and len(section_data['chunks']) > 0:
                meaningful_sections.append((section_title, section_data))
        
        # If we have meaningful sections, use them; otherwise use all sections
        if meaningful_sections:
            sections_to_use = meaningful_sections
        else:
            sections_to_use = sorted_sections
        
        # Create outline items with content-based titles
        outline_items = []
        order = 1
        
        for section_title, section_data in sections_to_use[:max_sections]:
            # Get content from this section
            section_chunks = section_data['chunks']
            section_text = " ".join([chunk.text for chunk in section_chunks])
            
            # Generate meaningful slide title based on content
            slide_title = self._generate_slide_title(section_title, section_text)
            description = self._create_slide_description(section_title, section_text)
            
            outline_item = OutlineItem(
                title=slide_title,
                description=description,
                level=1,
                order=order
            )
            outline_items.append(outline_item)
            order += 1
        
        logger.info(f"Generated outline with {len(outline_items)} items following PDF order")
        return outline_items
    
    def _generate_slide_title(self, section_title: str, section_text: str) -> str:
        """Generate a meaningful slide title based on content analysis"""
        
        # First, try to extract meaningful titles from the content
        meaningful_titles = self._extract_content_titles(section_text)
        
        if meaningful_titles:
            return meaningful_titles[0]  # Use the first meaningful title found
        
        # Fallback: clean up the section title
        return self._clean_section_title(section_title)
    
    def _extract_content_titles(self, text: str) -> List[str]:
        """Extract meaningful titles from content that would work for slides"""
        
        # Look for design problem/solution focused patterns
        title_patterns = [
            r'General Purpose',  # From your PDF
            r'Target Audience',  # From your PDF
            r'Design Goals?',    # From your PDF
            r'Paper Sketches?',  # From your PDF
            r'Data Model',       # From your PDF
            r'User Research',    # Common in design reports
            r'Problem Analysis', # Common in design reports
            r'Solution Design',  # Common in design reports
            r'User Testing',     # Common in design reports
            r'Final Prototype',  # Common in design reports
            r'Key Findings',     # Common in design reports
        ]
        
        found_titles = []
        for pattern in title_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found_titles.append(pattern)
        
        # Look for content that suggests specific design topics
        if 'task management' in text.lower() and 'application' in text.lower():
            found_titles.append('Task Management Problem')
        if 'overpromising' in text.lower() or 'overcomplicating' in text.lower():
            found_titles.append('Current Problems')
        if 'accomplishment' in text.lower() and 'completion' in text.lower():
            found_titles.append('User Experience Goals')
        if 'sketch' in text.lower() and 'wireframe' in text.lower():
            found_titles.append('Design Solution')
        if 'data' in text.lower() and 'model' in text.lower():
            found_titles.append('System Design')
        if 'interview' in text.lower() and 'research' in text.lower():
            found_titles.append('User Research')
        if 'empathise' in text.lower() or 'empathize' in text.lower():
            found_titles.append('Problem Understanding')
        if 'conceptualise' in text.lower() or 'conceptualize' in text.lower():
            found_titles.append('Solution Development')
        
        return found_titles
    
    def _clean_section_title(self, title: str) -> str:
        """Clean up section titles for better presentation"""
        # Remove numbers and clean up
        if re.match(r'^\d{2}\s+', title):
            # Remove "01 " from "01 empathise"
            title = re.sub(r'^\d{2}\s+', '', title)
            title = title.title()  # Capitalize first letter
        
        # Clean up common patterns
        title = title.replace('_', ' ')
        title = title.strip()
        
        return title
    
    def _create_slide_description(self, section_title: str, section_text: str) -> str:
        """Create a concise description suitable for slide deck"""
        # Take first 150 characters and clean up
        preview = section_text[:150].strip()
        
        # Remove common PDF artifacts
        preview = preview.replace('\n', ' ').replace('\t', ' ')
        preview = ' '.join(preview.split())  # Remove extra whitespace
        
        # Add ellipsis if truncated
        if len(section_text) > 150:
            preview += "..."
        
        return preview
    
    def _create_outline_prompt(self, title: str, content: str, max_sections: int) -> str:
        """Create prompt for outline generation"""
        return f"""
Analyze the following document and create a comprehensive outline for a presentation. Break down the content into meaningful sections that would work well for slides.

Document Title: {title}

Document Content:
{content}

Instructions:
1. Create {max_sections} main sections that cover all the important content in the document
2. Each section should have a clear, descriptive title that captures the main topic
3. Each description should briefly explain what information is covered in that section
4. Organize sections in a logical flow that would work for a presentation
5. Make sure to cover all major topics, concepts, and findings from the document
6. Use titles that are specific and informative, not generic
7. Ensure each section has enough content to create meaningful slides

Format your response as a JSON array where each item has:
- "title": clear, descriptive section title
- "description": brief description of what this section covers
- "level": 1 (for main sections)
- "order": numerical order (1, 2, 3, etc.)

Example format:
[
  {{
    "title": "Project Overview and Goals",
    "description": "Introduction to the project, its objectives, and what it aims to achieve",
    "level": 1,
    "order": 1
  }},
  {{
    "title": "Problem Analysis",
    "description": "Analysis of current issues and challenges that the project addresses",
    "level": 1,
    "order": 2
  }},
  {{
    "title": "Design Approach",
    "description": "The methodology and approach used in the project design",
    "level": 1,
    "order": 3
  }}
]

Please provide only the JSON array, no additional text.
"""
    
    def _parse_outline_response(self, response_text: str) -> List[OutlineItem]:
        """Parse the AI response into OutlineItem objects"""
        try:
            # Clean the response text
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            # Parse JSON
            outline_data = json.loads(response_text)
            
            outline_items = []
            for item in outline_data:
                outline_item = OutlineItem(
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    level=item.get("level", 1),
                    order=item.get("order", 1)
                )
                outline_items.append(outline_item)
            
            return outline_items
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing outline JSON: {str(e)}")
            logger.error(f"Response text: {response_text}")
            return self._create_fallback_outline_from_text(response_text)
        except Exception as e:
            logger.error(f"Error parsing outline response: {str(e)}")
            return []
    
    def _create_fallback_outline_from_text(self, text: str) -> List[OutlineItem]:
        """Create outline from text when JSON parsing fails"""
        lines = text.split('\n')
        outline_items = []
        order = 1
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('{') and not line.startswith('['):
                # Extract title (remove numbers, bullets, etc.)
                title = line
                for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '-', '*', '•']:
                    if title.startswith(prefix):
                        title = title[len(prefix):].strip()
                        break
                
                if title:
                    outline_item = OutlineItem(
                        title=title,
                        description=f"Content related to {title.lower()}",
                        level=1,
                        order=order
                    )
                    outline_items.append(outline_item)
                    order += 1
        
        return outline_items[:10]  # Limit to 10 items
    
    def _create_fallback_outline(self, chunks: List[Chunk], max_sections: int) -> List[OutlineItem]:
        """Create simple outline based on chunk sections when AI fails"""
        sections = {}
        
        for chunk in chunks:
            section_title = chunk.metadata.get('section_title', 'General')
            if section_title not in sections:
                sections[section_title] = []
            sections[section_title].append(chunk)
        
        outline_items = []
        order = 1
        
        for section_title, section_chunks in list(sections.items())[:max_sections]:
            # Create description from first few chunks
            description = " ".join([chunk.text[:100] for chunk in section_chunks[:2]])
            if len(description) > 200:
                description = description[:200] + "..."
            
            outline_item = OutlineItem(
                title=section_title,
                description=description,
                level=1,
                order=order
            )
            outline_items.append(outline_item)
            order += 1
        
        return outline_items