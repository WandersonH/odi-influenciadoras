#!/usr/bin/env python3
"""Comentários das publicações do NÚCLEO (23/07 a 14/08/2026) das quatro influenciadoras.

Uso: python scripts/collect_comentarios.py --rede youtube|instagram|tiktok [--por-post 50]

- YouTube: API oficial (commentThreads.list, 100 por página, do mais novo ao mais antigo, até o fim), sem custo em US$.
- Instagram: Apify datadoping~instagram-comments-and-replies-scraper (o do ODI Atlas; US$ 1,40 por mil no caso 008),
  até --por-post comentários por publicação, ordem "popular", sem respostas.
- TikTok: Apify clockworks~tiktok-comments-scraper (o do ODI Atlas; cerca de US$ 0,50 por mil), até --por-post por vídeo.
Teto: etapa "comentarios" de data/config/coleta.json (US$ 5,00 autorizados em 22/11/2026). Instagram leva até US$ 3,60 e
TikTok até US$ 1,20 por execução, sempre limitados ao que resta da etapa e ao mínimo de US$ 0,50 da Apify.

Universo por publicação = número de comentários que a plataforma informa no acervo de posts (YouTube e TikTok); o
Instagram não informou (⛔). Lido = comentários recebidos. Cobertura "completa" só quando lido ≥ universo.

Privacidade (CLAUDE.md, regra 10): texto e autor ficam SÓ no repositório privado (INFL_INTERNO_DIR); sem ele nada é lido.
Ao público vai data/comentarios/<rede>_resumo.json: contagens por publicação e por influenciadora, e quantos comentários
citam os temas do dicionário (acordo/Hamas, Gaza e Palestina, Israel, islamofobia), sem texto nem autor.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apify  # noqa: E402
import texto as tx  # noqa: E402
from collect_apify_posts import gasto_etapa, quando  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ETAPA = "comentarios"
ATOR = {"instagram": "datadoping~instagram-comments-and-replies-scraper", "tiktok": "clockworks~tiktok-comments-scraper"}
CAP_REDE = {"instagram": 3.6, "tiktok": 1.2}
FONTES = {"youtube": ("data/youtube/videos.csv", "video_id"), "instagram": ("data/instagram/posts.csv", "post_id"),
          "tiktok": ("data/tiktok/posts.csv", "post_id")}
COD = {"instagram": re.compile(r"instagram\.com/(?:[\w.]+/)?(?:p|reel|reels|tv)/([\w-]+)"), "tiktok": re.compile(r"/video/(\d+)")}
TEMAS_COMENTARIO = ("acordo_hamas", "gaza_palestina", "israel_guerra", "islamofobia_preconceito")
CAMPOS = ["comment_id", "rede", "ator_id", "post_id", "autor", "texto", "curtidas", "publicado_em", "coletado_em"]


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        return int(float(str(v)))
    except (TypeError, ValueError):
        return None


def youtube(posts, chave, max_paginas=40):
    out, chamadas, erros = [], 0, []
    for p in posts:
        token = None
        for _ in range(max_paginas):
            q = {"part": "snippet", "videoId": p["post_id"], "maxResults": 100, "order": "time", "textFormat": "plainText", "key": chave}
            if token:
                q["pageToken"] = token
            try:
                with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/commentThreads?" + urllib.parse.urlencode(q), timeout=60) as r:
                    d = json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                erros.append(f"{p['post_id']}: HTTP {e.code}")
                break
            chamadas += 1
            for it in d.get("items", []):
                s = it["snippet"]["topLevelComment"]["snippet"]
                out.append({"comment_id": it["id"], "post_id": p["post_id"], "autor": s.get("authorDisplayName", ""),
                            "texto": " ".join(str(s.get("textOriginal") or s.get("textDisplay") or "").split()),
                            "curtidas": s.get("likeCount", 0), "publicado_em": s.get("publishedAt", "")})
            token = d.get("nextPageToken")
            if not token:
                break
    return out, {"chamadas_api": chamadas, "custo_usd": 0}, erros


def apify_rede(rede, posts, por_post, cap, executar):
    if rede == "instagram":
        pl = {"code_or_id_or_url": [p["url"] for p in posts], "sort_by": "popular", "max_comments": por_post,
              "scrape_replies": False, "max_replies": 20}
    else:
        pl = {"postURLs": [p["url"] for p in posts], "commentsPerPost": por_post, "maxRepliesPerComment": 0}
    run, itens = executar(ATOR[rede], pl, cap)
    por_cod = {}
    for p in posts:
        m = COD[rede].search(p["url"])
        por_cod[m.group(1) if m else p["post_id"]] = p
    out = []
    for x in itens or []:
        if rede == "instagram":
            if x.get("content_type") == "caption":
                continue
            m = COD[rede].search(str(x.get("input_url") or x.get("post_url") or ""))
            texto, cid = x.get("text"), x.get("comment_id") or x.get("id")
            u = x.get("user") if isinstance(x.get("user"), dict) else {}
            autor, curt, pub = x.get("username") or u.get("username") or "", x.get("like_count") or 0, x.get("created_at_utc") or ""
        else:
            m = COD[rede].search(str(x.get("videoWebUrl") or x.get("submittedVideoUrl") or x.get("input") or ""))
            texto, cid = x.get("text"), x.get("cid") or x.get("id")
            autor, curt, pub = x.get("uniqueId") or "", x.get("diggCount") or 0, x.get("createTimeISO") or ""
        p = por_cod.get(m.group(1)) if m else None
        texto = " ".join(str(texto or "").split())
        if p and texto and cid:
            out.append({"comment_id": str(cid), "post_id": p["post_id"], "autor": autor, "texto": texto, "curtidas": curt, "publicado_em": quando(pub)})
    return out, {"run_apify": run.get("id"), "itens_recebidos": len(itens or []), "custo_usd": apify.custo_run(run)}, []


def main(argv=None, raiz: Path = RAIZ, executar=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rede", required=True, choices=list(FONTES))
    ap.add_argument("--por-post", type=int, default=50)
    a = ap.parse_args(argv)
    interno = os.environ.get("INFL_INTERNO_DIR", "")
    if not interno or not Path(interno).is_dir():
        print(f"{a.rede}: repositório privado indisponível: nada é lido (texto e autor de comentários só vão para o privado).")
        return 1
    arq, chave = FONTES[a.rede]
    posts = [{"post_id": r[chave], "ator_id": r["ator_id"], "url": r["url"], "universo": num(r.get("comentarios"))}
             for r in ler(raiz / arq) if r.get("janela") == "nucleo"]
    if not posts:
        print(f"{a.rede}: nenhuma publicação no núcleo")
        return 1
    if a.rede == "youtube":
        k = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if not k:
            print("youtube: YOUTUBE_API_KEY ausente: nada lido")
            return 1
        lidos, execucao, erros = youtube(posts, k)
    else:
        coleta = json.loads((raiz / "data/config/coleta.json").read_text(encoding="utf-8"))["apify"]
        teto, gasto = float(coleta.get("etapas", {}).get(ETAPA, 0)), gasto_etapa(ETAPA, raiz)
        cap = round(min(teto - gasto, CAP_REDE[a.rede]), 4)
        if not coleta.get("autorizacao") or cap < 0.5:
            print(f"{a.rede}: resta US$ {round(teto - gasto, 4)} na etapa {ETAPA}: abaixo do mínimo de US$ 0,50 por execução, nada roda.")
            return 1
        if executar is None:
            token = os.environ.get(coleta["segredo"], "").strip()
            if not token:
                print(f"{a.rede}: segredo ausente: nada roda")
                return 1
            executar = lambda ator, p, c: apify.run_actor(token, ator, p, c)  # noqa: E731
        try:
            lidos, execucao, erros = apify_rede(a.rede, posts, a.por_post, cap, executar)
        except apify.ErroDepoisDaExecucao as e:
            lidos, execucao, erros = [], {"run_apify": e.run.get("id"), "custo_usd": apify.custo_run(e.run)}, [str(e)]
        except Exception as e:  # noqa: BLE001
            lidos, execucao, erros = [], {"custo_usd": 0}, [apify.erro_curto(e)]
        execucao["cap_usd"] = cap
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dono = {p["post_id"]: p["ator_id"] for p in posts}
    for c in lidos:
        c.update({"rede": a.rede, "ator_id": dono[c["post_id"]], "coletado_em": agora})
    # privado: texto e autor
    d = Path(interno) / "data/comentarios"
    d.mkdir(parents=True, exist_ok=True)
    priv = d / f"{a.rede}.csv"
    ant = {r["comment_id"]: r for r in ler(priv)}
    for c in lidos:
        ant[c["comment_id"]] = c
    with priv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(ant.values(), key=lambda r: (r["ator_id"], r["post_id"], r["publicado_em"])))
    # público: só contagens
    cfg = json.loads((raiz / "data/config/temas.json").read_text(encoding="utf-8"))
    latinos = {k: [tx.term_regex(t) for t in cfg["temas"][k] if tx.norm(t.rstrip("*")).strip()] for k in TEMAS_COMENTARIO}
    literais = {k: [t for t in cfg["temas"][k] if not tx.norm(t.rstrip("*")).strip()] for k in TEMAS_COMENTARIO}
    todos = list(ant.values())
    def temas_de(t):
        n_ = tx.norm(t)
        return [k for k in TEMAS_COMENTARIO if any(r.search(n_) for r in latinos[k]) or any(x in t for x in literais[k])]
    por_post = []
    for p in posts:
        cs = [c for c in todos if c["post_id"] == p["post_id"]]
        tem = Counter(k for c in cs for k in temas_de(c["texto"]))
        por_post.append({"post_id": p["post_id"], "ator_id": p["ator_id"], "url": p["url"], "universo": p["universo"], "lidos": len(cs),
                         "cobertura": "⛔ universo não informado" if p["universo"] is None else "completa" if len(cs) >= p["universo"] else "amostra",
                         "temas": dict(tem)})
    por_infl = {}
    for aid in sorted(set(dono.values())):
        cs = [c for c in todos if c["ator_id"] == aid]
        ps = [p for p in por_post if p["ator_id"] == aid]
        uni = [p["universo"] for p in ps]
        por_infl[aid] = {"publicacoes": len(ps), "universo": None if any(u is None for u in uni) else sum(uni), "lidos": len(cs),
                         "comentaristas_distintos": len({c["autor"].lower() for c in cs if c["autor"]}),
                         "temas": dict(Counter(k for c in cs for k in temas_de(c["texto"]))),
                         "nuvem": tx.nuvem([c["texto"] for c in cs], set(), top=40)}
    resumo = {"rede": a.rede, "gerado_em": agora, "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "janela": "núcleo",
              "metodo": __doc__.split("\n\n")[1].strip() + " " + __doc__.split("\n\n")[3].strip(),
              "temas_procurados": {k: cfg["temas"][k] for k in TEMAS_COMENTARIO}, "por_influenciadora": por_infl, "por_publicacao": por_post,
              "execucao": execucao, "erros": erros}
    (raiz / "data/comentarios").mkdir(parents=True, exist_ok=True)
    (raiz / f"data/comentarios/{a.rede}_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.rede != "youtube":
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (raiz / "data/manifest").mkdir(parents=True, exist_ok=True)
        (raiz / f"data/manifest/apify_{a.rede}_comentarios_{stamp}.json").write_text(json.dumps(
            {"rede": a.rede, "etapa": ETAPA, "ator": ATOR[a.rede], **execucao, "lidos": len(lidos), "erros": erros,
             "run_id": resumo["run_id"], "gerado_em": agora}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{a.rede}: {len(lidos)} comentários lidos em {len(posts)} publicações do núcleo; custo US$ {execucao.get('custo_usd')}; "
          f"temas: {dict(Counter(k for c in todos for k in temas_de(c['texto'])))}; {len(erros)} erro(s)")
    return 0 if lidos else 1


if __name__ == "__main__":
    raise SystemExit(main())
