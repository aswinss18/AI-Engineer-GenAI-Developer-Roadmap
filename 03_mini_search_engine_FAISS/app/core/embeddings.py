import hashlib
import numpy as np

def get_embedding(text: str, dim: int = 128):
    """Deterministic lightweight embedding for demo/testing.

    Produces a fixed-size vector from input text using repeated SHA-256
    digests. This avoids external dependencies and provides stable
    embeddings across runs.
    """
    if text is None:
        text = ""

    out = np.zeros(dim, dtype=float)
    i = 0
    filled = 0
    while filled < dim:
        chunk = hashlib.sha256((text + str(i)).encode("utf-8")).digest()
        for b in chunk:
            if filled >= dim:
                break
            out[filled] = float(b)
            filled += 1
        i += 1

    return out


def normalize(vec):
    a = np.array(vec, dtype=float)
    norm = np.linalg.norm(a)
    if norm == 0:
        return a
    return a / norm
