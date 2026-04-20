import faiss
import numpy as np
import pickle
import os
import logging

logger = logging.getLogger(__name__)

class VoiceVectorStore:
    def __init__(self):
        self.dimension = 13  # MFCC
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        self.index_path = "faiss_voice.index"
        self.meta_path = "voice_metadata.pkl"
        self._load()
    
    def register_voice(self, mfcc_vector: np.ndarray, user_id: str, username: str):
        """MFCC → FAISS"""
        norm_vector = mfcc_vector / np.linalg.norm(mfcc_vector)
        norm_vector = norm_vector.reshape(1, -1).astype('float32')
        self.index.add(norm_vector)
        self.metadata.append({"user_id": user_id, "username": username})
        self._save()
        logger.info(f"✅ Voice registered: {username}")
    
    def recognize_voice(self, query_mfcc: np.ndarray, threshold: float = 0.7):
        """FAISS Cosine Search"""
        query_norm = query_mfcc / np.linalg.norm(query_mfcc)
        query_norm = query_norm.reshape(1, -1).astype('float32')
        scores, indices = self.index.search(query_norm, 1)
        
        score, idx = scores[0][0], indices[0][0]
        if idx != -1 and score >= threshold:
            meta = self.metadata[idx]
            return {
                "success": True,
                "user_id": meta["user_id"],
                "username": meta["username"],
                "confidence": float(score),
                "threshold": threshold
            }
        return None
    
    def stats(self):
        return {"total_voices": self.index.ntotal, "dimension": self.dimension}
    
    def _save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, 'wb') as f:
            pickle.dump(self.metadata, f)
    
    def _load(self):
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.meta_path, 'rb') as f:
                self.metadata = pickle.load(f)

voice_store = VoiceVectorStore()