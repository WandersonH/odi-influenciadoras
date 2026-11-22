import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import transcrever as tr  # noqa: E402


def escrever(caminho, campos, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)


class TestTranscrever(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        escrever(self.tmp / "data/instagram/posts.csv", ["post_id", "ator_id", "publicado_em", "janela", "tipo", "url"], [
            {"post_id": "a", "ator_id": "m", "publicado_em": "2026-08-01", "janela": "nucleo", "tipo": "vídeo", "url": "u1"},
            {"post_id": "b", "ator_id": "m", "publicado_em": "2026-08-02", "janela": "nucleo", "tipo": "carrossel", "url": "u2"},
            {"post_id": "c", "ator_id": "m", "publicado_em": "2026-07-01", "janela": "base", "tipo": "vídeo", "url": "u3"},
            {"post_id": "d", "ator_id": "h", "publicado_em": "2026-08-03", "janela": "nucleo", "tipo": "vídeo", "url": "u4"},
        ])

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_so_videos_do_nucleo_e_retoma(self):
        baixados = []

        def baixar(url, pasta):
            baixados.append(url)
            if url == "u4":
                raise RuntimeError("download: bloqueado")
            return "x.mp3"
        rc = tr.main(["--rede", "instagram"], raiz=self.tmp, baixar=baixar,
                     transcrever=lambda c, m: {"texto": "fala", "idioma": "pt", "duracao_s": 30, "fonte": "teste"})
        self.assertEqual(rc, 0)
        self.assertEqual(baixados, ["u1", "u4"])
        m = json.loads((self.tmp / "data/manifest/transcricao_instagram_latest.json").read_text())
        self.assertEqual((m["universo_videos"], m["publicacoes_sem_video"], m["transcritos"]), (2, 1, 1))
        self.assertEqual(m["falhas"][0]["post_id"], "d")
        # segunda execução: só refaz a que falhou
        baixados.clear()
        tr.main(["--rede", "instagram"], raiz=self.tmp, baixar=lambda u, p: baixados.append(u) or "x.mp3",
                transcrever=lambda c, m: {"texto": "fala 2", "idioma": "pt", "duracao_s": 9, "fonte": "teste"})
        self.assertEqual(baixados, ["u4"])

    def test_youtube_usa_legenda_antes_do_audio(self):
        escrever(self.tmp / "data/youtube/videos.csv", ["video_id", "ator_id", "publicado_em", "janela", "url"], [
            {"video_id": "v", "ator_id": "m", "publicado_em": "2026-08-01", "janela": "nucleo", "url": "y"}])
        rc = tr.main(["--rede", "youtube"], raiz=self.tmp,
                     legenda=lambda vid: {"texto": "oi", "idioma": "pt", "fonte": "legenda do YouTube"},
                     baixar=lambda *a: self.fail("não devia baixar"), transcrever=lambda *a: self.fail("não devia transcrever"))
        self.assertEqual(rc, 0)
        with (self.tmp / "data/transcricoes/youtube.csv").open(encoding="utf-8") as f:
            self.assertEqual(next(csv.DictReader(f))["fonte"], "legenda do YouTube")


if __name__ == "__main__":
    unittest.main()
