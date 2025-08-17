from deepgram import Deepgram
import json, os
from typing import List, Dict

from app.settings import APP_SETTINGS


class SttAgent:
    def __init__(self, audio_file_path: str):
        self.audio_file_path = audio_file_path
        self.json_cache_path = f"{self.audio_file_path.rsplit('.', 1)[0]}.json"
        self.dg = Deepgram(APP_SETTINGS.DEEPGRAM_API_KEY)

    def parse_audio(self, force=False) -> Dict:
        """
        Parse audio to JSON and cache result.
        If force=False, it will use cached JSON if available.
        """
        # Nếu đã có cache và không ép chạy lại
        if os.path.exists(self.json_cache_path) and not force:
            print(f"Using cached transcription: {self.json_cache_path}")
            return self.json_cache_path

        params = {
            "punctuate": True,
            "model": "nova-2",
            "language": "vi",
            "smart_format": True,
            "paragraphs": True,
            "utterances": True,
            "utt_split": 0.8,
        }

        if os.path.isfile(self.audio_file_path):
            with open(self.audio_file_path, "rb") as f:
                source = {"buffer": f, "mimetype": "audio/" + APP_SETTINGS.MIMETYPE}
                res = self.dg.transcription.sync_prerecorded(source, params)
                # Lưu kết quả JSON
                with open(self.json_cache_path, "w", encoding="utf-8") as transcript:
                    json.dump(res, transcript, ensure_ascii=False, indent=2)
                print(f"Transcription saved to: {self.json_cache_path}")
        else:
            raise FileNotFoundError(f"{self.audio_file_path} is not a valid file.")

        return self.json_cache_path

    def parse_text(self) -> List[str]:
        """
        Read cached JSON and return cleaned sentences.
        """
        if not os.path.exists(self.json_cache_path):
            raise FileNotFoundError(
                f"Cached transcription not found: {self.json_cache_path}"
            )

        with open(self.json_cache_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        transcript_text = data["results"]["channels"][0]["alternatives"][0][
            "transcript"
        ]
        # Tách câu, làm sạch
        sentences = [
            sentence.strip() + "."
            for sentence in transcript_text.split(".")
            if sentence.strip()
        ]
        return sentences
