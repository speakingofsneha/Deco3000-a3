#!/usr/bin/env python3
"""
Example usage of the PDF to Slide Deck Converter
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.processing_service import PDFProcessingService
from src.models import PDFProcessingRequest

def main():
    """Example of how to use the processing service directly"""
    
    print("This example uses free local LLM (Llama 3 via Ollama)")
    print("Make sure Ollama is installed and running:")
    print("1. Install Ollama: https://ollama.ai/")
    print("2. Start Ollama: ollama serve")
    print("3. Pull model: ollama pull llama3")
    print()
    
    # Example PDF path (replace with your actual PDF)
    pdf_path = "example.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Please place a PDF file named '{pdf_path}' in the current directory")
        return
    
    print("Processing PDF...")
    
    try:
        # Initialize processing service
        service = PDFProcessingService()
        
        # Create processing request
        request = PDFProcessingRequest(
            pdf_path=pdf_path,
            max_chunks=500,
            chunk_size=400,
            overlap=50
        )
        
        # Process PDF
        response = service.process_pdf(request)
        
        if response.success:
            print(f"✓ Success! Processing took {response.processing_time:.2f} seconds")
            print(f"✓ Generated {len(response.slide_deck.slides)} slides")
            print(f"✓ Slide deck saved to: outputs/{Path(pdf_path).stem}_slides.json")
            
            # Display first few slides
            print("\nFirst few slides:")
            for i, slide in enumerate(response.slide_deck.slides[:3], 1):
                print(f"\n{i}. {slide.title}")
                for bullet in slide.content[:2]:
                    print(f"   • {bullet.text[:100]}...")
        else:
            print(f"✗ Error: {response.message}")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")

if __name__ == "__main__":
    main()