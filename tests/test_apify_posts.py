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

    def test_uma_execucao_por_rede_com_metade_do_teste(self):
        caps, pedidos = [], []

        def executar(ator, p, c):
            caps.append(c); pedidos.append(p)
            return {"id": "r", "status": "SUCCEEDED", "usageTotalUsd": 0.01}, [
                {"shortCode": "abc", "timestamp": "2026-08-01T10:00:00.000Z", "ownerUsername": "hyattomar", "likesCount": 5},
                {"shortCode": "zzz", "timestamp": "2026-08-01T10:00:00.000Z", "ownerUsername": "outra"}]
        rc = cap.main(["--rede", "instagram", "--etapa", "teste"], executar=executar, raiz=self.tmp)
        self.assertEqual(rc, 0)
        self.assertEqual(caps, [0.5])
        self.assertEqual(len(pedidos[0]["directUrls"]), 4)
        m = json.loads((self.tmp / "data/manifest/instagram_latest.json").read_text())
        self.assertEqual(m["custo_usd"], 0.01)
        hy = [p for p in m["perfis"] if p["ator"] == "hyatt-omar"][0]
        self.assertEqual((hy["lidos"], hy["no_nucleo"]), (1, 1))
        self.assertEqual(hy["universo_fonte"], "⛔ não informado pelo ator")
        self.assertIn("1 item(ns) de outro perfil", m["erros"][0])

    def test_nao_roda_abaixo_do_minimo_da_apify(self):
        (self.tmp / "data/manifest").mkdir(parents=True)
        (self.tmp / "data/manifest/apify_tiktok_teste_x.json").write_text(json.dumps({"etapa": "teste", "custo_usd": 0.7}))
        chamado = []
        rc = cap.main(["--rede", "instagram", "--etapa", "teste"], executar=lambda *a: chamado.append(a), raiz=self.tmp)
        self.assertEqual((rc, chamado), (1, []))

    def test_posts_pede_o_recorte_e_marca_teto(self):
        pedidos = []

        def executar(ator, p, c):
            pedidos.append(p)
            return {"id": "r", "status": "SUCCEEDED", "usageTotalUsd": c}, []
        cap.main(["--rede", "tiktok", "--etapa", "posts"], executar=executar, raiz=self.tmp)
        self.assertEqual((pedidos[0]["oldestPostDateUnified"], pedidos[0]["newestPostDate"]), ("2026-06-01", "2026-08-14"))
        m = json.loads((self.tmp / "data/manifest/tiktok_latest.json").read_text())
        self.assertTrue(m["perfis"][0]["cobertura"].startswith("parcial ⛔ (execução parou no teto"))


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

    def test_datas_com_fracao_e_fuso(self):
        self.assertEqual(cap.quando("2026-06-26T00:17:34.000Z"), "2026-06-26T00:17:34Z")
        self.assertEqual(cap.quando("2026-06-26T00:17:34-03:00"), "2026-06-26T03:17:34Z")
        self.assertEqual(cap.quando(1785542400), "2026-08-01T00:00:00Z")
        self.assertEqual(cap.quando("Fri Jul 31 10:00:00 +0000 2026"), "2026-07-31T10:00:00Z")

    def test_x_pedido_e_linha(self):
        p = cap.pedido("x", ["eumariamchami"], "posts", 2000, "2026-06-01T00:00:00Z", "xquik~x-tweet-scraper", "2026-08-14T23:59:59Z")
        self.assertEqual(p["searchTerms"], ["from:eumariamchami -filter:retweets"])
        self.assertEqual((p["since"], p["until"], p["maxItemsPerTarget"]), ("2026-06-01", "2026-08-15", 2000))
        x = {"id": "9", "createdAt": "Fri Jul 31 10:00:00 +0000 2026", "fullText": "oi", "viewCount": 100, "likeCount": 3,
             "replyCount": 1, "retweetCount": 2, "quoteCount": 1, "url": "u", "author": {"userName": "EuMariamChami", "statusesCount": 500}}
        l = cap.linha("x", x, "m", "eumariamchami", self.J, "agora")
        self.assertEqual((l["janela"], l["visualizacoes"], l["compartilhamentos"]), ("nucleo", 100, 3))
        self.assertTrue(cap.e_do_perfil("x", x, "eumariamchami"))
        self.assertEqual(cap.universo("x", [x])[0], 500)

    def test_apidojo_campos_e_dono(self):
        x = {"id": "9", "uploadedAt": 1785542400, "title": "t", "views": 50, "likes": 4, "comments": 1, "shares": 0,
             "postPage": "p", "channel": {"username": "HyattOmar", "videos": 226}}
        l = cap.linha("tiktok", x, "h", "@hyattomar", self.J, "agora")
        self.assertEqual((l["post_id"], l["publicado_em"], l["visualizacoes"]), ("9", "2026-08-01T00:00:00Z", 50))
        self.assertTrue(cap.e_do_perfil("tiktok", x, "@hyattomar"))
        self.assertEqual(cap.universo("tiktok", [x])[0], 226)
        self.assertEqual(cap.pedido("tiktok", ["@a", "@b"], "teste", 15, "2026-06-01", "apidojo~tiktok-profile-scraper"),
                         {"usernames": ["a", "b"], "maxItems": 30})

    def test_instagram_curtida_oculta_vira_vazio(self):
        x = {"shortCode": "s", "timestamp": "2026-06-10T00:00:00.000Z", "likesCount": -1}
        self.assertEqual(cap.linha("instagram", x, "a", "@a", self.J, "agora")["curtidas"], "")

    def test_post_de_outro_perfil_fica_fora(self):
        self.assertFalse(cap.e_do_perfil("instagram", {"ownerUsername": "outra"}, "@hyattomar"))
        self.assertTrue(cap.e_do_perfil("instagram", {"ownerUsername": "HyattOmar"}, "@hyattomar"))


if __name__ == "__main__":
    unittest.main()
