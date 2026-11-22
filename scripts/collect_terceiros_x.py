#!/usr/bin/env python3
"""Citações das influenciadoras por OUTRAS contas no X, só no núcleo (23/07 a 14/08/2026). Pago (Apify), com teto.

Uma busca do próprio X por influenciadora, com o nome entre aspas OU o @, excluindo a própria conta e reposts:
  ("Mariam Chami" OR @eumariamchami) -from:eumariamchami since:2026-07-23 until:2026-08-15 -filter:retweets
Ator: xquik~x-tweet-scraper (o mesmo dos posts). Etapa do teto: "terceiros_transcricoes".

Universo: o X não informa quantos posts existem para a busca: ⛔. O manifesto registra quanto foi lido e se a leitura
parou no limite de itens (amostra) ou antes dele.

Privacidade (CLAUDE.md, regra 10): texto e autor de terceiros vão SÓ para o repositório privado (INFL_INTERNO_DIR);
sem ele, nada de terceiros é gravado. Ao público vão só contagens por influenciadora, por dia e por tipo de menção.
Cada menção por nome ainda precisa de revisão de homônimos (regra 12); a menção pelo @ é inequívoca.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apify  # noqa: E402
from collect_apify_posts import g, gasto_etapa, inteiro, quando  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ATOR = "xquik~x-tweet-scraper"
ETAPA = "terceiros_transcricoes"
CAMPOS = ["chave", "ator_id", "post_id", "autor", "autor_seguidores", "publicado_em", "texto", "tipo_mencao", "url",
          "visualizacoes", "curtidas", "respostas", "reposts", "coletado_em"]


def consulta(nome: str, handle: str, inicio: str = "", fim: str = "") -> list[str]:
    """Duas buscas por influenciadora, sem OR e sem datas: com OR e/ou com datas a busca do ator voltou quase vazia
    (runs 45070739356 e 45071871689: 2 itens). O núcleo é filtrado depois, pela data de cada post."""
    return [f'"{nome}" -from:{handle} -filter:retweets', f"@{handle} -from:{handle} -filter:retweets"]


def tipo_mencao(texto: str, nome: str, handle: str) -> str:
    t = (texto or "").lower()
    por_arroba = f"@{handle.lower()}" in t
    por_nome = nome.lower() in t
    return "arroba e nome" if por_arroba and por_nome else "arroba" if por_arroba else "nome" if por_nome else "outra (resposta ou marcação)"


def main(argv=None, raiz: Path = RAIZ, executar=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ator", default=ATOR, help="xquik~x-tweet-scraper (padrão) ou apidojo~tweet-scraper (busca histórica com since:/until: na própria busca)")
    ap.add_argument("--com-datas", action="store_true", help="período do núcleo nos campos since/until do ator")
    ap.add_argument("--max-por-influenciadora", type=int, default=600, help="itens por busca (2 buscas por influenciadora)")
    a = ap.parse_args(argv)
    coleta = json.loads((raiz / "data/config/coleta.json").read_text(encoding="utf-8"))["apify"]
    atores = json.loads((raiz / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    nuc = json.loads((raiz / "data/config/projeto.json").read_text(encoding="utf-8"))["janelas"]["nucleo"]
    teto, gasto = float(coleta.get("etapas", {}).get(ETAPA, 0)), gasto_etapa(ETAPA, raiz)
    cap = round(min(teto - gasto, 0.5), 4)
    if not coleta.get("autorizacao") or cap < 0.5:
        print(f"terceiros X: resta US$ {round(teto - gasto, 4)} na etapa {ETAPA}, abaixo do mínimo de US$ 0,50 por execução: nada roda.")
        return 1
    interno = os.environ.get("INFL_INTERNO_DIR", "")
    if not interno or not Path(interno).is_dir():
        print("terceiros X: repositório privado indisponível: nada roda (texto e autor de terceiros só podem ir para o privado).")
        return 1
    token = os.environ.get(coleta["segredo"], "").strip()
    if executar is None:
        if not token:
            print("terceiros X: segredo ausente: nada roda.")
            return 1
        executar = lambda ator, p, c: apify.run_actor(token, ator, p, c)  # noqa: E731
    alvos = [(x["id"], x["nome"], x["perfis"]["x"]["perfil"]) for x in atores if x["perfis"].get("x", {}).get("confirmado")]
    qs = {aid: consulta(nome, h) for aid, nome, h in alvos}
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    erros, itens, custo, run_id = [], [], 0.0, None
    try:
        termos = [q for v in qs.values() for q in v]
        if a.ator.startswith("apidojo~"):
            until = (date.fromisoformat(nuc["fim"][:10]) + timedelta(days=1)).isoformat()
            termos = [f"{q} since:{nuc['inicio'][:10]} until:{until}" for q in termos]
        pedido = {"searchTerms": termos, "maxItems": a.max_por_influenciadora * len(termos),
                  "maxItemsPerTarget": a.max_por_influenciadora, "queryType": "Latest"}
        if a.ator.startswith("apidojo~"):
            pedido = {"searchTerms": termos, "maxItems": a.max_por_influenciadora * len(alvos), "sort": "Latest"}
        elif a.com_datas:  # período nos campos do ator, buscas separadas (sem OR)
            pedido["since"] = nuc["inicio"][:10]
            pedido["until"] = (date.fromisoformat(nuc["fim"][:10]) + timedelta(days=1)).isoformat()
        run, itens = executar(a.ator, pedido, cap)
        custo, run_id = apify.custo_run(run), run.get("id")
    except apify.ErroDepoisDaExecucao as e:
        custo = apify.custo_run(e.run)
        erros.append(str(e))
    except Exception as e:  # noqa: BLE001
        erros.append(apify.erro_curto(e))
    linhas, resumo = [], []
    proprios = {h.lower() for _, _, h in alvos}
    for aid, nome, h in alvos:
        meus = []
        for x in itens:
            if not isinstance(x, dict) or x.get("noResults") or not g(x, "id"):
                continue
            autor = str(g(x, "author.userName", "author.username") or "")
            txt = " ".join(str(g(x, "fullText", "text") or "").split())
            if autor.lower() in proprios and autor.lower() == h.lower():
                continue
            if nome.lower() not in txt.lower() and f"@{h.lower()}" not in txt.lower():
                continue
            pub = quando(g(x, "createdAt"))
            if not (nuc["inicio"][:10] <= pub[:10] <= nuc["fim"][:10]):
                continue
            meus.append({"chave": f"{aid}|{g(x, 'id')}", "ator_id": aid, "post_id": str(g(x, "id")), "autor": autor,
                         "autor_seguidores": inteiro(g(x, "author.followers")), "publicado_em": pub, "texto": txt,
                         "tipo_mencao": tipo_mencao(txt, nome, h), "url": g(x, "url", "twitterUrl") or "",
                         "visualizacoes": inteiro(g(x, "viewCount")), "curtidas": inteiro(g(x, "likeCount")),
                         "respostas": inteiro(g(x, "replyCount")), "reposts": inteiro(g(x, "retweetCount")), "coletado_em": agora})
        linhas += meus
        datas_lidas = sorted(quando(g(x, "createdAt"))[:10] for x in itens if isinstance(x, dict) and (nome.lower() in str(g(x, "fullText", "text") or "").lower() or f"@{h.lower()}" in str(g(x, "fullText", "text") or "").lower()))
        resumo.append({"ator": aid, "consulta": qs[aid], "lidos": len(meus), "periodo_lido": [datas_lidas[0], datas_lidas[-1]] if datas_lidas else None, "universo": "⛔ o X não informa o total da busca",
                       "por_tipo": dict(Counter(m["tipo_mencao"] for m in meus)),
                       "por_dia": dict(sorted(Counter(m["publicado_em"][:10] for m in meus).items())),
                       "autores_distintos": len({m["autor"].lower() for m in meus}),
                       "visualizacoes_somadas": sum(m["visualizacoes"] or 0 for m in meus),
                       "revisao_homonimos": "pendente (menções só por nome)" if any(m["tipo_mencao"] == "nome" for m in meus) else "não se aplica (todas pelo @)",
                       "itens_lidos_antes_do_filtro_de_data": sum(1 for x in itens if isinstance(x, dict) and (nome.lower() in str(g(x, "fullText", "text") or "").lower() or f"@{h.lower()}" in str(g(x, "fullText", "text") or "").lower())),
                       "cobertura": "verificar: a leitura vai do mais recente para trás e pode não alcançar o núcleo antes do limite" })
    d = Path(interno) / "data/terceiros"
    d.mkdir(parents=True, exist_ok=True)
    arq = d / "x_mencoes.csv"
    existentes = {}
    if arq.exists():
        with arq.open(encoding="utf-8", newline="") as f:
            existentes = {r["chave"]: r for r in csv.DictReader(f)}
    for l in linhas:
        existentes[l["chave"]] = l
    with arq.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(sorted(existentes.values(), key=lambda r: (r["ator_id"], r["publicado_em"])))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    man = {"rede": "x", "etapa": ETAPA, "tipo": "menções de terceiros", "ator": a.ator, "run_apify": run_id,
           "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "gerado_em": agora, "janela": "núcleo",
           "itens_recebidos": len(itens), "cap_por_execucao_usd": cap, "custo_usd": custo, "influenciadoras": resumo,
           "destino_texto_e_autor": "repositório privado (data/terceiros/x_mencoes.csv)", "erros": erros}
    (raiz / "data/manifest").mkdir(parents=True, exist_ok=True)
    txt = json.dumps(man, ensure_ascii=False, indent=1)
    (raiz / f"data/manifest/apify_x_terceiros_{stamp}.json").write_text(txt, encoding="utf-8")
    (raiz / "data/manifest/terceiros_x_latest.json").write_text(txt, encoding="utf-8")
    print(f"terceiros X: {len(itens)} itens recebidos; " + "; ".join(f"{r['ator']} {r['lidos']}" for r in resumo) + f"; custo US$ {custo}; {len(erros)} erro(s)")
    return 0 if not erros else 1


if __name__ == "__main__":
    raise SystemExit(main())
