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
    
    def generate_outline_from_narrative(self, narrative: str, pdf_title: str) -> List[OutlineItem]:
        """Generate outline structure from the narrative plan"""
        logger.info("Generating outline from narrative plan")
        
        prompt = f"""You are analyzing a UX case study narrative to extract the key sections/story beats.

CASE STUDY NARRATIVE:
{narrative}

YOUR TASK:
Extract 6-10 key sections from this narrative. Each section should represent a major story beat or phase in the case study story. The sections should follow the narrative's flow and structure.

REQUIREMENTS:
1. If the narrative already uses explicit Markdown headings (e.g., "**tldr;**", "**Team and Constraints**"), REUSE THOSE EXACT TITLES in the same order.
2. Extract sections that align with the narrative's story structure, with SPECIAL EMPHASIS on process sections: ideation, wireframes, mockups, prototyping, testing, iterations, design process, etc.
3. Create clear, descriptive titles for any additional sections you must infer (e.g., "Understanding the Problem", "User Research Insights", "Ideation and Concept Development", "Wireframes and Early Designs", "Mockups and Visual Design", "Prototyping Process", "Testing and Iterations", etc.)
4. Order sections to match the narrative's flow. Do NOT reorder the narrative's headings.
5. Each section should have a brief description (1-2 sentences) that explains what content belongs in that section based on the narrative
6. The sections should reflect the story beats in the narrative, with PARTICULAR ATTENTION to design process sections (ideation, wireframes, mockups, prototyping, testing, iterations)
7. Ensure process-related sections are included: ideation, wireframes, mockups, prototyping, testing, and iterations

OUTPUT FORMAT:
Return a JSON array of sections, each with:
- "title": A clear, descriptive title for the section
- "description": A brief description of what content belongs in this section based on the narrative

Example format:
[
  {{"title": "Understanding the Problem", "description": "The user's challenges and pain points that motivated this project"}},
  {{"title": "Research and Discovery", "description": "The research methods and key findings that informed the design"}},
  ...
]

Return ONLY the JSON array, no other text."""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert at analyzing narratives and extracting structured outlines. You identify key story beats and create logical section divisions that reflect the narrative's flow."
                },
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm_service.generate_chat_completion(
                messages,
                max_tokens=1500,
                temperature=0.3
            )
            
            # Parse JSON response
            response = response.strip()
            # Remove markdown code blocks if present
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
                response = response.strip()
            
            try:
                sections = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    sections = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse JSON from response")
            
            # Convert to OutlineItem list
            outline_items = []
            for idx, section in enumerate(sections[:10], start=1):  # Limit to 10 sections
                title = section.get("title", f"Section {idx}")
                description = section.get("description", "")
                
                outline_items.append(
                    OutlineItem(
                        title=self._clean_title(title),
                        description=description,
                        level=1,
                        order=idx
                    )
                )
            
            logger.info(f"Generated {len(outline_items)} outline items from narrative")
            return outline_items
            
        except Exception as e:
            logger.error(f"Error generating outline from narrative: {str(e)}")
            # Fallback: create a simple outline from narrative structure
            return self._create_fallback_outline_from_narrative(narrative)
    
    def _create_fallback_outline_from_narrative(self, narrative: str) -> List[OutlineItem]:
        """Create a simple fallback outline by identifying key sections in the narrative"""
        # Look for common story beats in the narrative
        sections = []
        narrative_lower = narrative.lower()
        
        # Identify story beats based on narrative content
        story_beats = [
            ("Title of your project", ["title", "project name", "core focus"]),
            ("A brief description", ["brief description", "project covers", "overview", "outcome"]),
            ("Team and your role", ["team", "role", "responsible", "solo"]),
            ("Setting the context", ["context", "assignment brief", "scope", "when", "how long"]),
            ("What's the problem?", ["problem", "challenge", "pain point", "user"]),
            ("Research themes + early findings", ["research", "themes", "findings", "interview", "survey", "insights"]),
            ("Problem statement", ["problem statement", "how might we", "hmw"]),
            ("Assumptions, constraints, and blockers", ["assumptions", "constraints", "blockers", "limitations"]),
            ("Design goals + expected outcomes", ["design goals", "expected outcomes", "behaviours", "experiences"]),
            ("Insights to action - Ideation", ["ideation", "brainstorm", "concepts", "directions", "sketches", "ideation methods"]),
            ("Design process and iterations", ["design process", "iterations", "rounds", "linear", "cyclical", "iterative", "evolution"]),
            ("Wireframes and early designs", ["wireframes", "wireframe", "early designs", "low-fidelity", "sketches", "wireframing"]),
            ("Mockups and visual design", ["mockups", "mockup", "visual design", "color palette", "typography", "spacing", "layout"]),
            ("Prototyping", ["prototyping", "prototype", "tools", "interface decisions", "interactive", "clickable"]),
            ("Testing + feedback", ["testing", "feedback", "sus", "heuristic evaluation", "think aloud", "usability testing", "test rounds"]),
            ("The final outcome", ["final outcome", "final design", "walkthrough", "design goals met"]),
            ("What didn't go as planned", ["didn't go as planned", "adapted", "compromised", "learned", "next time"])
        ]
        
        order = 1
        for title, keywords in story_beats:
            if any(keyword in narrative_lower for keyword in keywords):
                # Extract a relevant description from narrative context
                desc = f"Content related to {title.lower()} as described in the narrative"
                sections.append(
                    OutlineItem(
                        title=title,
                        description=desc,
                        level=1,
                        order=order
                    )
                )
                order += 1
        
        if not sections:
            # Ultimate fallback: create basic structure
            sections = [
                OutlineItem(title="Introduction", description="Project introduction and context", level=1, order=1),
                OutlineItem(title="Research", description="Research findings and insights", level=1, order=2),
                OutlineItem(title="Solution", description="Design solution and approach", level=1, order=3),
                OutlineItem(title="Results", description="Outcomes and impact", level=1, order=4),
            ]
        
        return sections
    
    def generate_outline(self, pdf_title: str, chunks: List[Chunk], max_sections: int = 8) -> List[OutlineItem]:
        """Generate outline with content-aware ordering and guaranteed coverage of key design topics.
        - Derive topics from content (not PDF headers)
        - Order slides in a canonical design narrative when possible
        - Fall back to PDF order when topics are ambiguous
        """

        # Canonical topic order for design visual reports
        topic_order = [
            "Context",
            "Problem Overview",
            "User Research",
            "Key Insights",
            "Ideation",
            "Chosen direction",
            "User Flow",
            "Wireframes",
            "Data Model",
            "Evaluation / Testing",
            "Final Design",
            "Next Steps"
        ]

        # Broad keyword patterns aligned with the canonical order above
        topic_patterns: Dict[str, List[str]] = {
            "Context": [
                r"context", r"background", r"overview", r"introduction",
                r"project brief", r"why", r"scope", r"opportunity",
                r"stakeholder", r"current(\s|-)state", r"existing system"
            ],
            "Problem Overview": [
                r"problem", r"problem statement", r"challenge", r"pain point",
                r"opportunity area", r"current(\s|-)state", r"as-is",
                r"we aim", r"we need", r"why this matters", r"understand"
            ],
            "User Research": [
                r"user research", r"research", r"method", r"interview",
                r"survey", r"questionnaire", r"observation", r"participant",
                r"persona", r"journey map", r"empathy map",
                r"contextual inquiry", r"sample size"
            ],
            "Key Insights": [
                r"insight", r"key insight", r"learning", r"theme",
                r"finding", r"pattern", r"we found", r"we observed",
                r"synthesis", r"affinity", r"quote"
            ],
            "Ideation": [
                r"ideation", r"brainstorm", r"concept", r"idea", 
                r"sketch", r"how might we", r"hmw", r"storyboard",
                r"low(\s|-)fi", r"wire sketch"
            ],
            "Chosen direction": [
                r"chosen solution", r"final concept", r"approach",
                r"selected idea", r"we chose", r"why we selected",
                r"solution direction", r"concept direction"
            ],
            "User Flow": [
                r"user flow", r"task flow", r"navigation flow",
                r"happy path", r"user journey", r"user steps",
                r"interaction flow", r"screen flow"
            ],
            "Wireframes": [
                r"wireframe", r"mockup", r"screen", r"ui flow",
                r"prototype", r"layout", r"fidelity", r"annotation"
            ],
            "Data Model": [
                r"data model", r"system architecture", r"entity",
                r"schema", r"er diagram", r"system design",
                r"information structure", r"information architecture"
            ],
            "Evaluation / Testing": [
                r"usability", r"user test", r"testing", r"feedback",
                r"iteration", r"issue", r"finding", r"participant",
                r"task completion", r"observation", r"result"
            ],
            "Final Design": [
                r"final design", r"hi(\s|-)fi", r"visual design",
                r"final prototype", r"interaction", r"screens",
                r"design system", r"end result"
            ],
            "Next Steps": [
                r"next step", r"future work", r"improvement",
                r"roadmap", r"plan", r"what's next", r"future iteration"
            ],
        }

        # Broad keyword patterns that generalize across reports
        topic_patterns: Dict[str, List[str]] = {
            "Problem Overview": [
                r"problem", r"pain point", r"challenge", r"current(\s|-)state", r"as-is",
                r"understand", r"understanding", r"context", r"background", r"why this", r"we aim"
            ],
            "User Research": [
                r"user research", r"interview", r"survey", r"observation", r"persona", r"journey map"
            ],
            "Key Insights": [
                r"insight", r"finding", r"theme", r"learning", r"we found", r"we observed"
            ],
            "Design Goals": [
                r"goal", r"objective", r"success metric", r"design principle"
            ],
            "Chosen direction": [
                r"solution", r"concept", r"approach", r"ideation", r"prototype", r"wireframe"
            ],
            "User Flow": [
                r"user flow", r"flow diagram", r"task flow", r"screen flow", r"navigation flow"
            ],
            "Wireframes": [
                r"annotated wireframe", r"annotation", r"wireframe", r"screen flow", r"ui flow", r"mockup"
            ],
            "System / Data Model": [
                r"data model", r"entity", r"schema", r"architecture", r"system design", r"er diagram"
            ],
            "Evaluation / Testing": [
                r"usability", r"test", r"evaluation", r"feedback", r"iteration", r"finding"
            ],
            "Next Steps": [
                r"next step", r"future work", r"roadmap", r"plan"
            ],
        }

        # Aggregate topic candidates across chunks
        topic_candidates: Dict[str, Dict[str, Any]] = {}
        for chunk in chunks:
            text = chunk.text
            page = chunk.page_number
            for topic, patterns in topic_patterns.items():
                if any(re.search(p, text, flags=re.IGNORECASE) for p in patterns):
                    if topic not in topic_candidates:
                        topic_candidates[topic] = {
                            "first_page": page,
                            "snippets": [text[:300]],
                        }
                    else:
                        topic_candidates[topic]["first_page"] = min(topic_candidates[topic]["first_page"], page)
                        if len(topic_candidates[topic]["snippets"]) < 3:
                            topic_candidates[topic]["snippets"].append(text[:300])

        # Build ordered list of topics present, respecting canonical order
        ordered_topics = [t for t in topic_order if t in topic_candidates]

        # If we still have room, append additional topics by earliest page
        if len(ordered_topics) < max_sections:
            remaining = [
                (t, data["first_page"]) for t, data in topic_candidates.items() if t not in ordered_topics
            ]
            remaining.sort(key=lambda x: x[1])
            for t, _ in remaining:
                if len(ordered_topics) >= max_sections:
                    break
                ordered_topics.append(t)

        outline_items: List[OutlineItem] = []
        order_counter = 1

        # Helper to create description from snippets
        def build_desc(snippets: List[str]) -> str:
            joined = " ".join(snippets)
            return self._create_description(joined)

        # Create items from detected topics first
        for topic in ordered_topics[:max_sections]:
            data = topic_candidates[topic]
            outline_items.append(
                OutlineItem(
                    title=topic,
                    description=build_desc(data["snippets"]),
                    level=1,
                    order=order_counter,
                )
            )
            order_counter += 1

        logger.info(f"Generated outline with {len(outline_items)} items (content-aware ordering)")
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