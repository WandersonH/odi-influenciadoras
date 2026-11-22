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


def legendas_apify(ids: list[str], raiz: Path = RAIZ, executar=None) -> dict:
    """Legendas do YouTube pela Apify (seemuapps~youtube-transcript-scraper; o ODI Atlas mediu US$ 0,0001 por transcrição
    + início). Etapa "terceiros_transcricoes" do teto autorizado; a Apify exige teto mínimo de US$ 0,50 por execução.
    Grava o manifesto apify_youtube_transcricao_*.json com o custo. Devolve {video_id: resultado}."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import apify
    from collect_apify_posts import gasto_etapa
    coleta = json.loads((raiz / "data/config/coleta.json").read_text(encoding="utf-8"))["apify"]
    etapa = "terceiros_transcricoes"
    teto, gasto = float(coleta.get("etapas", {}).get(etapa, 0)), gasto_etapa(etapa, raiz)
    cap = round(min(0.5, teto - gasto), 4)
    if not coleta.get("autorizacao") or cap < 0.5 or not ids:
        print(f"youtube/apify: sem teto suficiente na etapa {etapa} (resta {round(teto - gasto, 4)}): nada roda.")
        return {}
    token = os.environ.get(coleta["segredo"], "").strip()
    if executar is None:
        if not token:
            print("youtube/apify: segredo ausente: nada roda.")
            return {}
        executar = lambda ator, p, c: apify.run_actor(token, ator, p, c)  # noqa: E731
    ator = "seemuapps~youtube-transcript-scraper"
    run, itens = executar(ator, {"videoUrls": [f"https://www.youtube.com/watch?v={v}" for v in ids],
                                 "languages": ["pt", "pt-BR", "ar", "en"], "preferManualCaptions": True}, cap)
    out = {}
    for x in itens or []:
        vid = str(x.get("videoId") or "") or str(x.get("inputUrl") or "").split("v=")[-1].split("&")[0]
        segs = x.get("segments") or x.get("transcriptSegments") or []
        texto = " ".join(" ".join(str(s.get("text") or "").split()) for s in segs if s.get("text"))
        if not texto:
            texto = " ".join(str(x.get("transcript") or x.get("text") or "").split())
        if texto:
            auto = x.get("isAutoGenerated") or x.get("isGenerated") or x.get("autoGenerated")
            out[vid] = {"texto": texto, "idioma": x.get("language") or x.get("languageCode") or "",
                        "fonte": "legenda do YouTube" + (" (automática)" if auto else "") + " lida pela Apify (seemuapps)"}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    m = {"rede": "youtube", "etapa": etapa, "ator": ator, "run_apify": run.get("id"), "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
         "pedidos": len(ids), "itens_recebidos": len(itens or []), "com_texto": len(out), "cap_por_execucao_usd": cap,
         "custo_usd": apify.custo_run(run)}
    (raiz / "data/manifest").mkdir(parents=True, exist_ok=True)
    (raiz / f"data/manifest/apify_youtube_transcricao_{stamp}.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"youtube/apify: {len(out)} de {len(ids)} com legenda; custo US$ {m['custo_usd']}")
    return out


_MODELO = {}


def whisper(caminho: str, modelo: str):
    if modelo not in _MODELO:
        from faster_whisper import WhisperModel
        _MODELO[modelo] = WhisperModel(modelo, device="cpu", compute_type="int8")
    # decodifica com o ffmpeg (16 kHz, mono): evita o PyAV, cuja versão nova quebrou o decode_audio do faster-whisper
    import numpy as np
    r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", caminho, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                       capture_output=True, timeout=900)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError("ffmpeg: " + r.stderr.decode("utf-8", "replace")[-200:])
    audio = np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768.0
    segs, info = _MODELO[modelo].transcribe(audio, vad_filter=True, beam_size=1)
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
    ap.add_argument("--apify", action="store_true", help="YouTube: legendas pela Apify (etapa terceiros_transcricoes)")
    ap.add_argument("--limite-minutos", type=float, default=300, help="para com folga antes do tempo do job")
    a = ap.parse_args(argv)

    inicio = time.time()
    videos, sem_video = alvos(a.rede, a.janela, raiz)
    destino = raiz / f"data/transcricoes/{a.rede}.csv"
    feitas = {r["post_id"]: r for r in ler_csv(destino)}
    falhas, novas, parou_por_tempo = [], 0, False
    pela_apify = {}
    if a.apify and a.rede == "youtube":
        pend = [v["post_id"] for v in videos if feitas.get(v["post_id"], {}).get("status") != "ok"]
        pela_apify = legendas_apify(pend, raiz)

    for v in videos:
        if feitas.get(v["post_id"], {}).get("status") == "ok":
            continue
        if (time.time() - inicio) / 60 > a.limite_minutos:
            parou_por_tempo = True
            break
        agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = pela_apify.get(v["post_id"]) or (legenda(v["post_id"]) if a.rede == "youtube" else None)
        if res is None and a.apify:
            falhas.append({"post_id": v["post_id"], "motivo": "sem legenda pela Apify"})
            feitas[v["post_id"]] = {**v, "status": "falhou: sem legenda pela Apify", "texto": "", "transcrito_em": agora}
            gravar(destino, feitas)
            continue
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
