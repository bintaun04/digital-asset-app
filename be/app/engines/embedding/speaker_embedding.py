# app/engines/embedding/speaker_embedding.py
# PHIÊN BẢN DEMO ĐƠN GIẢN - Không dùng model nặng
import numpy as np
from pathlib import Path
import json
import os

class SpeakerEmbeddingEngine:
    def __init__(self, config):
        self.config = config
        self.data_dir = Path("data/voiceprints")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.voiceprints = self.load_voiceprints()

    def load_voiceprints(self):
        db_file = self.data_dir / "voiceprints.json"
        if db_file.exists():
            with open(db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_voiceprints(self):
        db_file = self.data_dir / "voiceprints.json"
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(self.voiceprints, f, ensure_ascii=False, indent=2)

    def extract_embedding(self, audio_path: str):
        """Demo: trả về vector ngẫu nhiên hoặc dựa trên độ dài file"""
        # Thực tế nên dùng MFCC, nhưng để đơn giản ta dùng độ dài + random
        size = os.path.getsize(audio_path) // 1000   # KB
        embedding = np.array([size % 100, len(audio_path) % 50, 0.5], dtype=np.float32)
        return embedding / np.linalg.norm(embedding) if np.linalg.norm(embedding) > 0 else np.ones(3)

    def enroll_user(self, user_id: str, audio_paths: list):
        embeddings = [self.extract_embedding(p) for p in audio_paths]
        mean_embedding = np.mean(embeddings, axis=0)
        mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)

        self.voiceprints[user_id] = {
            "embedding": mean_embedding.tolist(),
            "num_samples": len(audio_paths),
            "samples": [Path(p).name for p in audio_paths]
        }
        self.save_voiceprints()
        return mean_embedding

    def verify_user(self, user_id: str, audio_path: str, threshold: float = 0.6):
        if user_id not in self.voiceprints:
            return False, 0.0

        query_emb = self.extract_embedding(audio_path)
        stored_emb = np.array(self.voiceprints[user_id]["embedding"])

        # Cosine similarity đơn giản
        score = float(np.dot(query_emb, stored_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(stored_emb) + 1e-8))

        is_verified = score > threshold
        return is_verified, round(score, 4)