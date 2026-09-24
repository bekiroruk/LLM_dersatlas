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
    _roman_name_claims_supported,
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

    def test_generic_comparison_uses_balanced_exact_evidence_when_model_abstains(self):
        question = "Tanzimat ve Islahat fermanlarının farkları nelerdir?"
        sources = [
            source(
                "tanzimat",
                "Tanzimat Fermanı 3 Kasım 1839 tarihinde ilan edildi. "
                "Can, mal ve namus güvenliğini düzenledi.",
            ),
            source(
                "islahat",
                "Islahat Fermanı 1856 yılında ilan edildi. "
                "Gayrimüslim tebaanın haklarını genişletti.",
            ),
            source(
                "distractor",
                "Osmanlı Devleti ile ilgili genel bir tekrar sayfasıdır.",
            ),
        ]
        abstention = {
            "role": "assistant",
            "content": json.dumps({
                "answer": "",
                "source_ids": [],
                "insufficient_evidence": True,
            }),
        }
        result, model = self.run_question(
            question,
            sources=sources,
            responses=[abstention],
        )

        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(
            result["answer_method"],
            "comparison_evidence_excerpt",
        )
        self.assertIn("Tanzimat Fermanı", result["answer"])
        self.assertIn("Islahat Fermanı", result["answer"])
        self.assertNotIn("genel bir tekrar", result["answer"])
        self.assertEqual(len(result["sources"]), 2)
        self.assertTrue(any(
            item["tool"] == "balanced_comparison_context"
            for item in result["trace"]
        ))
        for messages, _ in model.calls:
            context = messages[1]["content"]
            self.assertNotIn("genel bir tekrar", context)

    def test_generic_comparison_accepts_grounded_synthesis_across_two_pages(self):
        question = "Tanzimat ve Islahat fermanlarının farkları nelerdir?"
        sources = [
            source(
                "shared",
                "Tanzimat Fermanı'nda Mustafa Reşit Paşa etkilidir. "
                "Islahat Fermanı'nda Âli ve Fuat Paşalar etkilidir.",
            ),
            source(
                "tanzimat",
                "Tanzimat Fermanı 3 Kasım 1839 tarihinde ilan edildi. "
                "Can, mal ve namus güvenliğini düzenledi.",
            ),
            source(
                "islahat",
                "Islahat Fermanı 1856 yılında ilan edildi. "
                "Gayrimüslim tebaanın haklarını genişletti.",
            ),
        ]
        answer = (
            "Tanzimat Fermanı 1839 yılında ilan edilip can, mal ve namus "
            "güvenliğini düzenlerken Islahat Fermanı 1856 yılında ilan "
            "edilmiş ve gayrimüslim tebaanın haklarını genişletmiştir. "
            "[K1] [K2]"
        )
        result, model = self.run_question(
            question,
            sources=sources,
            responses=[payload(answer, ["K1", "K2"])],
        )

        self.assertEqual(result["outcome"], "answered")
        self.assertNotEqual(
            result.get("answer_method"),
            "comparison_evidence_excerpt",
        )
        self.assertIn("1839", result["answer"])
        self.assertIn("1856", result["answer"])
        context = self.context(model)
        self.assertIn("Tanzimat Fermanı 3 Kasım 1839", context[0]["text"])
        self.assertIn("Islahat Fermanı 1856", context[1]["text"])

    def test_period_range_and_source_heading_cannot_leak_into_comparison_answer(self):
        question = "Tanzimat ve Islahat fermanlarının farkları nelerdir?"
        sources = [
            source(
                "shared",
                "Tanzimat Dönemi 1839-1876 arasındadır. "
                "Tanzimat Fermanı'nda Mustafa Reşit Paşa etkilidir. "
                "Islahat Fermanı'nda Âli ve Fuat Paşalar etkilidir.",
            ),
            source(
                "tanzimat",
                "Tanzimat Fermanı 3 Kasım 1839 tarihinde ilan edildi. "
                "Can, mal ve namus güvenliğini düzenledi.",
            ),
            source(
                "islahat",
                "Islahat Fermanı 1856 yılında ilan edildi. "
                "Gayrimüslim tebaanın haklarını genişletti. "
                "118. CİZYE VERGİSİNİN KALDIRILMASIYLA İLİŞKİ",
            ),
        ]
        invalid = (
            "Tanzimat Fermanı 1839-1876 yılları arasında ilan edilmiştir. "
            "İlgili kaynaklarda '118. CİZYE VERGİSİNİN KALDIRILMASIYLA "
            "İLİŞKİ' gibi detaylar bulunmaktadır. [K1] [K2] [K3]"
        )
        result, _ = self.run_question(
            question,
            sources=sources,
            responses=[payload(invalid, ["K1", "K2", "K3"])],
        )

        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(
            result["answer_method"],
            "comparison_evidence_excerpt",
        )
        self.assertNotIn("1839-1876 yılları arasında ilan", result["answer"])
        self.assertNotIn("İlgili kaynaklarda", result["answer"])
        self.assertNotIn("gibi detaylar", result["answer"])
        self.assertTrue(any(
            item["tool"] == "unsupported_claim_rejected"
            for item in result["trace"]
        ))

    def test_reported_comparison_fallback_is_clean_and_topic_focused(self):
        question = "Tanzimat ve Islahat fermanlarının farkları nelerdir?"
        sources = [
            source(
                "tanzimat-summary",
                "Çırağan Olayı II. Abdülhamid’e karşıdır. "
                "Tanzimat Dönemi 1839-1876 arasındadır. "
                "Tanzimat Dönemi padişahları Abdülmecid, Abdülaziz ve "
                "V. Murat’tır. Tanzimat Fermanı’nda Mustafa Reşit Paşa "
                "etkilidir.",
            ),
            source(
                "islahat-rights",
                "İl genel meclislerine katılabilecek Yeni okul ve ibadethane "
                "açabilecek Kritik eşleştirme Azınlıklara en geniş haklar → "
                "Islahat Fermanı 118. CİZYE VERGİSİNİN KALDIRILMASIYLA "
                "İLİŞKİ",
            ),
            source(
                "tanzimat-reasons",
                "Tanzimat Fermanı → Mustafa Reşit Paşa 111. TANZİMAT "
                "FERMANI’NIN İLAN NEDENLERİ Başlıca nedenler: Azınlık "
                "isyanlarını önlemek Avrupa devletlerinin iç işlerine "
                "karışmasını engellemek",
            ),
            source(
                "islahat-summary",
                "115. ISLAHAT FERMANI Islahat Fermanı: Abdülmecid "
                "Dönemi’nde ilan edilmiştir. Hazırlanmasında etkili "
                "olanlar: Âli Paşa",
            ),
        ]
        abstention = {
            "role": "assistant",
            "content": json.dumps({
                "answer": "",
                "source_ids": [],
                "insufficient_evidence": True,
            }),
        }
        result, _ = self.run_question(
            question,
            sources=sources,
            responses=[abstention],
        )

        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(
            result["answer_method"],
            "comparison_evidence_excerpt",
        )
        self.assertIn("Karşılaştırma:\nTanzimat:", result["answer"])
        self.assertIn("\nIslahat:", result["answer"])
        self.assertIn("Azınlık isyanlarını önlemek;", result["answer"])
        self.assertIn("Azınlıklara en geniş haklar", result["answer"])
        self.assertIn("Abdülmecid Dönemi’nde ilan edilmiştir", result["answer"])
        for leaked in (
            "Çırağan Olayı",
            "1839-1876",
            "İl genel meclislerine",
            "Kritik eşleştirme",
            "111.",
            "115.",
            "118.",
            "CİZYE VERGİSİNİN KALDIRILMASIYLA İLİŞKİ",
        ):
            with self.subTest(leaked=leaked):
                self.assertNotIn(leaked, result["answer"])

    def test_ferman_comparison_prefers_ferman_facts_over_period_boundary(self):
        question = "Tanzimat ve Islahat fermanlarının farkları nelerdir?"
        sources = [
            source(
                "period",
                "Tanzimat Dönemi: 1839 Tanzimat Fermanı’nın ilanından "
                "1876 I. Meşrutiyet’in ilanına kadar geçen süreçtir.",
            ),
            source(
                "tanzimat",
                "Tanzimat Fermanı → Mustafa Reşit Paşa 111. TANZİMAT "
                "FERMANI’NIN İLAN NEDENLERİ Başlıca nedenler: Azınlık "
                "isyanlarını önlemek Avrupa devletlerinin iç işlerine "
                "karışmasını engellemek",
            ),
            source(
                "shared",
                "Tanzimat Fermanı: Osmanlı Devleti’nde anayasallaşma "
                "sürecini başlatmıştır. Islahat Fermanı: Abdülmecid "
                "Dönemi’nde ilan edilmiştir. Hazırlanmasında etkili "
                "olanlar: Âli Paşa Fuat Paşa. Tanzimat Fermanı’yla "
                "benzer amaçlar taşır: Azınlık isyanlarını önlemek "
                "Avrupa müdahalesini azaltmak Osmanlı Devleti’nin "
                "dağılmasını önlemek Azınlıkları devlete bağlamak",
            ),
            source(
                "islahat",
                "Islahat Fermanı’yla: Gayrimüslimlere çok geniş haklar "
                "verilmiştir. Azınlıklar: Devlet memuru olabilecek Asker "
                "olabilecek Her tür okula gidebilecek",
            ),
        ]
        abstention = {
            "role": "assistant",
            "content": json.dumps({
                "answer": "",
                "source_ids": [],
                "insufficient_evidence": True,
            }),
        }
        result, model = self.run_question(
            question,
            sources=sources,
            responses=[abstention],
        )

        context = "\n".join(item["text"] for item in self.context(model))
        self.assertNotIn("1839 Tanzimat Fermanı’nın ilanından", context)
        self.assertNotIn("benzer amaçlar taşır", context)
        self.assertIn("Tanzimat Fermanı: Mustafa Reşit Paşa", context)
        self.assertIn("anayasallaşma sürecini başlatmıştır", context)
        self.assertIn("Gayrimüslimlere çok geniş haklar", context)
        self.assertEqual(result["outcome"], "answered")
        self.assertNotIn("1839 Tanzimat Fermanı’nın ilanından", result["answer"])

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
        result, model = self.run_question(
            question,
            sources=[rainfall, source("plants", TABLE)],
        )
        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(result["answer_method"], "structured_evidence")
        self.assertIn("yıl boyunca düzenlidir", result["answer"])
        self.assertIn("yağış rejimi: düzensizdir", result["answer"])
        self.assertIn("Nemli ormanlar", result["answer"])
        self.assertIn("Kızılçam, maki", result["answer"])
        self.assertEqual({item["chunk_id"] for item in result["sources"]}, {"rainfall", "plants"})
        self.assertEqual(model.calls, [])

    def test_mixed_question_rejects_vegetation_only_sources(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        result, model = self.run_question(question, sources=[source("plants", TABLE)])
        self.assertEqual(result["outcome"], "insufficient")
        self.assertEqual(model.calls, [])

    def test_incomplete_or_misassigned_rainfall_rows_fail_closed(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        bad_karadeniz = source(
            "bad-karadeniz",
            "Karadeniz iklimi\nYaz sıcak ve kurak\n"
            "Kış soğuk ve kar yağışlı.",
        )
        incomplete_akdeniz = source(
            "incomplete-akdeniz",
            "Akdeniz iklimi orta kuşak ve mutlak konumla ilişkilidir; "
            "en fazla yağış kışın cephelerle düşer.",
        )

        result, model = self.run_question(
            question,
            sources=[source("plants", TABLE), bad_karadeniz, incomplete_akdeniz],
        )

        self.assertEqual(result["outcome"], "insufficient")
        self.assertNotIn("kış soğuk", result["answer"].casefold())
        self.assertNotIn("mutlak konum", result["answer"].casefold())
        self.assertEqual(model.calls, [])

    def test_mixed_question_uses_structured_evidence_before_model(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        rainfall = source(
            "rainfall",
            "Karadeniz ikliminde yağış yıl boyunca düzenlidir. "
            "Akdeniz ikliminde yağış düzensizdir ve yaz kuraklığı görülür.",
        )
        result, model = self.run_question(
            question,
            sources=[rainfall, source("plants", TABLE)],
            responses=[payload("Geçersiz model yanıtı. [K99]", ["K99"])],
        )
        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(result["answer_method"], "structured_evidence")
        self.assertIn("yıl boyunca düzenlidir", result["answer"])
        self.assertIn("yağış rejimi: düzensizdir", result["answer"])
        self.assertIn("Nemli ormanlar", result["answer"])
        self.assertIn("Kızılçam, maki", result["answer"])
        self.assertEqual(model.calls, [])
        self.assertEqual(
            {item["chunk_id"] for item in result["sources"]},
            {"rainfall", "plants"},
        )

    def test_reported_clipped_rainfall_text_is_rendered_as_clean_claims(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        rainfall = source(
            "rainfall",
            "Karadeniz iklimi yağış rejimi: ’de azdır. Tuzak / not: "
            "‘Yaz yağışlı’ ile ‘yaz kuraklığı yok’ aynı şey değildir; "
            "Karadeniz yıl boyu yağışlıdır.\n"
            "Akdeniz iklimi yağış rejimi: kış yağışlı; yaz kurak, "
            "zeytin, rejim düzensiz.",
        )

        result, model = self.run_question(
            question,
            sources=[source("plants", TABLE), rainfall],
        )

        self.assertEqual(result["outcome"], "answered")
        self.assertEqual(result["answer_method"], "structured_evidence")
        self.assertIn("yağış rejimi: yıl boyu yağışlıdır", result["answer"])
        self.assertIn(
            "yağış rejimi: kış yağışlı; yaz kurak; rejim düzensizdir",
            result["answer"],
        )
        self.assertNotIn("’de azdır", result["answer"])
        self.assertNotIn("Tuzak", result["answer"])
        self.assertNotIn("zeytin", result["answer"])
        self.assertEqual(model.calls, [])

    def test_reported_table_rows_become_a_clean_sourced_comparison(self):
        question = (
            "Karadeniz ve Akdeniz iklimlerini yağış rejimleri ve doğal "
            "bitki örtüleri bakımından karşılaştır."
        )
        rainfall = source(
            "rainfall-table",
            "Yayılış Gürcistan sınırından Bulgaristan sınırına kadar "
            "Karadeniz kıyıları; İstanbul’un kuzeyi ve Yıldız Dağları "
            "Yaz Serin ve yağışlı Kış Ilık ve yağışlı "
            "En fazla yağış Sonbahar\n"
            "Güney Marmara, Ege kıyıları, Akdeniz kıyıları ve "
            "Güneydoğu’nun batısı Yaz Sıcak ve kurak "
            "Kış Ilık ve yağışlı En fazla yağış Kış",
        )
        vegetation = source(
            "vegetation-table",
            "Flora bölgesi Türkiye'de yayılışı Baskın görünüm\n"
            "Avrupa-Sibirya Marmara’nın kuzeyi ve Karadeniz kıyı kuşağı "
            "Nemli ormanlar\n"
            "Güney Marmara, Ege, Akdeniz ve Güneydoğu’nun batısına "
            "uzanan Akdeniz iklim sahaları Kızılçam, maki ve kuraklığa "
            "dayanıklı Akdeniz türleri",
        )
        result, model = self.run_question(
            question,
            sources=[vegetation, rainfall],
        )

        self.assertEqual(result["answer_method"], "structured_evidence")
        self.assertIn("yaz serin ve yağışlı", result["answer"])
        self.assertIn("en fazla yağış dönemi: sonbahar", result["answer"])
        self.assertIn("Nemli ormanlar", result["answer"])
        self.assertIn("yaz sıcak ve kurak", result["answer"])
        self.assertIn("Kızılçam, maki ve kuraklığa dayanıklı", result["answer"])
        self.assertNotIn("Yayılış Gürcistan", result["answer"])
        self.assertNotIn("Notlarındaki ilgili kaynak satırları", result["answer"])
        self.assertEqual(model.calls, [])

    def test_attached_ile_wording_uses_the_same_structured_comparison(self):
        question = (
            "Akdeniz iklimiyle Karadeniz iklimini yağış düzeni ve "
            "bitki örtüsü yönünden kıyaslar mısın?"
        )
        rainfall = source(
            "rainfall",
            "Akdeniz ikliminde yağış düzensizdir ve yaz kuraklığı görülür. "
            "Karadeniz ikliminde yağış yıl boyunca düzenlidir.",
        )
        result, model = self.run_question(
            question,
            sources=[source("plants", TABLE), rainfall],
        )
        self.assertEqual(result["answer_method"], "structured_evidence")
        self.assertIn("Akdeniz iklimi", result["answer"])
        self.assertIn("Karadeniz iklimi", result["answer"])
        self.assertIn("Kızılçam, maki", result["answer"])
        self.assertIn("Nemli ormanlar", result["answer"])
        self.assertEqual(model.calls, [])

    def test_context_summary_request_produces_exactly_one_grounded_sentence(self):
        question = (
            "Akdeniz iklimiyle Karadeniz iklimini yağış düzeni ve "
            "bitki örtüsü yönünden kıyaslar mısın. en belirgin "
            "farkı tek cümlede özetler misin?"
        )
        rainfall = source(
            "rainfall",
            "Akdeniz ikliminde yağış düzensizdir ve yaz kuraklığı görülür. "
            "Karadeniz ikliminde yağış yıl boyunca düzenlidir.",
        )
        result, model = self.run_question(
            question,
            sources=[source("plants", TABLE), rainfall],
        )
        self.assertEqual(result["answer_method"], "structured_evidence")
        self.assertEqual(result["answer"].count("."), 1)
        self.assertIn("buna karşılık", result["answer"])
        self.assertEqual(model.calls, [])

    def test_single_rainfall_fact_returns_only_the_requested_season(self):
        notes = source(
            "rainfall",
            "Karadeniz ikliminde her ay yağış 50 mm üzerindedir ve en fazla "
            "yağış sonbahardadır. Tuzak: Grafikte önce 50 mm çizgisini "
            "kontrol edin. Sert karasal iklimde yaz maksimumu vardır.",
        )
        result, model = self.run_question(
            "Karadeniz ikliminde en fazla yağış hangi mevsimde görülür?",
            sources=[notes],
        )
        self.assertEqual(
            result["answer"],
            "Karadeniz ikliminde en fazla yağış sonbahar mevsiminde görülür. [K1]",
        )
        self.assertNotIn("Tuzak", result["answer"])
        self.assertEqual(model.calls, [])

    def test_false_year_premise_is_corrected_from_explicit_source(self):
        notes = source("reform", "Islahat Fermanı 1856 yılında ilan edilmiştir.")
        result, model = self.run_question(
            "Islahat Fermanı 1876 yılında mı ilan edildi?",
            sources=[notes],
        )
        self.assertEqual(
            result["answer"],
            "Hayır. Islahat Fermanı 1856 yılında ilan edilmiştir. [K1]",
        )
        self.assertEqual(model.calls, [])

    def test_conquest_date_and_ruler_are_copied_from_explicit_event_block(self):
        notes = source(
            "conquest",
            "İstanbul'un Fethi\nTarih: 29 Mayıs 1453\n"
            "Padişah: Fatih Sultan Mehmet",
        )
        result, model = self.run_question(
            "İstanbul hangi tarihte ve hangi padişah döneminde fethedildi?",
            sources=[notes],
        )
        self.assertEqual(
            result["answer"],
            "İstanbul 29 Mayıs 1453 tarihinde Fatih Sultan Mehmet döneminde "
            "fethedilmiştir. [K1]",
        )
        self.assertNotIn("I. Fatih", result["answer"])
        self.assertEqual(model.calls, [])

    def test_conquest_prefers_complete_ruler_over_malformed_ordinal_title(self):
        malformed = source(
            "malformed-conquest",
            "İstanbul'un Fethi\nTarih: 29 Mayıs 1453\n"
            "Padişah: I. Fatih Sultan",
        )
        complete = source(
            "complete-conquest",
            "İstanbul'un Fethi\nTarih: 29 Mayıs 1453\n"
            "Padişah: Fatih Sultan Mehmet",
        )
        result, model = self.run_question(
            "İstanbul hangi tarihte ve hangi padişah döneminde fethedildi?",
            sources=[malformed, complete],
        )
        self.assertIn("Fatih Sultan Mehmet döneminde", result["answer"])
        self.assertNotIn("I. Fatih", result["answer"])
        self.assertEqual(model.calls, [])

    def test_conquest_with_date_but_without_ruler_fails_closed(self):
        date_only = source(
            "date-only-conquest",
            "Yükselme Dönemi son tekrar\nİstanbul 29 Mayıs 1453'te fethedildi.\n"
            "Feth-i Mübin İstanbul'un fethidir.",
        )
        unrelated = source(
            "unrelated-ruler",
            "Meclisi açma-kapama yetkisi padişahtadır. Devletin başkenti "
            "İstanbul'dur.",
        )
        result, model = self.run_question(
            "İstanbul hangi tarihte ve hangi padişah döneminde fethedildi?",
            sources=[date_only, unrelated],
        )
        self.assertEqual(result["outcome"], "insufficient")
        self.assertNotIn("Meclisi açma", result["answer"])
        self.assertEqual(model.calls, [])

    def test_question_bank_list_cannot_be_returned_as_an_answer(self):
        questions = source(
            "question-bank",
            "Konfederasyonda üye devletler kişiliklerini korur mu? "
            "Türkiye’de yasama yetkisi hangi organa aittir? "
            "Türkiye’de yürütme yetkisi ve görevi kime aittir? "
            "Yargı yetkisi kimlerce kullanılır?",
        )
        copied = payload(
            "Türkiye’de yasama yetkisi hangi organa aittir? "
            "Türkiye’de yürütme yetkisi ve görevi kime aittir? [K1]",
            ["K1"],
        )
        result, _ = self.run_question(
            "1982 Anayasası'na göre yasama yetkisi kime aittir?",
            sources=[questions],
            responses=[copied],
        )
        self.assertNotEqual(result["outcome"], "answered")
        self.assertNotIn("hangi organa aittir?", result["answer"])

    def test_model_cannot_add_an_unsupported_roman_ordinal_to_a_name(self):
        self.assertFalse(_roman_name_claims_supported(
            "İstanbul I. Fatih Sultan döneminde fethedildi.",
            ["Fatih Sultan Mehmet tarafından fethedildi."],
        ))
        self.assertTrue(_roman_name_claims_supported(
            "I. Meşrutiyet ilan edildi.",
            ["I. Meşrutiyet ilan edildi."],
        ))

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
