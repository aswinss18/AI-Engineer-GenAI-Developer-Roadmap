"""
Memory system for ReAct agent - Short-term and Long-term memory.
Moved from core/memory.py — imports updated to use app package paths.
"""

import json
import logging
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import faiss
from app.services.internals.embeddings import get_embedding
from app.core.config import settings
import os
import time
import re

logger = logging.getLogger(__name__)


class AgentMemory:
    def __init__(self):
        self.chat_history: List[Dict[str, str]] = []
        self.memory_store: List[Dict[str, Any]] = []
        self.memory_index = None
        self.embedding_dim = 1536

        self.memory_file = os.path.join(settings.persistence_dir, "agent_memory.json")
        self.memory_index_file = os.path.join(settings.persistence_dir, "agent_memory_index.bin")

        self._initialize_memory()

    def _initialize_memory(self):
        try:
            os.makedirs(settings.persistence_dir, exist_ok=True)
            self.memory_index = faiss.IndexFlatIP(self.embedding_dim)
            self._load_memory()
            logger.info(f"Memory system initialized with {len(self.memory_store)} stored memories")
        except Exception as e:
            logger.error(f"Error initializing memory: {e}")
            self.memory_store = []
            self.memory_index = faiss.IndexFlatIP(self.embedding_dim)

    def _load_memory(self):
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self.memory_store = json.load(f)
                logger.info(f"Loaded {len(self.memory_store)} memories from disk")
            if os.path.exists(self.memory_index_file) and len(self.memory_store) > 0:
                self.memory_index = faiss.read_index(self.memory_index_file)
                logger.info(f"Loaded memory index with {self.memory_index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Error loading memory: {e}")

    def _save_memory(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_store, f, indent=2, ensure_ascii=False)
            if self.memory_index.ntotal > 0:
                faiss.write_index(self.memory_index, self.memory_index_file)
            logger.info(f"Saved {len(self.memory_store)} memories to disk")
        except Exception as e:
            logger.error(f"Error saving memory: {e}")

    def add_to_chat_history(self, role: str, content: str):
        self.chat_history.append(
            {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
        )
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

    def get_chat_history(self, max_messages: int = 10) -> List[Dict[str, str]]:
        recent_history = self.chat_history[-max_messages:] if self.chat_history else []
        return [{"role": msg["role"], "content": msg["content"]} for msg in recent_history]

    def store_memory(self, text: str, memory_type: str = "fact", metadata: Optional[Dict[str, Any]] = None):
        try:
            importance_score = self.calculate_importance(text)
            if importance_score < 0.6:
                logger.debug(f"Skipping low-importance memory: {text[:50]}... (score: {importance_score:.2f})")
                return
            embedding = get_embedding(text)
            embedding_array = np.array([embedding]).astype("float32")
            faiss.normalize_L2(embedding_array)
            memory_entry = {
                "text": text,
                "type": memory_type,
                "importance": importance_score,
                "timestamp": time.time(),
                "access_count": 0,
                "last_accessed": time.time(),
                "metadata": metadata or {},
            }
            self.memory_store.append(memory_entry)
            self.memory_index.add(embedding_array)
            self._save_memory()
            logger.info(f"Stored memory (importance: {importance_score:.2f}): {text[:50]}...")
        except Exception as e:
            logger.error(f"Error storing memory: {e}")

    def retrieve_memory(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        try:
            if len(self.memory_store) == 0:
                return []
            query_embedding = get_embedding(query)
            query_array = np.array([query_embedding]).astype("float32")
            faiss.normalize_L2(query_array)
            search_k = min(k * 3, len(self.memory_store))
            scores, indices = self.memory_index.search(query_array, search_k)
            ranked_memories = self._rank_memories(query, scores[0], indices[0])
            top_memories = ranked_memories[:k]
            for memory in top_memories:
                memory["access_count"] = memory.get("access_count", 0) + 1
                memory["last_accessed"] = time.time()
            self._save_memory()
            logger.info(f"Retrieved {len(top_memories)} memories using advanced ranking")
            return top_memories
        except Exception as e:
            logger.error(f"Error retrieving memory: {e}")
            return []

    def _rank_memories(self, query: str, similarity_scores: np.ndarray, indices: np.ndarray) -> List[Dict[str, Any]]:
        try:
            current_time = time.time()
            ranked_memories = []
            for i, idx in enumerate(indices):
                if idx == -1:
                    continue
                memory = self.memory_store[idx].copy()
                similarity = float(similarity_scores[i])
                if similarity < 0.3:
                    continue
                similarity_score = similarity
                importance_score = memory.get("importance", 0.5)
                memory_timestamp = memory.get("timestamp", current_time)
                age_days = (current_time - memory_timestamp) / (24 * 60 * 60)
                if age_days <= 1:
                    recency_score = 1.0
                elif age_days <= 7:
                    recency_score = 0.8
                elif age_days <= 30:
                    recency_score = 0.6
                elif age_days <= 90:
                    recency_score = 0.4
                else:
                    recency_score = 0.2
                access_count = memory.get("access_count", 0)
                frequency_score = min(access_count / 10.0, 1.0)
                context_boost = 0.0
                query_words = set(query.lower().split())
                memory_words = set(memory["text"].lower().split())
                common_words = query_words.intersection(memory_words)
                if common_words:
                    context_boost = min(len(common_words) * 0.1, 0.3)
                memory_type = memory.get("type", "other")
                type_boost = 0.1 if memory_type == "fact" else 0.05 if memory_type == "preference" else 0.0
                combined_score = (
                    0.40 * similarity_score
                    + 0.30 * importance_score
                    + 0.15 * recency_score
                    + 0.10 * frequency_score
                    + 0.05 * context_boost
                ) + type_boost
                combined_score = min(combined_score, 1.0)
                if combined_score > 0.5:
                    memory.update({
                        "similarity_score": similarity_score,
                        "importance_score": importance_score,
                        "recency_score": recency_score,
                        "frequency_score": frequency_score,
                        "context_boost": context_boost,
                        "combined_score": combined_score,
                        "age_days": age_days,
                    })
                    ranked_memories.append(memory)
            ranked_memories.sort(key=lambda x: x["combined_score"], reverse=True)
            logger.info(f"Ranked {len(ranked_memories)} memories using advanced scoring")
            return ranked_memories
        except Exception as e:
            logger.error(f"Error ranking memories: {e}")
            return []

    def calculate_importance(self, text: str) -> float:
        try:
            score = 0.3
            high_importance = [
                "salary", "income", "pay", "money", "cost", "price", "budget",
                "name", "location", "address", "live", "work", "job", "company",
                "goal", "objective", "target", "plan", "strategy", "important",
            ]
            medium_importance = [
                "skill", "experience", "education", "degree", "certification",
                "prefer", "like", "favorite", "dislike", "hate", "want", "need",
                "project", "team", "manager", "colleague", "client", "customer",
            ]
            low_importance = [
                "weather", "temperature", "condition", "time", "date", "today",
                "yesterday", "tomorrow", "week", "month", "year", "season",
            ]
            text_lower = text.lower()
            for keyword in high_importance:
                if keyword in text_lower:
                    score += 0.3
            for keyword in medium_importance:
                if keyword in text_lower:
                    score += 0.2
            for keyword in low_importance:
                if keyword in text_lower:
                    score += 0.1
            if re.search(r"\d+", text):
                score += 0.1
            if any(symbol in text for symbol in ["₹", "$", "€", "£", "¥"]):
                score += 0.2
            personal_pronouns = ["my", "i am", "i work", "i live", "i like", "i prefer"]
            if any(pronoun in text_lower for pronoun in personal_pronouns):
                score += 0.15
            if len(text.split()) < 3:
                score *= 0.7
            if len(text.split()) > 10:
                score += 0.1
            return min(score, 1.0)
        except Exception as e:
            logger.error(f"Error calculating importance: {e}")
            return 0.5

    def should_store_memory(self, text: str) -> bool:
        return self.calculate_importance(text) > 0.6

    def extract_and_store_facts(self, conversation: str, response: str):
        try:
            if not self.should_store_memory(conversation):
                return
            facts_to_store = []
            if "my name is" in conversation.lower():
                name_part = conversation.lower().split("my name is")[1].split(".")[0].split(",")[0].strip()
                facts_to_store.append(f"User's name is {name_part}")
            if "i live in" in conversation.lower():
                location_part = conversation.lower().split("i live in")[1].split(".")[0].split(",")[0].strip()
                facts_to_store.append(f"User lives in {location_part}")
            if "i work as" in conversation.lower():
                job_part = conversation.lower().split("i work as")[1].split(".")[0].split(",")[0].strip()
                facts_to_store.append(f"User works as {job_part}")
            elif "i am a" in conversation.lower():
                job_part = conversation.lower().split("i am a")[1].split(".")[0].split(",")[0].strip()
                facts_to_store.append(f"User is a {job_part}")
            if "salary" in conversation.lower() and any(char.isdigit() for char in conversation):
                facts_to_store.append(f"Salary information mentioned: {conversation}")
            if self.should_store_memory(response):
                if "aswin" in response.lower():
                    if "bangalore" in response.lower():
                        facts_to_store.append("Aswin is located in Bangalore")
                    if "software developer" in response.lower():
                        facts_to_store.append("Aswin is a Software Developer")
                    if "giglabz" in response.lower():
                        facts_to_store.append("Aswin works at GigLabz Private Ltd")
                    if "salary" in response.lower() and "₹" in response:
                        salary_match = re.search(r"₹[\d,]+", response)
                        if salary_match:
                            facts_to_store.append(f"Aswin's salary is {salary_match.group()}")
            for fact in facts_to_store:
                self.store_memory(fact, "fact", {"source": "conversation", "extracted_from": conversation[:100], "confidence": "high"})
            logger.info(f"Extracted and stored {len(facts_to_store)} facts from conversation")
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")

    def get_memory_context(self, query: str) -> str:
        try:
            relevant_memories = self.retrieve_memory(query, k=5)
            if not relevant_memories:
                return ""
            memory_groups = {"facts": [], "preferences": [], "other": []}
            for memory in relevant_memories:
                memory_type = memory.get("type", "other")
                if memory_type == "fact":
                    memory_groups["facts"].append(memory)
                elif memory_type == "preference":
                    memory_groups["preferences"].append(memory)
                else:
                    memory_groups["other"].append(memory)
            context_parts = []
            if memory_groups["facts"]:
                context_parts.append("IMPORTANT FACTS:")
                for memory in memory_groups["facts"][:3]:
                    confidence = memory.get("metadata", {}).get("confidence", "medium")
                    context_parts.append(f"- {memory['text']} (confidence: {confidence})")
            if memory_groups["preferences"]:
                context_parts.append("\nUSER PREFERENCES:")
                for memory in memory_groups["preferences"][:2]:
                    context_parts.append(f"- {memory['text']}")
            if memory_groups["other"]:
                context_parts.append("\nOTHER RELEVANT INFO:")
                for memory in memory_groups["other"][:2]:
                    context_parts.append(f"- {memory['text']}")
            if context_parts:
                return "RELEVANT MEMORY CONTEXT:\n" + "\n".join(context_parts) + "\n"
            return ""
        except Exception as e:
            logger.error(f"Error getting memory context: {e}")
            return ""

    def clear_chat_history(self):
        self.chat_history = []
        logger.info("Chat history cleared")

    def clear_all_memory(self):
        self.chat_history = []
        self.memory_store = []
        self.memory_index = faiss.IndexFlatIP(self.embedding_dim)
        try:
            if os.path.exists(self.memory_file):
                os.remove(self.memory_file)
            if os.path.exists(self.memory_index_file):
                os.remove(self.memory_index_file)
        except Exception as e:
            logger.error(f"Error removing memory files: {e}")
        logger.info("All memory cleared")

    def get_memory_stats(self) -> Dict[str, Any]:
        try:
            stats = {
                "chat_history_length": len(self.chat_history),
                "stored_memories": len(self.memory_store),
                "memory_index_size": self.memory_index.ntotal if self.memory_index else 0,
            }
            if self.memory_store:
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
                    mem_type = memory.get("type", "unknown")
                    memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
                    confidence = memory.get("metadata", {}).get("confidence", "unknown")
                    confidence_levels[confidence] = confidence_levels.get(confidence, 0) + 1
                    source = memory.get("metadata", {}).get("source", "unknown")
                    sources[source] = sources.get(source, 0) + 1
                    importance = memory.get("importance", 0.5)
                    total_importance += importance
                    if importance >= 0.8:
                        importance_distribution["high"] += 1
                    elif importance >= 0.6:
                        importance_distribution["medium"] += 1
                    else:
                        importance_distribution["low"] += 1
                    access_count = memory.get("access_count", 0)
                    total_access_count += access_count
                    if access_count >= 5:
                        access_frequency["frequent"] += 1
                    elif access_count >= 2:
                        access_frequency["occasional"] += 1
                    else:
                        access_frequency["rare"] += 1
                    age_days = (current_time - memory.get("timestamp", current_time)) / (24 * 60 * 60)
                    if age_days <= 7:
                        age_distribution["recent"] += 1
                    elif age_days <= 30:
                        age_distribution["old"] += 1
                    else:
                        age_distribution["very_old"] += 1
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
                    "scoring_system": "advanced_ranking_enabled",
                })
            if self.chat_history:
                stats["last_conversation"] = self.chat_history[-1]["timestamp"]
                stats["conversation_turns"] = len([msg for msg in self.chat_history if msg["role"] == "user"])
            return stats
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}

    def cleanup_old_memories(self, days_to_keep: int = 30):
        try:
            current_time = time.time()
            cutoff_timestamp = current_time - (days_to_keep * 24 * 60 * 60)
            memories_to_keep = []
            decay_applied_count = 0
            for memory in self.memory_store:
                memory_timestamp = memory.get("timestamp", current_time)
                age_days = (current_time - memory_timestamp) / (24 * 60 * 60)
                original_importance = memory.get("importance", 0.5)
                decayed_importance = self._apply_memory_decay(original_importance, age_days)
                if decayed_importance != original_importance:
                    memory["importance"] = decayed_importance
                    decay_applied_count += 1
                if memory_timestamp > cutoff_timestamp or decayed_importance > 0.3:
                    memories_to_keep.append(memory)
            removed_count = len(self.memory_store) - len(memories_to_keep)
            if removed_count > 0 or decay_applied_count > 0:
                self.memory_store = memories_to_keep
                if memories_to_keep:
                    self.memory_index = faiss.IndexFlatIP(self.embedding_dim)
                    for memory in memories_to_keep:
                        try:
                            embedding = get_embedding(memory["text"])
                            embedding_array = np.array([embedding]).astype("float32")
                            faiss.normalize_L2(embedding_array)
                            self.memory_index.add(embedding_array)
                        except Exception as e:
                            logger.error(f"Error re-indexing memory: {e}")
                else:
                    self.memory_index = faiss.IndexFlatIP(self.embedding_dim)
                self._save_memory()
                logger.info(f"Memory cleanup: removed {removed_count}, decay applied to {decay_applied_count}, kept {len(memories_to_keep)}")
                return {"removed": removed_count, "kept": len(memories_to_keep), "decay_applied": decay_applied_count}
            return {"removed": 0, "kept": len(self.memory_store), "decay_applied": 0}
        except Exception as e:
            logger.error(f"Error cleaning up memories: {e}")
            return {"error": str(e)}

    def _apply_memory_decay(self, importance: float, age_days: float) -> float:
        try:
            if age_days < 1:
                return importance
            if age_days <= 7:
                decay_factor = 0.95
            elif age_days <= 30:
                decay_factor = 0.85
            elif age_days <= 90:
                decay_factor = 0.70
            elif age_days <= 180:
                decay_factor = 0.50
            else:
                decay_factor = 0.30
            decayed_importance = importance * decay_factor
            if importance > 0.9:
                decayed_importance = max(decayed_importance, 0.6)
            elif importance > 0.8:
                decayed_importance = max(decayed_importance, 0.4)
            return max(decayed_importance, 0.0)
        except Exception as e:
            logger.error(f"Error applying memory decay: {e}")
            return importance


# Global memory instance
agent_memory = AgentMemory()


# Convenience functions
def add_to_chat_history(role: str, content: str):
    agent_memory.add_to_chat_history(role, content)


def get_chat_history(max_messages: int = 10) -> List[Dict[str, str]]:
    return agent_memory.get_chat_history(max_messages)


def store_memory(text: str, memory_type: str = "fact", metadata: Optional[Dict[str, Any]] = None):
    agent_memory.store_memory(text, memory_type, metadata)


def retrieve_memory(query: str, k: int = 3) -> List[Dict[str, Any]]:
    return agent_memory.retrieve_memory(query, k)


def get_memory_context(query: str) -> str:
    return agent_memory.get_memory_context(query)


def get_memory_stats() -> Dict[str, Any]:
    return agent_memory.get_memory_stats()


def clear_chat_history():
    agent_memory.clear_chat_history()


def clear_all_memory():
    agent_memory.clear_all_memory()


def extract_and_store_facts(conversation: str, response: str):
    agent_memory.extract_and_store_facts(conversation, response)
