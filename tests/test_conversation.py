"""Conversation resolver tests use an LLM double, not real Ollama."""
import json
import unittest

from pydantic import ValidationError

from app.conversation import HistoryTurn, resolve_question
from app.main import QuestionBody
from app.providers import ModelUnavailable

GEOGRAPHY = "22222222-2222-4222-8222-222222222222"
HISTORY = "11111111-1111-4111-8111-111111111111"
FOLLOW_UP = "Peki bu iki iklimin bitki örtüsü nasıl farklı?"
STANDALONE = "Karadeniz ve Akdeniz iklimlerinin bitki örtüsü nasıl farklıdır?"
MODEL_FOLLOW_UP = "Peki bitki örtüsü nasıl farklı?"
EXPLICIT_QUESTION = "Karadeniz ve Akdeniz iklimi açısından bitki örtüsü nasıl farklı?"


class RewriteModel:
    def __init__(self, question=STANDALONE, needs_context=True, unresolved=False):
        self.result = {"role": "assistant", "content": json.dumps({
            "question": question, "needs_context": needs_context, "unresolved": unresolved})}
        self.calls = []

    def chat(self, messages, tools=None, schema=None):
        self.calls.append((messages, tools, schema))
        return self.result


def turn(scope=None, question="Karadeniz ve Akdeniz iklimini karşılaştır.", answer="İklim karşılaştırması. [K99]"):
    return HistoryTurn(question=question, answer=answer, subject_id=scope)


