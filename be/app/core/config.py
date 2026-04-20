from pydantic_settings import BaseSettings

class VoiceConfig(BaseSettings):
    whisper_model: str = "qbsmlabs/PhoWhisper-small"  
    embedding_model: str = "speechbrain/spkrec-ecapa-voxceleb"
    sample_rate: int = 16000
    enroll_min_samples: int = 3
    enroll_max_samples: int = 5
    verify_threshold: float = 0.75         
    faiss_index_path: str = "data/voice_index.faiss"
    embeddings_path: str = "data/voice_embeddings.npy"

    class Config:
        env_file = ".env"
        extra = "ignore"

voice_config = VoiceConfig()