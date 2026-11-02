"""Pipeline NLP & mesin indexing Information Retrieval.

Tahapan:
    Text Normalization -> Case Folding -> Cleaning -> Stopword Removal
    -> Stemming (Sastrawi) -> Vektorisasi TF-IDF -> Inverted Index
"""

from __future__ import annotations

import re
from collections import defaultdict

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from sklearn.feature_extraction.text import TfidfVectorizer

# Sastrawi: factory menghasilkan objek stemmer/stopword-remover yang siap pakai.
_stemmer = StemmerFactory().create_stemmer()
_stopword_remover = StopWordRemoverFactory().create_stop_word_remover()


def preprocess_text(text: str) -> str:
    """Cleaning -> Case Folding -> Stopword Removal -> Stemming."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    text_clean = _stopword_remover.remove(text)
    text_stemmed = _stemmer.stem(text_clean)

    return text_stemmed


def preprocess_corpus(corpus: list[str]) -> list[str]:
    """Menerapkan ``preprocess_text`` ke seluruh dokumen dalam corpus."""
    return [preprocess_text(doc) for doc in corpus]


def build_tfidf_index(corpus: list[str]):
    """Membangun matriks TF-IDF dari corpus dokumen putusan.

    Mengembalikan ``(vectorizer, tfidf_matrix, feature_names)``.
    """
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    feature_names = vectorizer.get_feature_names_out()

    return vectorizer, tfidf_matrix, feature_names


def build_inverted_index(corpus: list[str]) -> dict[str, set[int]]:
    """Membangun inverted index ``{term: {doc_id, ...}}`` dari corpus terproses."""
    inverted: dict[str, set[int]] = defaultdict(set)
    for doc_id, doc in enumerate(corpus):
        for term in doc.split():
            inverted[term].add(doc_id)
    return dict(inverted)


def tokenize(text: str) -> list[str]:
    """Tokenizing sederhana berbasis spasi atas teks yang telah diproses."""
    return text.split()


def main() -> None:
    sample_docs = [
        "Putusan tindak pidana narkotika dengan barang bukti sabu.",
        "Pengadilan Negeri menjatuhkan pidana penjara kepada terdakwa.",
    ]
    processed = preprocess_corpus(sample_docs)

    vectorizer, matrix, features = build_tfidf_index(processed)
    print("Jumlah dokumen :", matrix.shape[0])
    print("Jumlah fitur   :", matrix.shape[1])
    print("Contoh fitur   :", list(features[:10]))


if __name__ == "__main__":
    main()
