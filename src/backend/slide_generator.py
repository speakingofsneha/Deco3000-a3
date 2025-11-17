# imports for type hints, json handling, logging, and file paths
from typing import List, Dict, Any, Tuple
import json
import uuid
from datetime import datetime
import logging
from pathlib import Path
import math

# import data models for slides and outlines
from .models import Slide, SlideDeck, SlideType, OutlineItem, BulletPoint

logger = logging.getLogger(__name__)

# class that generates slide decks from outlines and bullet points
class SlideGenerator:
    # initialize slide generator with counter and layout options
    def __init__(self):
        # track slide numbers as we create them
        self.slide_counter = 0
        # cycle through different media layouts for variety
        self.media_layout_cycle = [
            "media-description-below",
            "media-description-above",
            "two-media-description",
            "heading-two-media-description-below",
            "heading-two-media-description",
            "heading-four-points-media-left",
            "heading-description-media-right"
        ]

    # split bullets into smaller groups for slides with media layouts
    def _chunk_bullets_for_media(self, bullets: List[BulletPoint], max_group_size: int = 6) -> List[List[BulletPoint]]:
        """split media-heavy sections into bite-sized clusters for flexible layouts"""
        groups = []
        # create groups of bullets up to max_group_size
        for i in range(0, len(bullets), max_group_size):
            groups.append(bullets[i:i + max_group_size])
        return groups

    # determine where to place media between bullets in inline layouts
    def _build_media_breakpoints(self, bullet_count: int) -> List[int]:
        """create positions where inline media placeholders should appear"""
        # place media every 3 bullets starting from bullet 3
        return [idx for idx in range(3, bullet_count + 1, 3)]

    # choose the best layout based on number of bullets and group position
    def _select_layout_for_group(self, bullet_count: int, group_index: int, has_media: bool) -> str:
        """pick a layout that matches the amount of text we are showing, ensuring layout diversity"""
        # for media slides, select from media layouts with diversity
        if has_media:
            # single bullet: alternate between single and double media layouts for diversity
            if bullet_count == 1:
                # mix of 1-image and 2-image layouts
                single_media_layouts = ["media-description-below", "media-description-above"]
                # every 3rd slide with 1 bullet gets 2 images for variety
                if group_index % 3 == 0:
                    return "two-media-description"
                return single_media_layouts[group_index % len(single_media_layouts)]
            
            # two bullets: mix between 1-image and 2-image layouts
            if bullet_count == 2:
                # alternate between 2-image and 1-image layouts
                if group_index % 2 == 0:
                    return "two-media-description"  # 2 images
                else:
                    return "media-description-below"  # 1 image
            
            # three bullets: mix between 1-image and 2-image layouts
            if bullet_count == 3:
                layouts = [
                    "heading-two-media-description-below",  # 2 images
                    "heading-two-media-description",  # 2 images
                    "heading-description-media-right"  # 1 image
                ]
                return layouts[group_index % len(layouts)]
            
            # four bullets: mix between 1-image and 2-image layouts
            if bullet_count == 4:
                layouts = [
                    "heading-four-points-media-left",  # 1 image
                    "heading-two-media-description-below",  # 2 images
                    "heading-two-media-description"  # 2 images
                ]
                return layouts[group_index % len(layouts)]
            
            # 5+ bullets: alternate between different multi-media layouts (mix of 1 and 2 images)
            if bullet_count >= 5:
                layouts = [
                    "heading-two-media-description-below",  # 2 images
                    "heading-two-media-description",  # 2 images
                    "heading-description-media-right",  # 1 image
                    "heading-four-points-media-left"  # 1 image
                ]
                return layouts[group_index % len(layouts)]
            
            # fallback for media slides
            return "media-description-below"
        
        # text-only layouts based on bullet count
        if bullet_count == 1:
            return "key-statement"
        if bullet_count == 2:
            return "two-col-description"
        if bullet_count == 3:
            # alternate between horizontal and list
            return "three-points-list" if group_index % 2 == 0 else "three-points"
        if bullet_count == 4:
            # alternate between horizontal and grid
            return "four-points-grid" if group_index % 2 == 0 else "four-points"
        if bullet_count >= 5:
            # for 5+ bullets, use grid layouts
            if bullet_count == 6:
                return "six-points"
            # default to four-points-grid-below for 5+ bullets
            return "four-points-grid-below"
        
        # fallback
        return "key-statement"
    
    # check if a slide should include media based on its content
    def _should_have_media(self, title: str, bullets: List[BulletPoint]) -> tuple[bool, str]:
        """
        Intelligently detect if a slide should have media based on content.
        Returns: (has_media: bool, media_type: str)
        Media types: 'interface', 'data', 'flow', 'diagram'
        """
        # combine title and bullet text to analyze content
        combined_text = title.lower() + " " + " ".join([b.text.lower() for b in bullets])
        
        # keywords that indicate interface or ui content
        interface_keywords = [
            'solution overview', 'user interface', 'ui design', 'ui mockup',
            'prototype', 'wireframe', 'mockup', 'screen design', 'interface design',
            'dashboard design', 'application interface', 'web app interface'
        ]
        
        # keywords for user flow diagrams
        flow_keywords = [
            'user flow', 'user journey', 'user pathway', 'interaction flow',
            'navigation flow', 'workflow diagram', 'process flow'
        ]
        
        # keywords for data visualization content
        data_keywords = [
            'survey results', 'survey data', 'research findings', 'research results',
            'data visualization', 'chart', 'graph', 'statistics', 'survey responses',
            'interview results', 'study results', 'questionnaire results'
        ]
        
        # keywords for architecture or system diagrams
        diagram_keywords = [
            'system architecture', 'architecture diagram', 'system diagram',
            'flow diagram', 'process diagram', 'schema diagram', 'blueprint'
        ]
        
        # check content against keyword lists and return appropriate media type
        if any(keyword in combined_text for keyword in interface_keywords):
            return (True, 'interface')
        
        if any(keyword in combined_text for keyword in flow_keywords):
            return (True, 'flow')
        
        if any(keyword in combined_text for keyword in data_keywords):
            return (True, 'data')
        
        if any(keyword in combined_text for keyword in diagram_keywords):
            return (True, 'diagram')
        
        # default: enable media layouts for all case study sections
        if bullets:
            return (True, 'interface')
        
        return (False, '')
    
    # main method to create a complete slide deck from outline and bullets
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
        
        # create title slide using pdf filename without extension
        pdf_filename = Path(source_pdf).stem
        title_slide = self._create_title_slide(pdf_filename, source_pdf)
        slides.append(title_slide)
        
        # create content slides for each outline section
        for outline_item in outline_items:
            if outline_item.title in bullets_data:
                # create slides with bullets if available
                content_slides = self._create_content_slides(
                    outline_item, 
                    bullets_data[outline_item.title]
                )
                slides.extend(content_slides)
            else:
                # create simple slide if no bullets available
                simple_slide = self._create_simple_slide(outline_item)
                slides.append(simple_slide)
        
        # build final slide deck object
        slide_deck = SlideDeck(
            title=pdf_filename,
            slides=slides,
            metadata=metadata or {},
            created_at=datetime.now().isoformat(),
            source_pdf=source_pdf
        )
        
        logger.info(f"Generated slide deck with {len(slides)} slides")
        return slide_deck
    
    # create the first slide with the document title
    def _create_title_slide(self, title: str, source_pdf: str) -> Slide:
        """Create title slide"""
        self.slide_counter += 1
        
        # return slide object with title and metadata
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
    
    # create one or more slides for an outline section with bullets
    def _create_content_slides(
        self, 
        outline_item: OutlineItem, 
        bullets: List[BulletPoint]
    ) -> List[Slide]:
        """Create content slides for an outline item"""
        slides = []
        
        # return simple slide if no bullets available
        if not bullets:
            return [self._create_simple_slide(outline_item)]
        
        slide_title = outline_item.title
        
        # check if this section should include media
        has_media, media_type = self._should_have_media(slide_title, bullets)
        
        # create special problem statement slide format
        if "problem statement" in slide_title.lower() or "how might we" in slide_title.lower():
            # use exact text from bullets (which comes from outline description) without any modifications
            statement_text = ""
            if bullets and len(bullets) > 0:
                statement_text = bullets[0].text.strip()
            elif outline_item.description:
                statement_text = outline_item.description.strip()
            
            # create problem statement slide with exact text
            self.slide_counter += 1
            problem_slide = Slide(
                id=f"slide_{self.slide_counter}",
                type=SlideType.CONTENT,
                title="Problem Statement",
                content=[
                    BulletPoint(
                        text=statement_text or "How might we … ?",
                        provenance=[],
                        confidence=1.0
                    )
                ],
                provenance=[],
                        metadata={
                            "slide_number": self.slide_counter,
                            "outline_item": outline_item.title,
                    "has_media": False,
                    "media_type": "",
                        "layout": "problem-statement",
                    "is_media_slide": False
                }
            )
            return [problem_slide]
        
        # create slides with media layouts if content suggests media
        if has_media:
            layout_index = 0
            # split bullets into groups for multiple slides
            bullet_groups = self._chunk_bullets_for_media(bullets)
            
            # create a slide for each bullet group
            for group_index, group in enumerate(bullet_groups):
                self.slide_counter += 1
                
                # collect page numbers from bullets for provenance
                slide_pages = set()
                clean_bullets = []
                for bullet in group:
                    # create clean bullet without provenance
                    clean_bullet = BulletPoint(
                        text=bullet.text,
                        provenance=[],
                        confidence=bullet.confidence
                    )
                    clean_bullets.append(clean_bullet)
                    
                    # collect page references
                    for prov in bullet.provenance:
                        if prov.startswith("Page "):
                            slide_pages.add(prov)
                
                # determine layout and media placement
                slide_provenance = sorted(list(slide_pages))
                layout = self._select_layout_for_group(len(clean_bullets), layout_index, has_media=True)
                layout_index += 1
                
                # calculate how many media slots this slide needs
                # for two-media layouts, need 2 slots; for single media, need 1
                if layout in ["two-media-description", "heading-two-media-description-below", "heading-two-media-description"]:
                    media_slots = 2
                else:
                    media_slots = 1
                
                # create slide with media metadata
                slide = Slide(
                    id=f"slide_{self.slide_counter}",
                    type=SlideType.CONTENT,
                    title=slide_title,
                    content=clean_bullets,
                    provenance=slide_provenance,
                    metadata={
                        "slide_number": self.slide_counter,
                        "outline_item": outline_item.title,
                        "has_media": True,
                        "media_type": media_type or "interface",
                        "layout": layout,
                        "is_media_slide": False,
                        "media_slots": media_slots,
                        "media_panel": layout_index
                    }
                )
                slides.append(slide)
        else:
            # create text-only slides with appropriate layouts
            # group bullets by layout requirements
            layout_index = 0
            bullet_groups = self._chunk_bullets_for_media(bullets, max_group_size=6)
            
            # create a slide for each bullet group
            for group_idx, bullet_group in enumerate(bullet_groups):
                self.slide_counter += 1
                
                # collect page numbers from bullets for slide provenance
                slide_pages = set()
                clean_bullets = []
                for bullet in bullet_group:
                    # create clean bullet without individual provenance
                    clean_bullet = BulletPoint(
                        text=bullet.text,
                        provenance=[],
                        confidence=bullet.confidence
                    )
                    clean_bullets.append(clean_bullet)
                    
                    # collect page references for slide-level provenance
                    for prov in bullet.provenance:
                        if prov.startswith("Page "):
                            slide_pages.add(prov)
                
                slide_provenance = sorted(list(slide_pages))
                
                # select appropriate text-only layout
                layout = self._select_layout_for_group(len(clean_bullets), layout_index, has_media=False)
                layout_index += 1
                
                # create slide with layout metadata
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
                        "layout": layout,
                        "is_media_slide": False
                    }
                )
                slides.append(slide)
        
        return slides
    
    # create a simple slide when no bullets are provided
    def _create_simple_slide(self, outline_item: OutlineItem) -> Slide:
        """Create a simple slide when no bullets are available"""
        self.slide_counter += 1
        
        # create a bullet from the outline description
        bullets = [
            BulletPoint(
                text=outline_item.description,
                provenance=[],
                confidence=0.5
            )
        ]
        # check if media should be included
        has_media, media_type = self._should_have_media(outline_item.title, bullets)
        
        # use side-by-side layout if media is needed
        layout = "image-left-text-right" if has_media else "default"
        
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
                "layout": layout,
                "is_media_slide": has_media
            }
        )
    
    # create a summary slide listing outline sections
    def _create_summary_slide(self, outline_items: List[OutlineItem]) -> Slide:
        """Create summary slide"""
        self.slide_counter += 1
        
        # create bullets for first 5 outline items
        summary_bullets = []
        for i, item in enumerate(outline_items[:5], 1):
            summary_bullets.append(
                BulletPoint(
                    text=f"{i}. {item.title}",
                    provenance=[],
                    confidence=1.0
                )
            )
        
        # add note if there are more items
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
    
    # save slide deck to a json file
    def export_to_json(self, slide_deck: SlideDeck, filepath: str):
        """Export slide deck to JSON file"""
        try:
            # write slide deck data as formatted json
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(slide_deck.dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Slide deck exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Error exporting slide deck: {str(e)}")
            raise
    
    # load slide deck from a json file
    def load_from_json(self, filepath: str) -> SlideDeck:
        """Load slide deck from JSON file"""
        try:
            # read json file and create slide deck object
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return SlideDeck(**data)
            
        except Exception as e:
            logger.error(f"Error loading slide deck: {str(e)}")
            raise
    
    # calculate statistics about the slide deck
    def get_slide_statistics(self, slide_deck: SlideDeck) -> Dict[str, Any]:
        """Get statistics about the slide deck"""
        # count different types of slides
        total_slides = len(slide_deck.slides)
        content_slides = len([s for s in slide_deck.slides if s.type == SlideType.CONTENT])
        title_slides = len([s for s in slide_deck.slides if s.type == SlideType.TITLE])
        
        # count total bullets across all slides
        total_bullets = sum(len(slide.content) for slide in slide_deck.slides)
        
        # count slides that have provenance information
        slides_with_provenance = len([
            slide for slide in slide_deck.slides 
            if any(bullet.provenance for bullet in slide.content)
        ])
        
        # return statistics dictionary
        return {
            "total_slides": total_slides,
            "content_slides": content_slides,
            "title_slides": title_slides,
            "total_bullets": total_bullets,
            "slides_with_provenance": slides_with_provenance,
            "average_bullets_per_slide": total_bullets / total_slides if total_slides > 0 else 0
        }