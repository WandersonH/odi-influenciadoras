#!/usr/bin/env python3
"""IRaMuTeQ das matérias da imprensa (caderno 07): corpus, CHD de Reinert e similitude, como o corpus das influenciadoras.

Texto de cada matéria = título + texto completo extraído (collect_imprensa_texto.py), só as de status "ok"
(600 caracteres ou mais). As demais (paywall, vídeo, link não convertido) ficam fora e são contadas no JSON.
Variáveis: *veic_<veículo> e *recorte_<dia|nucleo> ("dia" = apareceu nas buscas de 30/07 a 02/08; "nucleo" = só
no restante do núcleo, 23/07 a 14/08). Segmentos de ~40 palavras; CHD (scripts/chd_reinert.py: lematização
pelo dicionário do IRaMuTeQ, classe mínima de 5%, χ² ≥ 3,84) e similitude (scripts/similitude.py), com o recorte como variável de cor.

Privacidade e direito autoral: o corpus e os segmentos característicos (trechos das matérias) ficam só no privado.
No público vão as formas, as classes, as variáveis, a árvore da similitude e as contagens.
Saídas: privado data/corpus/imprensa_iramuteq.txt e data/corpus/imprensa_segmentos.json;
público data/corpus/imprensa_chd.json e data/corpus/imprensa_similitude.gexf.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chd_reinert as cr  # noqa: E402
from build_corpus import segmentar, PALAVRAS_SEGMENTO  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)


def var(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s) or "x"


def textos(linhas: list[dict]) -> tuple[list[dict], dict]:
    ts, fora = [], {}
    for r in linhas:
        if r.get("status") != "ok":
            fora[r.get("status") or "?"] = fora.get(r.get("status") or "?", 0) + 1
            continue
        corpo = re.sub(r"\s+", " ", f"{r['titulo']}. {r['texto']}").strip()
        ts.append({"veiculo": r["veiculo"], "recorte": "dia" if "dia do anúncio" in r["recortes"] else "nucleo",
                   "titulo": r["titulo"], "url": r["url"], "texto": corpo})
    return ts, fora


def main(root: Path = RAIZ) -> int:
    interno = os.environ.get("INFL_INTERNO_DIR", "").strip()
    fonte = Path(interno) / "data/imprensa/textos.csv" if interno else None
    if not fonte or not fonte.exists():
        print("⛔ textos das matérias indisponíveis (privado): rode collect_imprensa_texto.py")
        return 1
    linhas = list(csv.DictReader(fonte.open(encoding="utf-8")))
    ts, fora = textos(linhas)
    if len(ts) < 10:
        print(f"⛔ só {len(ts)} matérias com texto: corpus pequeno demais para a CHD")
        return 1
    dp = Path(interno) / "data/corpus"
    dp.mkdir(parents=True, exist_ok=True)
    with (dp / "imprensa_iramuteq.txt").open("w", encoding="utf-8") as f:
        for t in sorted(ts, key=lambda t: (t["recorte"], t["veiculo"])):
            f.write(f"**** *veic_{var(t['veiculo'])} *recorte_{t['recorte']}\n{t['texto']}\n\n")
    segs = [{"veiculo": t["veiculo"], "recorte": t["recorte"], "url": t["url"], "texto": s} for t in ts for s in segmentar(t["texto"])]
    X, voc = cr.matriz([s["texto"] for s in segs])
    n_ativos = int((X.sum(1) > 0).sum())
    mc = max(cr.MIN_CLASSE, int(cr.MIN_CLASSE_PCT * n_ativos))
    rot, arvore, escolha_k = cr.chd_iramuteq(X, min_classe=mc, n_textos=len(ts))
    cl = rot > 0
    n = int(cl.sum())
    Xc, rc = X[cl], rot[cl]
    tot = Xc.sum(0)
    veic = sorted({s["veiculo"] for s in segs})
    veic_arr = np.array([s["veiculo"] for s in segs])[cl]
    rec_arr = np.array([s["recorte"] for s in segs])[cl]
    classes, privados = [], []
    for k in sorted(set(rc.tolist())):
        m = rc == k
        nk = int(m.sum())
        ch = cr.chi2_assoc(Xc[m].sum(0), tot, nk, n)
        formas = [[voc[j], round(float(ch[j]), 1), int(Xc[m][:, j].sum())] for j in np.argsort(-ch)[:25] if ch[j] >= cr.CHI_CRIT]
        variaveis = {}
        for nome, arr, mods in (("veiculo", veic_arr, veic), ("recorte", rec_arr, ["dia", "nucleo"])):
            for c in mods:
                em = arr == c
                vch = cr.chi2_assoc(np.array([float((em & m).sum())]), np.array([float(em.sum())]), nk, n)[0]
                variaveis[f"{nome}:{c}"] = {"segmentos": int((em & m).sum()), "pct_da_classe": round(100 * (em & m).sum() / nk, 1),
                                            "chi2": round(float(vch), 1)}
        idx = np.where(cl)[0][m]
        peso = {j: ch[j] for j in range(len(voc)) if ch[j] > 0}
        score = sorted(((sum(peso.get(j, 0) for j in np.nonzero(X[i])[0]), i) for i in idx), reverse=True)[:5]
        privados.append({"classe": k, "segmentos_caracteristicos": [{"veiculo": segs[i]["veiculo"], "url": segs[i]["url"],
                                                                    "texto": segs[i]["texto"][:300]} for _, i in score]})
        classes.append({"classe": k, "segmentos": nk, "pct": round(100 * nk / max(1, n), 1), "formas": formas, "variaveis": variaveis,
                        "veiculos_dos_segmentos_caracteristicos": [segs[i]["veiculo"] for _, i in score], "nome": None})
    out = {"gerado_em_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
           "metodo": (f"CHD de Reinert (implementação em Python/numpy): até {cr.K} classes, formas com {cr.MIN_FREQ}+ segmentos, "
                      f"classe mínima de {int(cr.MIN_CLASSE_PCT * 100)}% dos segmentos, formas características com χ² ≥ {cr.CHI_CRIT} (p < 0,05). "
                      f"Segmentos de ~{PALAVRAS_SEGMENTO} palavras de título + texto completo das matérias. Os nomes das classes são dados pelo pesquisador. "
                      "O corpus e os trechos ficam no repositório privado (texto de terceiros, com direito autoral); conferir no IRaMuTeQ com o arquivo de lá."),
           "universo": "⛔ o Google Notícias não informa o total; base = matérias distintas entre os 10 primeiros por termo do tema",
           "materias_lidas": len(linhas), "textos": len(ts), "fora_do_corpus": fora,
           "textos_por_recorte": {r: sum(1 for t in ts if t["recorte"] == r) for r in ("dia", "nucleo")},
           "veiculos": len({t["veiculo"] for t in ts}),
           "lematizacao": cr.lematizacao(), "escolha_classes": escolha_k, "segmentos_total": len(segs), "segmentos_classificados": n,
           "pct_classificados": round(100 * n / max(1, len(segs)), 1), "formas_ativas": len(voc),
           "aproveitamento": cr.aproveitamento(rot, len(segs)), "arvore": arvore, "classes": classes}
    d = root / "data/corpus"
    d.mkdir(parents=True, exist_ok=True)
    try:
        import similitude as sim
        res = sim.ads(X, voc, [s["recorte"] for s in segs])
        if res:
            out["similitude"] = res
            sim.gexf(res, d / "imprensa_similitude.gexf")
    except Exception as e:  # noqa: BLE001
        out["similitude"] = {"erro": f"{type(e).__name__}: {str(e)[:160]}"}
    (d / "imprensa_chd.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (dp / "imprensa_segmentos.json").write_text(json.dumps(privados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"corpus da imprensa: {len(ts)} matérias de {out['veiculos']} veículos (fora: {fora}), {len(segs)} segmentos, "
          f"{n} classificados ({out['pct_classificados']}%), {len(voc)} formas, {len(classes)} classes")
    for c in classes:
        top = sorted(((v["chi2"], k) for k, v in c["variaveis"].items()), reverse=True)[:2]
        print(f"  classe {c['classe']} ({c['pct']}%): " + ", ".join(f[0] for f in c["formas"][:10]) + " | " + " ".join(f"{k} χ²{v}" for v, k in top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
