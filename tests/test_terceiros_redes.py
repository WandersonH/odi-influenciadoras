import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import collect_terceiros_redes as c

ALVOS = [("fabiola-oliveira", "Fabíola Oliveira", "fabiolaoliver"), ("mariam-chami", "Mariam Chami", "mariamchami1")]


def tt(pid, autor, texto, data):
    return {"id": pid, "title": texto, "uploadedAtFormatted": data + "T12:00:00.000Z", "postPage": f"https://t/{pid}",
            "channel": {"username": autor, "followers": 50}, "views": 10, "likes": 1, "comments": 0}


class T(unittest.TestCase):
    def test_tiktok_filtra_nucleo_propria_e_acento(self):
        itens = [tt("1", "outra", "vi a Fabiola Oliveira falando", "2026-07-30"),   # sem acento, núcleo: conta
                 tt("2", "fabiolaoliver", "Fabíola Oliveira aqui", "2026-07-30"),    # a própria: não conta
                 tt("3", "outra", "Fabíola Oliveira", "2026-09-10"),                 # fora do núcleo
                 tt("4", "outra", "nada a ver", "2026-07-30"),                       # não cita
                 tt("5", "fabiolaoliver", "oi @mariamchami1", "2026-08-01")]         # outra do estudo cita Mariam
        linhas, resumo, validos = c.separa("tiktok", itens, ALVOS, "2026-07-23", "2026-08-14", "agora")
        self.assertEqual(validos, 5)
        self.assertEqual(sorted(l["chave"] for l in linhas), ["fabiola-oliveira|1", "mariam-chami|5"])
        r = {x["ator"]: x for x in resumo}
        self.assertEqual(r["fabiola-oliveira"]["citam_a_influenciadora"], 2)
        self.assertEqual(r["fabiola-oliveira"]["no_nucleo"], 1)
        self.assertEqual(r["mariam-chami"]["de_outras_do_estudo"], 1)
        self.assertEqual(r["mariam-chami"]["por_tipo"], {"arroba": 1})

    def test_instagram_marcacao_conta_como_arroba(self):
        x = {"id": "9", "ownerUsername": "loja", "timestamp": "2026-08-02T10:00:00.000Z", "caption": "look do dia", "mentions": ["mariamchami1"], "shortCode": "abc"}
        y = c.normaliza("instagram", x)
        self.assertEqual(c.cita(y, "Mariam Chami", "mariamchami1"), "arroba")
        self.assertEqual(y["url"], "https://www.instagram.com/p/abc/")

    def test_formato_clockworks(self):
        x = {"id": "7", "text": "a Mariam Chami disse", "createTimeISO": "2026-08-01T10:00:00.000Z", "webVideoUrl": "https://t/7",
             "authorMeta": {"name": "perfilx", "fans": 20000}, "playCount": 5, "mentions": ["@mariamchami1"]}
        y = c.normaliza("tiktok", x)
        self.assertEqual((y["autor"], y["autor_seguidores"], y["publicado_em"][:10]), ("perfilx", 20000, "2026-08-01"))
        self.assertEqual(c.cita(y, "Mariam Chami", "mariamchami1"), "arroba e nome")

    def test_pedido(self):
        self.assertEqual(c.pedido("tiktok", ["A"], 50, "clockworks~tiktok-scraper"), {"searchQueries": ["A"], "searchSection": "/video", "resultsPerPage": 50})
        self.assertEqual(c.pedido("tiktok", ["A", "B"], 10)["maxItems"], 20)
        self.assertTrue(c.pedido("instagram", ["A"], 5)["keywordSearch"])


if __name__ == "__main__":
    unittest.main()
