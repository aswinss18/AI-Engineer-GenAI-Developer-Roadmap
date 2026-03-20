"""
Advanced Prompt Architecture - Minimal + Structured + Purpose-driven
Implements modular prompt system with token optimization
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PromptTemplates:
    """Modular prompt templates for different use cases"""
    
    # Core prompt templates - minimal and focused
    RAG_PROMPT = """You are a precise AI assistant analyzing documents.

Context: {context}

Question: {question}

Answer clearly with sources."""

    AGENT_PROMPT = """You are an AI agent with tools.

Available tools: {tools}

Query: {query}

Decide: Answer directly OR call tools. Be concise."""

    MEMORY_PROMPT = """User Profile: {profile}

Relevant Memory: {memory}

Use only if relevant to current query."""

    CALCULATION_PROMPT = """You are a calculation assistant.

Data: {data}
Task: {task}

Calculate precisely and explain briefly."""

    WEATHER_PROMPT = """You are a weather assistant.

Location: {location}
Query: {query}

Provide current weather information."""

    # System behavior templates
    REACT_SYSTEM = """Use ReAct pattern:
1. Reason about the query
2. Act with appropriate tools
3. Observe results
4. Provide final answer

Be systematic and concise."""

    DOCUMENT_SEARCH_SYSTEM = """For person/entity queries:
1. ALWAYS search documents first
2. Extract relevant information
3. Provide comprehensive answer

