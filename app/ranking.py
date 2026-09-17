"""Bağımsız ve test edilebilir BM25 + Reciprocal Rank Fusion."""
import math
import re
from collections import Counter, defaultdict

STOP_WORDS = set(
    """
    ve veya ile bir bu şu o da de için
    mı mi mu mü nedir nelerdir nasıl hangi
    kim kimdir kime hakkında göre bana
    anlat açıkla lütfen
    """.split()
)


def tokenize(text):
    """Türkçe arama için kelime ve hafif ek normalizasyonu."""

    text = text.replace("İ", "i").replace("I", "ı").lower()

    # Tarihî metinlerde sık görülen şapkalı harfleri normalize et.
    text = text.translate(
        str.maketrans(
            {
                "â": "a",
                "î": "i",
                "û": "u",
            }
        )
    )

    words = [
        word
        for word in re.findall(r"[^\W_]+", text, re.UNICODE)
        if word not in STOP_WORDS and len(word) > 1
    ]

    expanded = []

    for word in words:
        expanded.append(word)

        # kayseri -> kayser
        # tarihi -> tarih
        # devleti -> devlet
        # fermanı -> ferman
        if len(word) > 5 and word[-1] in {"i", "ı", "u", "ü"}:
            stem = word[:-1]

            if len(stem) > 2 and stem not in STOP_WORDS:
                expanded.append(stem)

    return expanded


def bm25(query, documents):
    """documents: (id, text) listesi. Sadece pozitif eşleşmeleri döndürür."""
    query_tokens = set(tokenize(query))
    if not documents or not query_tokens:
        return []
    tokenized = [(key, tokenize(text)) for key, text in documents]
    avg_length = sum(len(tokens) for _, tokens in tokenized) / len(tokenized) or 1
    df = Counter(term for _, tokens in tokenized for term in set(tokens))
    scores = []
    for key, tokens in tokenized:
        counts = Counter(tokens)
        score = 0.0
        for term in query_tokens:
            frequency = counts[term]
            if frequency:
                idf = math.log(1 + (len(documents) - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * len(tokens) / avg_length))
        if score > 0:
            scores.append((key, score))
    return sorted(scores, key=lambda x: (-x[1], x[0]))


def reciprocal_rank_fusion(*rankings, k=60):
    scores = defaultdict(float)
    for ranking in rankings:
        for rank, (key, _) in enumerate(ranking, 1):
            scores[key] += 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))

