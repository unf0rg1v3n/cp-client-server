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