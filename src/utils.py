import random


def mod_pow(base, exponent, modulus):
    result = 1
    base %= modulus
    while exponent > 0:
        if exponent % 2 == 1:
            result = (result * base) % modulus
        base = (base * base) % modulus
        exponent //= 2
    return result


def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a


def mod_inverse(a, m):
    def extended_gcd(a, b):
        if b == 0:
            return a, 1, 0
        else:
            g, x, y = extended_gcd(b, a % b)
            return g, y, x - (a // b) * y

    g, x, _ = extended_gcd(a, m)
    if g != 1:
        raise ValueError("Обратного элемента не существует")
    else:
        return x % m


def is_prime(n, k=40):
    if n <= 1 or n == 4:
        return False
    if n <= 3:
        return True

    # Представим n-1 как 2^r * d
    r, d = 0, n - 1
    while d % 2 == 0:
        d //= 2
        r += 1

    for _ in range(k):
        a = random.randrange(2, n - 2)
        x = mod_pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = mod_pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generate_large_prime(bits=512):
    while True:
        candidate = random.getrandbits(bits) | (1 << bits - 1) | 1
        if is_prime(candidate):
            return candidate


class RSA:
    def __init__(self, bits=512):
        self.p = generate_large_prime(bits)
        self.q = generate_large_prime(bits)
        self.n = self.p * self.q
        self.phi = (self.p - 1) * (self.q - 1)
        self.e = 65537  # commonly used public exponent
        self.d = mod_inverse(self.e, self.phi)

    def encrypt(self, message: int) -> int:
        return mod_pow(message, self.e, self.n)

    def decrypt(self, ciphertext: int) -> int:
        return mod_pow(ciphertext, self.d, self.n)

    @property
    def public_key(self):
        return (self.e, self.n)

    @property
    def private_key(self):
        return (self.d, self.n)

    @staticmethod
    def encrypt_with_public_key(message: int, e: int, n: int) -> int:
        return mod_pow(message, e, n)

    @staticmethod
    def split_message(message: str, block_size: int = 32) -> list[bytes]:
        """Разбивает сообщение на блоки"""
        message_bytes = message.encode('utf-8')
        return [message_bytes[i:i + block_size] for i in range(0, len(message_bytes), block_size)]

    @staticmethod
    def join_message(blocks: list[bytes]) -> str:
        """Объединяет блоки в сообщение"""
        return b''.join(blocks).decode('utf-8')

    @staticmethod
    def encrypt_message(message: str, e: int, n: int) -> list[int]:
        """Шифрует сообщение, разбивая его на блоки"""
        blocks = RSA.split_message(message)
        encrypted_blocks = []
        for block in blocks:
            block_int = int.from_bytes(block, 'big')
            encrypted_blocks.append(RSA.encrypt_with_public_key(block_int, e, n))
        return encrypted_blocks

    def decrypt_message(self, encrypted_blocks: list[int]) -> str:
        """Дешифрует сообщение из блоков"""
        decrypted_blocks = []
        for block in encrypted_blocks:
            decrypted_int = self.decrypt(block)
            # Определяем минимальное количество байт для хранения числа
            byte_length = (decrypted_int.bit_length() + 7) // 8
            decrypted_blocks.append(decrypted_int.to_bytes(byte_length, 'big'))
        return RSA.join_message(decrypted_blocks)