import csv
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import collect_youtube as cy  # noqa: E402


class FilaApi(cy.Api):
    """API falsa: devolve respostas enfileiradas por rota, sem rede."""

    def __init__(self, respostas):
        super().__init__("CHAVE-TESTE", cy.CUSTO)
        self.respostas = {k: list(v) for k, v in respostas.items()}
        self.pedidos = []

    def get(self, rota, **params):
        self.pedidos.append((rota, params))
        self.unidades += self.custo[rota]
        self.chamadas[rota] = self.chamadas.get(rota, 0) + 1
        return self.respostas[rota].pop(0)


class TestNormalizar(unittest.TestCase):
    def test_remove_acentos_e_mantem_arabe(self):
        self.assertEqual(cy.normalizar("Desarmamento Árabe حماس"), "desarmamento arabe حماس")


class TestListarUploads(unittest.TestCase):
    def test_para_pela_data_inicial_sem_nova_pagina(self):
        pagina = {
            "items": [
                {"contentDetails": {"videoId": "a", "videoPublishedAt": "2026-08-02T10:00:00Z"}, "snippet": {"publishedAt": "2026-08-02T10:00:00Z", "title": "a"}},
                {"contentDetails": {"videoId": "b", "videoPublishedAt": "2026-07-30T10:00:00Z"}, "snippet": {"publishedAt": "2026-07-30T10:00:00Z", "title": "b"}},
                {"contentDetails": {"videoId": "c", "videoPublishedAt": "2026-05-20T10:00:00Z"}, "snippet": {"publishedAt": "2026-05-20T10:00:00Z", "title": "c"}},
            ],
            "nextPageToken": "PROXIMA",
        }
        api = FilaApi({"playlistItems.list": [pagina]})
        itens, cobertura, paginas = cy.listar_uploads(
            api, "UCabcdefghijklmnopqrstuv", "2026-06-01T00:00:00Z", "2026-08-14T23:59:59Z", 40)
        self.assertEqual([i["video_id"] for i in itens], ["a", "b"])
        self.assertTrue(cobertura.startswith("completa (parou pela data inicial"))
        self.assertEqual(paginas, 1)
        self.assertEqual(len(api.pedidos), 1)

    def test_limite_de_paginas_nao_vira_completa(self):
        pagina = {"items": [{"contentDetails": {"videoId": "a", "videoPublishedAt": "2026-08-02T10:00:00Z"}, "snippet": {"publishedAt": "2026-08-02T10:00:00Z", "title": "a"}}], "nextPageToken": "X"}
        api = FilaApi({"playlistItems.list": [pagina]})
        _, cobertura, _ = cy.listar_uploads(api, "UCabcdefghijklmnopqrstuv", "2026-06-01T00:00:00Z", "2026-08-14T23:59:59Z", 1)
        self.assertTrue(cobertura.startswith("incompleta"))


class TestTerceiros(unittest.TestCase):
    def test_exclui_canal_proprio_e_guarda_estimativa(self):
        d = {
            "pageInfo": {"totalResults": 812},
            "items": [
                {"id": {"videoId": "v1"}, "snippet": {"channelId": "PROPRIO", "channelTitle": "Ela", "publishedAt": "2026-08-01T00:00:00Z", "title": "x"}},
                {"id": {"videoId": "v2"}, "snippet": {"channelId": "OUTRO", "channelTitle": "Podcast", "publishedAt": "2026-08-03T00:00:00Z", "title": "y"}},
            ],
        }
        api = FilaApi({"search.list": [d]})
        itens, est, paginas = cy.buscar_terceiros(api, '"Mariam Chami"', "2026-07-23T00:00:00Z", "2026-08-14T23:59:59Z", {"PROPRIO"}, 2)
        self.assertEqual([i["video_id"] for i in itens], ["v2"])
        self.assertEqual(est, 812)
        self.assertEqual(paginas, 1)


class TestGravarMerge(unittest.TestCase):
    def test_atualiza_chave_repetida_sem_apagar(self):
        campos = ["video_id", "publicado_em", "visualizacoes"]
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "videos.csv"
            cy.gravar_merge(caminho, [{"video_id": "a", "publicado_em": "2026-07-01", "visualizacoes": 10}], campos, "video_id")
            novos, total = cy.gravar_merge(caminho, [
                {"video_id": "a", "publicado_em": "2026-07-01", "visualizacoes": 25},
                {"video_id": "b", "publicado_em": "2026-08-01", "visualizacoes": 3},
            ], campos, "video_id")
            with caminho.open(encoding="utf-8") as f:
                linhas = {r["video_id"]: r["visualizacoes"] for r in csv.DictReader(f)}
        self.assertEqual((novos, total), (1, 2))
        self.assertEqual(linhas, {"a": "25", "b": "3"})


class TestChaveNaoVazaEmErro(unittest.TestCase):
    def test_erro_http_nao_mostra_a_chave(self):
        erro = urllib.error.HTTPError("https://x", 403, "Forbidden", {}, io.BytesIO(b"chave CHAVE-TESTE recusada"))
        api = cy.Api("CHAVE-TESTE")
        with mock.patch.object(cy.urllib.request, "urlopen", side_effect=erro):
            with self.assertRaises(cy.ErroAPI) as ctx:
                api.get("channels.list", part="id", forHandle="x")
        self.assertNotIn("CHAVE-TESTE", str(ctx.exception))
        self.assertIn("HTTP 403", str(ctx.exception))


class TestEndereco(unittest.TestCase):
    def test_rota_vira_recurso_no_endereco(self):
        pedidos = []

        class Resp(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def falso(url, timeout=0):
            pedidos.append(url)
            return Resp(b"{}")
        api = cy.Api("K")
        with mock.patch.object(cy.urllib.request, "urlopen", side_effect=falso):
            api.get("channels.list", part="id", forHandle="x")
            api.get("playlistItems.list", part="id", playlistId="UU")
        self.assertTrue(pedidos[0].startswith("https://www.googleapis.com/youtube/v3/channels?"))
        self.assertTrue(pedidos[1].startswith("https://www.googleapis.com/youtube/v3/playlistItems?"))


if __name__ == "__main__":
    unittest.main()
