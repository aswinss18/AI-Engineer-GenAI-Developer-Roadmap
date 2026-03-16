"""
Memory system for ReAct agent - Short-term and Long-term memory
"""

import json
import logging
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import faiss
from .embeddings import get_embedding
import os

logger = logging.getLogger(__name__)

class AgentMemory:
    def __init__(self):
        # Short-term memory (conversation history)
        self.chat_history: List[Dict[str, str]] = []
        
        # Long-term memory (vector-based)
        self.memory_store: List[Dict[str, Any]] = []
        self.memory_index = None
        self.embedding_dim = 1536  # OpenAI embedding dimension
        
        # Memory persistence
        self.memory_file = "persistence/agent_memory.json"
        self.memory_index_file = "persistence/agent_memory_index.bin"
        
        # Initialize memory
        self._initialize_memory()
    
    def _initialize_memory(self):
        """Initialize memory system and load persisted data"""
        try:
            # Create persistence directory
            os.makedirs("persistence", exist_ok=True)
            
            # Initialize FAISS index
            self.memory_index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for similarity
            
            # Load persisted memory
            self._load_memory()
            
            logger.info(f"Memory system initialized with {len(self.memory_store)} stored memories")
            
        except Exception as e:
            logger.error(f"Error initializing memory: {e}")
            # Fallback to empty memory
            self.memory_store = []
            self.memory_index = faiss.IndexFlatIP(self.embedding_dim)
    
    def _load_memory(self):
        """Load persisted memory from disk"""
        try:
            # Load memory store
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.memory_store = json.load(f)
                logger.info(f"Loaded {len(self.memory_store)} memories from disk")
            
            # Load memory index
            if os.path.exists(self.memory_index_file) and len(self.memory_store) > 0:
                self.memory_index = faiss.read_index(self.memory_index_file)
                logger.info(f"Loaded memory index with {self.memory_index.ntotal} vectors")
            
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
    
    def _save_memory(self):
        """Save memory to disk"""
        try:
            # Save memory store
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory_store, f, indent=2, ensure_ascii=False)
            
            # Save memory index
            if self.memory_index.ntotal > 0:
                faiss.write_index(self.memory_index, self.memory_index_file)
            
            logger.info(f"Saved {len(self.memory_store)} memories to disk")
            
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
    
    def add_to_chat_history(self, role: str, content: str):
        """Add message to short-term memory (chat history)"""
        self.chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 messages to prevent context overflow
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]
    
    def get_chat_history(self, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent chat history for context"""
        # Return only role and content for LLM context
        recent_history = self.chat_history[-max_messages:] if self.chat_history else []
        return [{"role": msg["role"], "content": msg["content"]} for msg in recent_history]
    
    def store_memory(self, text: str, memory_type: str = "fact", metadata: Optional[Dict[str, Any]] = None):
        """Store important information in long-term memory"""
        try:
            # Get embedding for the text
            embedding = get_embedding(text)
            embedding_array = np.array([embedding]).astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(embedding_array)
            
            # Create memory entry
            memory_entry = {
                "text": text,
                "type": memory_type,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Add to memory store and index
            self.memory_store.append(memory_entry)
            self.memory_index.add(embedding_array)
            
            # Save to disk
            self._save_memory()
            
            logger.info(f"Stored memory: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
    
    def retrieve_memory(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant memories based on query"""
        try:
            if len(self.memory_store) == 0:
                return []
            
            # Get query embedding
            query_embedding = get_embedding(query)
            query_array = np.array([query_embedding]).astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_array)
            
            # Search for similar memories
            k = min(k, len(self.memory_store))  # Don't search for more than available
            scores, indices = self.memory_index.search(query_array, k)
            
            # Return relevant memories with scores
            relevant_memories = []
            for i, idx in enumerate(indices[0]):
                if idx != -1 and scores[0][i] > 0.7:  # Similarity threshold
                    memory = self.memory_store[idx].copy()
                    memory["similarity_score"] = float(scores[0][i])
                    relevant_memories.append(memory)
            
            logger.info(f"Retrieved {len(relevant_memories)} relevant memories for query")
            return relevant_memories
            
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return []
    
    def extract_and_store_facts(self, conversation: str, response: str):
        """Extract and store important facts from conversation"""
        try:
            # Simple fact extraction - in production, use more sophisticated NLP
            facts_to_store = []
            
            # Extract user preferences and information
            if "my name is" in conversation.lower():
                name_part = conversation.lower().split("my name is")[1].split(".")[0].strip()
                facts_to_store.append(f"User's name is {name_part}")
            
            if "i live in" in conversation.lower():
                location_part = conversation.lower().split("i live in")[1].split(".")[0].strip()
                facts_to_store.append(f"User lives in {location_part}")
            
            if "i work as" in conversation.lower() or "i am a" in conversation.lower():
                if "i work as" in conversation.lower():
                    job_part = conversation.lower().split("i work as")[1].split(".")[0].strip()
                    facts_to_store.append(f"User works as {job_part}")
                elif "i am a" in conversation.lower():
                    job_part = conversation.lower().split("i am a")[1].split(".")[0].strip()
                    facts_to_store.append(f"User is a {job_part}")
            
            # Extract facts from response (like Aswin's information)
            if "aswin" in response.lower():
                if "bangalore" in response.lower():
                    facts_to_store.append("Aswin is located in Bangalore")
                if "software developer" in response.lower():
                    facts_to_store.append("Aswin is a Software Developer")
                if "giglabz" in response.lower():
                    facts_to_store.append("Aswin works at GigLabz Private Ltd")
            
            # Store extracted facts
            for fact in facts_to_store:
                self.store_memory(fact, "fact", {"source": "conversation"})
            
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
    
    def get_memory_context(self, query: str) -> str:
        """Get relevant memory context for the query"""
        try:
            relevant_memories = self.retrieve_memory(query, k=3)
            
            if not relevant_memories:
                return ""
            
            memory_context = "Relevant information from previous conversations:\n"
            for memory in relevant_memories:
                memory_context += f"- {memory['text']}\n"
            
            return memory_context
            
        except Exception as e:
            logger.error(f"Error getting memory context: {e}")
            return ""
    
    def clear_chat_history(self):
        """Clear short-term memory (chat history)"""
        self.chat_history = []
        logger.info("Chat history cleared")
    
    def clear_all_memory(self):
        """Clear all memory (use with caution)"""
        self.chat_history = []
        self.memory_store = []
        self.memory_index = faiss.IndexFlatIP(self.embedding_dim)
        
        # Remove persisted files
        try:
            if os.path.exists(self.memory_file):
                os.remove(self.memory_file)
            if os.path.exists(self.memory_index_file):
                os.remove(self.memory_index_file)
        except Exception as e:
            logger.error(f"Error removing memory files: {e}")
        
        logger.info("All memory cleared")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "chat_history_length": len(self.chat_history),
            "stored_memories": len(self.memory_store),
            "memory_types": list(set(mem.get("type", "unknown") for mem in self.memory_store)),
            "oldest_memory": self.memory_store[0]["timestamp"] if self.memory_store else None,
            "newest_memory": self.memory_store[-1]["timestamp"] if self.memory_store else None
        }

