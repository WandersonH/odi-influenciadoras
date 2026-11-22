import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect_terceiros_x as tx3  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class TestTerceirosX(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data/config").mkdir(parents=True)
        for f in ("coleta.json", "atores.json", "projeto.json"):
            shutil.copy(RAIZ / "data/config" / f, self.tmp / "data/config" / f)
        self.priv = self.tmp / "privado"
        self.priv.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_consulta(self):
        self.assertEqual(tx3.consulta("Mariam Chami", "eumariamchami", "2026-07-23T00:00:00Z", "2026-08-14T23:59:59Z"),
                         '("Mariam Chami" OR @eumariamchami) -from:eumariamchami -filter:retweets')

    def test_publico_so_contagens_privado_texto(self):
        import os
        from unittest import mock
        itens = [
            {"id": "1", "author": {"userName": "fulano", "followers": 10}, "fullText": "vi o vídeo da @eumariamchami", "createdAt": "Fri Jul 31 10:00:00 +0000 2026"},
            {"id": "2", "author": {"userName": "eumariamchami"}, "fullText": "Mariam Chami aqui", "createdAt": "2026-07-31T10:00:00Z"},
            {"id": "3", "author": {"userName": "outra"}, "fullText": "Carima Orra falou bem", "createdAt": "2026-08-02T10:00:00Z"},
            {"id": "4", "author": {"userName": "x"}, "fullText": "Mariam Chami em junho", "createdAt": "2026-06-10T10:00:00Z"},
        ]
        with mock.patch.dict(os.environ, {"INFL_INTERNO_DIR": str(self.priv)}):
            rc = tx3.main([], raiz=self.tmp, executar=lambda a, p, c: ({"id": "r", "usageTotalUsd": 0.002}, itens))
        self.assertEqual(rc, 0)
        m = json.loads((self.tmp / "data/manifest/terceiros_x_latest.json").read_text())
        por = {r["ator"]: r for r in m["influenciadoras"]}
        self.assertEqual(por["mariam-chami"]["lidos"], 1)
        self.assertEqual(por["mariam-chami"]["por_tipo"], {"arroba": 1})
        self.assertEqual(por["carima-orra"]["lidos"], 1)
        self.assertNotIn("fulano", json.dumps(m))
        with (self.priv / "data/terceiros/x_mencoes.csv").open(encoding="utf-8") as f:
            self.assertEqual({r["autor"] for r in csv.DictReader(f)}, {"fulano", "outra"})

    def test_sem_privado_nao_roda(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"INFL_INTERNO_DIR": ""}):
            self.assertEqual(tx3.main([], raiz=self.tmp, executar=lambda *a: self.fail("não devia rodar")), 1)


if __name__ == "__main__":
    unittest.main()
