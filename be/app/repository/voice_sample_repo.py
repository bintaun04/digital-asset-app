# # app/repository/voice_sample_repo.py
# import logging
# from typing import List, Optional
# from sqlalchemy.orm import Session
# from datetime import datetime

# from app.core.database import get_db
# from app.models.voice_sample import VoiceSample  

# logger = logging.getLogger("VoiceSampleRepository")


# class VoiceSampleRepository:

#     @staticmethod
#     def create(
#         user_id: int,
#         file_path: str,
#         sample_type: str = "enroll",
#         duration: float = 0.0
#     ):
#         """Tạo mới một voice sample"""
#         db: Session = next(get_db())
#         try:
#             sample = VoiceSample(
#                 user_id=user_id,
#                 file_path=file_path,
#                 sample_type=sample_type,
#                 duration=duration
#             )
#             db.add(sample)
#             db.commit()
#             db.refresh(sample)
#             logger.info(f"✅ VoiceSample created for user {user_id} | type={sample_type}")
#             return sample
#         except Exception as e:
#             db.rollback()
#             logger.error(f"❌ Failed to create VoiceSample: {e}")
#             return None
#         finally:
#             db.close()

#     @staticmethod
#     def get_by_user(user_id: int, limit: int = 10) -> List[dict]:
#         db: Session = next(get_db())
#         try:
#             samples = db.query(VoiceSample)\
#                         .filter(VoiceSample.user_id == user_id)\
#                         .order_by(VoiceSample.created_at.desc())\
#                         .limit(limit)\
#                         .all()

#             return [{
#                 "id": s.id,
#                 "sample_type": s.sample_type.value if hasattr(s.sample_type, 'value') else s.sample_type,
#                 "file_path": s.file_path,
#                 "duration": s.duration,
#                 "created_at": s.created_at.isoformat() if s.created_at else None
#             } for s in samples]
#         finally:
#             db.close()

#     @staticmethod
#     def get_by_id(sample_id: int):
#         db: Session = next(get_db())
#         try:
#             return db.query(VoiceSample).filter(VoiceSample.id == sample_id).first()
#         finally:
#             db.close()