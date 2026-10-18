import os
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from backend.services import script_generator as generator


class GenerationTests(unittest.TestCase):
    def test_explicit_topic_and_audience_are_not_rewritten(self):
        self.assertEqual(generator._explicit_request_parts("바다 생태계에 대해 궁금증을 풀어가며 이야기해줘")["topic"], "바다 생태계")
        parts = generator._explicit_request_parts("중학생을 위한 자전거 여행 방송")
        self.assertEqual(parts["topic"], "자전거 여행")
        self.assertEqual(parts["audience"], "중학생")

    def test_interprets_request_with_topic_specific_questions(self):
        cases = [
            ("바다 생태계에 대해 궁금증을 풀어가며 이야기해줘", "바다 생태계", "일반 청취자", ["먹이그물은 어떻게 이어지나요?", "해조류는 어떤 역할을 하나요?", "산호와 생물은 어떻게 연결되나요?", "환경 변화는 어떤 영향을 주나요?", "생물 간 관계가 왜 중요한가요?"]),
            ("중학생을 위한 자전거 여행 방송", "자전거 여행", "중학생", ["자전거는 어떻게 점검하나요?", "경로는 어떻게 고르나요?", "어떤 준비물이 필요한가요?", "휴식은 어떻게 계획하나요?", "어떤 안전 수칙을 확인하나요?"]),
        ]
        for request, topic, audience, questions in cases:
            with self.subTest(topic=topic), patch.object(generator, "_section_draft", return_value={"topic": topic, "audience": audience, "approach": "쉬운 설명", "questions": questions}) as draft:
                brief = generator._request_brief(None, "http://localhost:11434", request, "", 5)
                self.assertEqual(brief["topic"], topic)
                self.assertEqual(brief["audience"], audience)
                self.assertIn(request, draft.call_args.args[2])
                self.assertEqual(len(brief["questions"]), 5)

    def test_model_failure_never_uses_offline_templates(self):
        with patch.object(generator, "build_opener") as factory, patch.object(generator, "_generic_sections") as generic, patch.object(generator, "_known_sections") as known:
            factory.return_value.open.side_effect = URLError("offline")
            with self.assertRaises(generator.ScriptGenerationError):
                generator.generate_script_plan("바다 생태계", "casual", "summary", "ko", "", 5, [])
            generic.assert_not_called()
            known.assert_not_called()

    def test_explicit_offline_setting_is_not_silent_fallback(self):
        with patch.dict(os.environ, {"SCRIPT_PROVIDER": "offline"}):
            with self.assertRaises(generator.ScriptGenerationError):
                generator._ollama_sections("자전거 여행", "summary", "ko", 5)

    def test_model_supplements_missing_content_before_closing(self):
        sections = [("opening", "바다", [("A", "먹이그물은 서로 연결되어 있습니다.")]), ("closing", "마무리", [("A", "다음에는 주변 바다도 관찰해보세요.")])]
        drafts = [
            {"title": "해조류의 역할", "dialogue": [{"speaker": "A", "text": text} for text in ["해조류는 햇빛을 이용해 유기물을 만듭니다.", "작은 동물들이 그 유기물을 먹습니다.", "해조류 숲은 숨을 공간이 되기도 합니다.", "서식지와 먹이를 함께 살펴볼 수 있죠."]]},
            {"title": "조간대의 변화", "dialogue": [{"speaker": "A", "text": text} for text in ["밀물과 썰물로 바닷물이 드러나는 곳이 달라집니다.", "그곳에 사는 생물은 노출되는 시간을 견뎌야 합니다.", "바위 틈에 붙어 있는 생물을 떠올려보세요.", "사는 위치에 따라 만나는 환경이 다릅니다."]]},
        ]
        with patch.object(generator, "_section_draft", side_effect=drafts) as draft:
            result = generator._complete_missing_content(None, "local", "주제: 바다 생태계", sections, 5)
            self.assertEqual(draft.call_count, 2)
            self.assertEqual(result[-1][0], "closing")
            self.assertEqual(result[1][1], "해조류의 역할")
            self.assertEqual(sections[1][0], "closing")

    def test_repeated_dialogue_and_boilerplate_are_rejected(self):
        with self.assertRaises(ValueError):
            generator._validate_new_turns([("A", "해조류 숲은 작은 생물들의 서식지가 됩니다.")], [("main", "내용", [("A", "해조류 숲은 작은 생물들의 서식지가 됩니다.")])])
        with self.assertRaises(ValueError):
            generator._validate_new_turns([("A", "처음부터 전부 결정하기보다 조건을 나누세요.")], [])

    def test_render_uses_resolved_topic_and_warns_when_short(self):
        sections = [("main", "먹이그물", [("A", "작은 생물을 먹는 생물도 다른 생물의 먹이가 됩니다.")])]
        brief = {"topic": "바다 생태계", "questions": ["먹이그물은 무엇인가요?"], "audience": "중학생", "approach": "쉬운 설명"}
        with patch.object(generator, "_ollama_sections", return_value=(sections, brief)):
            plan = generator.generate_script_plan("바다 생태계를 설명해줘", "casual", "summary", "ko", "", 5, [])
        self.assertEqual(plan.resolved_topic, "바다 생태계")
        self.assertNotIn("설명해줘", plan.script)
        self.assertIn("목표 시간보다 짧은", plan.generation_notice)
        self.assertEqual(plan.generation_provider, "ollama")

    def test_duplicate_section_is_rewritten_instead_of_aborting(self):
        repeated = "해조류 숲은 작은 생물들의 서식지가 됩니다."
        sections = [("main", "서식지", [("A", repeated)])]
        good = {"title": "먹이 관계", "dialogue": [{"speaker": "A", "text": text} for text in ["플랑크톤은 바다 먹이그물의 출발점 중 하나입니다.", "작은 동물이 플랑크톤을 먹습니다.", "그 작은 동물을 물고기가 먹기도 하죠.", "이런 관계가 서로 이어져 있습니다."]]}
        bad = {"title": "반복", "dialogue": [{"speaker": "A", "text": repeated}] * 4}
        with patch.object(generator, "_section_draft", side_effect=[bad, good]) as draft:
            result = generator._validated_section(None, "local", "질문", sections)
        self.assertEqual(result, good)
        self.assertEqual(draft.call_count, 2)
        self.assertIn("재작성 1", draft.call_args.args[2])

    def test_short_reactions_are_allowed(self):
        generator._validate_new_turns([("A", "그렇군요.")], [("main", "내용", [("A", "그렇군요.")])])

    def test_rewrite_attempts_are_bounded(self):
        repeated = "해조류 숲은 작은 생물들의 서식지가 됩니다."
        bad = {"title": "반복", "dialogue": [{"speaker": "A", "text": repeated}] * 4}
        with patch.object(generator, "_section_draft", return_value=bad) as draft:
            with self.assertRaises(generator.ScriptGenerationError):
                generator._validated_section(None, "local", "질문", [])
        self.assertEqual(draft.call_count, 3)

    def test_partial_duplicate_keeps_new_dialogue_without_retry(self):
        repeated = "해조류 숲은 작은 생물들의 서식지가 됩니다."
        draft = {"title": "먹이", "dialogue": [
            {"speaker": "A", "text": repeated},
            {"speaker": "A", "text": "민서: 작은 생물은 다른 동물의 먹이가 됩니다."},
            {"speaker": "B", "text": "먹이 관계가 서로 이어지는 거군요."},
            {"speaker": "A", "text": repeated}]}
        with patch.object(generator, "_section_draft", return_value=draft) as model:
            result = generator._validated_section(None, "local", "질문", [("main", "서식지", [("A", repeated)])])
        self.assertEqual(model.call_count, 1)
        self.assertEqual(len(result["dialogue"]), 2)
        self.assertNotIn("민서:", result["dialogue"][0]["text"])

    def test_failed_optional_supplement_keeps_existing_script(self):
        repeated = "해조류 숲은 작은 생물들의 서식지가 됩니다."
        sections = [("main", "내용", [("A", repeated)])]
        bad = {"title": "반복", "dialogue": [{"speaker": "A", "text": repeated}] * 4}
        with patch.object(generator, "_section_draft", return_value=bad):
            result = generator._complete_missing_content(None, "local", "질문", sections, 5)
        self.assertEqual(result, sections)

    def test_repeated_sentence_is_removed_without_losing_new_sentence(self):
        old = "해조류 숲은 작은 생물들의 서식지가 됩니다."
        new = "조간대는 밀물과 썰물의 영향을 받습니다."
        self.assertEqual(generator._without_repeated_sentences(old + " " + new, [("main", "서식지", [("A", old)])]), new)

    def test_mixed_scripts_trigger_rewrite_not_character_deletion(self):
        good = {"title": "은하계의 블랙홀", "dialogue": [
            {"speaker": "A", "text": "우리 은하계에도 블랙홀이 있습니다."},
            {"speaker": "B", "text": "빛이 빠져나오지 못하는 영역을 이야기하는 거죠."}]}
        for title, text in [("블랙홀과 우리銀河系", "우리 은하계 이야기입니다."), ("블랙홀", "우리銀河系의 黑洞입니다."), ("블랙홀", "ブラックホール 이야기입니다.")]:
            bad = {"title": title, "dialogue": [{"speaker": "A", "text": text}, {"speaker": "B", "text": "다음 설명입니다."}]}
            with self.subTest(text=text), patch.object(generator, "_section_draft", side_effect=[bad, good]) as model:
                result = generator._validated_section(None, "local", "질문", [])
                self.assertEqual(result, good)
                self.assertEqual(model.call_count, 2)

    def test_latin_abbreviations_and_names_remain_allowed(self):
        generator._check_script_language("AI와 GPS, NASA의 관측, SAE J3016을 이야기합니다.")


if __name__ == "__main__":
    unittest.main()
