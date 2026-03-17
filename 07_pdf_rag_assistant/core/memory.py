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
import time
import re

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
        """Store important information in long-term memory with scoring"""
        try:
            # Calculate importance score
            importance_score = self.calculate_importance(text)
            
            # Only store if importance is above threshold
            if importance_score < 0.6:
                logger.debug(f"Skipping low-importance memory: {text[:50]}... (score: {importance_score:.2f})")
                return
            
            # Get embedding for the text
            embedding = get_embedding(text)
            embedding_array = np.array([embedding]).astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(embedding_array)
            
            # Create memory entry with scoring
            memory_entry = {
                "text": text,
                "type": memory_type,
                "importance": importance_score,
                "timestamp": time.time(),
                "access_count": 0,
                "last_accessed": time.time(),
                "metadata": metadata or {}
            }
            
            # Add to memory store and index
            self.memory_store.append(memory_entry)
            self.memory_index.add(embedding_array)
            
            # Save to disk
            self._save_memory()
            
            logger.info(f"Stored memory (importance: {importance_score:.2f}): {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
    
    def retrieve_memory(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Advanced memory retrieval with Store → Score → Rank → Retrieve → Inject architecture
        Uses combined similarity + importance + recency scoring like ChatGPT/Notion AI
        """
        try:
            if len(self.memory_store) == 0:
                return []

            # Get query embedding
            query_embedding = get_embedding(query)
            query_array = np.array([query_embedding]).astype('float32')

            # Normalize for cosine similarity
            faiss.normalize_L2(query_array)

            # Search for more memories than needed for better ranking
            search_k = min(k * 3, len(self.memory_store))  # Search 3x more for better ranking
            scores, indices = self.memory_index.search(query_array, search_k)

            # Advanced ranking with combined scoring
            ranked_memories = self._rank_memories(query, scores[0], indices[0])

            # Return top k memories
            top_memories = ranked_memories[:k]

            # Update access counts for retrieved memories
            for memory in top_memories:
                memory["access_count"] = memory.get("access_count", 0) + 1
                memory["last_accessed"] = time.time()

            # Save updated access counts
            self._save_memory()

            logger.info(f"Retrieved {len(top_memories)} memories using advanced ranking")
            return top_memories

        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return []
    
    def _rank_memories(self, query: str, similarity_scores: np.ndarray, indices: np.ndarray) -> List[Dict[str, Any]]:
        """
        Advanced memory ranking system: similarity + importance + recency + access_frequency
        
        Args:
            query: User query for context-aware scoring
            similarity_scores: FAISS similarity scores
            indices: Memory indices from FAISS search
            
        Returns:
            Ranked list of memories with combined scores
        """
        try:
            current_time = time.time()
            ranked_memories = []
            
            for i, idx in enumerate(indices):
                if idx == -1:  # Invalid index
                    continue
                    
                memory = self.memory_store[idx].copy()
                similarity = float(similarity_scores[i])
                
                # Skip very low similarity memories
                if similarity < 0.3:
                    continue
                
                # 1. Similarity Score (0.0 - 1.0)
                similarity_score = similarity
                
                # 2. Importance Score (already calculated, 0.0 - 1.0)
                importance_score = memory.get("importance", 0.5)
                
                # 3. Recency Score (0.0 - 1.0)
                memory_timestamp = memory.get("timestamp", current_time)
                age_seconds = current_time - memory_timestamp
                age_days = age_seconds / (24 * 60 * 60)
                
                # Exponential decay for recency (fresh memories get higher scores)
                if age_days <= 1:
                    recency_score = 1.0  # Very recent
                elif age_days <= 7:
                    recency_score = 0.8  # Recent
                elif age_days <= 30:
                    recency_score = 0.6  # Somewhat recent
                elif age_days <= 90:
                    recency_score = 0.4  # Old
                else:
                    recency_score = 0.2  # Very old
                
                # 4. Access Frequency Score (0.0 - 1.0)
                access_count = memory.get("access_count", 0)
                # Normalize access count (cap at 10 for scoring)
                frequency_score = min(access_count / 10.0, 1.0)
                
                # 5. Context Relevance Boost
                context_boost = 0.0
                query_lower = query.lower()
                memory_text_lower = memory["text"].lower()
                
                # Boost for exact keyword matches
                query_words = set(query_lower.split())
                memory_words = set(memory_text_lower.split())
                common_words = query_words.intersection(memory_words)
                if common_words:
                    context_boost = min(len(common_words) * 0.1, 0.3)  # Max 0.3 boost
                
                # 6. Memory Type Boost
                memory_type = memory.get("type", "other")
                type_boost = 0.0
                if memory_type == "fact":
                    type_boost = 0.1  # Facts are generally important
                elif memory_type == "preference":
                    type_boost = 0.05  # Preferences are moderately important
                
                # Combined Score Calculation (weighted average)
                # Weights: similarity=40%, importance=30%, recency=15%, frequency=10%, context=5%
                combined_score = (
                    0.40 * similarity_score +
                    0.30 * importance_score +
                    0.15 * recency_score +
                    0.10 * frequency_score +
                    0.05 * context_boost
                ) + type_boost
                
                # Cap at 1.0
                combined_score = min(combined_score, 1.0)
                
                # Only include memories above threshold
                if combined_score > 0.5:  # Minimum threshold for relevance
                    memory["similarity_score"] = similarity_score
                    memory["importance_score"] = importance_score
                    memory["recency_score"] = recency_score
                    memory["frequency_score"] = frequency_score
                    memory["context_boost"] = context_boost
                    memory["combined_score"] = combined_score
                    memory["age_days"] = age_days
                    
                    ranked_memories.append(memory)
            
            # Sort by combined score (highest first)
            ranked_memories.sort(key=lambda x: x["combined_score"], reverse=True)
            
            logger.info(f"Ranked {len(ranked_memories)} memories using advanced scoring")
            return ranked_memories
            
        except Exception as e:
            logger.error(f"Error ranking memories: {e}")
            return []

    
    def calculate_importance(self, text: str) -> float:
        """
        Calculate importance score for memory text (0.0 to 1.0)
        
        Args:
            text: Text to score
            
        Returns:
            Importance score between 0.0 and 1.0
        """
        try:
            # Base score
            score = 0.3
            
            # High importance keywords (0.3 each, max 0.9)
            high_importance = [
                "salary", "income", "pay", "money", "cost", "price", "budget",
                "name", "location", "address", "live", "work", "job", "company",
                "goal", "objective", "target", "plan", "strategy", "important"
            ]
            
            # Medium importance keywords (0.2 each, max 0.6)
            medium_importance = [
                "skill", "experience", "education", "degree", "certification",
                "prefer", "like", "favorite", "dislike", "hate", "want", "need",
                "project", "team", "manager", "colleague", "client", "customer"
            ]
            
            # Low importance keywords (0.1 each, max 0.3)
            low_importance = [
                "weather", "temperature", "condition", "time", "date", "today",
                "yesterday", "tomorrow", "week", "month", "year", "season"
            ]
            
            text_lower = text.lower()
            
            # Score based on keyword presence
            for keyword in high_importance:
                if keyword in text_lower:
                    score += 0.3
            
            for keyword in medium_importance:
                if keyword in text_lower:
                    score += 0.2
            
            for keyword in low_importance:
                if keyword in text_lower:
                    score += 0.1
            
            # Boost for numerical data (likely important facts)
            if re.search(r'\d+', text):
                score += 0.1
            
            # Boost for currency symbols (financial data)
            if any(symbol in text for symbol in ['₹', '$', '€', '£', '¥']):
                score += 0.2
            
            # Boost for personal pronouns (personal information)
            personal_pronouns = ['my', 'i am', 'i work', 'i live', 'i like', 'i prefer']
            if any(pronoun in text_lower for pronoun in personal_pronouns):
                score += 0.15
            
            # Penalty for very short text (likely not important)
            if len(text.split()) < 3:
                score *= 0.7
            
            # Boost for longer, detailed text
            if len(text.split()) > 10:
                score += 0.1
            
            # Cap at 1.0
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating importance: {e}")
            return 0.5  # Default medium importance
    def should_store_memory(self, text: str) -> bool:
        """
        Determine if text contains important information worth storing
        Uses importance scoring - only store if importance > 0.6
        """
        importance = self.calculate_importance(text)
        return importance > 0.6
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
        """Get comprehensive memory system statistics with advanced scoring info"""
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
                importance_distribution = {"high": 0, "medium": 0, "low": 0}
                access_frequency = {"frequent": 0, "occasional": 0, "rare": 0}
                age_distribution = {"recent": 0, "old": 0, "very_old": 0}
                
                current_time = time.time()
                total_importance = 0
                total_access_count = 0
                
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
                    
                    # Importance distribution
                    importance = memory.get("importance", 0.5)
                    total_importance += importance
                    if importance >= 0.8:
                        importance_distribution["high"] += 1
                    elif importance >= 0.6:
                        importance_distribution["medium"] += 1
                    else:
                        importance_distribution["low"] += 1
                    
                    # Access frequency distribution
                    access_count = memory.get("access_count", 0)
                    total_access_count += access_count
                    if access_count >= 5:
                        access_frequency["frequent"] += 1
                    elif access_count >= 2:
                        access_frequency["occasional"] += 1
                    else:
                        access_frequency["rare"] += 1
                    
                    # Age distribution
                    memory_timestamp = memory.get("timestamp", current_time)
                    age_days = (current_time - memory_timestamp) / (24 * 60 * 60)
                    if age_days <= 7:
                        age_distribution["recent"] += 1
                    elif age_days <= 30:
                        age_distribution["old"] += 1
                    else:
                        age_distribution["very_old"] += 1
                
                # Calculate averages
                avg_importance = total_importance / len(self.memory_store)
                avg_access_count = total_access_count / len(self.memory_store)
                
                stats.update({
                    "memory_types": memory_types,
                    "confidence_distribution": confidence_levels,
                    "source_distribution": sources,
                    "importance_distribution": importance_distribution,
                    "access_frequency_distribution": access_frequency,
                    "age_distribution": age_distribution,
                    "average_importance": round(avg_importance, 3),
                    "average_access_count": round(avg_access_count, 2),
                    "oldest_memory": self.memory_store[0]["timestamp"],
                    "newest_memory": self.memory_store[-1]["timestamp"],
                    "scoring_system": "advanced_ranking_enabled"
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
        """
        Advanced memory cleanup with decay functionality
        Removes memories older than specified days and applies decay to aging memories
        """
        try:
            current_time = time.time()
            cutoff_timestamp = current_time - (days_to_keep * 24 * 60 * 60)
            
            # Find memories to keep with decay applied
            memories_to_keep = []
            indices_to_keep = []
            decay_applied_count = 0
            
            for i, memory in enumerate(self.memory_store):
                memory_timestamp = memory.get("timestamp", current_time)
                age_seconds = current_time - memory_timestamp
                age_days = age_seconds / (24 * 60 * 60)
                
                # Apply memory decay based on age
                original_importance = memory.get("importance", 0.5)
                decayed_importance = self._apply_memory_decay(original_importance, age_days)
                
                # Update importance if decay was applied
                if decayed_importance != original_importance:
                    memory["importance"] = decayed_importance
                    decay_applied_count += 1
                
                # Keep memory if it's recent enough OR still important after decay
                if memory_timestamp > cutoff_timestamp or decayed_importance > 0.3:
                    memories_to_keep.append(memory)
                    indices_to_keep.append(i)
            
            removed_count = len(self.memory_store) - len(memories_to_keep)
            
            if removed_count > 0 or decay_applied_count > 0:
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
                
                logger.info(f"Memory cleanup: removed {removed_count} old memories, applied decay to {decay_applied_count} memories, kept {len(memories_to_keep)}")
                return {
                    "removed": removed_count, 
                    "kept": len(memories_to_keep),
                    "decay_applied": decay_applied_count
                }
            
            return {
                "removed": 0, 
                "kept": len(self.memory_store),
                "decay_applied": 0
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up memories: {e}")
            return {"error": str(e)}
    
    def _apply_memory_decay(self, importance: float, age_days: float) -> float:
        """
        Apply memory decay based on age - older memories become less important
        
        Args:
            importance: Original importance score (0.0 - 1.0)
            age_days: Age of memory in days
            
        Returns:
            Decayed importance score
        """
        try:
            # No decay for very recent memories (< 1 day)
            if age_days < 1:
                return importance
            
            # Gradual decay based on age
            if age_days <= 7:  # 1-7 days: minimal decay
                decay_factor = 0.95
            elif age_days <= 30:  # 1-4 weeks: moderate decay
                decay_factor = 0.85
            elif age_days <= 90:  # 1-3 months: significant decay
                decay_factor = 0.70
            elif age_days <= 180:  # 3-6 months: heavy decay
                decay_factor = 0.50
            else:  # > 6 months: very heavy decay
                decay_factor = 0.30
            
            # Apply decay
            decayed_importance = importance * decay_factor
            
            # Ensure minimum threshold for very important memories
            if importance > 0.9:  # Very important memories decay slower
                decayed_importance = max(decayed_importance, 0.6)
            elif importance > 0.8:  # Important memories
                decayed_importance = max(decayed_importance, 0.4)
            
            return max(decayed_importance, 0.0)  # Never go below 0
            
        except Exception as e:
            logger.error(f"Error applying memory decay: {e}")
            return importance  # Return original if error

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

def _rank_memories(self, query: str, similarity_scores: np.ndarray, indices: np.ndarray) -> List[Dict[str, Any]]:
    """
    Advanced memory ranking system: similarity + importance + recency + access_frequency

    Args:
        query: User query for context-aware scoring
        similarity_scores: FAISS similarity scores
        indices: Memory indices from FAISS search

    Returns:
        Ranked list of memories with combined scores
    """
    try:
        current_time = time.time()
        ranked_memories = []

        for i, idx in enumerate(indices):
            if idx == -1:  # Invalid index
                continue

            memory = self.memory_store[idx].copy()
            similarity = float(similarity_scores[i])

            # Skip very low similarity memories
            if similarity < 0.3:
                continue

            # 1. Similarity Score (0.0 - 1.0)
            similarity_score = similarity

            # 2. Importance Score (already calculated, 0.0 - 1.0)
            importance_score = memory.get("importance", 0.5)

            # 3. Recency Score (0.0 - 1.0)
            memory_timestamp = memory.get("timestamp", current_time)
            age_seconds = current_time - memory_timestamp
            age_days = age_seconds / (24 * 60 * 60)

            # Exponential decay for recency (fresh memories get higher scores)
            if age_days <= 1:
                recency_score = 1.0  # Very recent
            elif age_days <= 7:
                recency_score = 0.8  # Recent
            elif age_days <= 30:
                recency_score = 0.6  # Somewhat recent
            elif age_days <= 90:
                recency_score = 0.4  # Old
            else:
                recency_score = 0.2  # Very old

            # 4. Access Frequency Score (0.0 - 1.0)
            access_count = memory.get("access_count", 0)
            # Normalize access count (cap at 10 for scoring)
            frequency_score = min(access_count / 10.0, 1.0)

            # 5. Context Relevance Boost
            context_boost = 0.0
            query_lower = query.lower()
            memory_text_lower = memory["text"].lower()

            # Boost for exact keyword matches
            query_words = set(query_lower.split())
            memory_words = set(memory_text_lower.split())
            common_words = query_words.intersection(memory_words)
            if common_words:
                context_boost = min(len(common_words) * 0.1, 0.3)  # Max 0.3 boost

            # 6. Memory Type Boost
            memory_type = memory.get("type", "other")
            type_boost = 0.0
            if memory_type == "fact":
                type_boost = 0.1  # Facts are generally important
            elif memory_type == "preference":
                type_boost = 0.05  # Preferences are moderately important

            # Combined Score Calculation (weighted average)
            # Weights: similarity=40%, importance=30%, recency=15%, frequency=10%, context=5%
            combined_score = (
                0.40 * similarity_score +
                0.30 * importance_score +
                0.15 * recency_score +
                0.10 * frequency_score +
                0.05 * context_boost
            ) + type_boost

            # Cap at 1.0
            combined_score = min(combined_score, 1.0)

            # Only include memories above threshold
            if combined_score > 0.5:  # Minimum threshold for relevance
                memory["similarity_score"] = similarity_score
                memory["importance_score"] = importance_score
                memory["recency_score"] = recency_score
                memory["frequency_score"] = frequency_score
                memory["context_boost"] = context_boost
                memory["combined_score"] = combined_score
                memory["age_days"] = age_days

                ranked_memories.append(memory)

        # Sort by combined score (highest first)
        ranked_memories.sort(key=lambda x: x["combined_score"], reverse=True)

        logger.info(f"Ranked {len(ranked_memories)} memories using advanced scoring")
        return ranked_memories

    except Exception as e:
        logger.error(f"Error ranking memories: {e}")
        return []

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