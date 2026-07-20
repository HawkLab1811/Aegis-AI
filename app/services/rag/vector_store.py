"""
Vector Store Service for RAG using ChromaDB.

This service handles:
- Document ingestion and chunking
- Vector embeddings with sentence-transformers or OpenAI
- Similarity search for retrieval
- Per-RAG collection management
- Media file extraction (images, videos, Excel, Word, PowerPoint)
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any

# ChromaDB imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# LangChain imports for document processing
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import (
        TextLoader,
        PyPDFLoader,
        UnstructuredMarkdownLoader,
    )
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Media extractor
from app.services.rag.media_extractor import (
    MediaExtractorService, get_media_extractor,
    IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, EXCEL_EXTENSIONS,
    CSV_EXTENSIONS, WORD_EXTENSIONS, PPT_EXTENSIONS
)


# Project root for fallback
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Data directory - can be overridden by DATA_DIR environment variable
# For Docker, mount a volume at /app/data
DATA_DIR = Path(os.environ.get("DATA_DIR", str(PROJECT_ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Base path for ChromaDB persistence
CHROMA_PERSIST_BASE = DATA_DIR / "chroma_db"

# All media extensions that need special handling
MEDIA_EXTENSIONS = (
    IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | EXCEL_EXTENSIONS |
    CSV_EXTENSIONS | WORD_EXTENSIONS | PPT_EXTENSIONS
)


class VectorStoreService:
    """
    Service for managing vector stores for RAG knowledge bases.
    
    Each RAG has its own ChromaDB collection for isolated vector storage.
    """
    
    def __init__(self, persist_directory: Optional[Path] = None):
        """
        Initialize the vector store service.
        
        Args:
            persist_directory: Base directory for ChromaDB persistence
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is required. Install with: pip install chromadb")
        
        self.persist_directory = persist_directory or CHROMA_PERSIST_BASE
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self._client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Text splitter for chunking documents
        self._text_splitter = None
        if LANGCHAIN_AVAILABLE:
            self._text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
    
    def _get_collection_name(self, rag_id: int) -> str:
        """Get the ChromaDB collection name for a RAG."""
        return f"rag_{rag_id}"
    
    def _get_or_create_collection(self, rag_id: int):
        """Get or create a ChromaDB collection for a RAG."""
        collection_name = self._get_collection_name(rag_id)
        return self._client.get_or_create_collection(
            name=collection_name,
            metadata={"rag_id": str(rag_id)}
        )
    
    def _generate_doc_id(self, content: str, source: str) -> str:
        """Generate a unique document ID based on content and source."""
        hash_input = f"{source}:{content[:500]}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def _load_document(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Load a document and return chunks with metadata.
        Routes media files (images, videos, Excel, Word, PPT) to the
        MediaExtractorService, and text-based files to LangChain loaders.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            List of document chunks with content and metadata
        """
        suffix = file_path.suffix.lower()

        # Route media files to the extractor
        if suffix in MEDIA_EXTENSIONS:
            try:
                extractor = get_media_extractor()
                # Try to attach a vision provider if not set
                if not extractor._vision_provider:
                    self._attach_vision_provider(extractor)
                return extractor.extract(file_path)
            except Exception as e:
                print(f"[VectorStore] Media extraction failed for {file_path}: {e}")
                return [{
                    "content": f"[{suffix.upper()}: {file_path.name}] - Extraction failed: {str(e)}",
                    "metadata": {"source": str(file_path), "media_type": "unknown", "error": str(e)}
                }]

        # Standard text-based document loading
        documents = []

        if not LANGCHAIN_AVAILABLE:
            # Fallback: simple text reading
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    chunk_size = 1000
                    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                    for i, chunk in enumerate(chunks):
                        if chunk.strip():
                            documents.append({
                                "content": chunk,
                                "metadata": {
                                    "source": str(file_path),
                                    "chunk_index": i
                                }
                            })
            except Exception as e:
                print(f"Error loading document {file_path}: {e}")
            return documents

        # Use LangChain loaders based on file type
        try:
            if suffix == '.pdf':
                loader = PyPDFLoader(str(file_path))
            elif suffix == '.md':
                loader = UnstructuredMarkdownLoader(str(file_path))
            else:
                loader = TextLoader(str(file_path), encoding='utf-8')

            raw_docs = loader.load()

            if self._text_splitter:
                split_docs = self._text_splitter.split_documents(raw_docs)
            else:
                split_docs = raw_docs

            for i, doc in enumerate(split_docs):
                documents.append({
                    "content": doc.page_content,
                    "metadata": {
                        "source": str(file_path),
                        "chunk_index": i,
                        **doc.metadata
                    }
                })

        except Exception as e:
            print(f"Error loading document {file_path}: {e}")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    documents.append({
                        "content": content,
                        "metadata": {"source": str(file_path)}
                    })
            except Exception as e2:
                print(f"Fallback reading also failed: {e2}")

        return documents

    def _attach_vision_provider(self, extractor: MediaExtractorService):
        """
        Try to find and attach a configured vision-capable engine
        from the database to the media extractor.
        Only uses models known to support vision/image input.
        """
        try:
            from app.core.database import SessionLocal
            from app.models.ai_engine import AIEngine
            from app.core.config import decrypt_value
            from app.services.llm.factory import get_provider

            # Vision-capable model IDs
            VISION_MODELS = {
                "gpt-4o", "gpt-4o-vision", "gpt-4o-mini",
                "gemini-3-flash", "gemini-3-pro",
                "gemini-2-5-flash", "gemini-2-5-pro",
                "mimo-v2-omni", "mimo-v2.5-pro", "mimo-v2.5",
                "claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5",
            }

            db = SessionLocal()
            try:
                engines = db.query(AIEngine).filter(
                    AIEngine.is_active == True,
                    AIEngine.api_key_encrypted.isnot(None)
                ).all()

                if not engines:
                    print("[VectorStore] No engines with API keys configured - vision extraction unavailable")
                    return

                # First pass: find a vision-specific model
                for engine in engines:
                    if engine.model_id in VISION_MODELS:
                        try:
                            provider = get_provider(
                                provider_name=engine.provider,
                                model_id=engine.model_id,
                                api_key=engine.api_key_encrypted,
                                encrypted=True,
                                base_url=engine.base_url
                            )
                            extractor.set_vision_provider(provider)
                            print(f"[VectorStore] Attached vision provider: {engine.display_name}")
                            return
                        except Exception as e:
                            print(f"[VectorStore] Failed to create provider for {engine.display_name}: {e}")
                            continue

                # No vision model found - log warning
                configured_names = [e.display_name for e in engines]
                print(f"[VectorStore] WARNING: No vision-capable engine found. Configured: {configured_names}")
                print(f"[VectorStore] Image/video descriptions will be empty. Configure a vision model (GPT-4o, Gemini, MiMo Omni, etc.)")

            finally:
                db.close()

        except Exception as e:
            print(f"[VectorStore] Could not attach vision provider: {e}")
    
    def add_document(
        self,
        rag_id: int,
        file_path: Path,
        file_id: Optional[int] = None
    ) -> int:
        """
        Add a document to a RAG's vector store.
        
        Args:
            rag_id: ID of the RAG knowledge base
            file_path: Path to the document file
            file_id: Optional file ID for tracking
            
        Returns:
            Number of chunks added
        """
        collection = self._get_or_create_collection(rag_id)
        
        # Load and chunk the document
        doc_chunks = self._load_document(file_path)
        
        if not doc_chunks:
            return 0
        
        # Add chunks to ChromaDB
        ids = []
        documents = []
        metadatas = []
        
        for chunk in doc_chunks:
            doc_id = self._generate_doc_id(chunk["content"], str(file_path))
            ids.append(doc_id)
            documents.append(chunk["content"])
            metadata = chunk["metadata"].copy()
            if file_id:
                metadata["file_id"] = str(file_id)
            metadatas.append(metadata)
        
        # Add to collection (ChromaDB handles embeddings automatically)
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
        
        return len(doc_chunks)
    
    def remove_document(self, rag_id: int, file_path: str) -> bool:
        """
        Remove a document from a RAG's vector store.
        
        Args:
            rag_id: ID of the RAG knowledge base
            file_path: Path of the document to remove
            
        Returns:
            True if documents were removed
        """
        try:
            collection = self._get_or_create_collection(rag_id)
            
            # Find documents with matching source
            results = collection.get(
                where={"source": file_path}
            )
            
            if results and results['ids']:
                collection.delete(ids=results['ids'])
                return True
            
            return False
        except Exception as e:
            print(f"Error removing document: {e}")
            return False
    
    def query(
        self,
        rag_id: int,
        query_text: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for relevant documents.
        
        Args:
            rag_id: ID of the RAG knowledge base
            query_text: The query text
            n_results: Number of results to return
            
        Returns:
            List of relevant document chunks with metadata and scores
        """
        try:
            collection = self._get_or_create_collection(rag_id)
            
            # Check if collection has documents
            if collection.count() == 0:
                return []
            
            # Query the collection
            results = collection.query(
                query_texts=[query_text],
                n_results=min(n_results, collection.count())
            )
            
            # Format results
            formatted_results = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            print(f"Error querying vector store: {e}")
            return []
    
    def get_context_for_query(
        self,
        rag_id: int,
        query_text: str,
        max_tokens: int = 2000
    ) -> str:
        """
        Get formatted context from RAG for a query.
        
        Args:
            rag_id: ID of the RAG knowledge base
            query_text: The user's query
            max_tokens: Approximate max tokens for context (chars / 4)
            
        Returns:
            Formatted context string for LLM prompt
        """
        results = self.query(rag_id, query_text, n_results=5)
        
        if not results:
            return ""
        
        # Build context string
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Approximate chars to tokens
        
        for i, result in enumerate(results, 1):
            content = result["content"]
            source = result["metadata"].get("source", "Unknown")
            source_name = Path(source).name if source != "Unknown" else source
            
            part = f"[Source: {source_name}]\n{content}\n"
            
            if total_chars + len(part) > max_chars:
                break
            
            context_parts.append(part)
            total_chars += len(part)
        
        if context_parts:
            return "### Relevant Knowledge Base Context:\n\n" + "\n---\n".join(context_parts)
        
        return ""
    
    def delete_collection(self, rag_id: int) -> bool:
        """
        Delete an entire RAG collection.
        
        Args:
            rag_id: ID of the RAG knowledge base
            
        Returns:
            True if collection was deleted
        """
        try:
            collection_name = self._get_collection_name(rag_id)
            self._client.delete_collection(collection_name)
            return True
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False
    
    def get_collection_stats(self, rag_id: int) -> Dict[str, Any]:
        """
        Get statistics for a RAG collection.
        
        Args:
            rag_id: ID of the RAG knowledge base
            
        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self._get_or_create_collection(rag_id)
            return {
                "rag_id": rag_id,
                "document_count": collection.count(),
                "collection_name": self._get_collection_name(rag_id)
            }
        except Exception as e:
            return {
                "rag_id": rag_id,
                "error": str(e)
            }


# Singleton instance
_vector_store_service: Optional[VectorStoreService] = None


def get_vector_store_service() -> VectorStoreService:
    """Get the global vector store service instance."""
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service
