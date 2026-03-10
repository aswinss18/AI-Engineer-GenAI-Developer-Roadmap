from rank_bm25 import BM25Okapi

tokenized_docs = []

bm25 = None


def build_bm25(documents):

    global bm25, tokenized_docs

    tokenized_docs = [doc.split(" ") for doc in documents]

    bm25 = BM25Okapi(tokenized_docs)


def keyword_search(query, k=5):

    query_tokens = query.split(" ")

    scores = bm25.get_scores(query_tokens)

    ranked = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )

    return ranked[:k]