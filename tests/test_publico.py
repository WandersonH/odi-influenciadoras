import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build_publico as bp
import collect_canais_comentaristas as cc


class Comum(unittest.TestCase):
    def test_pares_e_multi(self):
        r = bp.comum({"a": {"x", "y"}, "b": {"y", "z"}, "c": {"w"}}, {"x": "IG0001", "y": "IG0002", "z": "IG0003", "w": "IG0004"})
        self.assertEqual(r["autores_distintos"], 4)
        self.assertEqual(r["em_duas_ou_mais"], 1)
        self.assertEqual(r["codigos_duas_ou_mais"], ["IG0002"])
        p = r["pares"][0]
        self.assertEqual((p["a"], p["b"], p["comum"], p["codigos"]), ("a", "b", 1, ["IG0002"]))
        self.assertAlmostEqual(p["jaccard_pct"], 33.33)


class Contas(unittest.TestCase):
    def test_faixas(self):
        self.assertEqual(bp.faixa("2026-07-23T10:00:00Z"), "núcleo (23/07 a 14/08/2026)")
        self.assertEqual(bp.faixa("2026-06-01T00:00:00Z"), "linha de base (01/06 a 22/07/2026)")
        self.assertEqual(bp.faixa("2015-01-01"), "até 2019")
        self.assertIsNone(bp.faixa(""))

    def test_recentes_e_pais(self):
        canais = [{"autor": "a", "criado_em": "2026-07-25T00:00:00Z", "pais": "BR"},
                  {"autor": "b", "criado_em": "2018-01-01T00:00:00Z", "pais": ""},
                  {"autor": "c", "criado_em": "", "pais": "LB"}]
        r = bp.contas(canais, {"a": "A0001", "b": "A0002", "c": "A0003"}, {"a": "2026-08-01T00:00:00Z", "b": "2026-08-01T00:00:00Z"})
        self.assertEqual(r["canais_lidos"], 2)
        self.assertEqual(r["criados_ate_30_dias_antes_do_1o_comentario"], 1)
        self.assertEqual(r["com_pais"], 1)
        self.assertEqual(r["paises"][0]["pais"], "BR")


class Coletor(unittest.TestCase):
    def test_lotes_de_50(self):
        chamadas = []

        def get(rota, q):
            ids = q["id"].split(",")
            chamadas.append(len(ids))
            return {"items": [{"id": i, "snippet": {"authorChannelId": {"value": "UC" + i}}} for i in ids]}
        out, n, erros = cc.canais_dos_comentarios([str(i) for i in range(120)], "k", get=get)
        self.assertEqual(chamadas, [50, 50, 20])
        self.assertEqual(len(out), 120)
        self.assertEqual(out["7"], "UC7")

    def test_inscritos_ocultos(self):
        get = lambda rota, q: {"items": [{"id": "UC1", "snippet": {"publishedAt": "2020-01-01T00:00:00Z", "country": "BR"},
                                          "statistics": {"hiddenSubscriberCount": True, "videoCount": "3"}}]}
        out, _, _ = cc.dados_dos_canais(["UC1"], "k", "snippet,statistics", get=get)
        self.assertIsNone(out["UC1"]["inscritos"])
        self.assertEqual(out["UC1"]["pais"], "BR")


if __name__ == "__main__":
    unittest.main()
