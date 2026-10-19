import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch

from backend.services import tts_service as tts


class SupertonicTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.environment = patch.dict(os.environ, {
            "TTS_PROVIDER": "supertonic", "SUPERTONIC_VOICE_A": "F1",
            "SUPERTONIC_VOICE_B": "M1", "SUPERTONIC_MODEL_DIR": str(self.root),
            "SUPERTONIC_PROSODY": "1", "SUPERTONIC_EXPRESSIONS": "0",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        directory_patch = patch.object(tts, "STATIC_AUDIO_DIR", self.root)
        directory_patch.start()
        self.addCleanup(directory_patch.stop)
        self.engine = Mock()
        self.engine.get_voice_style.side_effect = lambda voice: voice
        self.engine.synthesize.return_value = (b"\x01\x00" * 4410, .1)

        def save(audio, path):
            with wave.open(path, "wb") as output:
                output.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
                output.writeframes(audio)
        self.engine.save_audio.side_effect = save
        engine_patch = patch.object(tts, "_supertonic_engine", return_value=self.engine)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)

    def test_stable_hosts_and_joined_audio(self):
        url = tts.create_speech_file("도윤: 반가워요.\n민서: 안녕하세요.\n도윤: 다시 만났네요.")
        calls = self.engine.synthesize.call_args_list
        self.assertEqual([call.kwargs["voice_style"] for call in calls], ["M1", "F1", "M1"])
        self.assertTrue(all(call.kwargs["lang"] == "ko" for call in calls))
        with wave.open(str(self.root / url.rsplit("/", 1)[1]), "rb") as audio:
            self.assertEqual(audio.getframerate(), 44100)
            self.assertEqual(audio.getnframes(), 3 * 4410 + 2 * int(44100 * .22))
        self.assertEqual(list(self.root.glob("supertonic-*")), [])
        self.assertEqual(tts.get_tts_provider_label(), "Supertonic 3")

    def test_single_unknown_host_and_english(self):
        tts.create_speech_file("Alex: Hello everyone.\nAlex: Welcome back.")
        self.assertEqual([call.kwargs["voice_style"] for call in self.engine.synthesize.call_args_list], ["F1", "F1"])
        self.assertEqual(self.engine.synthesize.call_args.kwargs["lang"], "en")

    def test_invalid_input_and_voices(self):
        for script in ("", "하나: 안녕\n둘: 안녕\n셋: 안녕"):
            with self.assertRaises(tts.TtsError):
                tts.create_speech_file(script)
        with patch.dict(os.environ, {"SUPERTONIC_VOICE_B": "F1"}):
            with self.assertRaises(tts.TtsError):
                tts.create_speech_file("민서: 안녕하세요.")

    def test_failure_does_not_fallback_or_leave_files(self):
        self.engine.synthesize.side_effect = RuntimeError("synthesis failed")
        with patch.object(tts, "create_piper_speech_file") as fallback:
            with self.assertRaises(tts.TtsError):
                tts.create_speech_file("민서: 안녕하세요.")
            fallback.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_delivery_and_pauses_follow_dialogue(self):
        turns = [("민서", "왜 그럴까요?"), ("도윤", "아, 맞아요."),
                 ("민서", "여기에는 서로 다른 이유가 있습니다."), ("민서", "오늘 기억할 건 하나예요.")]
        deliveries = [tts._supertonic_delivery(text, "casual", "deep_dive") for _, text in turns]
        self.assertEqual([item["kind"] for item in deliveries], ["question", "reaction", "explanation", "closing"])
        self.assertEqual(tts._supertonic_turn_pauses(turns, deliveries), [.10, .22, .28])
        tts.create_speech_file("\n".join(f"{name}: {text}" for name, text in turns))
        self.assertEqual([call.kwargs["speed"] for call in self.engine.synthesize.call_args_list], [.99, 1.02, .98, .97])
        self.assertEqual([call.args[0] for call in self.engine.synthesize.call_args_list], [text for _, text in turns])

    def test_tone_and_format_are_preserved_and_speed_is_bounded(self):
        self.assertLess(tts._supertonic_delivery("맞아요.", "calm", "deep_dive")["speed"],
                        tts._supertonic_delivery("맞아요.", "cheerful", "deep_dive")["speed"])
        self.assertLess(tts._supertonic_delivery("사례를 살펴보겠습니다.", "casual", "deep_dive")["speed"],
                        tts._supertonic_delivery("사례를 살펴보겠습니다.", "casual", "summary")["speed"])
        self.assertEqual(tts._supertonic_delivery("그랬군요. 많이 힘들었겠어요.", "calm", "deep_dive")["kind"], "empathy")
        for tone in ("casual", "formal", "cheerful", "calm"):
            for text in ("와, 그렇군요!", "왜일까요?", "정리하면 이렇습니다."):
                speed = tts._supertonic_delivery(text, tone, "deep_dive")["speed"]
                self.assertTrue(.88 <= speed <= 1.10)

    def test_tags_are_opt_in_and_only_one_safe_tag_survives(self):
        tts.create_speech_file("민서: <laugh> 아, 저도 그랬어요.")
        self.assertEqual(self.engine.synthesize.call_args.args[0], "아, 저도 그랬어요.")
        with patch.dict(os.environ, {"SUPERTONIC_EXPRESSIONS": "1"}):
            tts.create_speech_file("민서: <laugh><laugh><scream> 아, 저도 그랬어요.")
            self.assertEqual(self.engine.synthesize.call_args.args[0], "<laugh> 아, 저도 그랬어요.")
        with self.assertRaises(tts.TtsError):
            tts.create_speech_file("민서: <laugh>")

    def test_prosody_can_be_disabled_for_comparison(self):
        with patch.dict(os.environ, {"SUPERTONIC_PROSODY": "0"}):
            url = tts.create_speech_file("민서: 왜일까요?\n도윤: 아, 맞아요.")
        self.assertEqual([call.kwargs["speed"] for call in self.engine.synthesize.call_args_list], [1.0, 1.0])
        with wave.open(str(self.root / url.rsplit("/", 1)[1]), "rb") as audio:
            self.assertEqual(audio.getnframes(), 2 * 4410 + int(44100 * .12))

    def test_join_trims_only_edges_and_keeps_internal_silence(self):
        from array import array
        part = self.root / "part.wav"
        samples = array("h", [0] * 300 + [1000] * 100 + [0] * 100 + [1000] * 100 + [0] * 300)
        with wave.open(str(part), "wb") as audio:
            audio.setparams((1, 2, 1000, 0, "NONE", "not compressed"))
            audio.writeframes(samples.tobytes())
        joined = self.root / "joined.wav"
        tts._join_wav_files([part, part], joined, pauses=[.2])
        with wave.open(str(joined), "rb") as audio:
            self.assertEqual(audio.getnframes(), 2 * (80 + 300 + 80) + 200)
        with self.assertRaises(tts.TtsError):
            tts._join_wav_files([part, part], joined, pauses=[])


if __name__ == "__main__":
    unittest.main()
