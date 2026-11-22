import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_engajamento as be  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class TestEngajamento(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data/config").mkdir(parents=True)
        shutil.copy(RAIZ / "data/config/atores.json", self.tmp / "data/config/atores.json")
        (self.tmp / "data/tiktok").mkdir(parents=True)
        campos = ["post_id", "ator_id", "janela", "publicado_em", "url", "curtidas", "comentarios", "compartilhamentos", "visualizacoes", "texto"]
        linhas = [{"post_id": f"b{i}", "ator_id": "hyatt-omar", "janela": "base", "publicado_em": "2026-06-10", "url": "u",
                   "curtidas": c, "comentarios": 0, "compartilhamentos": 0, "visualizacoes": 10, "texto": ""} for i, c in enumerate([10, 20, 30])]
        linhas.append({"post_id": "n1", "ator_id": "hyatt-omar", "janela": "nucleo", "publicado_em": "2026-08-01", "url": "u",
                       "curtidas": 30, "comentarios": 5, "compartilhamentos": 5, "visualizacoes": 10, "texto": ""})
        linhas.append({"post_id": "n2", "ator_id": "carima-orra", "janela": "nucleo", "publicado_em": "2026-08-01", "url": "u",
                       "curtidas": 30, "comentarios": "", "compartilhamentos": "", "visualizacoes": 10, "texto": ""})
        with (self.tmp / "data/tiktok/posts.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos)
            w.writeheader()
            w.writerows(linhas)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_indice_contra_a_propria_base(self):
        be.main(self.tmp)
        d = json.loads((self.tmp / "data/engajamento.json").read_text())
        g = {(x["ator_id"], x["rede"]): x for x in d["grupos"]}
        self.assertEqual(g[("hyatt-omar", "tiktok")]["base_mediana_interacoes"], 20)
        p = {x["post_id"]: x for x in d["publicacoes"]}
        self.assertEqual(p["n1"]["indice"], 2.0)
        self.assertIsNone(p["n2"]["indice"])  # sem base: ⛔, nunca estimado
        self.assertTrue(g[("carima-orra", "tiktok")]["status"].startswith("⛔"))


if __name__ == "__main__":
    unittest.main()
