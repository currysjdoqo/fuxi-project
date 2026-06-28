"""
API Key 加密工具模块
使用 Fernet 对称加密算法保护 API Key
"""

import base64
import os
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

# 密钥存储路径（用户主目录，不在项目目录中）
KEY_STORE_PATH = Path.home() / ".fuxi_security" / "encryption.key"


def _generate_fernet_key() -> bytes:
    """生成 Fernet 密钥"""
    return Fernet.generate_key()


def _get_or_create_key() -> bytes:
    """获取或创建加密密钥"""
    if KEY_STORE_PATH.exists():
        return KEY_STORE_PATH.read_bytes()
    
    # 创建目录
    KEY_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # 生成新密钥并保存
    key = _generate_fernet_key()
    KEY_STORE_PATH.write_bytes(key)
    
    # 设置文件权限（仅当前用户可读）
    try:
        import stat
        KEY_STORE_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except:
        pass
    
    return key


def encrypt_api_key(api_key: str) -> str:
    """加密 API Key"""
    if not HAS_CRYPTOGRAPHY:
        return api_key
    
    try:
        fernet = Fernet(_get_or_create_key())
        encrypted = fernet.encrypt(api_key.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    except Exception:
        return api_key


def decrypt_api_key(encrypted_key: str) -> str:
    """解密 API Key"""
    if not HAS_CRYPTOGRAPHY:
        return encrypted_key
    
    try:
        fernet = Fernet(_get_or_create_key())
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key)
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    except Exception:
        return encrypted_key


def is_encrypted(api_key: str) -> bool:
    """检查 API Key 是否已加密"""
    if not HAS_CRYPTOGRAPHY:
        return False
    
    try:
        # 尝试解码，如果成功且长度合理则可能是加密的
        decoded = base64.urlsafe_b64decode(api_key)
        return len(decoded) > 0
    except:
        return False