For general queries: Use judgment."""

class PromptBuilder:
    """Dynamic prompt builder with token optimization"""
    
    def __init__(self):
        self.templates = PromptTemplates()
        self.max_context_chars = 1500
        self.max_memory_items = 3
        self.max_chunks = 5
    
    def build_rag_prompt(self, context: str, question: str) -> str:
        """Build optimized RAG prompt"""
        try:
            # Optimize context length
            optimized_context = self._optimize_context(context)
            
            return self.templates.RAG_PROMPT.format(
                context=optimized_context,
                question=question
            )
        except Exception as e:
            logger.error(f"Error building RAG prompt: {e}")
            return f"Answer this question based on the context: {question}"
    
    def build_agent_prompt(self, query: str, available_tools: List[str]) -> str:
        """Build optimized agent prompt"""
        try:
            # Optimize tools list
            tools_str = ", ".join(available_tools[:6])  # Limit to 6 tools
            
            return self.templates.AGENT_PROMPT.format(
                tools=tools_str,
                query=query
            )
        except Exception as e:
            logger.error(f"Error building agent prompt: {e}")
            return f"Process this query with available tools: {query}"
    
    def build_memory_prompt(self, profile: str, memory: List[Dict[str, Any]]) -> str:
        """Build optimized memory prompt"""
        try:
            # Optimize memory items
            optimized_memory = self._optimize_memory(memory)
            
            return self.templates.MEMORY_PROMPT.format(
                profile=profile,
                memory=optimized_memory
            )
        except Exception as e:
            logger.error(f"Error building memory prompt: {e}")
            return ""
    
    def build_combined_prompt(self, 
                            query: str,
                            context: Optional[str] = None,
                            memory: Optional[List[Dict[str, Any]]] = None,
                            available_tools: Optional[List[str]] = None,
                            user_profile: Optional[str] = None) -> str:
        """Build combined prompt with all components"""
        try:
            prompt_parts = []
            
            # Base agent prompt
            if available_tools:
                agent_prompt = self.build_agent_prompt(query, available_tools)
                prompt_parts.append(agent_prompt)
            
            # Memory context if available
            if memory and user_profile:
                memory_prompt = self.build_memory_prompt(user_profile, memory)
                if memory_prompt.strip():
                    prompt_parts.append(memory_prompt)
            
            # Document context if available
            if context:
                rag_prompt = self.build_rag_prompt(context, query)
                prompt_parts.append(rag_prompt)
            
            # System instructions
            prompt_parts.append(self.templates.REACT_SYSTEM)
            prompt_parts.append(self.templates.DOCUMENT_SEARCH_SYSTEM)
            
            # Combine with separators
            final_prompt = "\n\n".join(prompt_parts)
            
            # Final optimization
            return self._optimize_final_prompt(final_prompt)
            
        except Exception as e:
            logger.error(f"Error building combined prompt: {e}")
            return f"Process this query: {query}"
    
    def _optimize_context(self, context: str) -> str:
        """Optimize context for token efficiency"""
        try:
            if len(context) <= self.max_context_chars:
                return context
            
            # Split into sentences and prioritize
            sentences = context.split('. ')
            
            # Keep most important sentences (those with key terms)
            key_terms = ['name', 'salary', 'work', 'company', 'experience', 'location', 'goal']
            
            prioritized = []
            remaining = []
            
            for sentence in sentences:
                if any(term in sentence.lower() for term in key_terms):
                    prioritized.append(sentence)
                else:
                    remaining.append(sentence)
            
            # Combine prioritized first, then add remaining until limit
            result = '. '.join(prioritized)
            
            for sentence in remaining:
                test_result = result + '. ' + sentence
                if len(test_result) <= self.max_context_chars:
                    result = test_result
                else:
                    break
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing context: {e}")
            return context[:self.max_context_chars]
    
    def _optimize_memory(self, memory: List[Dict[str, Any]]) -> str:
        """Optimize memory for token efficiency"""
        try:
            if not memory:
                return ""
            
            # Limit to top memories
            top_memories = memory[:self.max_memory_items]
            
            # Format concisely
            memory_items = []
            for mem in top_memories:
                text = mem.get("text", "")
                importance = mem.get("importance", 0)
                confidence = mem.get("confidence", "medium")
                
                # Truncate long memories
                if len(text) > 100:
                    text = text[:97] + "..."
                
                memory_items.append(f"[{confidence}] {text}")
            
            return "\n".join(memory_items)
            
        except Exception as e:
            logger.error(f"Error optimizing memory: {e}")
            return ""
    
    def _optimize_final_prompt(self, prompt: str) -> str:
        """Final prompt optimization"""
        try:
            # Remove redundant whitespace
            lines = [line.strip() for line in prompt.split('\n') if line.strip()]
            
            # Remove duplicate lines
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen:
                    seen.add(line)
                    unique_lines.append(line)
            
            return '\n'.join(unique_lines)
            
        except Exception as e:
            logger.error(f"Error in final optimization: {e}")
            return prompt

class ContextSelector:
    """Smart context selection for optimal token usage"""
    
    def __init__(self):
        self.max_chunks = 5
        self.min_score_threshold = 0.7
    
    def select_best_context(self, chunks: List[Dict[str, Any]], query: str) -> str:
        """Select best context chunks with smart filtering"""
        try:
            if not chunks:
                return ""
            
            # Filter by score threshold
            high_score_chunks = [
                chunk for chunk in chunks 
                if chunk.get("combined_score", 0) >= self.min_score_threshold
            ]
            
            # If not enough high-score chunks, use top chunks
            if len(high_score_chunks) < 3:
                high_score_chunks = chunks[:self.max_chunks]
            else:
                high_score_chunks = high_score_chunks[:self.max_chunks]
            
            # Extract and combine text
            context_parts = []
            for chunk in high_score_chunks:
                text = chunk.get("text", "")
                doc = chunk.get("doc", "unknown")
                page = chunk.get("page", 0)
                
                # Add source info
                context_parts.append(f"[{doc}, p{page}] {text}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error selecting context: {e}")
            return ""
    
    def remove_duplicates(self, context: str) -> str:
        """Remove duplicate content from context"""
        try:
            paragraphs = context.split('\n\n')
            unique_paragraphs = []
            seen_content = set()
            
            for para in paragraphs:
                # Create a normalized version for comparison
                normalized = ' '.join(para.lower().split())
                
                # Check for substantial overlap
                is_duplicate = False
                for seen in seen_content:
                    if self._calculate_overlap(normalized, seen) > 0.8:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_paragraphs.append(para)
                    seen_content.add(normalized)
            
            return '\n\n'.join(unique_paragraphs)
            
        except Exception as e:
            logger.error(f"Error removing duplicates: {e}")
            return context
    
    def _calculate_overlap(self, text1: str, text2: str) -> float:
        """Calculate text overlap ratio"""
        try:
            words1 = set(text1.split())
            words2 = set(text2.split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating overlap: {e}")
            return 0.0

class MemorySelector:
    """Smart memory selection for relevant context"""
    
    def __init__(self):
        self.max_memories = 3
        self.relevance_threshold = 0.6
    
    def select_relevant_memories(self, memories: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Select most relevant memories for the query"""
        try:
            if not memories:
                return []
            
            # Filter by relevance score
            relevant_memories = [
                mem for mem in memories 
                if mem.get("combined_score", 0) >= self.relevance_threshold
            ]
            
            # Sort by combined score
            relevant_memories.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
            
            # Return top memories
            return relevant_memories[:self.max_memories]
            
        except Exception as e:
            logger.error(f"Error selecting memories: {e}")
            return memories[:self.max_memories]

# Global instances
prompt_builder = PromptBuilder()
context_selector = ContextSelector()
memory_selector = MemorySelector()

# Convenience functions
def build_optimized_prompt(query: str, 
                         context: Optional[str] = None,
                         memory: Optional[List[Dict[str, Any]]] = None,
                         available_tools: Optional[List[str]] = None,
                         user_profile: Optional[str] = None) -> str:
    """Build optimized prompt with all components"""
    return prompt_builder.build_combined_prompt(
        query=query,
        context=context,
        memory=memory,
        available_tools=available_tools,
        user_profile=user_profile
    )

def optimize_context(chunks: List[Dict[str, Any]], query: str) -> str:
    """Optimize context selection"""
    context = context_selector.select_best_context(chunks, query)
    return context_selector.remove_duplicates(context)

def optimize_memory(memories: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Optimize memory selection"""
    return memory_selector.select_relevant_memories(memories, query)