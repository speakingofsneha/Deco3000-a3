# vector embeddings and similarity search using faiss
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

# data structure for storing vector embeddings and chunks
@dataclass
class VectorStore:
    index: faiss.Index
    chunks: List[Chunk]
    model: SentenceTransformer

# service for chunking text and creating embeddings for semantic search
class ChunkingEmbeddingService:
    # initialize with sentence transformer model
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.vector_store = None
    
    # split pdf text into chunks for embedding, organized by page
    def chunk_text(self, pdf_structure: PDFStructure, chunk_size: int = 2000, overlap: int = 200) -> List[Chunk]:
        """Chunk text with IDs and metadata - page-based chunking (1-2 chunks per page)"""
        chunks = []
        chunk_id = 0
        
        # group all content by page number
        pages_content = {}
        for section in pdf_structure.sections:
            page = section['page']
            if page not in pages_content:
                pages_content[page] = []
            pages_content[page].extend(section['content'])
        
        # add paragraphs to their pages (default to page 1 if no page info)
        for para in pdf_structure.paragraphs:
            page = 1  # default page if not specified
            if page not in pages_content:
                pages_content[page] = []
            pages_content[page].append(para)
        
        # process each page separately to create chunks
        for page_num in sorted(pages_content.keys()):
            page_text = " ".join(pages_content[page_num])
            
            if not page_text.strip():
                continue
            
            # split page text into chunks with overlap
            page_chunks = self._split_text_into_chunks(
                page_text, 
                chunk_size, 
                overlap
            )
            
            # create chunk objects with metadata
            for i, chunk_text in enumerate(page_chunks):
                chunk = Chunk(
                    id=f"chunk_{chunk_id}",
                    text=chunk_text,
                    page_number=page_num,
                    chunk_index=i,
                    metadata={
                        'section_title': f'Page {page_num}',
                        'section_page': page_num,
                        'chunk_length': len(chunk_text),
                        'pdf_title': pdf_structure.title,
                        'chunks_per_page': len(page_chunks)
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
        
        logger.info(f"Created {len(chunks)} chunks across {len(pages_content)} pages (avg {len(chunks)/len(pages_content):.1f} chunks per page)")
        return chunks
    
    # split text into overlapping chunks, trying to break at sentence boundaries
    def _split_text_into_chunks(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        # return single chunk if text is small enough
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        # create chunks with overlap
        while start < len(text):
            end = start + chunk_size
            
            # try to break at sentence boundaries for cleaner chunks
            if end < len(text):
                # look for period in last 100 chars of chunk
                search_start = max(start + chunk_size - 100, start)
                sentence_end = text.rfind('.', search_start, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # try other punctuation marks
                    for punct in ['!', '?', '\n']:
                        punct_pos = text.rfind(punct, search_start, end)
                        if punct_pos > start:
                            end = punct_pos + 1
                            break
            
            # extract chunk and add if not empty
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # move start position back by overlap amount
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    # create vector embeddings for chunks and build faiss index for similarity search
    def create_embeddings(self, chunks: List[Chunk]) -> VectorStore:
        """Create embeddings and FAISS index"""
        if not chunks:
            raise ValueError("No chunks provided for embedding")
        
        # extract text from chunks
        texts = [chunk.text for chunk in chunks]
        
        # generate embeddings using sentence transformer
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        # create faiss index for fast similarity search
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # inner product for cosine similarity
        
        # normalize embeddings for cosine similarity calculation
        faiss.normalize_L2(embeddings)
        index.add(embeddings.astype('float32'))
        
        # store index and chunks together
        self.vector_store = VectorStore(
            index=index,
            chunks=chunks,
            model=self.model
        )
        
        logger.info(f"Created FAISS index with {index.ntotal} vectors")
        return self.vector_store
    
    # search for chunks similar to the query using vector similarity
    def search_similar_chunks(self, query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Search for similar chunks using FAISS"""
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        
        # create embedding for the query text
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # search faiss index for most similar chunks
        scores, indices = self.vector_store.index.search(
            query_embedding.astype('float32'), 
            top_k
        )
        
        # return chunks with their similarity scores
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.vector_store.chunks):
                chunk = self.vector_store.chunks[idx]
                results.append((chunk, float(score)))
        
        return results
    
    # save vector store to disk for later use
    def save_vector_store(self, filepath: str):
        """Save vector store to disk"""
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        
        # create directory if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # save faiss index to file
        faiss.write_index(self.vector_store.index, f"{filepath}.index")
        
        # save chunks and model metadata using pickle
        with open(f"{filepath}.chunks", 'wb') as f:
            pickle.dump({
                'chunks': self.vector_store.chunks,
                'model_name': self.model.get_sentence_embedding_dimension()
            }, f)
        
        logger.info(f"Vector store saved to {filepath}")
    
    # load vector store from disk
    def load_vector_store(self, filepath: str):
        """Load vector store from disk"""
        # load faiss index from file
        index = faiss.read_index(f"{filepath}.index")
        
        # load chunks and metadata from pickle file
        with open(f"{filepath}.chunks", 'rb') as f:
            data = pickle.load(f)
        
        # recreate vector store object
        self.vector_store = VectorStore(
            index=index,
            chunks=data['chunks'],
            model=self.model
        )
        
        logger.info(f"Vector store loaded from {filepath}")
        return self.vector_store