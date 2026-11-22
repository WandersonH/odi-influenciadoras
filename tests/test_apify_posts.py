import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect_apify_posts as cap  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "data/config").mkdir(parents=True)
        for f in ("coleta.json", "atores.json", "projeto.json"):
            shutil.copy(RAIZ / "data/config" / f, self.tmp / "data/config" / f)
        self.orig = cap.RAIZ
        cap.RAIZ = self.tmp

    def tearDown(self):
        cap.RAIZ = self.orig
        shutil.rmtree(self.tmp)


class TestTeto(Base):
    def test_nao_roda_sem_autorizacao(self):
        p = self.tmp / "data/config/coleta.json"
        d = json.loads(p.read_text())
        d["apify"]["autorizacao"] = ""
        p.write_text(json.dumps(d))
        chamado = []
        rc = cap.main(["--rede", "instagram", "--etapa", "teste"], executar=lambda *a: chamado.append(a), raiz=self.tmp)
        self.assertEqual(rc, 1)
        self.assertEqual(chamado, [])

    def test_cap_respeita_metade_do_teste_por_rede_e_gasto_anterior(self):
        (self.tmp / "data/manifest").mkdir(parents=True)
        (self.tmp / "data/manifest/apify_tiktok_teste_x.json").write_text(json.dumps({"etapa": "teste", "custo_usd": 0.7}))
        caps = []

        def executar(ator, p, c):
            caps.append(c)
            return {"id": "r", "status": "SUCCEEDED", "usageTotalUsd": 0.01}, [
                {"shortCode": "abc", "timestamp": "2026-08-01T10:00:00.000Z", "ownerUsername": p["directUrls"][0].rstrip("/").split("/")[-1], "likesCount": 5}]
        rc = cap.main(["--rede", "instagram", "--etapa", "teste"], executar=executar, raiz=self.tmp)
        self.assertEqual(rc, 0)
        # teto 1,00 - gasto 0,70 = 0,30 restante (< metade 0,50) dividido por 4 perfis
        self.assertEqual(caps, [0.075] * 4)
        m = json.loads((self.tmp / "data/manifest/instagram_latest.json").read_text())
        self.assertEqual(m["custo_usd"], 0.04)
        self.assertEqual(m["perfis"][0]["no_nucleo"], 1)
        self.assertEqual(m["perfis"][0]["universo_fonte"], "⛔ não informado pelo ator")


class TestLinha(unittest.TestCase):
    J = {"base": {"inicio": "2026-06-01T00:00:00Z", "fim": "2026-07-22T23:59:59Z"},
         "nucleo": {"inicio": "2026-07-23T00:00:00Z", "fim": "2026-08-14T23:59:59Z"}}

    def test_tiktok_janela_e_numeros(self):
        x = {"id": "1", "createTime": 1785542400, "text": "oi", "playCount": 100, "diggCount": 7, "commentCount": 2,
             "shareCount": 1, "webVideoUrl": "u", "authorMeta": {"name": "a", "video": 300}}
        l = cap.linha("tiktok", x, "a", "@a", self.J, "agora")
        self.assertEqual(l["janela"], "nucleo")
        self.assertEqual((l["visualizacoes"], l["curtidas"], l["comentarios"]), (100, 7, 2))
        self.assertEqual(cap.universo("tiktok", [x]), (300, "authorMeta.video (TikTok)"))

    def test_instagram_curtida_oculta_vira_vazio(self):
        x = {"shortCode": "s", "timestamp": "2026-06-10T00:00:00.000Z", "likesCount": -1}
        self.assertEqual(cap.linha("instagram", x, "a", "@a", self.J, "agora")["curtidas"], "")

    def test_post_de_outro_perfil_fica_fora(self):
        self.assertFalse(cap.e_do_perfil("instagram", {"ownerUsername": "outra"}, "@hyattomar"))
        self.assertTrue(cap.e_do_perfil("instagram", {"ownerUsername": "HyattOmar"}, "@hyattomar"))


if __name__ == "__main__":
    unittest.main()
