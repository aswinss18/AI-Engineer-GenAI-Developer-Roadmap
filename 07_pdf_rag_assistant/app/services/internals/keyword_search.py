"""
Keyword-based search for hybrid retrieval
Combines with vector search for better coverage
"""

import re
import logging
from typing import List, Dict, Any, Set
from collections import Counter, defaultdict
import math

logger = logging.getLogger(__name__)

class KeywordSearcher:
    def __init__(self):
        self.documents = []
        self.inverted_index = defaultdict(set)
        self.document_frequencies = defaultdict(int)
        self.total_documents = 0
        
    def build_index(self, documents: List[Dict[str, Any]]):
        """Build inverted index for keyword search"""
        logger.info(f"Building keyword search index for {len(documents)} documents")
        
        self.documents = documents
        self.total_documents = len(documents)
        self.inverted_index.clear()
        self.document_frequencies.clear()
        
        for doc_idx, doc in enumerate(documents):
            text = doc.get("text", "").lower()
            words = self._tokenize(text)
            unique_words = set(words)
            
            # Build inverted index
            for word in unique_words:
                self.inverted_index[word].add(doc_idx)
                self.document_frequencies[word] += 1
        
        logger.info(f"Index built with {len(self.inverted_index)} unique terms")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - split on non-alphanumeric characters"""
        # Remove punctuation and split
        words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        # Filter out very short words
        return [word for word in words if len(word) >= 2]
    
    def _calculate_tf_idf(self, query_terms: List[str], doc_idx: int) -> float:
        """Calculate TF-IDF score for a document given query terms"""
        if doc_idx >= len(self.documents):
            return 0.0
        
        doc_text = self.documents[doc_idx].get("text", "").lower()
        doc_words = self._tokenize(doc_text)
        doc_word_count = len(doc_words)
        
        if doc_word_count == 0:
            return 0.0
        
        # Count term frequencies in document
        term_counts = Counter(doc_words)
        score = 0.0
        
        for term in query_terms:
            if term in term_counts:
                # Term frequency
                tf = term_counts[term] / doc_word_count
                
                # Inverse document frequency
                df = self.document_frequencies.get(term, 0)
                if df > 0:
                    idf = math.log(self.total_documents / df)
                else:
                    idf = 0
                
                # TF-IDF score
                score += tf * idf
        
        return float(score)  # Ensure Python float
    
    def search(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Perform keyword search using TF-IDF scoring
        
        Args:
            query: Search query string
            k: Number of results to return
            
        Returns:
            List of documents with keyword search scores
        """
        if not self.documents:
            logger.warning("No documents indexed for keyword search")
            return []
        
        query_terms = self._tokenize(query)
        if not query_terms:
            logger.warning("No valid query terms found")
            return []
        
        logger.info(f"Keyword search for terms: {query_terms}")
        
        # Find documents containing any query terms
        candidate_docs = set()
        for term in query_terms:
            if term in self.inverted_index:
                candidate_docs.update(self.inverted_index[term])
        
        if not candidate_docs:
            logger.info("No documents found containing query terms")
            return []
        
        # Calculate TF-IDF scores for candidates
        scored_docs = []
        for doc_idx in candidate_docs:
            score = self._calculate_tf_idf(query_terms, doc_idx)
            if score > 0:
                doc_copy = self.documents[doc_idx].copy()
                doc_copy.update({
                    "keyword_score": float(score),  # Ensure Python float
                    "search_type": "keyword",
                    "matched_terms": [term for term in query_terms 
                                    if term in self.documents[doc_idx].get("text", "").lower()]
                })
                scored_docs.append((score, doc_copy))
        
        # Sort by score and return top-k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        results = [doc for _, doc in scored_docs[:k]]
        
        logger.info(f"Keyword search found {len(results)} results")
        return results

# Global keyword searcher instance
keyword_searcher = KeywordSearcher()

def build_keyword_index(documents: List[Dict[str, Any]]):
    """Build keyword search index from documents"""
    keyword_searcher.build_index(documents)

def keyword_search(query: str, k: int = 10) -> List[Dict[str, Any]]:
    """Perform keyword search"""
    return keyword_searcher.search(query, k)

def get_keyword_index_status() -> Dict[str, Any]:
    """Get status of keyword search index"""
    return {
        "total_documents": keyword_searcher.total_documents,
        "unique_terms": len(keyword_searcher.inverted_index),
        "index_built": keyword_searcher.total_documents > 0
    }