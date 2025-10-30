from typing import List, Dict, Any
import json
import uuid
from datetime import datetime
import logging

from .models import Slide, SlideDeck, SlideType, OutlineItem, BulletPoint

logger = logging.getLogger(__name__)

class SlideGenerator:
    def __init__(self):
        self.slide_counter = 0
    
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
        
        # Split bullets into slides (max 4 bullets per slide)
        max_bullets_per_slide = 4
        bullet_groups = [
            bullets[i:i + max_bullets_per_slide] 
            for i in range(0, len(bullets), max_bullets_per_slide)
        ]
        
        for group_idx, bullet_group in enumerate(bullet_groups):
            self.slide_counter += 1
            
            slide_title = outline_item.title
            
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
                    "total_parts": len(bullet_groups)
                }
            )
            slides.append(slide)
        
        return slides
    
    def _create_simple_slide(self, outline_item: OutlineItem) -> Slide:
        """Create a simple slide when no bullets are available"""
        self.slide_counter += 1
        
        return Slide(
            id=f"slide_{self.slide_counter}",
            type=SlideType.CONTENT,
            title=outline_item.title,
            content=[
                BulletPoint(
                    text=outline_item.description,
                    provenance=[],
                    confidence=0.5
                )
            ],
            provenance=[],
            metadata={
                "slide_number": self.slide_counter,
                "outline_item": outline_item.title,
                "is_simple": True
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