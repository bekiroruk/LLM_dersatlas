import tempfile
import unittest
from pathlib import Path
from app.ranking import tokenize, bm25, reciprocal_rank_fusion
from app.passwords import hash_password, check_password, token_hash
from app.citations import valid_citations
from app.ingestion import Section, DocumentError, chunk_sections, extract_document, clean_text
from app.rag import (
    _declared_source_ids,
    _focused_vegetation_evidence,
    _focused_climate_aspect_evidence,
    _normalize_citation_shapes,
    _retrieval_queries,
)
from pypdf import PdfWriter
from docx import Document as WordDocument


class CoreTests(unittest.TestCase):
    def test_comparison_retrieval_splits_both_sides(self):
        question = "Karadeniz ve Akdeniz iklimi açısından bitki örtüsü nasıl farklı?"
        self.assertEqual(
            _retrieval_queries(question),
            [
                question,
                "Karadeniz iklimi bitki örtüsü nasıl farklı",
                "Akdeniz iklimi bitki örtüsü nasıl farklı",
                "Karadeniz iklimi doğal bitki örtüsü flora bitki varlığı baskın görünüm",
                "Akdeniz iklimi doğal bitki örtüsü flora bitki varlığı baskın görünüm",
            ],
        )

    def test_mixed_comparison_adds_dedicated_rainfall_searches(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        self.assertEqual(
            _retrieval_queries(question),
            [
                "Karadeniz iklimi yağış rejimi yağışların mevsimlere dağılışı en fazla yağış en az yağış",
                "Akdeniz iklimi yağış rejimi yağışların mevsimlere dağılışı en fazla yağış en az yağış",
                "Karadeniz iklimi doğal bitki örtüsü flora bitki varlığı baskın görünüm",
                "Akdeniz iklimi doğal bitki örtüsü flora bitki varlığı baskın görünüm",
            ],
        )

    def test_attached_ile_comparison_splits_both_climates(self):
        question = (
            "Akdeniz iklimiyle Karadeniz iklimini yağış düzeni ve "
            "bitki örtüsü yönünden kıyaslar mısın?"
        )
        queries = _retrieval_queries(question)
        self.assertEqual(len(queries), 4)
        self.assertTrue(any(query.startswith("Akdeniz iklimi yağış rejimi") for query in queries))
        self.assertTrue(any(query.startswith("Karadeniz iklimi yağış rejimi") for query in queries))
        self.assertIn(
            "Akdeniz iklimi doğal bitki örtüsü flora bitki varlığı baskın görünüm",
            queries,
        )
        self.assertIn(
            "Karadeniz iklimi doğal bitki örtüsü flora bitki varlığı baskın görünüm",
            queries,
        )

    def test_false_year_question_adds_a_year_neutral_verification_query(self):
        question = "Islahat Fermanı 1876 yılında mı ilan edildi?"
        self.assertEqual(
            _retrieval_queries(question),
            [
                question,
                "Islahat Fermanı yılında ilan edildi",
                "Islahat Fermanı ilan tarihi hangi yıl",
            ],
        )

    def test_rainfall_evidence_rejects_answer_key_and_wildfire_text(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        distractors = (
            "1 E 9 III-IV 17 Doğu Karadeniz güney yamacı 18 Kahverengi orman 19 Nemlilik ve yağış",
            "Türkiye’de orman yangını hassasiyeti Akdeniz ikliminin görüldüğü kıyılarda yüksektir. Yaz sıcaklığı ve kuraklığı etkilidir.",
        )
        for text in distractors:
            with self.subTest(text=text):
                self.assertIsNone(
                    _focused_climate_aspect_evidence(question, text, "precipitation")
                )

    def test_vegetation_table_row_is_kept_as_one_evidence_relation(self):
        text = """11. TÜRKİYE'NİN BİTKİ VARLIĞI
11.1. Flora bölgeleri
Flora bölgesi Türkiye'de yayılışı Baskın görünüm
Avrupa-Sibirya Marmara'nın kuzeyi ve Karadeniz kıyı
kuşağı Nemli ormanlar
Akdeniz
Güney Marmara, Ege, Akdeniz ve
Güneydoğu'nun batısına uzanan
Akdeniz iklim sahaları
Kızılçam, maki ve kuraklığa dayanıklı Akdeniz türleri
Relikt Karadeniz'de kızılçam; Akdeniz'de kayın."""
        focus = _focused_vegetation_evidence(
            "Karadeniz ve Akdeniz iklimi açısından bitki örtüsü nasıl farklı?",
            text,
        )
        self.assertEqual(focus["covered"], ("karadeniz", "akdeniz"))
        self.assertIn("Karadeniz kıyı kuşağı Nemli ormanlar", focus["text"])
        self.assertIn("Akdeniz iklim sahaları Kızılçam, maki", focus["text"])
        self.assertNotIn("Relikt", focus["text"])

    def test_turkish_case(self):
        self.assertEqual(tokenize("ISLAHAT İSTANBUL ve 1839"), ["ıslahat", "istanbul", "1839"])

    def test_bm25_exact_date(self):
        result = bm25("1839 Tanzimat", [("a", "1856 Islahat Fermanı"), ("b", "1839 Tanzimat Fermanı")])
        self.assertEqual(result[0][0], "b")

    def test_no_lexical_match(self):
        self.assertEqual(bm25("kuantum", [("a", "Tanzimat Fermanı")]), [])

    def test_stop_words(self):
        self.assertEqual(bm25("ve veya için", [("a", "ve veya için")]), [])

    def test_rrf_consensus(self):
        result = reciprocal_rank_fusion([("a", .9), ("b", .8)], [("b", 10)])
        self.assertEqual(result[0][0], "b")
        self.assertLess(result[0][1], .1)

    def test_chunk_source_not_lost(self):
        parts = chunk_sections([Section("PDF sayfa 3", "Ankara " * 100), Section("PDF sayfa 4", "Meclis " * 100)], 100, 15)
        self.assertGreater(len(parts), 2)
        self.assertEqual({p.location for p in parts}, {"PDF sayfa 3", "PDF sayfa 4"})
        self.assertTrue(all(len(p.text) <= 100 for p in parts))

    def test_chunk_overlap_long_word(self):
        parts = chunk_sections([Section("blok 1", "a" * 301)], 100, 20)
        self.assertEqual(len(parts), 4)
        self.assertEqual(len(parts[-1].text), 61)

    def test_invalid_chunking(self):
        with self.assertRaises(ValueError):
            chunk_sections([], 100, 100)

    def test_text_cleanup(self):
        self.assertEqual(clean_text("A  B\r\n\n\nC\x00"), "A B\n\nC")

    def test_utf8_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not.md"
            path.write_text("# Tarih\n\nİstanbul ve Millî Mücadele", encoding="utf-8")
            sections, _ = extract_document(path, path.name)
            self.assertEqual(len(sections), 2)
            self.assertIn("İstanbul", sections[1].text)

    def test_non_utf8_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not.txt"
            path.write_bytes(b"\xff\xff")
            with self.assertRaises(DocumentError):
                extract_document(path, path.name)

    def test_blank_pdf_ocr_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "taranmis.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            writer.write(path)
            with self.assertRaisesRegex(DocumentError, "OCR"):
                extract_document(path, path.name)

    def test_docx_table_location(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not.docx"
            document = WordDocument()
            document.add_paragraph("Tarih notu")
            table = document.add_table(rows=1, cols=2)
            table.cell(0, 0).text, table.cell(0, 1).text = "1839", "Tanzimat"
            document.save(path)
            sections, warning = extract_document(path, path.name)
            self.assertTrue(any(s.location == "Tablo 1, satır 1" and "1839" in s.text for s in sections))
            self.assertIn("sayfa numarası değildir", warning)

    def test_password_salt_and_verification(self):
        first = hash_password("Güvenli-parola-123")
        second = hash_password("Güvenli-parola-123")
        self.assertNotEqual(first, second)
        self.assertTrue(check_password("Güvenli-parola-123", first))
        self.assertFalse(check_password("yanlış", first))
        self.assertFalse(check_password("test", "bozuk"))

    def test_password_length(self):
        with self.assertRaises(ValueError):
            hash_password("123")

    def test_session_hash(self):
        self.assertEqual(len(token_hash("opaque-session")), 64)
        self.assertNotEqual(token_hash("a"), token_hash("b"))

    def test_valid_citation(self):
        self.assertTrue(valid_citations("Kaynaklı cevap. [K1]", ["K1"], ["K1", "K2"]))

    def test_unknown_citation_rejected(self):
        self.assertFalse(valid_citations("Cevap. [K99]", ["K99"], ["K1"]))

    def test_missing_inline_citation_rejected(self):
        self.assertFalse(valid_citations("Cevap.", ["K1"], ["K1"]))

    def test_metadata_citation_mismatch(self):
        self.assertFalse(valid_citations("Cevap. [K1]", ["K2"], ["K1", "K2"]))

    def test_common_local_model_citation_shapes_are_normalized(self):
        self.assertEqual(
            _normalize_citation_shapes("Cevap. (K1) [K2, K3] 【K4】"),
            "Cevap. [K1] [K2] [K3] [K4]",
        )
        self.assertEqual(
            _declared_source_ids(["[K1, K2]", "K3 ve K4"]),
            ({"K1", "K2", "K3", "K4"}, False),
        )


if __name__ == "__main__":
    unittest.main()
