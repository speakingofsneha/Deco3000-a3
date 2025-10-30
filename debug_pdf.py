#!/usr/bin/env python3
"""
Debug script to see what's being extracted from the PDF
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.pdf_parser import PDFParser
from src.chunking_embedding import ChunkingEmbeddingService
import logging

logging.basicConfig(level=logging.INFO)

def debug_pdf(pdf_path):
    print("="*60)
    print("DEBUG: PDF Structure Analysis")
    print("="*60)
    
    # Parse PDF
    parser = PDFParser()
    structure = parser.extract_text_and_structure(pdf_path)
    
    print(f"\n1. TITLE: {structure.title}")
    print(f"2. TOTAL PAGES: {structure.total_pages}")
    print(f"3. SECTIONS FOUND: {len(structure.sections)}")
    
    print("\n" + "="*60)
    print("SECTIONS:")
    print("="*60)
    for i, section in enumerate(structure.sections, 1):
        content_preview = ' '.join(section['content'][:3])[:100]
        print(f"\n{i}. {section['title']}")
        print(f"   Page: {section['page']}")
        print(f"   Content items: {len(section['content'])}")
        print(f"   Preview: {content_preview}...")
    
    print("\n" + "="*60)
    print("CHUNKING:")
    print("="*60)
    
    chunking_service = ChunkingEmbeddingService()
    chunks = chunking_service.chunk_text(structure, chunk_size=400, overlap=100)
    
    print(f"Total chunks: {len(chunks)}")
    print("\nFirst 3 chunks:")
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"\n{i}. Chunk ID: {chunk.id}")
        print(f"   Page: {chunk.page_number}")
        print(f"   Section: {chunk.metadata.get('section_title')}")
        print(f"   Length: {len(chunk.text)} chars")
        print(f"   Text preview: {chunk.text[:150]}...")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "anu.pdf"
    
    debug_pdf(pdf_path)