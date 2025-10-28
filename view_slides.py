#!/usr/bin/env python3
"""
Simple script to view slide content in a readable format
"""

import json
import sys
from pathlib import Path

def view_slides(json_file):
    """View slides in a readable format"""
    
    # Load the slide deck
    with open(json_file, 'r') as f:
        slide_deck = json.load(f)
    
    print(f"🎯 SLIDE DECK: {slide_deck['title']}")
    print("=" * 60)
    print(f"📄 Source: {slide_deck['source_pdf']}")
    print(f"📅 Created: {slide_deck['created_at']}")
    print(f"📊 Total Slides: {len(slide_deck['slides'])}")
    print("=" * 60)
    
    for i, slide in enumerate(slide_deck['slides'], 1):
        print(f"\n📌 SLIDE {i}: {slide['title']}")
        print(f"   Type: {slide['type']}")
        print(f"   Bullets: {len(slide['content'])}")
        print("-" * 40)
        
        for j, bullet in enumerate(slide['content'], 1):
            print(f"   {j}. {bullet['text']}")
            if bullet['provenance']:
                print(f"      📎 Sources: {', '.join(bullet['provenance'])}")
            print(f"      🎯 Confidence: {bullet['confidence']:.2f}")
            print()
        
        print("-" * 40)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python view_slides.py <json_file>")
        sys.exit(1)
    
    json_file = sys.argv[1]
    if not Path(json_file).exists():
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    
    view_slides(json_file)