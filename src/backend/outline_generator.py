# generates outline structure from pdf content or narrative
from typing import List, Dict, Any
import logging
import json
import re

from .models import OutlineItem, Chunk
from .chunking_embedding import VectorStore
from .llm_service import get_llm_service

logger = logging.getLogger(__name__)

# generates outline sections from content or narrative
class OutlineGenerator:
    # initialize with llm service
    def __init__(self):
        self.llm_service = get_llm_service()
    
    # extract outline sections from narrative text using llm
    def generate_outline_from_narrative(self, narrative: str, pdf_title: str) -> List[OutlineItem]:
        """Generate outline structure from the narrative plan, extracting exact text for each section"""
        logger.info("Generating outline from narrative plan")
        
        # first, try to extract sections directly from markdown headings
        import re
        sections = []
        
        # look for markdown headings like **title** or ## title
        heading_pattern = r'\*\*([^*]+)\*\*|##\s+([^\n]+)'
        matches = list(re.finditer(heading_pattern, narrative))
        
        if matches:
            # extract sections based on markdown headings
            for i, match in enumerate(matches):
                # get the title (either from **title** or ## title)
                title = match.group(1) if match.group(1) else match.group(2)
                title = title.strip()
                
                # find the text content for this section
                section_start = match.end()
                section_end = matches[i + 1].start() if i + 1 < len(matches) else len(narrative)
                section_text = narrative[section_start:section_end].strip()
                
                # clean up the section text - remove extra whitespace but keep paragraphs
                section_text = re.sub(r'\n{3,}', '\n\n', section_text)
                section_text = section_text.strip()
                
                # use the first 1-2 sentences as description, or first 150 chars
                if section_text:
                    sentences = re.split(r'[.!?]+', section_text)
                    sentences = [s.strip() for s in sentences if s.strip()]
                    if sentences:
                        if len(sentences) <= 2:
                            description = section_text[:200].strip()
                        else:
                            description = '. '.join(sentences[:2]) + '.'
                    else:
                        description = section_text[:200].strip()
                else:
                    description = ""
                
                sections.append({
                    "title": title,
                    "description": description,
                    "text": section_text  # store full text for later use
                })
        
        # if we found sections from markdown, use them
        if sections:
            outline_items = []
            for idx, section in enumerate(sections, start=1):
                outline_items.append(
                    OutlineItem(
                        title=self._clean_title(section["title"]),
                        description=section["description"],
                        level=1,
                        order=idx
                    )
                )
            logger.info(f"Extracted {len(outline_items)} outline items directly from narrative headings")
            return outline_items
        
        # fallback: use llm to extract sections if no markdown headings found
        prompt = f"""You are analyzing a UX case study narrative to extract the key sections/story beats.

CASE STUDY NARRATIVE:
{narrative}

YOUR TASK:
Extract 6-10 key sections from this narrative. Each section should represent a major story beat or phase in the case study story. The sections should follow the narrative's flow and structure.

REQUIREMENTS:
1. If the narrative already uses explicit Markdown headings (e.g., "**tldr;**", "**Team and Constraints**"), REUSE THOSE EXACT TITLES in the same order.
2. Extract ALL sections from the narrative - you MUST include every major section mentioned, including "The Final Outcome" and "What Didn't Go as Planned" if they appear in the narrative.
3. Extract sections that align with the narrative's story structure, with SPECIAL EMPHASIS on process sections: ideation, wireframes, mockups, prototyping, testing, iterations, design process, etc.
4. Create clear, descriptive titles for any additional sections you must infer. Use simple, direct, student-friendly language that matches the style of a visual report outline. Avoid academic or formal phrasing.
5. Order sections to match the narrative's flow. Do NOT reorder the narrative's headings.
6. Each section should have a brief description (1-2 sentences) that explains what content belongs in that section based on the narrative. Use simple, clear, human language - match the style and tone of a student's visual report outline. Write like you're explaining to a friend. Keep it direct and straightforward.
7. The sections should reflect the story beats in the narrative, with PARTICULAR ATTENTION to design process sections (ideation, wireframes, mockups, prototyping, testing, iterations)
8. Ensure process-related sections are included: ideation, wireframes, mockups, prototyping, testing, and iterations
9. CRITICAL: You MUST include "The Final Outcome" and "What Didn't Go as Planned" sections if they appear in the narrative - do not skip any sections
10. CRITICAL: Match the style and tone of the visual report outline in the PDF - use simple, direct, student-friendly language. Avoid complex words, jargon, or academic phrasing.

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
                    "content": "You are an expert at analyzing narratives and extracting structured outlines. You identify key story beats and create logical section divisions that reflect the narrative's flow. CRITICAL: Match the style and tone of a visual report outline in a PDF - use simple, direct, student-friendly language. Avoid complex words, jargon, academic phrasing, or convoluted sentences. Write like a student explaining their project to a friend - keep it straightforward and clear."
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
    
    # generate outline by detecting topics in content and ordering them canonically
    def generate_outline(self, pdf_title: str, chunks: List[Chunk], max_sections: int = 8) -> List[OutlineItem]:
        """Generate outline with content-aware ordering and guaranteed coverage of key design topics.
        - Derive topics from content (not PDF headers)
        - Order slides in a canonical design narrative when possible
        - Fall back to PDF order when topics are ambiguous
        """

        # standard order for design case study sections
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

        # scan chunks to find which topics are present
        topic_candidates: Dict[str, Dict[str, Any]] = {}
        for chunk in chunks:
            text = chunk.text
            page = chunk.page_number
            # check if chunk matches any topic pattern
            for topic, patterns in topic_patterns.items():
                if any(re.search(p, text, flags=re.IGNORECASE) for p in patterns):
                    if topic not in topic_candidates:
                        topic_candidates[topic] = {
                            "first_page": page,
                            "snippets": [text[:300]],
                        }
                    else:
                        # track earliest page and collect snippets
                        topic_candidates[topic]["first_page"] = min(topic_candidates[topic]["first_page"], page)
                        if len(topic_candidates[topic]["snippets"]) < 3:
                            topic_candidates[topic]["snippets"].append(text[:300])

        # build ordered list following canonical order
        ordered_topics = [t for t in topic_order if t in topic_candidates]

        # add remaining topics by page order if space available
        if len(ordered_topics) < max_sections:
            remaining = [
                (t, data["first_page"]) for t, data in topic_candidates.items() if t not in ordered_topics
            ]
            remaining.sort(key=lambda x: x[1])
            for t, _ in remaining:
                if len(ordered_topics) >= max_sections:
                    break
                ordered_topics.append(t)

        # create outline items from detected topics
        outline_items: List[OutlineItem] = []
        order_counter = 1

        # helper to create description from text snippets
        def build_desc(snippets: List[str]) -> str:
            joined = " ".join(snippets)
            return self._create_description(joined)

        # create outline items for each detected topic
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
    
    # clean title by removing numbers and formatting
    def _clean_title(self, title: str) -> str:
        """Clean and improve title"""
        
        # remove leading numbers and formatting
        title = re.sub(r'^\d+\.?\s+', '', title)
        title = re.sub(r'^\d{2}\s+', '', title)
        
        # capitalize if all lowercase
        if title.islower():
            title = title.title()
        
        # clean up formatting
        title = title.replace('_', ' ')
        title = ' '.join(title.split())
        
        # limit length
        if len(title) > 60:
            title = title[:57] + "..."
        
        return title.strip()
    
    # create short description from text snippet
    def _create_description(self, text: str) -> str:
        """Create description from text"""
        # use first sentence if substantial, otherwise first 150 chars
        sentences = text.split('.')
        if sentences and len(sentences[0]) > 20:
            desc = sentences[0].strip() + '.'
        else:
            desc = text[:150].strip()
        
        # clean up whitespace
        desc = desc.replace('\n', ' ')
        desc = ' '.join(desc.split())
        
        # add ellipsis if truncated
        if len(text) > len(desc):
            desc += '...'
        
        return desc