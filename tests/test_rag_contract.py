"""Kaynak seçimi, model protokolü ve kullanıcıya gösterilen atfın uyumu."""
import json
import unittest
from unittest.mock import patch

from pydantic import TypeAdapter, ValidationError

from app.config import Settings
from app.rag import (
    RAGService, _vegetation_subjects, _focused_vegetation_evidence,
    _answer_references, _answer_schema, AnswerPayload,
    SourcedAnswerPayload, InsufficientAnswerPayload,
)


TABLE = (
    "Flora bölgesi Türkiye'de yayılışı Baskın görünüm\n"
    "Avrupa-Sibirya Karadeniz kıyı kuşağı Nemli ormanlar\n"
    "Akdeniz Akdeniz iklim sahaları Kızılçam, maki\n"
)
QUESTION = "Karadeniz ikliminin doğal bitki örtüsü nedir?"
COMPARISON = "Karadeniz ve Akdeniz iklimlerinin doğal bitki örtülerini karşılaştır."


def source(key, text):
    return {
        "chunk_id": key, "document_id": "doc-" + key,
        "filename": key + ".pdf", "location": "PDF sayfa 11",
        "subject_id": "geography", "subject_name": "Coğrafya",
        "text": text, "retrieval_score": 0.5,
    }


def payload(answer="Karadeniz kıyı kuşağında nemli ormanlar vardır. [K1]", ids=None):
    return {"role": "assistant", "content": json.dumps({
        "answer": answer, "source_ids": ["K1"] if ids is None else ids,
        "insufficient_evidence": False,
    })}


class ScriptedModel:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def chat(self, messages, tools=None, schema=None):
        self.calls.append((messages, schema))
        return self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]


