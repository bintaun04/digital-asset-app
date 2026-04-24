import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import base64

logger = logging.getLogger("UserBackup")


class UserBackupJSON:
    """Backup user data sang JSON file"""
    
    def __init__(self, backup_dir: str = "data/backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_file = self.backup_dir / "users_backup.json"
    
    def save_user(self, user_data: Dict) -> bool:
        """
        Lưu/cập nhật 1 user vào JSON
        
        Args:
            user_data: {
                'id': int,
                'email': str,
                'full_name': str,
                'voice_embedding': bytes,  # Sẽ convert sang base64
                'voice_key_text': str,
                'voice_language': str,
                'created_at': datetime
            }
        """
        try:
            # Load existing data
            users = self._load_all()
            
            # Convert bytes to base64 for JSON serialization
            serializable_data = self._prepare_for_json(user_data)
            
            # Update or append
            existing_index = next(
                (i for i, u in enumerate(users) if u['id'] == serializable_data['id']),
                None
            )
            
            if existing_index is not None:
                users[existing_index] = serializable_data
                logger.info(f"📝 Updated user {serializable_data['id']} in JSON backup")
            else:
                users.append(serializable_data)
                logger.info(f"➕ Added user {serializable_data['id']} to JSON backup")
            
            # Save to file
            with open(self.backup_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False, default=str)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save user to JSON: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Lấy user từ JSON backup"""
        try:
            users = self._load_all()
            user = next((u for u in users if u['id'] == user_id), None)
            
            if user:
                # Convert base64 back to bytes
                return self._restore_from_json(user)
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get user from JSON: {e}")
            return None
    
    def get_all_users(self) -> List[Dict]:
        """Lấy tất cả users từ JSON"""
        try:
            users = self._load_all()
            return [self._restore_from_json(u) for u in users]
        except Exception as e:
            logger.error(f"❌ Failed to load all users: {e}")
            return []
    
    def delete_user(self, user_id: int) -> bool:
        """Xóa user khỏi JSON backup"""
        try:
            users = self._load_all()
            users = [u for u in users if u['id'] != user_id]
            
            with open(self.backup_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"🗑️ Deleted user {user_id} from JSON backup")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete user from JSON: {e}")
            return False
    
    def _load_all(self) -> List[Dict]:
        """Load tất cả users từ file"""
        if not self.backup_file.exists():
            return []
        
        try:
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("⚠️ Corrupted JSON file, returning empty list")
            return []
    
    def _prepare_for_json(self, data: Dict) -> Dict:
        """Convert binary data sang JSON-serializable format"""
        result = data.copy()
        
        # Convert bytes to base64
        if 'voice_embedding' in result and result['voice_embedding']:
            result['voice_embedding'] = base64.b64encode(result['voice_embedding']).decode('utf-8')
        
        # Convert datetime to ISO string
        for key in ['created_at', 'updated_at', 'voice_registered_at']:
            if key in result and isinstance(result[key], datetime):
                result[key] = result[key].isoformat()
        
        return result
    
    def _restore_from_json(self, data: Dict) -> Dict:
        """Convert base64 back to bytes"""
        result = data.copy()
        
        # Convert base64 to bytes
        if 'voice_embedding' in result and result['voice_embedding']:
            result['voice_embedding'] = base64.b64decode(result['voice_embedding'])
        
        # Convert ISO string to datetime
        for key in ['created_at', 'updated_at', 'voice_registered_at']:
            if key in result and isinstance(result[key], str):
                try:
                    result[key] = datetime.fromisoformat(result[key])
                except:
                    pass
        
        return result