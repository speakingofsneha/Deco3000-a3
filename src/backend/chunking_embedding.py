import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Tuple
import uuid
import pickle
import os
import logging
from dataclasses import dataclass

from .models import Chunk
from .pdf_parser import PDFStructure

logger = logging.getLogger(__name__)

@dataclass
class VectorStore:
    index: faiss.Index
    chunks: List[Chunk]
    model: SentenceTransformer

class ChunkingEmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.vector_store = None
    
    def chunk_text(self, pdf_structure: PDFStructure, chunk_size: int = 500, overlap: int = 50) -> List[Chunk]:
        """Chunk text with IDs and metadata"""
        chunks = []
        chunk_id = 0
        
        # Process each section separately
        for section in pdf_structure.sections:
            section_text = " ".join(section['content'])
            
            # Split section into chunks
            section_chunks = self._split_text_into_chunks(
                section_text, 
                chunk_size, 
                overlap
            )
            
            for i, chunk_text in enumerate(section_chunks):
                chunk = Chunk(
                    id=f"chunk_{chunk_id}",
                    text=chunk_text,
                    page_number=section['page'],
                    chunk_index=i,
                    metadata={
                        'section_title': section['title'],
                        'section_page': section['page'],
                        'chunk_length': len(chunk_text),
                        'pdf_title': pdf_structure.title
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
        
        # Also chunk remaining paragraphs that weren't in sections
        remaining_text = " ".join(pdf_structure.paragraphs)
        if remaining_text.strip():
            remaining_chunks = self._split_text_into_chunks(
                remaining_text, 
                chunk_size, 
                overlap
            )
            
            for i, chunk_text in enumerate(remaining_chunks):
                chunk = Chunk(
                    id=f"chunk_{chunk_id}",
                    text=chunk_text,
                    page_number=1,  # Default page
                    chunk_index=i,
                    metadata={
                        'section_title': 'General',
                        'section_page': 1,
                        'chunk_length': len(chunk_text),
                        'pdf_title': pdf_structure.title
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
        
        return chunks
    
    def _split_text_into_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                search_start = max(start + chunk_size - 100, start)
                sentence_end = text.rfind('.', search_start, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for other sentence boundaries
                    for punct in ['!', '?', '\n']:
                        punct_pos = text.rfind(punct, search_start, end)
                        if punct_pos > start:
                            end = punct_pos + 1
                            break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def create_embeddings(self, chunks: List[Chunk]) -> VectorStore:
        """Create embeddings and FAISS index"""
        if not chunks:
            raise ValueError("No chunks provided for embedding")
        
        # Extract texts
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings.astype('float32'))
        
        self.vector_store = VectorStore(
            index=index,
            chunks=chunks,
            model=self.model
        )
        
        logger.info(f"Created FAISS index with {index.ntotal} vectors")
        return self.vector_store
    
    def search_similar_chunks(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Search for similar chunks using FAISS"""
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.vector_store.index.search(
            query_embedding.astype('float32'), 
            top_k
        )
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.vector_store.chunks):
                chunk = self.vector_store.chunks[idx]
                results.append((chunk, float(score)))
        
        return results
    
    def save_vector_store(self, filepath: str):
        """Save vector store to disk"""
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.vector_store.index, f"{filepath}.index")
        
        # Save chunks and model info
        with open(f"{filepath}.chunks", 'wb') as f:
            pickle.dump({
                'chunks': self.vector_store.chunks,
                'model_name': self.model.get_sentence_embedding_dimension()
            }, f)
        
        logger.info(f"Vector store saved to {filepath}")
    
    def load_vector_store(self, filepath: str):
        """Load vector store from disk"""
        # Load FAISS index
        index = faiss.read_index(f"{filepath}.index")
        
        # Load chunks and model info
        with open(f"{filepath}.chunks", 'rb') as f:
            data = pickle.load(f)
        
        self.vector_store = VectorStore(
            index=index,
            chunks=data['chunks'],
            model=self.model
        )
        
        logger.info(f"Vector store loaded from {filepath}")
        return self.vector_store