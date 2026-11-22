#!/usr/bin/env python3
"""Transcrição dos vídeos das influenciadoras no núcleo (23/07 a 14/08/2026). Sem custo em US$.

Uso: python scripts/transcrever.py --rede youtube|instagram|tiktok [--modelo small] [--janela nucleo]

- Universo da etapa: publicações em vídeo da rede na janela, tiradas do acervo público
  (data/youtube/videos.csv, data/instagram/posts.csv, data/tiktok/posts.csv). Imagem e carrossel
  sem vídeo não têm fala e ficam fora, contados à parte no manifesto.
- YouTube: tenta primeiro a legenda do próprio vídeo (youtube-transcript-api); sem ela, áudio + Whisper.
- Instagram e TikTok: áudio baixado com yt-dlp e transcrito com faster-whisper (CPU), idioma detectado.
- Retoma de onde parou: post já transcrito com sucesso não é refeito.
- Saída pública: data/transcricoes/<rede>.csv (fala das próprias influenciadoras em publicações públicas).
- Manifesto: data/manifest/transcricao_<rede>_latest.json com universo, transcritos, falhas e motivos.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS = ["post_id", "rede", "ator_id", "publicado_em", "janela", "url", "fonte", "idioma", "duracao_s", "status", "texto", "transcrito_em"]
ACERVO = {"youtube": ("data/youtube/videos.csv", "video_id"), "instagram": ("data/instagram/posts.csv", "post_id"),
          "tiktok": ("data/tiktok/posts.csv", "post_id")}


def ler_csv(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def alvos(rede: str, janela: str, raiz: Path = RAIZ):
    """(vídeos a transcrever, publicações sem vídeo) da rede na janela."""
    arq, chave = ACERVO[rede]
    linhas = [r for r in ler_csv(raiz / arq) if r.get("janela") == janela]
    videos, sem_video = [], []
    for r in linhas:
        pid = r[chave]
        if rede == "instagram" and r.get("tipo") in ("imagem", "carrossel"):
            sem_video.append(pid)
            continue
        videos.append({"post_id": pid, "rede": rede, "ator_id": r["ator_id"], "publicado_em": r["publicado_em"],
                       "janela": janela, "url": r["url"]})
    return videos, sem_video


def legenda_youtube(video_id: str):
    """Legenda do próprio vídeo (manual ou automática), em pt, ar ou en. None se não houver ou se for bloqueada."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return None
    try:
        api = YouTubeTranscriptApi()
        t = api.fetch(video_id, languages=["pt", "pt-BR", "ar", "en"])
        texto = " ".join(s.text for s in t.snippets)
        return {"texto": " ".join(texto.split()), "idioma": t.language_code, "fonte": "legenda do YouTube" + (" (automática)" if t.is_generated else "")}
    except Exception:  # noqa: BLE001
        return None


def baixar_audio(url: str, pasta: str) -> str:
    saida = os.path.join(pasta, "audio.%(ext)s")
    cmd = ["yt-dlp", "-q", "--no-warnings", "--no-playlist", "-f", "bestaudio/best", "-x", "--audio-format", "mp3",
           "--audio-quality", "5", "-o", saida, url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("download: " + (r.stderr.strip().splitlines() or ["falhou"])[-1][:200])
    for f in os.listdir(pasta):
        if f.startswith("audio."):
            return os.path.join(pasta, f)
    raise RuntimeError("download: arquivo de áudio não encontrado")


_MODELO = {}


def whisper(caminho: str, modelo: str):
    if modelo not in _MODELO:
        from faster_whisper import WhisperModel
        _MODELO[modelo] = WhisperModel(modelo, device="cpu", compute_type="int8")
    segs, info = _MODELO[modelo].transcribe(caminho, vad_filter=True, beam_size=1)
    texto = " ".join(s.text.strip() for s in segs)
    return {"texto": " ".join(texto.split()), "idioma": info.language, "duracao_s": round(info.duration),
            "fonte": f"Whisper {modelo} (faster-whisper, CPU)"}


def gravar(caminho: Path, linhas: dict):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(linhas.values(), key=lambda r: (r["ator_id"], r["publicado_em"])):
            w.writerow(r)


def main(argv=None, raiz: Path = RAIZ, legenda=legenda_youtube, baixar=baixar_audio, transcrever=whisper) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rede", required=True, choices=list(ACERVO))
    ap.add_argument("--modelo", default="small")
    ap.add_argument("--janela", default="nucleo")
    ap.add_argument("--limite-minutos", type=float, default=300, help="para com folga antes do tempo do job")
    a = ap.parse_args(argv)

    inicio = time.time()
    videos, sem_video = alvos(a.rede, a.janela, raiz)
    destino = raiz / f"data/transcricoes/{a.rede}.csv"
    feitas = {r["post_id"]: r for r in ler_csv(destino)}
    falhas, novas, parou_por_tempo = [], 0, False

    for v in videos:
        if feitas.get(v["post_id"], {}).get("status") == "ok":
            continue
        if (time.time() - inicio) / 60 > a.limite_minutos:
            parou_por_tempo = True
            break
        agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = legenda(v["post_id"]) if a.rede == "youtube" else None
        try:
            if res is None:
                with tempfile.TemporaryDirectory() as tmp:
                    res = transcrever(baixar(v["url"], tmp), a.modelo)
            feitas[v["post_id"]] = {**v, **res, "status": "ok", "transcrito_em": agora}
            novas += 1
        except Exception as e:  # noqa: BLE001
            motivo = str(e)[:240]
            falhas.append({"post_id": v["post_id"], "motivo": motivo})
            feitas[v["post_id"]] = {**v, "status": "falhou: " + motivo, "texto": "", "transcrito_em": agora}
        gravar(destino, feitas)  # grava a cada vídeo: uma queda no meio não perde o que já foi feito

    ok = sum(1 for v in videos if feitas.get(v["post_id"], {}).get("status") == "ok")
    manifesto = {"rede": a.rede, "janela": a.janela, "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
                 "gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "modelo": a.modelo, "custo_usd": 0,
                 "universo_videos": len(videos), "publicacoes_sem_video": len(sem_video), "transcritos": ok,
                 "novos_nesta_execucao": novas, "falhas": falhas, "parou_por_tempo": parou_por_tempo,
                 "fontes": sorted({r.get("fonte", "") for r in feitas.values() if r.get("status") == "ok"})}
    (raiz / "data/manifest").mkdir(parents=True, exist_ok=True)
    (raiz / f"data/manifest/transcricao_{a.rede}_latest.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{a.rede}: {ok} de {len(videos)} vídeos transcritos ({novas} nesta execução); {len(falhas)} falha(s); "
          f"{len(sem_video)} publicações sem vídeo fora; parou por tempo: {parou_por_tempo}")
    for f in falhas[:5]:
        print(f"  falha {f['post_id']}: {f['motivo']}")
    return 0 if ok or not videos else 1


if __name__ == "__main__":
    raise SystemExit(main())
