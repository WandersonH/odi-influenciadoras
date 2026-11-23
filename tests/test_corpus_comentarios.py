import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_corpus_comentarios as bcc  # noqa: E402


class TestAnonimizacao(unittest.TestCase):
    def test_arroba_de_terceiro_vira_perfil_e_proprio_fica(self):
        t = bcc.anonimizar("Oi @pérola.gavioli e @mariamchami_ veja https://x.com/a", {"mariamchami_"})
        self.assertNotIn("pérola", t)
        self.assertIn("@perfil", t)
        self.assertIn("@mariamchami_", t)
        self.assertIn("[link]", t)
        self.assertNotIn("x.com", t)

    def test_email_e_telefone(self):
        t = bcc.anonimizar("fala comigo fulano@gmail.com ou (11) 99876-5432, nasci em 1991", set())
        self.assertNotIn("gmail", t)
        self.assertNotIn("99876", t)
        self.assertIn("1991", t)

    def test_codigos_na_ordem_do_primeiro_comentario(self):
        cod = bcc.codigos([{"autor": "B", "publicado_em": "2026-08-02", "comment_id": "2"},
                           {"autor": "a", "publicado_em": "2026-08-01", "comment_id": "1"},
                           {"autor": "b", "publicado_em": "2026-08-03", "comment_id": "3"}], "IG")
        self.assertEqual(cod, {"a": "IG0001", "b": "IG0002"})


if __name__ == "__main__":
    unittest.main()


class TestSugestoes(unittest.TestCase):
    def test_conta_sugestoes_por_consulta(self):
        import importlib
        cs = importlib.import_module("collect_sugestoes")
        self.assertEqual(len(cs.consultas("Mariam Chami")), 28)
        respostas = {"Mariam Chami": ["mariam chami marido", "mariam chami idade"], "Mariam Chami m": ["mariam chami marido"]}
        cont = {}
        for q in cs.consultas("Mariam Chami"):
            for s in respostas.get(q, []):
                cont[s] = cont.get(s, 0) + 1
        self.assertEqual(cont["mariam chami marido"], 2)
