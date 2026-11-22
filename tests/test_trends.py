import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect_trends as ct  # noqa: E402

CFG = json.loads((Path(__file__).resolve().parent.parent / "data/config/trends.json").read_text(encoding="utf-8"))


class TestTrends(unittest.TestCase):
    def test_brasil(self):
        self.assertEqual((ct.HL, ct.TZ, ct.GEO), ("pt-BR", "180", "BR"))

    def test_periodo_do_estudo_e_nucleo(self):
        self.assertEqual(ct.resolver_periodo("eleitoral", CFG, "2026-11-22"), "2026-06-01 2026-08-14")
        self.assertEqual(ct.resolver_periodo("2026-07-23 2026-08-14", CFG), "2026-07-23 2026-08-14")

    def test_grupos_com_no_maximo_cinco_termos(self):
        for g in CFG["grupos"]:
            self.assertLessEqual(len(g["termos"]), 5, g["nome"])


if __name__ == "__main__":
    unittest.main()
