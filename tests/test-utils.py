import unittest
from src.utils import *


class TestUtils(unittest.TestCase):

    def test_mod_pow(self):
        self.assertEqual(mod_pow(2, 10, 1000), 24)
        self.assertEqual(mod_pow(3, 0, 7), 1)
        self.assertEqual(mod_pow(5, 3, 13), 8)

    def test_gcd(self):
        self.assertEqual(gcd(48, 18), 6)
        self.assertEqual(gcd(101, 103), 1)
        self.assertEqual(gcd(0, 5), 5)

    def test_mod_inverse(self):
        self.assertEqual(mod_inverse(3, 11), 4)
        self.assertEqual(mod_inverse(10, 17), 12)
        with self.assertRaises(ValueError):
            mod_inverse(6, 12)

    def test_is_prime_and_generate(self):
        prime = generate_large_prime(64)
        self.assertTrue(is_prime(prime))
        self.assertGreaterEqual(prime.bit_length(), 64)

if __name__ == "__main__":
    unittest.main()
