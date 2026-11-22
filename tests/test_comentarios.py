import csv
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect_comentarios as cc  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class TestComentarios(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data/config").mkdir(parents=True)
        for f in ("coleta.json", "temas.json"):
            shutil.copy(RAIZ / "data/config" / f, self.tmp / "data/config" / f)
        (self.tmp / "data/tiktok").mkdir(parents=True)
        with (self.tmp / "data/tiktok/posts.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["post_id", "ator_id", "url", "janela", "comentarios"])
            w.writeheader()
            w.writerow({"post_id": "111", "ator_id": "mariam-chami", "url": "https://www.tiktok.com/@m/video/111", "janela": "nucleo", "comentarios": 2})
            w.writerow({"post_id": "222", "ator_id": "mariam-chami", "url": "https://www.tiktok.com/@m/video/222", "janela": "base", "comentarios": 9})
        self.priv = self.tmp / "priv"
        self.priv.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_so_nucleo_privado_e_contagens(self):
        pedidos = []

        def executar(ator, p, c):
            pedidos.append((ator, p, c))
            return {"id": "r", "usageTotalUsd": 0.01}, [
                {"cid": "c1", "text": "e o Hamas? fala de Gaza", "uniqueId": "fulano", "videoWebUrl": "https://www.tiktok.com/@m/video/111", "createTimeISO": "2026-08-01T00:00:00.000Z"},
                {"cid": "c2", "text": "linda!", "uniqueId": "ciclana", "videoWebUrl": "https://www.tiktok.com/@m/video/111"}]
        with mock.patch.dict(os.environ, {"INFL_INTERNO_DIR": str(self.priv)}):
            rc = cc.main(["--rede", "tiktok"], raiz=self.tmp, executar=executar)
        self.assertEqual(rc, 0)
        self.assertEqual(pedidos[0][1]["postURLs"], ["https://www.tiktok.com/@m/video/111"])
        self.assertEqual(pedidos[0][2], 1.2)
        r = json.loads((self.tmp / "data/comentarios/tiktok_resumo.json").read_text())
        self.assertNotIn("fulano", json.dumps(r))
        self.assertEqual(r["por_publicacao"][0]["cobertura"], "completa")
        self.assertEqual(r["por_influenciadora"]["mariam-chami"]["temas"], {"acordo_hamas": 1, "gaza_palestina": 1})
        with (self.priv / "data/comentarios/tiktok.csv").open(encoding="utf-8") as f:
            self.assertEqual({x["autor"] for x in csv.DictReader(f)}, {"fulano", "ciclana"})

    def test_sem_privado_nao_le(self):
        with mock.patch.dict(os.environ, {"INFL_INTERNO_DIR": ""}):
            self.assertEqual(cc.main(["--rede", "tiktok"], raiz=self.tmp, executar=lambda *a: self.fail("não devia rodar")), 1)


if __name__ == "__main__":
    unittest.main()