# Global memory instance
agent_memory = AgentMemory()

# Convenience functions
def add_to_chat_history(role: str, content: str):
    """Add message to chat history"""
    agent_memory.add_to_chat_history(role, content)

def get_chat_history(max_messages: int = 10) -> List[Dict[str, str]]:
    """Get recent chat history"""
    return agent_memory.get_chat_history(max_messages)

def store_memory(text: str, memory_type: str = "fact", metadata: Optional[Dict[str, Any]] = None):
    """Store information in long-term memory"""
    agent_memory.store_memory(text, memory_type, metadata)

def retrieve_memory(query: str, k: int = 3) -> List[Dict[str, Any]]:
    """Retrieve relevant memories"""
    return agent_memory.retrieve_memory(query, k)

def get_memory_context(query: str) -> str:
    """Get memory context for query"""
    return agent_memory.get_memory_context(query)

def extract_and_store_facts(conversation: str, response: str):
    """Extract and store facts from conversation"""
    agent_memory.extract_and_store_facts(conversation, response)

def get_memory_stats() -> Dict[str, Any]:
    """Get memory statistics"""
    return agent_memory.get_memory_stats()

def clear_chat_history():
    """Clear chat history"""
    agent_memory.clear_chat_history()

def clear_all_memory():
    """Clear all memory"""
    agent_memory.clear_all_memory()