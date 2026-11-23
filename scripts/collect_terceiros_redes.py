#!/usr/bin/env python3
"""Quem falou delas no TikTok e no Instagram: publicações de OUTRAS contas que citam as influenciadoras, só no núcleo
(23/07 a 14/08/2026). Pago (Apify), com teto.

- TikTok: clockworks~tiktok-scraper, busca de vídeos com o nome de cada uma (searchQueries, seção /video), na ordem
  de relevância da própria busca, sem os filtros cobrados de data e ordem. Etapa do teto: "terceiros_transcricoes"
  (autorizada em 22/11/2026: "terceiros no TikTok"). O apidojo~tiktok-scraper, mais barato, devolveu só 10 itens nesta
  conta (run 45111607586).
- Instagram: apify~instagram-hashtag-scraper em modo de busca por palavra (keywordSearch) com o nome de cada uma.
  O ator não tem filtro de data: a busca devolve o que o Instagram mostra, e o núcleo é filtrado depois. Etapa do teto:
  "reserva" (pedido do responsável em 23/11/2026, 1h20, registrado em coleta.json).

Conta como item lido só a publicação que traz o nome ou o @ da influenciadora no texto (legenda, título ou
marcações) e não é da própria conta. O núcleo é filtrado pela data de cada publicação. A regra de homônimos é aplicada
depois, em build_terceiros.py.

Universo: nenhuma das duas buscas informa quantas publicações existem: ⛔. O manifesto registra quantos itens a busca
devolveu, quantos citam a influenciadora, o período que a leitura alcançou e quantos caem no núcleo.

Privacidade (CLAUDE.md, regra 10): texto e autor de terceiros vão SÓ para o repositório privado; sem ele, nada roda.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apify  # noqa: E402
from collect_apify_posts import g, gasto_etapa, inteiro, quando  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CONF = {
    # apidojo~tiktok-scraper devolveu só 10 itens nesta conta (limite do plano gratuito do ator; run 45111607586)
    "tiktok": {"ator": "clockworks~tiktok-scraper", "etapa": "terceiros_transcricoes", "cap": 0.7, "por_nome": 50},
    "instagram": {"ator": "apify~instagram-hashtag-scraper", "etapa": "reserva", "cap": 0.7, "por_nome": 60},
}
CAMPOS = ["chave", "ator_id", "post_id", "autor", "autor_seguidores", "publicado_em", "texto", "tipo_mencao", "url",
          "visualizacoes", "curtidas", "comentarios", "termo", "coletado_em"]


def pedido(rede: str, nomes: list[str], n: int, ator: str = "") -> dict:
    if rede == "tiktok" and ator.startswith("clockworks"):
        # sem os filtros cobrados de ordem e data: a ordem é a de relevância da própria busca
        return {"searchQueries": nomes, "searchSection": "/video", "resultsPerPage": n}
    if rede == "tiktok":
        return {"keywords": nomes, "sortType": "RELEVANCE", "dateRange": "LAST_SIX_MONTHS", "resultsPerPage": n,
                "maxItems": n * len(nomes)}
    return {"hashtags": nomes, "keywordSearch": True, "resultsType": "posts", "resultsLimit": n}


def normaliza(rede: str, x: dict) -> dict | None:
    if not isinstance(x, dict) or x.get("noResults") or x.get("error"):
        return None
    if rede == "tiktok":
        pid = g(x, "id")
        if not pid:
            return None
        # aceita os dois formatos: clockworks (authorMeta, text, createTimeISO) e apidojo (channel, title, uploadedAt)
        return {"post_id": str(pid), "autor": str(g(x, "authorMeta.name", "channel.username", "channel.name") or ""),
                "autor_seguidores": inteiro(g(x, "authorMeta.fans", "channel.followers")),
                "publicado_em": quando(g(x, "createTimeISO", "uploadedAtFormatted", "createTime", "uploadedAt")),
                "texto": " ".join(str(g(x, "text", "title") or "").split()), "url": g(x, "webVideoUrl", "postPage") or "",
                "visualizacoes": inteiro(g(x, "playCount", "views")), "curtidas": inteiro(g(x, "diggCount", "likes")),
                "comentarios": inteiro(g(x, "commentCount", "comments")),
                "marcados": [str(m.get("userUniqueId") or m.get("uniqueId") or "").lower() for m in (x.get("mentions") or []) if isinstance(m, dict)]
                            + [str(m).lower().lstrip("@") for m in (x.get("mentions") or []) if isinstance(m, str)],
                "termo": str(g(x, "searchQuery", "input", "inputSource") or "")}
    pid = g(x, "id", "shortCode")
    if not pid:
        return None
    return {"post_id": str(pid), "autor": str(g(x, "ownerUsername") or ""), "autor_seguidores": "",
            "publicado_em": quando(g(x, "timestamp")), "texto": " ".join(str(g(x, "caption") or "").split()),
            "url": g(x, "url") or (f"https://www.instagram.com/p/{x['shortCode']}/" if x.get("shortCode") else ""),
            "visualizacoes": inteiro(g(x, "videoViewCount", "videoPlayCount")), "curtidas": inteiro(g(x, "likesCount")),
            "comentarios": inteiro(g(x, "commentsCount")), "marcados": [str(m).lower().lstrip("@") for m in (x.get("mentions") or [])],
            "termo": str(g(x, "inputUrl", "searchTerm", "hashtag") or "")}


def _sem_acento(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def cita(item: dict, nome: str, handle: str) -> str | None:
    t = item["texto"].lower()
    arroba = f"@{handle.lower()}" in t or handle.lower() in item.get("marcados", [])
    por_nome = _sem_acento(nome) in _sem_acento(t)
    if arroba and por_nome:
        return "arroba e nome"
    return "arroba" if arroba else "nome" if por_nome else None


def separa(rede: str, itens: list, alvos: list[tuple], ini: str, fim: str, agora: str):
    proprios = {h.lower() for _, _, h in alvos}
    norm = [y for y in (normaliza(rede, x) for x in itens) if y]
    linhas, resumo = [], []
    for aid, nome, h in alvos:
        citam = [(y, cita(y, nome, h)) for y in norm]
        citam = [(y, t) for y, t in citam if t and y["autor"].lower() != h.lower()]
        datas = sorted(y["publicado_em"][:10] for y, _ in citam if y["publicado_em"])
        nucleo = [(y, t) for y, t in citam if ini <= y["publicado_em"][:10] <= fim]
        vistos = set()
        for y, t in nucleo:
            if y["post_id"] in vistos:
                continue
            vistos.add(y["post_id"])
            linhas.append({"chave": f"{aid}|{y['post_id']}", "ator_id": aid, **{k: y[k] for k in CAMPOS if k in y},
                           "tipo_mencao": t, "coletado_em": agora})
        resumo.append({"ator": aid, "termo": nome, "citam_a_influenciadora": len({y["post_id"] for y, _ in citam}),
                       "periodo_lido": [datas[0], datas[-1]] if datas else None, "no_nucleo": len(vistos),
                       "de_outras_do_estudo": sum(1 for y, _ in nucleo if y["autor"].lower() in proprios),
                       "por_tipo": dict(Counter(t for _, t in nucleo)), "universo": "⛔ a busca não informa o total",
                       "cobertura": ("a leitura alcançou o início do núcleo" if datas and datas[0] <= ini else
                                     "amostra: a leitura não chegou ao início do núcleo (a busca devolve o que a plataforma mostra)")})
    return linhas, resumo, len(norm)


def main(argv=None, raiz: Path = RAIZ, executar=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rede", choices=list(CONF), required=True)
    a = ap.parse_args(argv)
    cf = CONF[a.rede]
    coleta = json.loads((raiz / "data/config/coleta.json").read_text(encoding="utf-8"))["apify"]
    atores = json.loads((raiz / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    nuc = json.loads((raiz / "data/config/projeto.json").read_text(encoding="utf-8"))["janelas"]["nucleo"]
    ini, fim = nuc["inicio"][:10], nuc["fim"][:10]
    teto, gasto = float(coleta.get("etapas", {}).get(cf["etapa"], 0)), gasto_etapa(cf["etapa"], raiz)
    cap = round(min(teto - gasto, cf["cap"]), 4)
    if not coleta.get("autorizacao") or cap < 0.5:
        print(f"terceiros {a.rede}: resta US$ {round(teto - gasto, 4)} na etapa {cf['etapa']}, abaixo do mínimo de US$ 0,50 por execução: nada roda.")
        return 1
    interno = os.environ.get("INFL_INTERNO_DIR", "")
    if not interno or not Path(interno).is_dir():
        print(f"terceiros {a.rede}: repositório privado indisponível: nada roda (texto e autor de terceiros só vão para o privado).")
        return 1
    if executar is None:
        token = os.environ.get(coleta["segredo"], "").strip()
        if not token:
            print(f"terceiros {a.rede}: segredo ausente: nada roda.")
            return 1
        executar = lambda ator, p, c: apify.run_actor(token, ator, p, c)  # noqa: E731
    alvos = [(x["id"], x["nome"], x["perfis"][a.rede]["perfil"].lstrip("@")) for x in atores
             if x["perfis"].get(a.rede, {}).get("confirmado")]
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    erros, itens, custo, run_id = [], [], 0.0, None
    pl = pedido(a.rede, [n for _, n, _ in alvos], cf["por_nome"], cf["ator"])
    try:
        run, itens = executar(cf["ator"], pl, cap)
        custo, run_id = apify.custo_run(run), run.get("id")
    except apify.ErroDepoisDaExecucao as e:
        custo = apify.custo_run(e.run)
        erros.append(str(e))
    except Exception as e:  # noqa: BLE001
        erros.append(apify.erro_curto(e))
    d = Path(interno) / "data/terceiros"
    d.mkdir(parents=True, exist_ok=True)
    (Path(interno) / f"data/apify/{a.rede}").mkdir(parents=True, exist_ok=True)
    (Path(interno) / f"data/apify/{a.rede}/bruto_terceiros_{stamp}.json").write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
    linhas, resumo, validos = separa(a.rede, itens, alvos, ini, fim, agora)
    arq = d / f"{a.rede}_mencoes.csv"
    existentes = {}
    if arq.exists():
        with arq.open(encoding="utf-8", newline="") as f:
            existentes = {r["chave"]: r for r in csv.DictReader(f)}
    for l in linhas:
        existentes[l["chave"]] = l
    with arq.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(existentes.values(), key=lambda r: (r["ator_id"], r["publicado_em"])))
    man = {"rede": a.rede, "etapa": cf["etapa"], "tipo": "menções de terceiros", "ator": cf["ator"], "pedido": pl, "run_apify": run_id,
           "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "gerado_em": agora, "janela": "núcleo", "itens_recebidos": len(itens),
           "itens_validos": validos, "cap_por_execucao_usd": cap, "custo_usd": custo, "influenciadoras": resumo,
           "destino_texto_e_autor": f"repositório privado (data/terceiros/{a.rede}_mencoes.csv)", "erros": erros}
    (raiz / "data/manifest").mkdir(parents=True, exist_ok=True)
    txt = json.dumps(man, ensure_ascii=False, indent=1)
    (raiz / f"data/manifest/apify_{a.rede}_terceiros_{stamp}.json").write_text(txt, encoding="utf-8")
    (raiz / f"data/manifest/terceiros_{a.rede}_latest.json").write_text(txt, encoding="utf-8")
    print(f"terceiros {a.rede}: {len(itens)} itens recebidos ({validos} válidos); " +
          "; ".join(f"{r['ator']} citam {r['citam_a_influenciadora']}, núcleo {r['no_nucleo']}, período {r['periodo_lido']}" for r in resumo) +
          f"; {len(erros)} erro(s)")
    for e in erros[:3]:
        print("erro:", e)
    return 0 if not erros else 1


if __name__ == "__main__":
    raise SystemExit(main())
