from typing import List, Dict, Any
import logging
import json

from .models import OutlineItem, Chunk
from .chunking_embedding import VectorStore
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)

class OutlineGenerator:
    def __init__(self):
        self.llm_service = get_llm_service()
    
    def generate_outline(self, pdf_title: str, chunks: List[Chunk], max_sections: int = 10) -> List[OutlineItem]:
        """Generate outline using global pass over all chunks"""
        
        # Create a comprehensive summary of all content
        all_text = " ".join([chunk.text for chunk in chunks])
        
        # Truncate if too long (OpenAI has token limits)
        if len(all_text) > 50000:  # Rough token estimate
            all_text = all_text[:50000]
        
        prompt = self._create_outline_prompt(pdf_title, all_text, max_sections)
        
        try:
            messages = [
                {"role": "system", "content": "You are an expert at creating structured outlines from academic and technical documents."},
                {"role": "user", "content": prompt}
            ]
            
            outline_text = self.llm_service.generate_chat_completion(
                messages, 
                max_tokens=2000, 
                temperature=0.3
            )
            
            outline_items = self._parse_outline_response(outline_text)
            
            logger.info(f"Generated outline with {len(outline_items)} items")
            return outline_items
            
        except Exception as e:
            logger.error(f"Error generating outline: {str(e)}")
            # Fallback to simple outline based on sections
            return self._create_fallback_outline(chunks, max_sections)
    
    def _create_outline_prompt(self, title: str, content: str, max_sections: int) -> str:
        """Create prompt for outline generation"""
        return f"""
Please create a comprehensive outline for a presentation based on the following document:

Title: {title}

Content:
{content}

Requirements:
1. Create {max_sections} main sections maximum
2. Each section should have a clear, descriptive title
3. Include a brief description for each section
4. Organize sections in logical order
5. Focus on key concepts, findings, and important information
6. Make it suitable for a slide deck presentation

Format your response as a JSON array where each item has:
- "title": section title
- "description": brief description of what this section covers
- "level": hierarchy level (1 for main sections, 2 for subsections)
- "order": numerical order (1, 2, 3, etc.)

Example format:
[
  {{
    "title": "Introduction",
    "description": "Overview of the topic and objectives",
    "level": 1,
    "order": 1
  }},
  {{
    "title": "Key Findings",
    "description": "Main results and discoveries",
    "level": 1,
    "order": 2
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