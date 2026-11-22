import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect_imprensa as ci  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RSS = """<rss><channel>""" + "".join(
    f"<item><title>Notícia {i} - Veículo {i}</title><link>https://n/{i}</link><pubDate>Fri, 31 Jul 2026 1{i % 10}:00:00 GMT</pubDate>"
    f"<source url=\"https://v{i}.com\">Veículo {i}</source></item>" for i in range(1, 15)) + "</channel></rss>"


class TestImprensa(unittest.TestCase):
    def test_top10_e_veiculo(self):
        urls = []
        r = ci.buscar("Hamas desarmamento", "2026-07-30", "2026-08-03", get=lambda u: urls.append(u) or RSS)
        self.assertEqual(len(r), 10)
        self.assertEqual((r[0]["posicao"], r[0]["titulo"], r[0]["veiculo"]), (1, "Notícia 1", "Veículo 1"))
        self.assertIn("after%3A2026-07-30", urls[0])

    def test_main_grava_e_manifesto(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "data/config").mkdir(parents=True)
        shutil.copy(RAIZ / "data/config/atores.json", tmp / "data/config/atores.json")
        self.assertEqual(ci.main(tmp, get=lambda u: RSS), 0)
        d = json.loads((tmp / "data/imprensa/resultados.json").read_text())
        self.assertEqual(len(d["consultas"]), 2 * (len(ci.TERMOS_TEMA) + 4))
        shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()


class TestRedeImprensa(unittest.TestCase):
    def test_so_tema_e_sem_repetir_entre_recortes(self):
        import importlib, sys as _s
        from pathlib import Path as _P
        _s.path.insert(0, str(_P(__file__).resolve().parents[1] / "scripts"))
        bri = importlib.import_module("build_rede_imprensa")
        res = {"consultas": [
            {"recorte": "dia do anúncio", "grupo": "tema", "consulta": "Hamas", "resultados": [{"veiculo": "G1", "titulo": "a", "link": "L1"}]},
            {"recorte": "núcleo", "grupo": "tema", "consulta": "Hamas", "resultados": [{"veiculo": "G1", "titulo": "a", "link": "L1"}, {"veiculo": "BBC", "titulo": "b", "link": "L2"}]},
            {"recorte": "núcleo", "grupo": "influenciadora", "consulta": "Fabíola Oliveira", "resultados": [{"veiculo": "X", "titulo": "c", "link": "L3"}]},
        ]}
        n = bri.noticias_do_tema(res)
        self.assertEqual(sorted(x["link"] for x in n), ["L1", "L2"])
