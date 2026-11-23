import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class TestEmojis(unittest.TestCase):
    def setUp(self):
        try:
            import build_emojis
        except ModuleNotFoundError as e:  # workflows sem a biblioteca emoji
            self.skipTest(f"dependência ausente: {e.name}")
        self.be = build_emojis

    def test_posicao_e_repeticao(self):
        es = self.be.analisa("Parabéns 👏👏 que lindo ❤️")
        self.assertEqual([(k, p, c) for k, _, p, c in es], [("👏", "meio", False), ("👏", "meio", True), ("❤", "fim", False)])

    def test_so_emoji_e_bandeira(self):
        es = self.be.analisa("🇵🇸🇵🇸")
        self.assertEqual({p for _, _, p, _ in es}, {"só emoji"})
        self.assertEqual(es[0][0], "🇵🇸")

    def test_tom_de_pele_unido(self):
        self.assertEqual(self.be.norm("👏🏽"), "👏")


if __name__ == "__main__":
    unittest.main()
