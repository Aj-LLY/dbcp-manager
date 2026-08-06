"""
AES-256 加密工具 — 保护敏感 JSON 数据文件。
使用 PyCryptodome, 密钥从机器指纹派生, 仅本机可解密。
"""
import os
import hashlib
import base64

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def _get_key() -> bytes:
    """从机器指纹派生 256-bit AES 密钥。"""
    import platform
    import uuid
    fingerprint = f"{platform.node()}-{uuid.getnode()}-dap-secure-key"
    return hashlib.sha256(fingerprint.encode()).digest()


def encrypt_data(plaintext: str) -> str:
    """AES-256-CBC 加密 JSON 字符串，返回 Base64。"""
    if not HAS_CRYPTO:
        return plaintext  # pycryptodome 未安装时退回明文
    key = _get_key()
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(plaintext.encode('utf-8'), AES.block_size))
    return base64.b64encode(iv + ct).decode('ascii')


def decrypt_data(ciphertext: str) -> str:
    """解密 Base64 编码的密文，返回 JSON 字符串。"""
    if not HAS_CRYPTO:
        return ciphertext
    try:
        raw = base64.b64decode(ciphertext)
        iv, ct = raw[:16], raw[16:]
        cipher = AES.new(_get_key(), AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(ct), AES.block_size).decode('utf-8')
    except Exception:
        return ciphertext  # 解密失败退回原文


def is_crypto_available() -> bool:
    return HAS_CRYPTO