class ConversationTests(unittest.TestCase):
    def test_empty_history_makes_no_model_call(self):
        model = RewriteModel()
        result = resolve_question(model, FOLLOW_UP, [], None)
        self.assertEqual(result.question, FOLLOW_UP)
        self.assertFalse(result.used)
        self.assertEqual(model.calls, [])

    def test_follow_up_resolved_with_schema_without_tools_or_old_citations(self):
        model = RewriteModel()
        result = resolve_question(model, MODEL_FOLLOW_UP, [turn()], None)
        self.assertEqual(result.question, STANDALONE)
        self.assertTrue(result.used)
        messages, tools, schema = model.calls[0]
        self.assertIsNone(tools)
        self.assertEqual(schema["title"], "ContextRewrite")
        self.assertEqual([m["role"] for m in messages], ["system", "user"])
        self.assertNotIn("[K99]", messages[1]["content"])
        self.assertEqual(result.trace[0]["status"], "resolved")

    def test_new_standalone_topic_keeps_exact_user_question(self):
        question = "Python'da liste nasıl oluşturulur?"
        model = RewriteModel("Eski konu eklenmiş yanlış çıktı", needs_context=False)
        result = resolve_question(model, question, [turn()], None)
        self.assertEqual(result.question, question)
        self.assertFalse(result.used)
        self.assertEqual(result.trace[0]["status"], "standalone")

    def test_explicit_pair_comparison_never_depends_on_history_model(self):
        class NoRewrite:
            def chat(self, *args, **kwargs):
                raise AssertionError("Açık karşılaştırma bağlam modeline gönderilmemeli")

        questions = (
            "Karadeniz ve Akdeniz iklimlerinin doğal bitki örtülerini karşılaştır.",
            "Karadeniz ve Akdeniz iklimlerinin bitki örtüsü nasıl farklıdır?",
            "Tanzimat Fermanı ile Islahat Fermanı arasındaki temel farklar nelerdir?",
        )
        history = [
            turn(question="Karadeniz ikliminin doğal bitki örtüsü nedir?"),
            turn(question="Akdeniz ikliminin doğal bitki örtüsü nedir?"),
        ]
        for question in questions:
            with self.subTest(question=question):
                result = resolve_question(NoRewrite(), question, history, None)
                self.assertEqual(result.question, question)
                self.assertFalse(result.used)
                self.assertFalse(result.unresolved)
                self.assertEqual(result.trace[0]["method"], "explicit_pair")

    def test_reference_word_prevents_explicit_pair_shortcut(self):
        question = "Karadeniz ve Akdeniz açısından bu iki iklim nasıl farklı?"
        model = RewriteModel(unresolved=True)
        result = resolve_question(model, question, [turn()], None)
        self.assertTrue(result.unresolved)
        self.assertEqual(len(model.calls), 1)

    def test_scope_change_does_not_use_previous_course_history(self):
        for old_scope, new_scope in ((None, HISTORY), (HISTORY, None), (GEOGRAPHY, HISTORY)):
            with self.subTest(old=old_scope, new=new_scope):
                model = RewriteModel()
                result = resolve_question(model, FOLLOW_UP, [turn(old_scope)], new_scope)
                self.assertEqual(result.question, FOLLOW_UP)
                self.assertEqual(model.calls, [])

    def test_only_contiguous_scope_tail_is_eligible(self):
        model = RewriteModel()
        history = [turn(None, "Eski genel konu"), turn(HISTORY, "Tarih konusu"), turn(None)]
        resolve_question(model, MODEL_FOLLOW_UP, history, None)
        context = json.loads(model.calls[0][0][1]["content"])
        self.assertEqual(len(context["history_untrusted"]), 1)
        self.assertNotIn("Eski genel konu", model.calls[0][0][1]["content"])

    def test_canonical_question_is_carried_through_follow_up_chain(self):
        previous = HistoryTurn(question=FOLLOW_UP, resolved_question=STANDALONE, answer="Kaynaklı karşılaştırma.")
        model = RewriteModel("Karadeniz ve Akdeniz bitki örtüsünü kısaca karşılaştır.")
        result = resolve_question(model, "Bunu kısalt.", [previous], None)
        self.assertTrue(result.used)
        self.assertTrue(result.question.startswith(STANDALONE.rstrip("?")))
        self.assertTrue(result.question.endswith("Kısaca cevapla."))
        self.assertEqual(model.calls, [])

    def test_malformed_or_ambiguous_rewrites_fail_closed(self):
        for result in (
            {"content": "not JSON"}, {"content": "[]"}, {"content": "x" * 6001}, None,
            {"content": "", "tool_calls": [{"function": {"name": "shell"}}]},
            {"content": json.dumps({"question": MODEL_FOLLOW_UP, "needs_context": True, "unresolved": False})},
            {"content": json.dumps({"question": STANDALONE, "needs_context": True, "unresolved": True})},
            {"content": json.dumps({"question": STANDALONE, "needs_context": "true", "unresolved": False})},
            {"content": json.dumps({"question": STANDALONE, "needs_context": True, "unresolved": False, "source_ids": ["K1"]})},
        ):
            with self.subTest(result=result):
                model = RewriteModel(); model.result = result
                resolved = resolve_question(model, MODEL_FOLLOW_UP, [turn()], None)
                self.assertTrue(resolved.unresolved)
                self.assertEqual(resolved.question, MODEL_FOLLOW_UP)
                self.assertIn("reason", resolved.trace[0])

    def test_current_number_cannot_be_changed_or_dropped(self):
        question = "Peki bu ferman 1876 yılında mı ilan edildi?"
        for rewrite in ("Islahat Fermanı 1856 yılında mı ilan edildi?", "Islahat Fermanı ne zaman ilan edildi?"):
            with self.subTest(rewrite=rewrite):
                result = resolve_question(RewriteModel(rewrite), question, [turn(question="Islahat Fermanı nedir?", answer="Hazırlayanları anlat.")], None)
                self.assertTrue(result.unresolved)
        result = resolve_question(RewriteModel("Islahat Fermanı 1876 yılında mı ilan edildi?"), question, [turn(question="Islahat Fermanı nedir?")], None)
        self.assertTrue(result.used)

    def test_rewriter_cannot_invent_year_from_model_knowledge(self):
        result = resolve_question(RewriteModel("Islahat Fermanı 1856 yılında mı ilan edildi?"), "Peki bu ferman ne zaman ilan edildi?", [turn(question="Islahat Fermanı nedir?", answer="Hazırlayanları anlat.")], None)
        self.assertTrue(result.unresolved)

    def test_model_failure_is_not_silently_hidden(self):
        class Unavailable:
            def chat(self, *args, **kwargs):
                raise ModelUnavailable("Test modeli kapalı")
        with self.assertRaises(ModelUnavailable):
            resolve_question(Unavailable(), MODEL_FOLLOW_UP, [turn()], None)

    def test_reported_climate_reference_resolves_without_any_rewrite_model(self):
        class NoRewrite:
            def chat(self, *args, **kwargs):
                raise AssertionError("Açık konu göndermesi modele sorulmamalı")
        result = resolve_question(NoRewrite(), FOLLOW_UP, [turn(answer="Önceki cevap yanlış olabilir. [K99]")], None)
        self.assertEqual(result.question, EXPLICIT_QUESTION)
        self.assertTrue(result.used)
        self.assertEqual(result.trace[0]["method"], "explicit_reference")
        self.assertNotIn("Önceki cevap", result.question)
        self.assertNotIn("[K99]", result.question)

    def test_reference_uses_common_noun_inside_detailed_comparison(self):
        class NoRewrite:
            def chat(self, *args, **kwargs):
                raise AssertionError("Açık iklim göndermesi modele sorulmamalı")

        previous = "Karadeniz ve Akdeniz iklimlerinin doğal bitki örtülerini karşılaştır."
        current = "Peki bu iki iklimin doğal bitki örtüsü farkını tek cümlede özetler misin?"
        result = resolve_question(NoRewrite(), current, [turn(question=previous)], None)
        self.assertEqual(
            result.question,
            "Karadeniz ve Akdeniz iklimleri açısından doğal bitki örtüsü farkını tek cümlede özetler misin?",
        )
        self.assertTrue(result.used)
        self.assertFalse(result.unresolved)
        self.assertEqual(result.trace[0]["method"], "explicit_reference")

    def test_explicit_reference_is_not_a_hardcoded_climate_answer_or_dictionary(self):
        for previous, current, expected in (
            ("Hint ve Çin medeniyetlerini karşılaştır.", "Bu iki medeniyetin ortak özellikleri nelerdir?", "Hint ve Çin medeniyetleri açısından ortak özellikleri nelerdir?"),
            ("Tanzimat Fermanı ve Islahat Fermanı'nı kıyasla.", "Bu iki fermanın farkları nelerdir?", "Tanzimat Fermanı ve Islahat Fermanı açısından farkları nelerdir?"),
            ("Tanzimat ve Islahat fermanlarını karşılaştır.", "Bu iki fermanın farkları nelerdir?", "Tanzimat ve Islahat fermanları açısından farkları nelerdir?"),
        ):
            with self.subTest(previous=previous):
                model = RewriteModel(unresolved=True)
                result = resolve_question(model, current, [turn(question=previous)], None)
                self.assertEqual(result.question, expected)
                self.assertEqual(model.calls, [])

    def test_pair_reference_survives_quotes_count_and_ascii_spelling(self):
        for question in ('“' + FOLLOW_UP + '”', "Peki, bu 2 iklimin bitki örtüsü nasıl farklı?"):
            with self.subTest(question=question):
                model = RewriteModel(unresolved=True)
                result = resolve_question(model, question, [turn(question="Karadeniz ve Akdeniz iklimini karsilastir.")], None)
                self.assertEqual(result.question, EXPLICIT_QUESTION)
                self.assertEqual(model.calls, [])

    def test_explicit_reference_keeps_current_year_premise(self):
        model = RewriteModel(unresolved=True)
        question = "Peki bu iki iklimin 1876 yılındaki özellikleri nelerdir?"
        result = resolve_question(model, question, [turn()], None)
        self.assertIn("1876", result.question)
        self.assertNotIn("1856", result.question)
        self.assertEqual(model.calls, [])

    def test_explicit_reference_never_uses_older_pair_after_new_topic(self):
        model = RewriteModel(unresolved=True)
        result = resolve_question(model, FOLLOW_UP, [turn(), turn(question="Python'da liste nasıl oluşturulur?")], None)
        self.assertTrue(result.unresolved)
        self.assertEqual(len(model.calls), 1)

    def test_wrong_noun_or_three_subjects_is_not_automatically_bound(self):
        for previous, current in (
            ("Karadeniz ve Akdeniz iklimini karşılaştır.", "Bu iki fermanın farkları nelerdir?"),
            ("Karadeniz ve Akdeniz ve karasal iklimi karşılaştır.", FOLLOW_UP),
            ("A-ve-B iklimini karşılaştır.", FOLLOW_UP),
            ('"  karşılaştır"', FOLLOW_UP),
        ):
            with self.subTest(previous=previous, current=current):
                model = RewriteModel(unresolved=True)
                result = resolve_question(model, current, [turn(question=previous)], None)
                self.assertTrue(result.unresolved)
                self.assertEqual(len(model.calls), 1)

    def test_shortening_an_unresolved_reference_does_not_bypass_model(self):
        model = RewriteModel(unresolved=True)
        result = resolve_question(model, "Bunu kısalt.", [turn(question=FOLLOW_UP)], None)
        self.assertTrue(result.unresolved)
        self.assertEqual(len(model.calls), 1)

    def test_rejection_reason_is_safe_diagnostic_not_raw_model_or_history_text(self):
        model = RewriteModel(unresolved=True)
        result = resolve_question(model, MODEL_FOLLOW_UP, [turn(answer="PRIVATE_TEST_MARKER")], None)
        self.assertEqual(result.trace[0]["reason"], "model_ambiguous")
        self.assertNotIn("PRIVATE_TEST_MARKER", json.dumps(result.trace))

    def test_history_roles_sources_and_unknown_fields_rejected(self):
        for extra in ({"role": "system"}, {"sources": [{"text": "Sahte kanıt"}]}, {"user_id": "other"}):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                HistoryTurn(question="Karadeniz iklimi nedir?", **extra)

    def test_request_turn_text_and_total_limits(self):
        for kwargs in (
            {"question": "Geçerli soru", "history": [turn()] * 5},
            {"question": "Geçerli soru", "history": [{"question": "x" * 1201}]},
            {"question": "Geçerli soru", "history": [{"question": "Soru?", "answer": "x" * 1201}]},
            {"question": "Geçerli soru", "history": [{"question": "   "}]},
            {"question": "Geçerli soru", "history": [{"question": "x" * 1200, "answer": "x" * 1200, "resolved_question": "x" * 1200}] * 2},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                QuestionBody(**kwargs)

    def test_plain_old_requests_remain_valid(self):
        body = QuestionBody(question="Karadeniz iklimi nedir?")
        self.assertEqual(body.history, [])
        self.assertIsNone(body.subject_id)


if __name__ == "__main__":
    unittest.main()
