# app/services/challenge_service.py
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

from ..repository.challenge_repo import ChallengeRepository

logger = logging.getLogger("ChallengeService")


class ChallengeService:
    CHALLENGES = [
        "Xin chào, tôi là chủ tài khoản này.",
        "Hôm nay tôi muốn truy cập vào tài sản số của mình.",
        "Đây là giọng nói thật của tôi.",
        "Xác thực an toàn để mở khóa ví.",
        "Tôi xác nhận danh tính bằng giọng nói.",
        "Mở khóa tài sản digital asset ngay bây giờ.",
        "Giọng nói này thuộc về tôi."
    ]

    @staticmethod
    def generate_challenge(user_id: int, language: str = "vi") -> Dict:
        challenge_id = f"ch_{random.randint(100000, 999999)}"
        text = random.choice(ChallengeService.CHALLENGES)
        expires_at = datetime.utcnow() + timedelta(seconds=90)

        ChallengeRepository.save_challenge(
            challenge_id=challenge_id,
            user_id=user_id,
            text=text,
            expires_at=expires_at
        )

        logger.info(f"✅ Generated challenge {challenge_id} for user {user_id}")
        return {
            "challenge_id": challenge_id,
            "challenge_text": text,
            "expires_in": 90
        }

    @staticmethod
    def get_challenge(challenge_id: str, user_id: int) -> Optional[Dict]:
        return ChallengeRepository.get_challenge(challenge_id, user_id)

    @staticmethod
    def delete_challenge(challenge_id: str):
        ChallengeRepository.delete_challenge(challenge_id)