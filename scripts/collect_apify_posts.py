#!/usr/bin/env python3
"""Posts das influenciadoras no Instagram e no TikTok, pela Apify (pago, com teto por etapa).

Uso: python scripts/collect_apify_posts.py --rede instagram|tiktok --etapa teste|posts

- Só perfis com "confirmado": true em data/config/atores.json.
- Teto: data/config/coleta.json -> apify.etapas[etapa]. O gasto já feito na etapa é a soma de
  custo_usd dos manifestos data/manifest/apify_*.json da mesma etapa; nada roda se o teto acabou.
  Cada execução leva maxTotalChargeUsd = (resto da etapa) / (execuções previstas).
- Sem consulta de saldo ou de limites da conta.
- etapa teste: os N itens mais recentes por perfil (N = itens_teste), só para validar campos e preço.
- etapa posts: tudo desde o início da linha de base (01/06/2026).
- Público: data/<rede>/posts.csv (só as publicações das próprias influenciadoras, sem dados de terceiros).
- Bruto da Apify: só no privado (INFL_INTERNO_DIR); sem ele, o bruto não é gravado.
- Universo: total de publicações que a plataforma informa para o perfil, quando o ator devolve;
  senão ⛔ (None). O custo fica só no manifesto e nunca vai à página.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apify  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CAMPOS = ["post_id", "ator_id", "rede", "perfil", "publicado_em", "janela", "tipo", "texto", "visualizacoes",
          "curtidas", "comentarios", "compartilhamentos", "url", "coletado_em"]


def g(d, *chaves):
    """Primeiro valor presente entre caminhos com ponto (a.b.c)."""
    for ch in chaves:
        v = d
        for parte in ch.split("."):
            v = v.get(parte) if isinstance(v, dict) else None
        if v not in (None, ""):
            return v
    return None


def inteiro(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return ""


def quando(v):
    """Data em UTC no formato AAAA-MM-DDTHH:MM:SSZ (aceita epoch em segundos ou ISO com fração e fuso)."""
    if v in (None, ""):
        return ""
    if isinstance(v, (int, float)) or str(v).isdigit():
        return datetime.fromtimestamp(int(v), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = str(v).strip().replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        try:  # formato do X: "Fri Jul 31 10:00:00 +0000 2026"
            d = datetime.strptime(str(v).strip(), "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            return str(v)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


TIPOS_IG = {"1": "imagem", "2": "vídeo", "8": "carrossel", "image": "imagem", "video": "vídeo",
            "sidecar": "carrossel", "graphimage": "imagem", "graphvideo": "vídeo", "graphsidecar": "carrossel"}


def carregar(nome):
    return json.loads((RAIZ / "data/config" / nome).read_text(encoding="utf-8"))


def gasto_etapa(etapa: str, raiz: Path = RAIZ) -> float:
    tot = 0.0
    for f in glob.glob(str(raiz / "data/manifest/apify_*.json")):
        m = json.loads(Path(f).read_text(encoding="utf-8"))
        if m.get("etapa") == etapa:
            tot += float(m.get("custo_usd") or 0)
    return round(tot, 4)


def pedido(rede, perfis, etapa, n, desde, ator="", ate=""):
    """Uma execução por rede com todos os perfis (a Apify exige teto mínimo de US$ 0,50 por execução)."""
    us = [p.lstrip("@") for p in perfis]
    if rede == "instagram":
        p = {"directUrls": [f"https://www.instagram.com/{u}/" for u in us], "resultsType": "posts", "resultsLimit": n,
             "selectedFields": ["shortCode", "id", "url", "timestamp", "caption", "title", "likesCount", "commentsCount",
                                "displayUrl", "ownerUsername", "videoDuration", "videoPlayCount", "type"]}
        if etapa != "teste":
            p["onlyPostsNewerThan"] = desde[:10]
        return p
    if rede == "x":
        until = (date.fromisoformat(ate[:10]) + timedelta(days=1)).isoformat() if ate else None  # until: é exclusivo no X
        # sem until: no run 45070655413 a busca com since+until antigos voltou vazia; o recorte é filtrado depois, pela data
        qs = [f"from:{u} since:{desde[:10]} -filter:retweets" for u in us]
        if etapa == "teste":
            qs = [f"from:{u} -filter:retweets" for u in us]
        return {"searchTerms": qs, "maxItems": n * len(us), "queryType": "Latest"}
    if ator.startswith("apidojo~"):
        p = {"usernames": us, "maxItems": n * len(us)}
        if etapa != "teste":
            p["since"] = desde[:10]
        return p
    p = {"profiles": us, "resultsPerPage": n, "profileSorting": "latest", "profileScrapeSections": ["videos"],
         "shouldDownloadVideos": False, "shouldDownloadCovers": False, "shouldDownloadSubtitles": False}
    if etapa != "teste":
        p["oldestPostDateUnified"] = desde[:10]
        if ate:
            p["newestPostDate"] = ate[:10]
    return p


def linha(rede, x, ator_id, perfil, janelas, agora):
    if rede == "instagram":
        pid = str(g(x, "shortCode", "id") or "")
        pub = quando(g(x, "timestamp"))
        url = g(x, "url") or f"https://www.instagram.com/p/{pid}/"
        texto = g(x, "caption") or ""
        tipo = TIPOS_IG.get(str(g(x, "type") or "").lower(), str(g(x, "type") or ""))
        views = inteiro(g(x, "videoPlayCount", "videoViewCount"))
        likes = inteiro(g(x, "likesCount"))
        coms, shares = inteiro(g(x, "commentsCount")), ""
    elif rede == "x":
        pid = str(g(x, "id", "id_str", "tweetId") or "")
        pub = quando(g(x, "createdAt", "created_at", "date"))
        url = g(x, "url", "twitterUrl") or ""
        texto = g(x, "fullText", "text") or ""
        tipo = ("resposta" if g(x, "isReply", "inReplyToId") else "citação" if g(x, "isQuote", "quotedTweet") else "post")
        views, likes = inteiro(g(x, "viewCount", "views")), inteiro(g(x, "likeCount", "favoriteCount"))
        coms = inteiro(g(x, "replyCount"))
        rt, qt = inteiro(g(x, "retweetCount")), inteiro(g(x, "quoteCount"))
        shares = "" if rt == "" and qt == "" else (rt or 0) + (qt or 0)
    else:
        pid = str(g(x, "id", "video.id", "awemeId") or "")
        pub = quando(g(x, "createTimeISO", "createTime", "uploadedAt", "create_time"))
        url = g(x, "webVideoUrl", "postPage", "url") or ""
        texto = g(x, "text", "title", "desc", "description") or ""
        tipo = "vídeo"
        views = inteiro(g(x, "playCount", "views", "stats.playCount"))
        likes = inteiro(g(x, "diggCount", "likes", "stats.diggCount"))
        coms = inteiro(g(x, "commentCount", "comments", "stats.commentCount"))
        shares = inteiro(g(x, "shareCount", "shares", "stats.shareCount"))
    base, nuc = janelas["base"], janelas["nucleo"]
    janela = ("nucleo" if nuc["inicio"] <= pub <= nuc["fim"] else
              "base" if base["inicio"] <= pub <= base["fim"] else "fora")
    return {"post_id": pid, "ator_id": ator_id, "rede": rede, "perfil": perfil, "publicado_em": pub, "janela": janela,
            "tipo": tipo, "texto": " ".join(str(texto).split()), "visualizacoes": views,
            "curtidas": likes if likes == "" or likes >= 0 else "",
            "comentarios": coms, "compartilhamentos": shares, "url": url, "coletado_em": agora}


def universo(rede, itens):
    """Total de publicações que a plataforma informa para o perfil, se o ator trouxer."""
    for x in itens:
        if rede == "x":
            for campo in ("author.statusesCount", "author.statuses_count"):
                v = g(x, campo)
                if v not in (None, ""):
                    return inteiro(v), f"{campo} (X: posts, respostas e reposts de toda a vida da conta)"
            continue
        if rede == "tiktok":
            for campo in ("authorMeta.video", "channel.videos", "author.videoCount", "authorStats.videoCount"):
                v = g(x, campo)
                if v not in (None, ""):
                    return inteiro(v), f"{campo} (TikTok)"
        else:
            v = g(x, "ownerPostsCount", "owner.postsCount")
            if v not in (None, ""):
                return inteiro(v), "postsCount do perfil (Instagram)"
    return None, None


def dono(rede, x):
    if not isinstance(x, dict) or x.get("error") or x.get("noResults"):
        return None
    if rede == "instagram":
        d = g(x, "ownerUsername")
    elif rede == "x":
        d = g(x, "author.userName", "author.username", "author.screen_name", "user.screen_name")
    else:
        d = g(x, "authorMeta.name", "channel.username", "author.uniqueId", "author.unique_id", "author.username")
    return str(d or "").lower() or None


def e_do_perfil(rede, x, perfil):
    return dono(rede, x) == perfil.lstrip("@").lower()


def gravar_merge(caminho, linhas):
    existentes = {}
    if caminho.exists():
        with caminho.open(encoding="utf-8", newline="") as f:
            existentes = {r["post_id"]: r for r in csv.DictReader(f)}
    novos = len({l["post_id"] for l in linhas} - set(existentes))
    for l in linhas:
        existentes[l["post_id"]] = l
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        for r in sorted(existentes.values(), key=lambda r: r.get("publicado_em", "")):
            w.writerow(r)
    return novos, len(existentes)


def main(argv=None, executar=None, raiz=RAIZ):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rede", required=True, choices=["instagram", "tiktok", "x"])
    ap.add_argument("--etapa", required=True, choices=["teste", "posts"])
    ap.add_argument("--ator", default="", help="força outro ator (ex.: teste comparativo)")
    a = ap.parse_args(argv)

    coleta, atores, projeto = carregar("coleta.json"), carregar("atores.json"), carregar("projeto.json")
    cfg_apify, cfg_rede = coleta["apify"], dict(coleta["redes"][a.rede])
    if a.ator:
        cfg_rede["ator"] = a.ator
    teto = float(cfg_apify.get("etapas", {}).get(a.etapa, 0))
    if not cfg_apify.get("autorizacao") or teto <= 0:
        print(f"{a.rede}: etapa {a.etapa} sem teto autorizado em coleta.json: nada roda.")
        return 1
    token = os.environ.get(cfg_apify["segredo"], "").strip()
    if executar is None and not token:
        print(f"{a.rede}: segredo {cfg_apify['segredo']} ausente: nada roda.")
        return 1
    executar = executar or (lambda ator, p, cap: apify.run_actor(token, ator, p, cap))

    perfis = [(at["id"], at["perfis"][a.rede]["perfil"]) for at in atores["atores"]
              if at["perfis"].get(a.rede, {}).get("confirmado")]
    gasto = gasto_etapa(a.etapa, raiz)
    resto = round(teto - gasto, 4)
    # a etapa de teste é dividida entre as duas redes
    # a etapa de teste não tem divisão fixa entre redes: vale o que resta, até US$ 0,50 por execução
    orcamento_rede = round(min(resto, 0.5) if a.etapa == "teste" else resto, 4)
    print(f"{a.rede}: etapa {a.etapa}, teto {teto}, já gasto {gasto}, para esta rede até {orcamento_rede}")
    if orcamento_rede <= 0.01 or not perfis:
        print(f"{a.rede}: sem orçamento restante na etapa ou sem perfis confirmados: nada roda.")
        return 1
    cap = orcamento_rede
    if cap < 0.5:
        print(f"{a.rede}: restam US$ {cap} na etapa, abaixo do mínimo de US$ 0,50 por execução da Apify: nada roda.")
        return 1
    n = cfg_rede.get("itens_teste", 15) if a.etapa == "teste" else cfg_rede.get("max_itens_por_perfil", 1000)
    desde = projeto["janelas"]["base"]["inicio"]
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    linhas, por_perfil, brutos, custo, erros = [], [], {}, 0.0, []
    run_id = None
    try:
        run, itens = executar(cfg_rede["ator"], pedido(a.rede, [p for _, p in perfis], a.etapa, n, desde, cfg_rede["ator"], projeto["janelas"]["nucleo"]["fim"]), cap)
        custo = apify.custo_run(run)
        run_id = run.get("id")
    except apify.ErroDepoisDaExecucao as e:
        custo, itens = apify.custo_run(e.run), []
        erros.append(str(e))
    except Exception as e:  # noqa: BLE001
        itens = []
        erros.append(apify.erro_curto(e))
    brutos = itens
    bateu_teto = custo >= cap * 0.95
    for ator_id, perfil in perfis:
        meus = [x for x in itens if e_do_perfil(a.rede, x, perfil)]
        ls = [linha(a.rede, x, ator_id, perfil, projeto["janelas"], agora) for x in meus]
        ls = [l for l in ls if l["post_id"]]
        linhas += [l for l in ls if a.etapa == "teste" or l["janela"] != "fora"]
        uni, fonte = universo(a.rede, meus)
        datas = sorted(l["publicado_em"] for l in ls if l["publicado_em"])
        por_perfil.append({
            "ator": ator_id, "perfil": perfil, "lidos": len(ls),
            "universo": uni, "universo_fonte": fonte or "⛔ não informado pelo ator",
            "mais_antigo": datas[0] if datas else None, "mais_recente": datas[-1] if datas else None,
            "na_base": sum(1 for l in ls if l["janela"] == "base"), "no_nucleo": sum(1 for l in ls if l["janela"] == "nucleo"),
            "cobertura": ("amostra de teste (mais recentes)" if a.etapa == "teste" else
                          "parcial ⛔ (execução parou no teto de gasto)" if bateu_teto else
                          "completa (parou pela data inicial)" if len(ls) < n else "parcial ⛔ (parou no limite de itens)"),
        })
    outros = sum(1 for x in itens if dono(a.rede, x) not in {p.lstrip("@").lower() for _, p in perfis})
    if outros:
        erros.append(f"{outros} item(ns) de outro perfil ou sem dono identificado, fora do acervo")

    novos, total = gravar_merge(raiz / f"data/{a.rede}/posts.csv", linhas)
    interno = os.environ.get("INFL_INTERNO_DIR", "")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if interno and Path(interno).is_dir():
        d = Path(interno) / f"data/apify/{a.rede}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"bruto_{a.etapa}_{stamp}.json").write_text(json.dumps(brutos, ensure_ascii=False), encoding="utf-8")
        destino = "repositório privado"
    else:
        destino = "não gravado (privado indisponível)"
    manifesto = {"rede": a.rede, "etapa": a.etapa, "ator": cfg_rede["ator"], "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
                 "gerado_em": agora, "run_apify": run_id, "itens_recebidos": len(itens), "teto_etapa_usd": teto, "gasto_antes_usd": gasto, "cap_por_execucao_usd": cap,
                 "custo_usd": round(custo, 4), "perfis": por_perfil, "bruto": destino,
                 "posts_gravados": {"novos": novos, "total_no_acervo": total}, "erros": erros}
    (raiz / "data/manifest").mkdir(parents=True, exist_ok=True)
    txt = json.dumps(manifesto, ensure_ascii=False, indent=1)
    (raiz / f"data/manifest/apify_{a.rede}_{a.etapa}_{cfg_rede['ator'].split('~')[0]}_{stamp}.json").write_text(txt, encoding="utf-8")
    (raiz / f"data/manifest/{a.rede}_latest.json").write_text(txt, encoding="utf-8")
    ok = sum(1 for p in por_perfil if p.get("lidos"))
    print(f"{a.rede}: {ok} de {len(perfis)} perfis com posts; {novos} novos ({total} no acervo); custo US$ {round(custo, 4)}; {len(erros)} erro(s)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
