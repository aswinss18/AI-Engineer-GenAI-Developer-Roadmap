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
        """Retrieve relevant memories based on query with improved scoring"""
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
            
            # Return relevant memories with improved scoring
            relevant_memories = []
            for i, idx in enumerate(indices[0]):
                if idx != -1:
                    similarity_score = float(scores[0][i])
                    
                    # Improved threshold based on memory type and recency
                    memory = self.memory_store[idx].copy()
                    memory_type = memory.get("type", "unknown")
                    
                    # Different thresholds for different memory types
                    threshold = 0.7  # Default threshold
                    if memory_type == "fact":
                        threshold = 0.65  # Lower threshold for facts
                    elif memory_type == "preference":
                        threshold = 0.75  # Higher threshold for preferences
                    
                    # Boost score for recent memories
                    try:
                        from datetime import datetime, timedelta
                        memory_time = datetime.fromisoformat(memory["timestamp"])
                        age_days = (datetime.now() - memory_time).days
                        
                        # Boost recent memories (within 7 days)
                        if age_days <= 7:
                            similarity_score *= 1.1  # 10% boost for recent memories
                    except:
                        pass  # Skip if timestamp parsing fails
                    
                    if similarity_score > threshold:
                        memory["similarity_score"] = similarity_score
                        relevant_memories.append(memory)
            
            # Sort by similarity score (highest first)
            relevant_memories.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            logger.info(f"Retrieved {len(relevant_memories)} relevant memories for query")
            return relevant_memories
            
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return []
    
    def should_store_memory(self, text: str) -> bool:
        """
        Determine if text contains important information worth storing
        
        Args:
            text: Text to evaluate
            
        Returns:
            Boolean indicating if text should be stored
        """
        # Important keywords that indicate valuable information
        important_keywords = [
            # Personal information
            "name", "live", "work", "job", "profession", "age", "born",
            # Financial information  
            "salary", "income", "pay", "earn", "money", "cost", "price", "budget",
            # Location information
            "location", "city", "country", "address", "bangalore", "mumbai", "delhi",
            # Preferences and opinions
            "like", "prefer", "favorite", "hate", "dislike", "want", "need",
            # Skills and experience
            "skill", "experience", "expert", "good at", "know", "learned",
            # Important facts
            "temperature", "weather", "company", "project", "team", "manager"
        ]
        
        # Convert to lowercase for matching
        text_lower = text.lower()
        
        # Check for important keywords
        has_keywords = any(keyword in text_lower for keyword in important_keywords)
        
        # Filter out common conversational phrases
        ignore_phrases = [
            "hello", "hi", "how are you", "thank you", "thanks", "bye", "goodbye",
            "yes", "no", "ok", "okay", "sure", "maybe", "i think", "i guess",
            "what", "when", "where", "why", "how", "can you", "please", "sorry"
        ]
        
        # Don't store if it's just a common phrase
        is_common_phrase = any(phrase in text_lower for phrase in ignore_phrases) and len(text.split()) < 5
        
        # Store if it has important keywords and isn't just a common phrase
        return has_keywords and not is_common_phrase
    def extract_and_store_facts(self, conversation: str, response: str):
        """Extract and store important facts from conversation"""
        try:
            # Only store if conversation contains important information
            if not self.should_store_memory(conversation):
                logger.debug(f"Skipping memory storage for: {conversation[:50]}...")
                return
            
            facts_to_store = []
            
            # Extract user preferences and information
            if "my name is" in conversation.lower():
                name_part = conversation.lower().split("my name is")[1].split(".")[0].split(",")[0].strip()
                facts_to_store.append(f"User's name is {name_part}")
            
            if "i live in" in conversation.lower():
                location_part = conversation.lower().split("i live in")[1].split(".")[0].split(",")[0].strip()
                facts_to_store.append(f"User lives in {location_part}")
            
            if "i work as" in conversation.lower() or "i am a" in conversation.lower():
                if "i work as" in conversation.lower():
                    job_part = conversation.lower().split("i work as")[1].split(".")[0].split(",")[0].strip()
                    facts_to_store.append(f"User works as {job_part}")
                elif "i am a" in conversation.lower():
                    job_part = conversation.lower().split("i am a")[1].split(".")[0].split(",")[0].strip()
                    facts_to_store.append(f"User is a {job_part}")
            
            # Extract salary information
            if "salary" in conversation.lower() and any(char.isdigit() for char in conversation):
                facts_to_store.append(f"Salary information mentioned: {conversation}")
            
            # Extract facts from response (like Aswin's information) - only if important
            if self.should_store_memory(response):
                if "aswin" in response.lower():
                    if "bangalore" in response.lower():
                        facts_to_store.append("Aswin is located in Bangalore")
                    if "software developer" in response.lower():
                        facts_to_store.append("Aswin is a Software Developer")
                    if "giglabz" in response.lower():
                        facts_to_store.append("Aswin works at GigLabz Private Ltd")
                    if "salary" in response.lower() and "₹" in response:
                        # Extract salary amount
                        import re
                        salary_match = re.search(r'₹[\d,]+', response)
                        if salary_match:
                            facts_to_store.append(f"Aswin's salary is {salary_match.group()}")
                    if "temperature" in response.lower() and "°c" in response.lower():
                        # Extract temperature information
                        temp_match = re.search(r'\d+°C', response)
                        if temp_match:
                            facts_to_store.append(f"Bangalore temperature is {temp_match.group()}")
            
            # Store extracted facts with metadata
            for fact in facts_to_store:
                self.store_memory(
                    fact, 
                    "fact", 
                    {
                        "source": "conversation",
                        "extracted_from": conversation[:100],
                        "confidence": "high"
                    }
                )
            
            logger.info(f"Extracted and stored {len(facts_to_store)} facts from conversation")
            
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
    
    def get_memory_context(self, query: str) -> str:
        """Get relevant memory context for the query with improved formatting"""
        try:
            relevant_memories = self.retrieve_memory(query, k=5)  # Get more memories for better context
            
            if not relevant_memories:
                return ""
            
            # Group memories by type for better organization
            memory_groups = {
                "facts": [],
                "preferences": [],
                "other": []
            }
            
            for memory in relevant_memories:
                memory_type = memory.get("type", "other")
                if memory_type == "fact":
                    memory_groups["facts"].append(memory)
                elif memory_type == "preference":
                    memory_groups["preferences"].append(memory)
                else:
                    memory_groups["other"].append(memory)
            
            # Build context with organized sections
            context_parts = []
            
            if memory_groups["facts"]:
                context_parts.append("IMPORTANT FACTS:")
                for memory in memory_groups["facts"][:3]:  # Top 3 facts
                    confidence = memory.get("metadata", {}).get("confidence", "medium")
                    context_parts.append(f"- {memory['text']} (confidence: {confidence})")
            
            if memory_groups["preferences"]:
                context_parts.append("\nUSER PREFERENCES:")
                for memory in memory_groups["preferences"][:2]:  # Top 2 preferences
                    context_parts.append(f"- {memory['text']}")
            
            if memory_groups["other"]:
                context_parts.append("\nOTHER RELEVANT INFO:")
                for memory in memory_groups["other"][:2]:  # Top 2 other memories
                    context_parts.append(f"- {memory['text']}")
            
            if context_parts:
                return "RELEVANT MEMORY CONTEXT:\n" + "\n".join(context_parts) + "\n"
            
            return ""
            
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
        """Get comprehensive memory system statistics"""
        try:
            # Basic stats
            stats = {
                "chat_history_length": len(self.chat_history),
                "stored_memories": len(self.memory_store),
                "memory_index_size": self.memory_index.ntotal if self.memory_index else 0
            }
            
            if self.memory_store:
                # Memory type distribution
                memory_types = {}
                confidence_levels = {}
                sources = {}
                
                for memory in self.memory_store:
                    # Count memory types
                    mem_type = memory.get("type", "unknown")
                    memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
                    
                    # Count confidence levels
                    confidence = memory.get("metadata", {}).get("confidence", "unknown")
                    confidence_levels[confidence] = confidence_levels.get(confidence, 0) + 1
                    
                    # Count sources
                    source = memory.get("metadata", {}).get("source", "unknown")
                    sources[source] = sources.get(source, 0) + 1
                
                stats.update({
                    "memory_types": memory_types,
                    "confidence_distribution": confidence_levels,
                    "source_distribution": sources,
                    "oldest_memory": self.memory_store[0]["timestamp"],
                    "newest_memory": self.memory_store[-1]["timestamp"]
                })
            
            # Recent activity
            if self.chat_history:
                stats["last_conversation"] = self.chat_history[-1]["timestamp"]
                stats["conversation_turns"] = len([msg for msg in self.chat_history if msg["role"] == "user"])
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}
    
    def cleanup_old_memories(self, days_to_keep: int = 30):
        """Remove memories older than specified days"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Find memories to keep
            memories_to_keep = []
            indices_to_keep = []
            
            for i, memory in enumerate(self.memory_store):
                try:
                    memory_date = datetime.fromisoformat(memory["timestamp"])
                    if memory_date > cutoff_date:
                        memories_to_keep.append(memory)
                        indices_to_keep.append(i)
                except:
                    # Keep memories with invalid timestamps
                    memories_to_keep.append(memory)
                    indices_to_keep.append(i)
            
            removed_count = len(self.memory_store) - len(memories_to_keep)
            
            if removed_count > 0:
                # Rebuild memory store and index
                self.memory_store = memories_to_keep
                
                # Rebuild FAISS index with remaining memories
                if memories_to_keep:
                    self.memory_index = faiss.IndexFlatIP(self.embedding_dim)
                    for memory in memories_to_keep:
                        try:
                            # Re-embed and add to index
                            embedding = get_embedding(memory["text"])
                            embedding_array = np.array([embedding]).astype('float32')
                            faiss.normalize_L2(embedding_array)
                            self.memory_index.add(embedding_array)
                        except Exception as e:
                            logger.error(f"Error re-indexing memory: {e}")
                else:
                    self.memory_index = faiss.IndexFlatIP(self.embedding_dim)
                
                # Save updated memory
                self._save_memory()
                
                logger.info(f"Cleaned up {removed_count} old memories, kept {len(memories_to_keep)}")
                return {"removed": removed_count, "kept": len(memories_to_keep)}
            
            return {"removed": 0, "kept": len(self.memory_store)}
            
        except Exception as e:
            logger.error(f"Error cleaning up memories: {e}")
            return {"error": str(e)}

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