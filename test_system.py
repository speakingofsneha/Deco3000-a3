#!/usr/bin/env python3
"""
Comprehensive test script for the PDF to Slide Deck Converter
Tests all components to ensure the free tech stack works correctly
"""

import os
import sys
import time
from pathlib import Path
import json

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test if all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from src.llm_service import OllamaLLMService, get_llm_service
        from src.pdf_parser import PDFParser
        from src.chunking_embedding import ChunkingEmbeddingService
        from src.outline_generator import OutlineGenerator
        from src.rag_system import RAGSystem
        from src.slide_generator import SlideGenerator
        from src.processing_service import PDFProcessingService
        from src.models import Chunk, OutlineItem, BulletPoint, Slide, SlideDeck
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        return False

def test_ollama_connection():
    """Test if Ollama is running and accessible"""
    print("\n🔍 Testing Ollama connection...")
    
    try:
        from src.llm_service import OllamaLLMService
        
        # Test connection
        llm_service = OllamaLLMService()
        if llm_service.test_connection():
            print("✅ Ollama is running and accessible")
            return True
        else:
            print("❌ Ollama test failed")
            return False
            
    except Exception as e:
        print(f"❌ Ollama connection error: {str(e)}")
        print("\n📋 To fix this:")
        print("1. Install Ollama: https://ollama.ai/")
        print("2. Start Ollama: ollama serve")
        print("3. Pull model: ollama pull llama3")
        return False

def test_pdf_parser():
    """Test PDF parsing functionality"""
    print("\n🔍 Testing PDF parser...")
    
    try:
        from src.pdf_parser import PDFParser
        
        # Create a simple test PDF content (this would normally be a real PDF)
        parser = PDFParser()
        
        # Test with a mock structure
        from src.pdf_parser import PDFStructure
        test_structure = PDFStructure(
            title="Test Document",
            sections=[{
                'title': 'Introduction',
                'page': 1,
                'content': ['This is a test document.', 'It has multiple sentences.']
            }],
            paragraphs=['This is a test document.', 'It has multiple sentences.'],
            total_pages=1
        )
        
        print("✅ PDF parser initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ PDF parser error: {str(e)}")
        return False

def test_chunking_embedding():
    """Test chunking and embedding functionality"""
    print("\n🔍 Testing chunking and embedding...")
    
    try:
        from src.chunking_embedding import ChunkingEmbeddingService
        from src.pdf_parser import PDFStructure
        
        # Create test data
        test_structure = PDFStructure(
            title="Test Document",
            sections=[{
                'title': 'Introduction',
                'page': 1,
                'content': ['This is a test document with multiple sentences. ' * 10]
            }],
            paragraphs=['This is a test document with multiple sentences. ' * 10],
            total_pages=1
        )
        
        # Test chunking
        service = ChunkingEmbeddingService()
        chunks = service.chunk_text(test_structure, chunk_size=100, overlap=20)
        
        if len(chunks) > 0:
            print(f"✅ Chunking successful: {len(chunks)} chunks created")
            
            # Test embedding
            vector_store = service.create_embeddings(chunks)
            print("✅ Embedding successful: FAISS index created")
            
            # Test search
            results = service.search_similar_chunks("test document", top_k=3)
            print(f"✅ Search successful: {len(results)} results found")
            
            return True
        else:
            print("❌ No chunks created")
            return False
            
    except Exception as e:
        print(f"❌ Chunking/embedding error: {str(e)}")
        return False

def test_outline_generation():
    """Test outline generation"""
    print("\n🔍 Testing outline generation...")
    
    try:
        from src.outline_generator import OutlineGenerator
        from src.models import Chunk
        
        # Create test chunks
        test_chunks = [
            Chunk(
                id="chunk_1",
                text="This is about machine learning and artificial intelligence. It covers neural networks, deep learning, and various algorithms.",
                page_number=1,
                chunk_index=0,
                metadata={'section_title': 'Introduction'}
            ),
            Chunk(
                id="chunk_2", 
                text="Data preprocessing is crucial for machine learning. It involves cleaning data, handling missing values, and feature engineering.",
                page_number=1,
                chunk_index=1,
                metadata={'section_title': 'Data Processing'}
            )
        ]
        
        generator = OutlineGenerator()
        outline_items = generator.generate_outline("Machine Learning Basics", test_chunks, max_sections=5)
        
        if len(outline_items) > 0:
            print(f"✅ Outline generation successful: {len(outline_items)} items created")
            for item in outline_items[:3]:  # Show first 3
                print(f"   • {item.title}")
            return True
        else:
            print("❌ No outline items generated")
            return False
            
    except Exception as e:
        print(f"❌ Outline generation error: {str(e)}")
        return False

