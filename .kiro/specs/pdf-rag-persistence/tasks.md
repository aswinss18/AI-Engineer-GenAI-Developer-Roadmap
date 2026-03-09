# Implementation Plan: PDF RAG Persistence

## Overview

This implementation adds persistence capabilities to the existing PDF RAG assistant system. The approach creates a new `PersistenceManager` class that handles saving and loading of FAISS index, document metadata, and chunk data while maintaining compatibility with the existing cache system and minimal changes to the current architecture.

## Tasks

- [x] 1. Create persistence infrastructure and core interfaces
  - Create `core/persistence_manager.py` with base persistence functionality
  - Define persistence data structures and file paths
  - Set up atomic file operations for safe persistence
  - _Requirements: 1.1, 1.2, 5.3, 5.4_

- [ ] 2. Implement FAISS index persistence
  - [x] 2.1 Add FAISS index save/load methods to PersistenceManager
    - Implement `save_faiss_index()` and `load_faiss_index()` methods
    - Use FAISS native `write_index()` and `read_index()` functions
    - Handle index file corruption with error logging and fallback
    - _Requirements: 1.1, 1.3, 1.4_
  
  - [ ]* 2.2 Write unit tests for FAISS persistence
    - Test successful save/load operations
    - Test corruption handling and fallback behavior
    - Test empty index initialization
    - _Requirements: 1.1, 1.4_

- [ ] 3. Implement document metadata persistence
  - [x] 3.1 Add document metadata save/load methods
    - Create `save_document_metadata()` and `load_document_metadata()` methods
    - Store filename, file hash, processing timestamp, and document count in JSON
    - Ensure metadata consistency with FAISS index
    - _Requirements: 2.1, 2.2, 2.4_
  
  - [ ]* 3.2 Write unit tests for metadata persistence
    - Test metadata save/load operations
    - Test metadata consistency validation
    - Test JSON serialization edge cases
    - _Requirements: 2.1, 2.2, 2.4_

- [ ] 4. Implement chunk data persistence
  - [x] 4.1 Add chunk data save/load methods
    - Create `save_chunk_data()` and `load_chunk_data()` methods
    - Store text content, document name, page number, and chunk index
    - Ensure chunk order matches FAISS index order
    - _Requirements: 3.1, 3.2, 3.4_
  
  - [ ]* 4.2 Write unit tests for chunk data persistence
    - Test chunk data save/load operations
    - Test chunk order consistency
    - Test large chunk data handling
    - _Requirements: 3.1, 3.2, 3.4_

- [x] 5. Checkpoint - Ensure core persistence functionality works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Integrate persistence with vector store
  - [x] 6.1 Modify vector_store.py to use PersistenceManager
    - Add persistence manager instance to vector_store module
    - Update `add_embeddings()` to trigger incremental saves
    - Update `clear_documents()` to clear persisted state
    - _Requirements: 5.1, 5.2, 8.2, 8.3_
  
  - [ ]* 6.2 Write integration tests for vector store persistence
    - Test document addition triggers persistence
    - Test clear operation removes persisted state
    - Test vector store state consistency
    - _Requirements: 5.1, 8.2, 8.3_

- [ ] 7. Implement automatic state loading on startup
  - [x] 7.1 Add startup state loading to main.py
    - Create startup event handler to load persisted state
    - Load FAISS index, documents, and metadata on server start
    - Log number of documents loaded during startup
    - Handle missing or corrupted state gracefully
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ]* 7.2 Write tests for startup state loading
    - Test successful state restoration
    - Test empty state initialization
    - Test corrupted state handling
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 8. Implement state consistency validation
  - [x] 8.1 Add state validation methods to PersistenceManager
    - Validate FAISS index dimensions match expected values
    - Verify document count matches FAISS index size
    - Log warnings and reinitialize on inconsistency detection
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [ ]* 8.2 Write tests for state validation
    - Test dimension validation
    - Test document count validation
    - Test inconsistency detection and recovery
    - _Requirements: 7.1, 7.2, 7.3_

- [ ] 9. Add persistence status and management endpoints
  - [x] 9.1 Add persistence status endpoint to main.py
    - Create `/persistence/status` endpoint showing persistence health
    - Include loaded document count, last save time, and validation status
    - _Requirements: 7.4_
  
  - [x] 9.2 Add clear persisted state endpoint
    - Create `/persistence/clear` endpoint to remove all persisted data
    - Implement atomic clear operation to prevent partial corruption
    - Reset to empty state while preserving cache system
    - _Requirements: 8.1, 8.2, 8.4_
  
  - [ ]* 9.3 Write tests for persistence endpoints
    - Test status endpoint returns correct information
    - Test clear endpoint removes all persisted data
    - Test clear operation atomicity
    - _Requirements: 7.4, 8.1, 8.4_

- [ ] 10. Ensure cache system compatibility
  - [x] 10.1 Verify cache system integration
    - Test that per-file caching continues to work independently
    - Verify `/cache/clear` endpoint doesn't affect persisted state
    - Ensure no conflicts between cache and persistence systems
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [ ]* 10.2 Write integration tests for cache compatibility
    - Test cache operations don't interfere with persistence
    - Test persistence operations don't interfere with cache
    - Test independent clearing of cache vs persistence
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 11. Final integration and validation
  - [-] 11.1 Integration testing and error handling
    - Test complete workflow: upload PDF, restart server, query documents
    - Verify all persistence operations work together correctly
    - Test error scenarios and recovery mechanisms
    - _Requirements: All requirements_
  
  - [ ]* 11.2 Write end-to-end tests
    - Test full persistence workflow
    - Test server restart scenarios
    - Test error recovery and fallback behavior
    - _Requirements: All requirements_

- [ ] 12. Final checkpoint - Ensure all functionality works
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation maintains backward compatibility with existing cache system
- Persistence files will be stored in a new `persistence/` directory
- All persistence operations use atomic file writes to prevent corruption
- The existing vector_store.py global state approach is preserved for minimal changes