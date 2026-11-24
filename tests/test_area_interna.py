import json, pathlib, re, sys, unittest
RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import build_area_interna as b

SQL = (RAIZ / "supabase/migrations/20261124_area_interna.sql").read_text(encoding="utf-8")
LIVRO = json.loads((RAIZ / "data/config/livro_codigos_posicionamento.json").read_text(encoding="utf-8"))
PAGINA = (RAIZ / "area-interna.html").read_text(encoding="utf-8")


class Banco(unittest.TestCase):
    def test_rls_em_todas_as_tabelas(self):
        tabelas = re.findall(r"create table if not exists public\.(\w+)", SQL)
        self.assertEqual(sorted(tabelas), ["acessos", "codificacoes", "decisoes", "pesquisadores", "unidades"])
        for t in tabelas:
            self.assertIn(f"alter table public.{t} enable row level security", SQL)

    def test_livro_e_banco_tem_as_mesmas_categorias(self):
        for d in LIVRO["dimensoes"]:
            ids = [c["id"] for c in d["categorias"]]
            m = re.search(rf"\n  {d['id']} text check \({d['id']} in \(([^)]*)\)\)", SQL)
            self.assertIsNotNone(m, d["id"])
            self.assertEqual(sorted(re.findall(r"'(\w+)'", m.group(1))), sorted(ids), d["id"])

    def test_sem_escrita_direta_e_sem_anon(self):
        self.assertIn("revoke insert, update, delete on public.pesquisadores, public.unidades, public.codificacoes, public.decisoes, public.acessos from authenticated", SQL)
        self.assertIn("from public, anon", SQL)

    def test_funcoes_internas_checam_permissao(self):
        for f in ("_gravar", "_decidir"):
            corpo = SQL.split(f"function odi_interno.{f}(")[1].split("end $$;")[0]
            self.assertRegex(corpo, r"if not odi_interno\.eh_(pesquisador|responsavel)\(\) then raise")


class Pagina(unittest.TestCase):
    def test_sem_chave_no_codigo(self):
        self.assertNotRegex(PAGINA, r"eyJ[A-Za-z0-9_-]{20,}")
        self.assertNotRegex(PAGINA, r"sb_(publishable|secret)_[A-Za-z0-9]")
        self.assertIn("noindex", PAGINA)


class Unidades(unittest.TestCase):
    def test_so_nucleo_e_so_posts_das_quatro(self):
        us = b.unidades()
        self.assertTrue(us)
        self.assertEqual({u["rede"] for u in us} - {"youtube", "instagram", "tiktok"}, set())
        self.assertTrue(all(u["ator_id"] in {"mariam-chami", "carima-orra", "fabiola-oliveira", "hyatt-omar"} for u in us))
        self.assertEqual(len({u["id"] for u in us}), len(us))

    def test_sql_escapa_aspas(self):
        self.assertIn("'d''água'", b.sql([{"id": "x:1", "ator_id": "a", "rede": "tiktok", "publicado_em": None, "tipo": None, "url": None,
                                          "texto": "d'água", "transcricao": None, "transcricao_status": None, "ordem": "0"}]))


if __name__ == "__main__":
    unittest.main()
