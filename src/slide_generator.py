from typing import List, Dict, Any, Tuple
import json
import uuid
from datetime import datetime
import logging

from .models import Slide, SlideDeck, SlideType, OutlineItem, BulletPoint

logger = logging.getLogger(__name__)

class SlideGenerator:
    def __init__(self):
        self.slide_counter = 0
    
    def _should_have_media(self, title: str, bullets: List[BulletPoint]) -> tuple[bool, str]:
        """
        Intelligently detect if a slide should have media based on content.
        Returns: (has_media: bool, media_type: str)
        Media types: 'interface', 'data', 'flow', 'diagram'
        """
        # Combine title and all bullet text for analysis
        combined_text = title.lower() + " " + " ".join([b.text.lower() for b in bullets])
        
        # More specific keywords that strongly suggest interface/UI content
        # Only matches when these specific phrases appear
        interface_keywords = [
            'solution overview', 'user interface', 'ui design', 'ui mockup',
            'prototype', 'wireframe', 'mockup', 'screen design', 'interface design',
            'dashboard design', 'application interface', 'web app interface'
        ]
        
        # Specific keywords for user flow (need "user" or "flow" together)
        flow_keywords = [
            'user flow', 'user journey', 'user pathway', 'interaction flow',
            'navigation flow', 'workflow diagram', 'process flow'
        ]
        
        # Specific keywords for data/research visualization
        data_keywords = [
            'survey results', 'survey data', 'research findings', 'research results',
            'data visualization', 'chart', 'graph', 'statistics', 'survey responses',
            'interview results', 'study results', 'questionnaire results'
        ]
        
        # Specific keywords for diagrams/architecture
        diagram_keywords = [
            'system architecture', 'architecture diagram', 'system diagram',
            'flow diagram', 'process diagram', 'schema diagram', 'blueprint'
        ]
        
        # Check for interface/UI content (most specific first)
        if any(keyword in combined_text for keyword in interface_keywords):
            return (True, 'interface')
        
        # Check for user flow
        if any(keyword in combined_text for keyword in flow_keywords):
            return (True, 'flow')
        
        # Check for data/research
        if any(keyword in combined_text for keyword in data_keywords):
            return (True, 'data')
        
        # Check for diagrams
        if any(keyword in combined_text for keyword in diagram_keywords):
            return (True, 'diagram')
        
        return (False, '')
    
    def generate_slide_deck(
        self, 
        pdf_title: str, 
        outline_items: List[OutlineItem], 
        bullets_data: Dict[str, List[BulletPoint]],
        source_pdf: str,
        metadata: Dict[str, Any] = None
    ) -> SlideDeck:
        """Generate complete slide deck from outline and bullets"""
        
        slides = []
        
        # Create title slide
        title_slide = self._create_title_slide(pdf_title, source_pdf)
        slides.append(title_slide)
        
        # Create content slides for each outline item
        for outline_item in outline_items:
            if outline_item.title in bullets_data:
                content_slides = self._create_content_slides(
                    outline_item, 
                    bullets_data[outline_item.title]
                )
                slides.extend(content_slides)
            else:
                # Create a simple slide if no bullets available
                simple_slide = self._create_simple_slide(outline_item)
                slides.append(simple_slide)
        
        # Generate slide deck
        slide_deck = SlideDeck(
            title=pdf_title,
            slides=slides,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
            source_pdf=source_pdf
        )
        
        logger.info(f"Generated slide deck with {len(slides)} slides")
        return slide_deck
    
    def _create_title_slide(self, title: str, source_pdf: str) -> Slide:
        """Create title slide"""
        self.slide_counter += 1
        
        return Slide(
            id=f"slide_{self.slide_counter}",
            type=SlideType.TITLE,
            title=title,
            content=[],
            provenance=[],
            metadata={
                "slide_number": 1,
                "is_title": True,
                "source_pdf": source_pdf,
                "created_date": datetime.now().strftime('%Y-%m-%d')
            }
        )
    
    def _create_content_slides(
        self, 
        outline_item: OutlineItem, 
        bullets: List[BulletPoint]
    ) -> List[Slide]:
        """Create content slides for an outline item"""
        slides = []
        
        if not bullets:
            return [self._create_simple_slide(outline_item)]
        
        slide_title = outline_item.title
        
        # Check if this topic should have media (check all bullets)
        has_media, media_type = self._should_have_media(slide_title, bullets)
        
        if has_media:
            # For media slides: use plain description text, limit to ~2 bullets worth
            # Max ~400-500 characters per media slide to leave room for media
            max_chars_per_media_slide = 450
            
            # Split bullets by character count for media slides
            current_text = ""
            current_bullets = []
            slide_pages = set()
            
            for bullet in bullets:
                bullet_text = bullet.text
                bullet_length = len(bullet_text)
                
                # Collect page numbers
                for prov in bullet.provenance:
                    if prov.startswith("Page "):
                        slide_pages.add(prov)
                
                # If adding this bullet would exceed limit, create a slide with current content
                if current_text and len(current_text) + bullet_length + 50 > max_chars_per_media_slide:
                    self.slide_counter += 1
                    slide_provenance = sorted(list(slide_pages))
                    
                    # Create combined description text from bullets
                    description_text = " ".join([b.text for b in current_bullets])
                    description_bullet = BulletPoint(
                        text=description_text,
                        provenance=[],
                        confidence=0.8
                    )
                    
                    slide = Slide(
                        id=f"slide_{self.slide_counter}",
                        type=SlideType.CONTENT,
                        title=slide_title,
                        content=[description_bullet],
                        provenance=slide_provenance,
                        metadata={
                            "slide_number": self.slide_counter,
                            "outline_item": outline_item.title,
                            "has_media": True,
                            "media_type": media_type,
                            "layout": "media-above",
                            "is_media_slide": True  # Flag to render as description, not points
                        }
                    )
                    slides.append(slide)
                    
                    # Reset for next slide
                    current_text = bullet_text
                    current_bullets = [bullet]
                    slide_pages = set()
                    for prov in bullet.provenance:
                        if prov.startswith("Page "):
                            slide_pages.add(prov)
                else:
                    # Add to current slide
                    if current_text:
                        current_text += " " + bullet_text
                    else:
                        current_text = bullet_text
                    current_bullets.append(bullet)
            
            # Create final media slide with remaining content
            if current_bullets:
                self.slide_counter += 1
                slide_provenance = sorted(list(slide_pages))
                
                description_text = " ".join([b.text for b in current_bullets])
                description_bullet = BulletPoint(
                    text=description_text,
                    provenance=[],
                    confidence=0.8
                )
                
                slide = Slide(
                    id=f"slide_{self.slide_counter}",
                    type=SlideType.CONTENT,
                    title=slide_title,
                    content=[description_bullet],
                    provenance=slide_provenance,
                    metadata={
                        "slide_number": self.slide_counter,
                        "outline_item": outline_item.title,
                        "has_media": True,
                        "media_type": media_type,
                        "layout": "media-above",
                        "is_media_slide": True
                    }
                )
                slides.append(slide)
        else:
            # Regular slides: split bullets into slides (max 3 bullets per slide)
            max_bullets_per_slide = 3
            bullet_groups = [
                bullets[i:i + max_bullets_per_slide] 
                for i in range(0, len(bullets), max_bullets_per_slide)
            ]
            
            for group_idx, bullet_group in enumerate(bullet_groups):
                self.slide_counter += 1
                
                # Collect page numbers from all bullets for slide-level provenance
                slide_pages = set()
                clean_bullets = []
                for bullet in bullet_group:
                    # Remove provenance from individual bullets
                    clean_bullet = BulletPoint(
                        text=bullet.text,
                        provenance=[],
                        confidence=bullet.confidence
                    )
                    clean_bullets.append(clean_bullet)
                    
                    # Collect page numbers for slide provenance
                    for prov in bullet.provenance:
                        if prov.startswith("Page "):
                            slide_pages.add(prov)
                
                slide_provenance = sorted(list(slide_pages))
                
                slide = Slide(
                    id=f"slide_{self.slide_counter}",
                    type=SlideType.CONTENT,
                    title=slide_title,
                    content=clean_bullets,
                    provenance=slide_provenance,
                    metadata={
                        "slide_number": self.slide_counter,
                        "outline_item": outline_item.title,
                        "part": group_idx + 1 if len(bullet_groups) > 1 else 1,
                        "total_parts": len(bullet_groups),
                        "has_media": False,
                        "media_type": "",
                        "layout": "default",
                        "is_media_slide": False
                    }
                )
                slides.append(slide)
        
        return slides
    
    def _create_simple_slide(self, outline_item: OutlineItem) -> Slide:
        """Create a simple slide when no bullets are available"""
        self.slide_counter += 1
        
        # Check if this slide should have media
        bullets = [
            BulletPoint(
                text=outline_item.description,
                provenance=[],
                confidence=0.5
            )
        ]
        has_media, media_type = self._should_have_media(outline_item.title, bullets)
        
        return Slide(
            id=f"slide_{self.slide_counter}",
            type=SlideType.CONTENT,
            title=outline_item.title,
            content=bullets,
            provenance=[],
            metadata={
                "slide_number": self.slide_counter,
                "outline_item": outline_item.title,
                "is_simple": True,
                "has_media": has_media,
                "media_type": media_type,
                "layout": "media-above" if has_media else "default"
            }
        )
    
    def _create_summary_slide(self, outline_items: List[OutlineItem]) -> Slide:
        """Create summary slide"""
        self.slide_counter += 1
        
        summary_bullets = []
        for i, item in enumerate(outline_items[:5], 1):  # Limit to 5 items
            summary_bullets.append(
                BulletPoint(
                    text=f"{i}. {item.title}",
                    provenance=[],
                    confidence=1.0
                )
            )
        
        if len(outline_items) > 5:
            summary_bullets.append(
                BulletPoint(
                    text=f"... and {len(outline_items) - 5} more topics",
                    provenance=[],
                    confidence=1.0
                )
            )
        
        return Slide(
            id=f"slide_{self.slide_counter}",
            type=SlideType.CONTENT,
            title="Summary",
            content=summary_bullets,
            metadata={
                "slide_number": self.slide_counter,
                "is_summary": True
            }
        )
    
    def export_to_json(self, slide_deck: SlideDeck, filepath: str):
        """Export slide deck to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(slide_deck.dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Slide deck exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting slide deck: {str(e)}")
            raise
    
    def load_from_json(self, filepath: str) -> SlideDeck:
        """Load slide deck from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return SlideDeck(**data)
            
        except Exception as e:
            logger.error(f"Error loading slide deck: {str(e)}")
            raise
    
    def get_slide_statistics(self, slide_deck: SlideDeck) -> Dict[str, Any]:
        """Get statistics about the slide deck"""
        total_slides = len(slide_deck.slides)
        content_slides = len([s for s in slide_deck.slides if s.type == SlideType.CONTENT])
        title_slides = len([s for s in slide_deck.slides if s.type == SlideType.TITLE])
        
        total_bullets = sum(len(slide.content) for slide in slide_deck.slides)
        
        # Count slides with provenance
        slides_with_provenance = len([
            slide for slide in slide_deck.slides 
            if any(bullet.provenance for bullet in slide.content)
        ])
        
        return {
            "total_slides": total_slides,
            "content_slides": content_slides,
            "title_slides": title_slides,
            "total_bullets": total_bullets,
            "slides_with_provenance": slides_with_provenance,
            "average_bullets_per_slide": total_bullets / total_slides if total_slides > 0 else 0
        }