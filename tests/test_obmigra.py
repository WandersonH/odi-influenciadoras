import json, pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build_obmigra as b

CFG = {"nucleo": ["SÍRIA"], "contexto": ["EGITO"]}


def linha(pais, uf="SP", idade="30"):
    return {"PAIS_NACIONALIDADE": pais, "PAIS_NASCIMENTO": pais, "UNIDADE_FED_RESIDENCIA": uf, "MUNICIPIO_RESIDENCIA": "X",
            "CLASSIFICACAO_REVISADA": "TEMPORÁRIO", "TIPOLOGIA_AMPAROS": "ACOLHIDA HUMANITÁRIA", "SEXO": "Masculino",
            "IDADE": idade, "DATAENTRADA": "2026", "DATAREGISTRO": "2026"}


class T(unittest.TestCase):
    def test_agrega(self):
        L = [linha("SÍRIA"), linha("SÍRIA", "PR", "abc"), linha("EGITO"), linha("ESPANHA")]
        r = b.agrega(L, CFG)
        self.assertEqual(r["universo"], 4)
        self.assertEqual(r["nucleo_total"], 2)
        self.assertEqual(r["paises"]["SÍRIA"]["registros"], 2)
        self.assertIn(["não informada", 1], r["paises"]["SÍRIA"]["idade"])
        self.assertEqual(r["paises"]["EGITO"]["grupo"], "contexto")

    def test_profissao_celula_pequena(self):
        xs = [dict(linha("SÍRIA"), PROFISSAO="ESTUDANTE") for _ in range(4)] + [dict(linha("SÍRIA"), PROFISSAO="PILOTO")]
        r = b.profissoes(xs)
        self.assertEqual(r[0], ["ESTUDANTE", 4])
        self.assertTrue(r[-1][0].startswith("outras"))
        self.assertEqual(r[-1][1], 1)
        self.assertNotIn("PILOTO", [k for k, _ in r])

    def test_faixa(self):
        self.assertEqual(b.faixa("17"), "0 a 17")
        self.assertEqual(b.faixa("60"), "60 ou mais")


if __name__ == "__main__":
    unittest.main()
