import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect_checagens as cc  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class TestChecagens(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data/config").mkdir(parents=True)
        for f in ("projeto.json", "atores.json"):
            shutil.copy(RAIZ / "data/config" / f, self.tmp / "data/config" / f)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def resposta(self, url):
        if "Hamas" in url and "desarmamento" not in url and "acordo" not in url:
            return {"claims": [
                {"text": "Hamas aceitou desarmamento", "claimant": "João da Silva", "claimReview": [
                    {"publisher": {"name": "Lupa"}, "url": "u1", "reviewDate": "2026-08-01T00:00:00Z", "textualRating": "Falso", "title": "t"}]},
                {"text": "Vídeo de Mariam Chami sobre Gaza", "claimant": "Redes sociais", "claimReview": [
                    {"publisher": {"name": "Aos Fatos"}, "url": "u2", "reviewDate": "2026-09-10T00:00:00Z", "textualRating": "Enganoso"}]}]}
        return {}

    def test_janela_privacidade_e_manifesto(self):
        with mock.patch.dict(os.environ, {"FACTCHECK_API_KEY": "K"}, clear=False):
            rc = cc.main(raiz=self.tmp, get=self.resposta, hoje=date(2026, 11, 22))
        self.assertEqual(rc, 0)
        d = json.loads((self.tmp / "data/checagens/checagens.json").read_text())["checagens"]
        por = {x["url"]: x for x in d}
        self.assertEqual(por["u1"]["janela"], "nucleo")
        self.assertEqual(por["u1"]["quem_disse"], "pessoa ou perfil (nome omitido)")
        self.assertEqual(por["u2"]["janela"], "depois")
        self.assertEqual(por["u2"]["cita_influenciadora"], ["Mariam Chami"])
        m = json.loads((self.tmp / "data/manifest/checagens_latest.json").read_text())
        self.assertEqual((m["checagens_unicas"], m["no_nucleo"], m["citam_influenciadora"], m["max_age_days"]), (2, 1, 1, 175))

    def test_sem_chave_nao_roda(self):
        with mock.patch.dict(os.environ, {"FACTCHECK_API_KEY": "", "YOUTUBE_API_KEY": ""}, clear=False):
            self.assertEqual(cc.main(raiz=self.tmp, get=lambda u: self.fail("não devia chamar")), 1)


if __name__ == "__main__":
    unittest.main()
