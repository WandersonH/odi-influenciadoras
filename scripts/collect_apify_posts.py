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
from datetime import datetime, timezone
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
    if v in (None, ""):
        return ""
    if isinstance(v, (int, float)) or str(v).isdigit():
        return datetime.fromtimestamp(int(v), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = str(v).replace("+00:00", "Z")
    return s[:19] + "Z" if len(s) >= 19 and not s.endswith("Z") else s[:20] if s.endswith("Z") else s


def carregar(nome):
    return json.loads((RAIZ / "data/config" / nome).read_text(encoding="utf-8"))


def gasto_etapa(etapa: str, raiz: Path = RAIZ) -> float:
    tot = 0.0
    for f in glob.glob(str(raiz / "data/manifest/apify_*.json")):
        m = json.loads(Path(f).read_text(encoding="utf-8"))
        if m.get("etapa") == etapa:
            tot += float(m.get("custo_usd") or 0)
    return round(tot, 4)


def pedido(rede, perfis, etapa, n, desde):
    """Uma execução por rede com todos os perfis (a Apify exige teto mínimo de US$ 0,50 por execução)."""
    us = [p.lstrip("@") for p in perfis]
    if rede == "instagram":
        p = {"directUrls": [f"https://www.instagram.com/{u}/" for u in us], "resultsType": "posts", "resultsLimit": n,
             "selectedFields": ["shortCode", "id", "url", "timestamp", "caption", "title", "likesCount", "commentsCount",
                                "displayUrl", "ownerUsername", "videoDuration", "videoPlayCount", "type"]}
        if etapa != "teste":
            p["onlyPostsNewerThan"] = desde[:10]
        return p
    p = {"profiles": us, "resultsPerPage": n, "profileSorting": "latest", "profileScrapeSections": ["videos"],
         "shouldDownloadVideos": False, "shouldDownloadCovers": False, "shouldDownloadSubtitles": False}
    if etapa != "teste":
        p["oldestPostDateUnified"] = desde[:10]
    return p


def linha(rede, x, ator_id, perfil, janelas, agora):
    if rede == "instagram":
        pid = str(g(x, "shortCode", "id") or "")
        pub = quando(g(x, "timestamp"))
        url = g(x, "url") or f"https://www.instagram.com/p/{pid}/"
        texto = g(x, "caption") or ""
        tipo = str(g(x, "type") or "")
        views = inteiro(g(x, "videoPlayCount", "videoViewCount"))
        likes = inteiro(g(x, "likesCount"))
        coms, shares = inteiro(g(x, "commentsCount")), ""
    else:
        pid = str(g(x, "id") or "")
        pub = quando(g(x, "createTimeISO", "createTime"))
        url = g(x, "webVideoUrl") or ""
        texto = g(x, "text") or ""
        tipo = "vídeo"
        views, likes = inteiro(g(x, "playCount")), inteiro(g(x, "diggCount"))
        coms, shares = inteiro(g(x, "commentCount")), inteiro(g(x, "shareCount"))
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
        v = g(x, "authorMeta.video") if rede == "tiktok" else g(x, "ownerPostsCount", "owner.postsCount")
        if v not in (None, ""):
            return inteiro(v), ("authorMeta.video (TikTok)" if rede == "tiktok" else "postsCount do perfil (Instagram)")
    return None, None


def dono(rede, x):
    if not isinstance(x, dict) or x.get("error"):
        return None
    return str((g(x, "ownerUsername") if rede == "instagram" else g(x, "authorMeta.name")) or "").lower() or None


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
    ap.add_argument("--rede", required=True, choices=["instagram", "tiktok"])
    ap.add_argument("--etapa", required=True, choices=["teste", "posts"])
    a = ap.parse_args(argv)

    coleta, atores, projeto = carregar("coleta.json"), carregar("atores.json"), carregar("projeto.json")
    cfg_apify, cfg_rede = coleta["apify"], coleta["redes"][a.rede]
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
    redes_na_etapa = 2 if a.etapa == "teste" else 1
    orcamento_rede = round(min(resto, teto / redes_na_etapa), 4)
    print(f"{a.rede}: etapa {a.etapa}, teto {teto}, já gasto {gasto}, para esta rede até {orcamento_rede}")
    if orcamento_rede <= 0.01 or not perfis:
        print(f"{a.rede}: sem orçamento restante na etapa ou sem perfis confirmados: nada roda.")
        return 1
    cap = orcamento_rede
    if cap < 0.5:
        print(f"{a.rede}: restam US$ {cap} na etapa, abaixo do mínimo de US$ 0,50 por execução da Apify: nada roda.")
        return 1
    n = cfg_rede.get("itens_teste", 15) if a.etapa == "teste" else 1000
    desde = projeto["janelas"]["base"]["inicio"]
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    linhas, por_perfil, brutos, custo, erros = [], [], {}, 0.0, []
    run_id = None
    try:
        run, itens = executar(cfg_rede["ator"], pedido(a.rede, [p for _, p in perfis], a.etapa, n, desde), cap)
        custo = apify.custo_run(run)
        run_id = run.get("id")
    except apify.ErroDepoisDaExecucao as e:
        custo, itens = apify.custo_run(e.run), []
        erros.append(str(e))
    except Exception as e:  # noqa: BLE001
        itens = []
        erros.append(apify.erro_curto(e))
    brutos = itens
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
                          "completa (parou pela data inicial)" if datas and len(ls) < n else "parcial ⛔ (parou no limite)"),
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
    (raiz / f"data/manifest/apify_{a.rede}_{a.etapa}_{stamp}.json").write_text(txt, encoding="utf-8")
    (raiz / f"data/manifest/{a.rede}_latest.json").write_text(txt, encoding="utf-8")
    ok = sum(1 for p in por_perfil if p.get("lidos"))
    print(f"{a.rede}: {ok} de {len(perfis)} perfis com posts; {novos} novos ({total} no acervo); custo US$ {round(custo, 4)}; {len(erros)} erro(s)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