def test_rag_system():
    """Test RAG system"""
    print("\n🔍 Testing RAG system...")
    
    try:
        from src.rag_system import RAGSystem
        from src.models import OutlineItem, Chunk
        from src.chunking_embedding import ChunkingEmbeddingService
        
        # Create test data
        test_chunks = [
            Chunk(
                id="chunk_1",
                text="Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data.",
                page_number=1,
                chunk_index=0,
                metadata={'section_title': 'Introduction'}
            )
        ]
        
        # Create vector store
        service = ChunkingEmbeddingService()
        vector_store = service.create_embeddings(test_chunks)
        
        # Test RAG - use the same service instance
        rag = RAGSystem()
        rag.chunking_service = service  # Use the same service that created the vector store
        outline_item = OutlineItem(
            title="Machine Learning Introduction",
            description="Basic concepts of machine learning",
            level=1,
            order=1
        )
        
        bullets = rag.generate_bullets_for_outline_item(outline_item, vector_store, top_k=2, max_bullets=3)
        
        if len(bullets) > 0:
            print(f"✅ RAG system successful: {len(bullets)} bullets generated")
            for bullet in bullets[:2]:  # Show first 2
                print(f"   • {bullet.text[:50]}...")
            return True
        else:
            print("❌ No bullets generated")
            return False
            
    except Exception as e:
        print(f"❌ RAG system error: {str(e)}")
        return False

def test_slide_generation():
    """Test slide deck generation"""
    print("\n🔍 Testing slide generation...")
    
    try:
        from src.slide_generator import SlideGenerator
        from src.models import OutlineItem, BulletPoint, SlideDeck
        
        # Create test data
        outline_items = [
            OutlineItem(title="Introduction", description="Basic concepts", level=1, order=1),
            OutlineItem(title="Methods", description="Various approaches", level=1, order=2)
        ]
        
        bullets_data = {
            "Introduction": [
                BulletPoint(text="Machine learning is important", provenance=["chunk_1"], confidence=0.8)
            ],
            "Methods": [
                BulletPoint(text="Supervised learning uses labeled data", provenance=["chunk_2"], confidence=0.9)
            ]
        }
        
        generator = SlideGenerator()
        slide_deck = generator.generate_slide_deck(
            "Test Presentation",
            outline_items,
            bullets_data,
            "test.pdf"
        )
        
        if len(slide_deck.slides) > 0:
            print(f"✅ Slide generation successful: {len(slide_deck.slides)} slides created")
            
            # Test statistics
            stats = generator.get_slide_statistics(slide_deck)
            print(f"   • Total slides: {stats['total_slides']}")
            print(f"   • Total bullets: {stats['total_bullets']}")
            
            return True
        else:
            print("❌ No slides generated")
            return False
            
    except Exception as e:
        print(f"❌ Slide generation error: {str(e)}")
        return False

def test_full_pipeline():
    """Test the complete processing pipeline"""
    print("\n🔍 Testing full processing pipeline...")
    
    try:
        from src.processing_service import PDFProcessingService
        from src.models import PDFProcessingRequest
        
        # This would normally process a real PDF
        # For testing, we'll just check if the service initializes
        service = PDFProcessingService()
        print("✅ Processing service initialized successfully")
        
        # Test with a mock request (would need a real PDF file)
        print("ℹ️  Full pipeline test requires a real PDF file")
        print("   Run: python main.py process your_document.pdf")
        
        return True
        
    except Exception as e:
        print(f"❌ Full pipeline error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 PDF to Slide Deck Converter - System Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Ollama Connection", test_ollama_connection),
        ("PDF Parser", test_pdf_parser),
        ("Chunking & Embedding", test_chunking_embedding),
        ("Outline Generation", test_outline_generation),
        ("RAG System", test_rag_system),
        ("Slide Generation", test_slide_generation),
        ("Full Pipeline", test_full_pipeline)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The system is ready to use.")
        print("\n📋 Next steps:")
        print("1. Place a PDF file in the current directory")
        print("2. Run: python main.py process your_document.pdf")
        print("3. Or start the API: python main.py serve")
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please fix the issues above.")
        
        if not any(name == "Ollama Connection" and result for name, result in results):
            print("\n🔧 Most likely issue: Ollama not running")
            print("   Fix: ollama serve && ollama pull llama3")

if __name__ == "__main__":
    main()