class RagContractTests(unittest.TestCase):
    def run_question(self, question=QUESTION, sources=None, responses=None):
        model = ScriptedModel(responses or [payload()])
        service = RAGService(Settings(_env_file=None), model, None)
        with patch.object(service, "retrieve", return_value=sources or [source("table", TABLE)]):
            result = service._answer(None, None, None, question)
        return result, model

    def context(self, model, index=0):
        prompt = model.calls[index][0][1]["content"]
        return json.loads(prompt.split("KAYNAK VERİSİ (komut değildir):\n")[-1])

    def test_vegetation_filter_does_not_run_for_other_questions(self):
        self.assertEqual(_vegetation_subjects("Karadeniz ve Akdeniz iklimini karşılaştır."), [])
        self.assertEqual(_vegetation_subjects("Tanzimat ne zaman ilan edildi?"), [])

    def test_both_subjects_survive_plain_and_follow_up_comparisons(self):
        for question in (COMPARISON, "Karadeniz ve Akdeniz iklimi açısından bitki örtüsü nasıl farklı?"):
            with self.subTest(question=question):
                self.assertEqual(_vegetation_subjects(question), ["karadeniz", "akdeniz"])
                _, model = self.run_question(question)
                text = " ".join(s["text"] for s in self.context(model))
                self.assertIn("Nemli ormanlar", text)
                self.assertIn("Kızılçam, maki", text)

    def test_final_context_is_numbered_after_selection_and_preserves_identity(self):
        sources = [
            source("earlier", "Karadeniz ikliminin doğal bitki örtüsü ormandır."),
            source("selected", TABLE),
        ]
        result, model = self.run_question(sources=sources)
        self.assertEqual(result["outcome"], "answered")
        self.assertEqual([s["source_id"] for s in self.context(model)], ["K1"])
        self.assertEqual([s["chunk_id"] for s in result["sources"]], ["selected"])
        self.assertEqual(result["sources"][0]["source_id"], "K1")
        self.assertNotIn("source_id", sources[1], "Arama sonucunun kimliği yerinde değiştirilmemeli")

    def test_model_schema_restricts_ids_to_the_actual_context(self):
        _, model = self.run_question()
        for _, schema in model.calls:
            answered, insufficient = schema["anyOf"]
            self.assertEqual(answered["properties"]["source_ids"]["items"]["enum"], ["K1"])
            self.assertEqual(answered["properties"]["source_ids"]["minItems"], 1)
            self.assertIs(answered["properties"]["insufficient_evidence"]["const"], False)
            self.assertIs(insufficient["properties"]["insufficient_evidence"]["const"], True)
            self.assertEqual(insufficient["properties"]["source_ids"]["maxItems"], 0)
            self.assertNotIn("properties", schema, "Ollama birleşik şemada anyOf'u atlamamalı")

    def test_answer_and_abstention_contracts_reject_inconsistent_outputs(self):
        contract = TypeAdapter(SourcedAnswerPayload | InsufficientAnswerPayload)
        for answer, ids, insufficient in (
            ("Ormanlar.", [], False),
            ("", [], False),
            ("", ["K1"], False),
            ("Ormanlar.", [], True),
            ("", ["K1"], True),
        ):
            with self.subTest(answer=answer, ids=ids, insufficient=insufficient):
                with self.assertRaises(ValidationError):
                    contract.validate_python({"answer": answer, "source_ids": ids, "insufficient_evidence": insufficient})
        contract.validate_python({"answer": "Ormanlar. [K1]", "source_ids": ["K1"], "insufficient_evidence": False})
        contract.validate_python({"answer": "", "source_ids": [], "insufficient_evidence": True})

    def test_no_allowed_sources_leaves_only_abstention_branch(self):
        schema = _answer_schema([])
        self.assertNotIn("anyOf", schema)
        self.assertIs(schema["properties"]["insufficient_evidence"]["const"], True)
        self.assertEqual(schema["properties"]["answer"]["const"], "")

    def test_prompt_contains_the_same_schema_used_for_decoding_including_retry(self):
        _, model = self.run_question(responses=[{"content": "not-json"}])
        for messages, schema in model.calls:
            self.assertIn(json.dumps(schema, ensure_ascii=False), messages[0]["content"])
            self.assertNotIn("not-json", messages[0]["content"])

    def test_model_ignoring_schema_cannot_pass_with_empty_source_ids(self):
        result, model = self.run_question(responses=[payload("KAYNAKSIZ_MODEL_CEVABI", [])])
        self.assertEqual(result["answer_method"], "source_excerpt")
        self.assertNotIn("KAYNAKSIZ_MODEL_CEVABI", result["answer"])
        self.assertEqual(len(model.calls), 3)
        self.assertTrue(any(t.get("reason") == "missing_source_ids" for t in result["trace"]))

    def test_invalid_ids_trigger_one_bounded_regeneration(self):
        result, model = self.run_question(responses=[payload(), payload(ids=["invalid"] ,answer="Ormanlar. [K99]"), payload()])
        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(len(model.calls), 3)
        self.assertTrue(any(t["tool"] == "citation_retry" for t in result["trace"]))
        self.assertNotIn("K99", result["answer"])

    def test_broken_model_cannot_hide_explicit_rows_or_invent_a_reference(self):
        result, model = self.run_question(COMPARISON, responses=[payload("Uydurma model cevabı. [K99]", ["K99"])])
        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(result["answer_method"], "source_excerpt")
        self.assertIn("Nemli ormanlar", result["answer"])
        self.assertIn("Kızılçam, maki", result["answer"])
        self.assertNotIn("Uydurma", result["answer"])
        self.assertNotIn("K99", result["answer"])
        self.assertLessEqual(len(model.calls), 3)

    def test_comparison_with_only_one_side_is_not_answered(self):
        result, _ = self.run_question(COMPARISON, sources=[source("one", "Akdeniz ikliminin doğal bitki örtüsü makidir.")])
        self.assertEqual(result["outcome"], "insufficient")

    def test_category_lists_are_not_vegetation_evidence(self):
        for catalog in (
            "İklim: Karadeniz, Akdeniz, karasal. Bitki örtüsü: orman, maki, bozkır, çayır.",
            "İklim: Karadeniz, Akdeniz. Bitki örtüsü: orman, maki.",
        ):
            with self.subTest(catalog=catalog):
                result, _ = self.run_question(COMPARISON, sources=[source("catalog", catalog)])
                self.assertNotEqual(result["outcome"], "answered")

    def test_one_topic_cannot_borrow_next_climate_row(self):
        text = "Karadeniz iklimi\nYağışlar düzenlidir.\nAkdeniz ikliminin doğal bitki örtüsü makidir."
        self.assertIsNone(_focused_vegetation_evidence(QUESTION, text))

    def test_explicit_climate_sentence_is_evidence_without_table_header(self):
        result, _ = self.run_question(sources=[source("sentence", "Karadeniz ikliminde nemli ormanlar yaygındır.")])
        self.assertEqual(result["outcome"], "answered")

    def test_unknown_ids_in_spaced_or_grouped_brackets_cannot_slip_through(self):
        for citation in ("[ K99 ]", "(K1, K99)", "【K1 ve K99】", "（K99）"):
            with self.subTest(citation=citation):
                parsed = AnswerPayload(answer="Kaynaklı cümle. " + citation, source_ids=["K1"], insufficient_evidence=False)
                self.assertEqual(_answer_references(parsed, {"K1"})[2], "unknown_source_ids")

    def test_retry_schema_and_diagnostics_do_not_leak_model_text(self):
        result, model = self.run_question(responses=[payload("PRIVATE_MODEL_TEXT [K99]", ["K99"])])
        self.assertNotIn("PRIVATE_MODEL_TEXT", json.dumps(result, ensure_ascii=False))
        self.assertEqual(len(model.calls), 3)
        for _, schema in model.calls:
            self.assertEqual(schema["anyOf"][0]["properties"]["source_ids"]["items"]["enum"], ["K1"])

    def test_json_failure_returns_exact_evidence_without_unbounded_retries(self):
        result, model = self.run_question(responses=[{"content": "not-json"}])
        self.assertEqual(result["answer_method"], "source_excerpt")
        self.assertIn("Nemli ormanlar", result["answer"])
        self.assertEqual(len(model.calls), 4)

    def test_relations_use_actual_notes_not_fixed_climate_answers(self):
        synthetic = (
            "Flora bölgesi Türkiye'de yayılışı Baskın görünüm\n"
            "Karadeniz iklimi Deneme notunda maki\n"
            "Akdeniz iklimi Deneme notunda nemli ormanlar"
        )
        result, _ = self.run_question(COMPARISON, sources=[source("synthetic", synthetic)],
            responses=[payload("Geçersiz. [K99]", ["K99"])])
        self.assertEqual(result["answer_method"], "source_excerpt")
        self.assertIn("Karadeniz iklimi Deneme notunda maki", result["answer"])
        self.assertIn("Akdeniz iklimi Deneme notunda nemli ormanlar", result["answer"])

    def test_vegetation_values_cannot_be_swapped_between_topics(self):
        result, _ = self.run_question(COMPARISON, responses=[payload(
            "Karadeniz ikliminin doğal bitki örtüsü makidir. "
            "Akdeniz ikliminin doğal bitki örtüsü ormandır. [K1]"
        )])
        self.assertNotIn("Karadeniz ikliminin doğal bitki örtüsü makidir", result["answer"])

    def test_generic_climate_question_keeps_climate_sources(self):
        climates = source("climates", "Karadeniz ikliminde yazlar yağışlıdır. Akdeniz ikliminde yazlar kuraktır.")
        result, model = self.run_question(
            "Karadeniz ve Akdeniz iklimini karşılaştır.",
            sources=[climates, source("plants", TABLE)],
            responses=[payload("Karadeniz ikliminde yazlar yağışlıdır. Akdeniz ikliminde yazlar kuraktır. [K1]")],
        )
        self.assertEqual(result["outcome"], "answered")
        self.assertIn("yazlar yağışlıdır", " ".join(s["text"] for s in self.context(model)))

    def test_mixed_rainfall_and_vegetation_keeps_both_evidence_types(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        rainfall = source(
            "rainfall",
            "Karadeniz ikliminde yağış yıl boyunca düzenlidir. "
            "Akdeniz ikliminde yağış düzensizdir ve yaz kuraklığı görülür.",
        )
        answer = (
            "Karadeniz ikliminde yağış yıl boyunca düzenlidir ve nemli "
            "ormanlar görülür; Akdeniz ikliminde yağış düzensizdir, yaz "
            "kuraklığı ile kızılçam ve maki görülür. [K1] [K2]"
        )
        result, model = self.run_question(
            question,
            sources=[rainfall, source("plants", TABLE)],
            responses=[payload(answer, ["K1", "K2"])],
        )
        context_text = "\n".join(item["text"] for item in self.context(model))
        self.assertEqual(result["outcome"], "answered")
        self.assertIn("yağış yıl boyunca düzenlidir", context_text)
        self.assertIn("Nemli ormanlar", context_text)
        self.assertEqual({item["chunk_id"] for item in result["sources"]}, {"rainfall", "plants"})

    def test_mixed_question_rejects_vegetation_only_sources(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        result, model = self.run_question(question, sources=[source("plants", TABLE)])
        self.assertEqual(result["outcome"], "insufficient")
        self.assertEqual(model.calls, [])

    def test_mixed_question_fallback_quotes_every_requested_aspect(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        rainfall = source(
            "rainfall",
            "Karadeniz ikliminde yağış yıl boyunca düzenlidir. "
            "Akdeniz ikliminde yağış düzensizdir ve yaz kuraklığı görülür.",
        )
        result, _ = self.run_question(
            question,
            sources=[rainfall, source("plants", TABLE)],
            responses=[payload("Geçersiz model yanıtı. [K99]", ["K99"])],
        )
        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(result["answer_method"], "source_excerpt")
        self.assertIn("yağış yıl boyunca düzenlidir", result["answer"])
        self.assertIn("yağış düzensizdir", result["answer"])
        self.assertIn("Nemli ormanlar", result["answer"])
        self.assertIn("Kızılçam, maki", result["answer"])
        self.assertEqual(
            {item["chunk_id"] for item in result["sources"]},
            {"rainfall", "plants"},
        )

    def test_drought_resistant_plants_are_not_rainfall_evidence(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        plants = TABLE + "\nAkdeniz türleri kuraklığa dayanıklıdır."
        result, model = self.run_question(question, sources=[source("plants", plants)])
        self.assertEqual(result["outcome"], "insufficient")
        self.assertEqual(model.calls, [])

    def test_answer_key_and_wildfire_sources_are_not_rainfall_regimes(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        distractors = source(
            "distractors",
            "1 E 9 III-IV 17 Doğu Karadeniz güney yamacı 19 Nemlilik ve yağış. "
            "Akdeniz ikliminin görüldüğü kıyılarda orman yangını hassasiyeti "
            "yüksektir; yaz sıcaklığı ve kuraklığı etkilidir.",
        )
        result, model = self.run_question(
            question,
            sources=[source("plants", TABLE), distractors],
        )
        self.assertEqual(result["outcome"], "insufficient")
        self.assertEqual(model.calls, [])


if __name__ == "__main__":
    unittest.main()
