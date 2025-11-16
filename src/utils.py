import hashlib
import hmac
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64


def generate_random_bytes(length=32):
    return os.urandom(length)


def hmac_sha256(key: bytes, message: bytes) -> bytes:
    return hmac.new(key, message, hashlib.sha256).digest()


def verify_hmac(key: bytes, message: bytes, expected_hmac: bytes) -> bool:
    computed_hmac = hmac_sha256(key, message)
    return hmac.compare_digest(computed_hmac, expected_hmac)


class SKID3:
    
    def __init__(self, shared_key: bytes):
        self.shared_key = shared_key
        self.session_key = None
        self.ra = None  # Случайное число Alice
        self.rb = None  # Случайное число Bob
        
    def initiate_as_alice(self) -> bytes:
        self.ra = generate_random_bytes(32)
        return self.ra
    
    def respond_as_bob(self, ra: bytes) -> tuple[bytes, bytes]:
        self.ra = ra
        self.rb = generate_random_bytes(32)
        
        message = self.ra + self.rb
        hmac_value = hmac_sha256(self.shared_key, message)
        
        return self.rb, hmac_value
    
    def verify_and_respond_as_alice(self, rb: bytes, received_hmac: bytes) -> bytes:
        self.rb = rb
        
        message = self.ra + self.rb
        if not verify_hmac(self.shared_key, message, received_hmac):
            raise ValueError("Ошибка аутентификации Bob! HMAC не совпадает.")
        
        # Вычисляем HMAC(K_AB, R_B || R_A)
        message = self.rb + self.ra
        hmac_value = hmac_sha256(self.shared_key, message)
        
        # Генерируем сессионный ключ
        self._generate_session_key()
        
        return hmac_value
    
    def verify_as_bob(self, received_hmac: bytes) -> bool:
        message = self.rb + self.ra
        if not verify_hmac(self.shared_key, message, received_hmac):
            raise ValueError("Ошибка аутентификации Alice! HMAC не совпадает.")
        
        self._generate_session_key()
        
        return True
    
    def _generate_session_key(self):
        message = self.ra + self.rb + b"session"
        self.session_key = hmac_sha256(self.shared_key, message)
        
    def get_session_key(self) -> bytes:
        if self.session_key is None:
            raise ValueError("Сессионный ключ еще не установлен!")
        return self.session_key


class AESCipher:
    
    def __init__(self, key: bytes):
        self.key = key[:32]
    
    def encrypt(self, plaintext: str) -> str:
        iv = generate_random_bytes(16)
        
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        
        plaintext_bytes = plaintext.encode('utf-8')
        ciphertext = cipher.encrypt(pad(plaintext_bytes, AES.block_size))
        
        return base64.b64encode(iv + ciphertext).decode('utf-8')
    
    def decrypt(self, ciphertext_b64: str) -> str:
        data = base64.b64decode(ciphertext_b64)
        
        iv = data[:16]
        ciphertext = data[16:]
        
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        
        plaintext_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)
        
        return plaintext_bytes.decode('utf-8')


def derive_key_from_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = os.urandom(16)
    
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000, dklen=32)
    return key, salt