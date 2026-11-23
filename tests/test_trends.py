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


class TestRelacionados(unittest.TestCase):
    def test_relacionados_do_tema_ligados(self):
        import json
        from pathlib import Path
        cfg = json.loads((Path(__file__).resolve().parents[1] / "data/config/trends.json").read_text(encoding="utf-8"))
        rel = cfg.get("relacionados", {})
        self.assertIn("tema_topicos", rel.get("grupos", []))
        self.assertIn("tema_palavras", rel.get("grupos", []))
        self.assertIn("2026-07-23 2026-08-14", rel.get("periodos", []))

    def test_write_related_principais_e_em_alta(self):
        import csv, tempfile
        from pathlib import Path
        data = {"default": {"rankedList": [
            {"rankedKeyword": [{"query": "hamas israel", "value": 100, "formattedValue": "100"}]},
            {"rankedKeyword": [{"query": "acordo hamas", "value": 5000, "formattedValue": "Aumento repentino"},
                               {"topic": {"title": "Desarmamento", "type": "Assunto"}, "value": 350, "formattedValue": "+350%"}]}]}}
        with tempfile.TemporaryDirectory() as d:
            n = ct.write_related([("Hamas", "consultas", data)], Path(d) / "r.csv")
            rows = list(csv.DictReader(open(Path(d) / "r.csv", encoding="utf-8"), delimiter=";"))
        self.assertEqual(n, 3)
        self.assertEqual([r["lista"] for r in rows], ["principais", "em_alta", "em_alta"])
        self.assertEqual(rows[2]["texto"], "Desarmamento")
