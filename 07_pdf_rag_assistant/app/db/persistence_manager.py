"""
Persistence Manager for PDF RAG Assistant

Handles saving and loading of FAISS index, document metadata, and chunk data
to maintain state across server restarts.
"""

import json
import os
import tempfile
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import faiss
import numpy as np

logger = logging.getLogger(__name__)


class PersistenceManager:
    """Manages persistence of FAISS index, document metadata, and chunk data."""
    
    def __init__(self, persistence_dir: str = "persistence"):
        """
        Initialize the persistence manager.
        
        Args:
            persistence_dir: Directory to store persistence files
        """
        self.persistence_dir = Path(persistence_dir)
        self.persistence_dir.mkdir(exist_ok=True)
        
        # Define file paths
        self.faiss_index_path = self.persistence_dir / "faiss_index.bin"
        self.metadata_path = self.persistence_dir / "metadata.json"
        self.chunks_path = self.persistence_dir / "chunks.json"
        
        logger.info(f"Persistence manager initialized with directory: {self.persistence_dir}")
    
    def _atomic_write(self, file_path: Path, content: bytes) -> None:
        """
        Write content to file atomically using temporary file and move.
        
        Args:
            file_path: Target file path
            content: Content to write as bytes
        """
        try:
            # Create temporary file in the same directory
            temp_fd, temp_path = tempfile.mkstemp(
                dir=file_path.parent,
                prefix=f".{file_path.name}.tmp"
            )
            
            try:
                # Write content to temporary file
                with os.fdopen(temp_fd, 'wb') as temp_file:
                    temp_file.write(content)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())
                
                # Atomically move temporary file to target
                shutil.move(temp_path, file_path)
                logger.debug(f"Atomically wrote {len(content)} bytes to {file_path}")
                
            except Exception:
                # Clean up temporary file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
                
        except Exception as e:
            logger.error(f"Failed to write {file_path}: {e}")
            raise
    
    def _atomic_write_json(self, file_path: Path, data: Any) -> None:
        """
        Write JSON data to file atomically.
        
        Args:
            file_path: Target file path
            data: Data to serialize as JSON
        """
        json_content = json.dumps(data, indent=2, ensure_ascii=False)
        self._atomic_write(file_path, json_content.encode('utf-8'))
    
    def save_faiss_index(self, index: faiss.Index) -> None:
        """
        Save FAISS index to disk using native FAISS methods.
        
        Args:
            index: FAISS index to save
        """
        try:
            # Use temporary file for atomic write
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.persistence_dir,
                prefix=".faiss_index.tmp"
            )
            os.close(temp_fd)  # Close file descriptor, FAISS will handle the file
            
            try:
                # Write index using FAISS native method
                faiss.write_index(index, temp_path)
                
                # Atomically move to final location
                shutil.move(temp_path, self.faiss_index_path)
                logger.info(f"FAISS index saved to {self.faiss_index_path}")
                
            except Exception:
                # Clean up temporary file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
                
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            raise
    
    def load_faiss_index(self, dimension: int = 1536) -> faiss.Index:
        """
        Load FAISS index from disk or create new empty index.
        
        Args:
            dimension: Vector dimension for new index if file doesn't exist
            
        Returns:
            Loaded FAISS index or new empty index
        """
        if not self.faiss_index_path.exists():
            logger.info("No existing FAISS index found, creating new empty index")
            return faiss.IndexFlatL2(dimension)
        
        try:
            index = faiss.read_index(str(self.faiss_index_path))
            
            # Check dimension compatibility
            if index.d != dimension:
                logger.warning(f"FAISS index dimension mismatch: file has {index.d}, requested {dimension}")
                logger.info("Creating new empty index due to dimension mismatch")
                return faiss.IndexFlatL2(dimension)
            
            logger.info(f"FAISS index loaded from {self.faiss_index_path}, size: {index.ntotal}")
            return index
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index from {self.faiss_index_path}: {e}")
            logger.info("Creating new empty index due to corruption")
            return faiss.IndexFlatL2(dimension)
    
    def create_document_metadata(self, filename: str, file_hash: str, 
                                chunks: List[Dict[str, Any]], index: faiss.Index) -> Dict[str, Any]:
        """
        Create comprehensive document metadata including all required fields.
        
        Args:
            filename: Name of the processed file
            file_hash: MD5 hash of the file content
            chunks: List of processed chunks
            index: FAISS index
            
        Returns:
            Dictionary containing complete document metadata
        """
        document_names = set(chunk.get("doc", "") for chunk in chunks)
        
        return {
            "filename": filename,
            "file_hash": file_hash,
            "processing_timestamp": datetime.now().isoformat(),
            "document_count": len(document_names),
            "total_chunks": len(chunks),
            "faiss_index_size": index.ntotal,
            "documents": list(document_names)
        }

    def save_document_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Save document metadata to JSON file.
        
        Args:
            metadata: Dictionary containing document metadata including:
                     - filename: Name of the processed file
                     - file_hash: MD5 hash of the file content  
                     - processing_timestamp: When the document was processed
                     - document_count: Number of documents processed
        """
        try:
            # Ensure required fields are present with defaults
            enhanced_metadata = {
                "filename": metadata.get("filename", "unknown"),
                "file_hash": metadata.get("file_hash", ""),
                "processing_timestamp": metadata.get("processing_timestamp", datetime.now().isoformat()),
                "document_count": metadata.get("document_count", 0),
                "total_chunks": metadata.get("total_chunks", 0),
                "faiss_index_size": metadata.get("faiss_index_size", 0),
                "documents": metadata.get("documents", []),
                "last_saved": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            self._atomic_write_json(self.metadata_path, enhanced_metadata)
            logger.info(f"Document metadata saved to {self.metadata_path}")
            
        except Exception as e:
            logger.error(f"Failed to save document metadata: {e}")
            raise
    def create_document_metadata(self, filename: str, file_hash: str,
                                chunks: List[Dict[str, Any]], index: faiss.Index) -> Dict[str, Any]:
        """
        Create comprehensive document metadata including all required fields.

        Args:
            filename: Name of the processed file
            file_hash: MD5 hash of the file content
            chunks: List of processed chunks
            index: FAISS index

        Returns:
            Dictionary containing complete document metadata
        """
        document_names = set(chunk.get("doc", "") for chunk in chunks)

        return {
            "filename": filename,
            "file_hash": file_hash,
            "processing_timestamp": datetime.now().isoformat(),
            "document_count": len(document_names),
            "total_chunks": len(chunks),
            "faiss_index_size": index.ntotal,
            "documents": list(document_names)
        }
    
    def load_document_metadata(self) -> Dict[str, Any]:
        """
        Load document metadata from JSON file.
        
        Returns:
            Dictionary containing document metadata, empty dict if file doesn't exist
        """
        if not self.metadata_path.exists():
            logger.info("No existing metadata found, returning empty metadata")
            return {}
        
        try:
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"Document metadata loaded from {self.metadata_path}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load document metadata from {self.metadata_path}: {e}")
            logger.info("Returning empty metadata due to corruption")
            return {}
    
    def save_chunk_data(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Save chunk data to JSON file.
        
        Args:
            chunks: List of chunk dictionaries with text content and metadata
        """
        try:
            chunk_data = {
                "chunks": chunks,
                "count": len(chunks),
                "last_saved": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            self._atomic_write_json(self.chunks_path, chunk_data)
            logger.info(f"Chunk data saved to {self.chunks_path}, count: {len(chunks)}")
            
        except Exception as e:
            logger.error(f"Failed to save chunk data: {e}")
            raise
    
    def load_chunk_data(self) -> List[Dict[str, Any]]:
        """
        Load chunk data from JSON file.
        
        Returns:
            List of chunk dictionaries, empty list if file doesn't exist
        """
        if not self.chunks_path.exists():
            logger.info("No existing chunk data found, returning empty list")
            return []
        
        try:
            with open(self.chunks_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunks = data.get("chunks", [])
            logger.info(f"Chunk data loaded from {self.chunks_path}, count: {len(chunks)}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to load chunk data from {self.chunks_path}: {e}")
            logger.info("Returning empty chunk list due to corruption")
            return []
    
    def save_complete_state(self, index: faiss.Index, chunks: List[Dict[str, Any]], 
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save complete system state (FAISS index, chunks, and metadata).
        
        Args:
            index: FAISS index to save
            chunks: List of chunk dictionaries
            metadata: Optional metadata dictionary
        """
        try:
            # Save FAISS index
            self.save_faiss_index(index)
            
            # Save chunk data
            self.save_chunk_data(chunks)
            
            # Save metadata
            if metadata is None:
                # Extract document information from chunks
                document_names = set(chunk.get("doc", "") for chunk in chunks)
                metadata = {
                    "document_count": len(document_names),
                    "total_chunks": len(chunks),
                    "faiss_index_size": index.ntotal,
                    "documents": list(document_names),  # List of processed document filenames
                    "processing_timestamp": datetime.now().isoformat()
                }
            
            self.save_document_metadata(metadata)
            
            logger.info("Complete system state saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save complete state: {e}")
            raise
    
    def load_complete_state(self, dimension: int = 1536) -> tuple[faiss.Index, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Load complete system state (FAISS index, chunks, and metadata).
        
        Args:
            dimension: Vector dimension for new index if needed
            
        Returns:
            Tuple of (faiss_index, chunks_list, metadata_dict)
        """
        try:
            # Load components
            index = self.load_faiss_index(dimension)
            chunks = self.load_chunk_data()
            metadata = self.load_document_metadata()
            
            # Validate consistency
            if self._validate_state_consistency(index, chunks, metadata):
                logger.info("Complete system state loaded and validated successfully")
            else:
                logger.warning("State inconsistency detected, but continuing with loaded data")
            
            return index, chunks, metadata
            
        except Exception as e:
            logger.error(f"Failed to load complete state: {e}")
            # Return empty state on error
            return faiss.IndexFlatL2(dimension), [], {}
    
    def _validate_state_consistency(self, index: faiss.Index, chunks: List[Dict[str, Any]], 
                                      metadata: Dict[str, Any]) -> bool:
            """
            Validate consistency between FAISS index, chunks, and metadata.

            Args:
                index: FAISS index
                chunks: List of chunks
                metadata: Metadata dictionary

            Returns:
                True if state is consistent, False otherwise
            """
            try:
                # Validate FAISS index dimensions match expected values (Requirement 7.1)
                if not self._validate_faiss_dimensions(index):
                    return False

                # Verify document count matches FAISS index size (Requirement 7.2)
                if not self._validate_document_count_consistency(index, chunks, metadata):
                    return False

                # Additional metadata consistency checks
                if not self._validate_metadata_consistency(chunks, metadata):
                    return False

                logger.debug("State consistency validation passed")
                return True

            except Exception as e:
                logger.error(f"Error during state validation: {e}")
                return False

    def _validate_faiss_dimensions(self, index: faiss.Index, expected_dimension: int = 1536) -> bool:
        """
        Validate that FAISS index dimensions match expected values.

        Args:
            index: FAISS index to validate
            expected_dimension: Expected dimension size (default 1536 for OpenAI embeddings)

        Returns:
            True if dimensions are valid, False otherwise
        """
        try:
            actual_dimension = index.d
            if actual_dimension != expected_dimension:
                logger.warning(
                    f"FAISS index dimension mismatch: expected {expected_dimension}, "
                    f"got {actual_dimension}. This may indicate corrupted state or "
                    f"incompatible embedding model."
                )
                return False

            logger.debug(f"FAISS index dimension validation passed: {actual_dimension}")
            return True

        except Exception as e:
            logger.error(f"Error validating FAISS dimensions: {e}")
            return False

    def _validate_document_count_consistency(self, index: faiss.Index, chunks: List[Dict[str, Any]], 
                                           metadata: Dict[str, Any]) -> bool:
        """
        Verify that the number of documents matches the FAISS index size.

        Args:
            index: FAISS index
            chunks: List of chunks
            metadata: Metadata dictionary

        Returns:
            True if document counts are consistent, False otherwise
        """
        try:
            faiss_size = index.ntotal
            chunk_count = len(chunks)

            # Primary check: FAISS index size should match chunk count
            if faiss_size != chunk_count:
                logger.warning(
                    f"Document count inconsistency detected: FAISS index contains "
                    f"{faiss_size} vectors but found {chunk_count} chunks. "
                    f"This indicates corrupted or incomplete state."
                )
                return False

            # Secondary check: metadata should match actual counts
            if metadata:
                expected_chunks = metadata.get("total_chunks")
                expected_faiss_size = metadata.get("faiss_index_size")

                if expected_chunks is not None and expected_chunks != chunk_count:
                    logger.warning(
                        f"Metadata chunk count ({expected_chunks}) doesn't match "
                        f"actual chunk count ({chunk_count})"
                    )
                    return False

                if expected_faiss_size is not None and expected_faiss_size != faiss_size:
                    logger.warning(
                        f"Metadata FAISS size ({expected_faiss_size}) doesn't match "
                        f"actual FAISS size ({faiss_size})"
                    )
                    return False

            logger.debug(f"Document count consistency validation passed: {chunk_count} chunks")
            return True

        except Exception as e:
            logger.error(f"Error validating document count consistency: {e}")
            return False

    def _validate_metadata_consistency(self, chunks: List[Dict[str, Any]], 
                                     metadata: Dict[str, Any]) -> bool:
        """
        Validate metadata consistency with chunk data.

        Args:
            chunks: List of chunks
            metadata: Metadata dictionary

        Returns:
            True if metadata is consistent, False otherwise
        """
        try:
            if not metadata:
                logger.debug("No metadata to validate")
                return True

            # Validate document count in metadata
            if "documents" in metadata:
                metadata_doc_count = len(metadata["documents"])
                # Count unique documents in chunks
                unique_docs = set()
                for chunk in chunks:
                    if "document_name" in chunk:
                        unique_docs.add(chunk["document_name"])

                actual_doc_count = len(unique_docs)
                if metadata_doc_count != actual_doc_count:
                    logger.warning(
                        f"Metadata document count ({metadata_doc_count}) doesn't match "
                        f"actual unique documents in chunks ({actual_doc_count})"
                    )
                    return False

            # Validate timestamp consistency
            if "last_updated" in metadata:
                last_updated = metadata["last_updated"]
                if not isinstance(last_updated, str):
                    logger.warning("Invalid last_updated timestamp format in metadata")
                    return False

            logger.debug("Metadata consistency validation passed")
            return True

        except Exception as e:
            logger.error(f"Error validating metadata consistency: {e}")
            return False

    def validate_and_recover_state(self, dimension: int = 1536) -> tuple[faiss.Index, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validate loaded state and recover from inconsistencies if detected.

        This method implements Requirement 7.3: Log warnings and reinitialize 
        with empty state if state inconsistency is detected.

        Args:
            dimension: Expected FAISS index dimension

        Returns:
            Tuple of (index, chunks, metadata) - either loaded or empty state
        """
        try:
            # Attempt to load existing state
            index, chunks, metadata = self.load_complete_state(dimension)

            # Validate the loaded state
            if self._validate_state_consistency(index, chunks, metadata):
                logger.info(f"Successfully loaded and validated persisted state with {len(chunks)} chunks")
                return index, chunks, metadata
            else:
                # State is inconsistent - log warning and reinitialize
                logger.warning(
                    "State inconsistency detected during validation. "
                    "Reinitializing with empty state to prevent system failures."
                )
                return self._create_empty_state(dimension)

        except Exception as e:
            logger.error(f"Error loading persisted state: {e}. Initializing with empty state.")
            return self._create_empty_state(dimension)

    def _create_empty_state(self, dimension: int = 1536) -> tuple[faiss.Index, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Create empty state for initialization.

        Args:
            dimension: FAISS index dimension

        Returns:
            Tuple of (empty_index, empty_chunks, empty_metadata)
        """
        empty_index = faiss.IndexFlatL2(dimension)
        empty_chunks = []
        empty_metadata = {
            "documents": {},
            "total_chunks": 0,
            "faiss_index_size": 0,
            "last_updated": datetime.now().isoformat(),
            "version": "1.0"
        }

        logger.info("Initialized empty state")
        return empty_index, empty_chunks, empty_metadata

    
    def clear_persisted_state(self) -> None:
        """
        Clear all persisted state files atomically.
        """
        try:
            files_to_remove = [
                self.faiss_index_path,
                self.metadata_path,
                self.chunks_path
            ]
            
            # Remove files that exist
            removed_count = 0
            for file_path in files_to_remove:
                if file_path.exists():
                    file_path.unlink()
                    removed_count += 1
            
            logger.info(f"Cleared {removed_count} persistence files")
            
        except Exception as e:
            logger.error(f"Failed to clear persisted state: {e}")
            raise
    
    def get_persistence_status(self) -> Dict[str, Any]:
        """
        Get current persistence status and health information.
        
        Returns:
            Dictionary containing persistence status information
        """
        try:
            status = {
                "persistence_dir": str(self.persistence_dir),
                "files": {
                    "faiss_index": {
                        "exists": self.faiss_index_path.exists(),
                        "path": str(self.faiss_index_path),
                        "size_bytes": self.faiss_index_path.stat().st_size if self.faiss_index_path.exists() else 0
                    },
                    "metadata": {
                        "exists": self.metadata_path.exists(),
                        "path": str(self.metadata_path),
                        "size_bytes": self.metadata_path.stat().st_size if self.metadata_path.exists() else 0
                    },
                    "chunks": {
                        "exists": self.chunks_path.exists(),
                        "path": str(self.chunks_path),
                        "size_bytes": self.chunks_path.stat().st_size if self.chunks_path.exists() else 0
                    }
                }
            }
            
            # Add metadata info if available
            if self.metadata_path.exists():
                try:
                    metadata = self.load_document_metadata()
                    status["last_saved"] = metadata.get("last_saved")
                    status["document_count"] = metadata.get("document_count", 0)
                    status["total_chunks"] = metadata.get("total_chunks", 0)
                except Exception:
                    status["metadata_error"] = "Failed to read metadata"
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get persistence status: {e}")
            return {"error": str(e)}

    def create_document_metadata(self, filename: str, file_hash: str, 
                                chunks: List[Dict[str, Any]], index: faiss.Index) -> Dict[str, Any]:
        """
        Create comprehensive document metadata including all required fields.
        
        Args:
            filename: Name of the processed file
            file_hash: MD5 hash of the file content
            chunks: List of processed chunks
            index: FAISS index
            
        Returns:
            Dictionary containing complete document metadata
        """
        document_names = set(chunk.get("doc", "") for chunk in chunks)
        
        return {
            "filename": filename,
            "file_hash": file_hash,
            "processing_timestamp": datetime.now().isoformat(),
            "document_count": len(document_names),
            "total_chunks": len(chunks),
            "faiss_index_size": index.ntotal,
            "documents": list(document_names)
        }


# Global persistence manager instance
persistence_manager = PersistenceManager()