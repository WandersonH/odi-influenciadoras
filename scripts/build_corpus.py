#!/usr/bin/env python3
"""Corpus para o IRaMuTeQ, CHD de Reinert e análise de similitude (seção 8.3 do plano).

Texto de cada publicação do recorte (01/06 a 14/08/2026) = legenda + fala transcrita (quando houver), das quatro
influenciadoras, nas redes coletadas. Publicação sem texto nenhum fica fora (contada no JSON).

1. Corpus no formato do IRaMuTeQ (data/corpus/influenciadoras_iramuteq.txt): uma linha de cabeçalho por texto,
   "**** *infl_<id> *rede_<rede> *janela_<base|nucleo> *fala_<sim|nao>", seguida do texto. Risadas normalizadas.
2. Segmentos de texto de cerca de 40 palavras (o padrão do IRaMuTeQ), com a influenciadora como variável.
3. CHD de Reinert (scripts/chd_reinert.py, lematização pelo dicionário do IRaMuTeQ, classe mínima de
   5%, χ² ≥ 3,84) e similitude (scripts/similitude.py), com a influenciadora como variável.
   A implementação aproxima o IRaMuTeQ; os nomes das classes são dados pelo pesquisador; conferir no IRaMuTeQ com o arquivo 1.
Saídas: data/corpus/influenciadoras_iramuteq.txt, data/corpus/chd.json, data/corpus/similitude.gexf.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chd_reinert as cr  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
FONTES = {"youtube": ("data/youtube/videos.csv", "video_id"), "instagram": ("data/instagram/posts.csv", "post_id"),
          "tiktok": ("data/tiktok/posts.csv", "post_id"), "x": ("data/x/posts.csv", "post_id")}
PALAVRAS_SEGMENTO = 40
URL = re.compile(r"https?://\S+|www\.\S+")


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def limpar(t: str) -> str:
    t = cr.normalizar_risadas(URL.sub(" ", t or ""))
    t = t.replace("*", " ").replace("$", " ")  # caracteres reservados do formato do IRaMuTeQ
    return " ".join(t.split())


def segmentar(texto: str, n: int = PALAVRAS_SEGMENTO) -> list[str]:
    """Corta em frases e junta frases até ~n palavras (como o IRaMuTeQ faz com o tamanho de segmento padrão)."""
    frases = [f.strip() for f in re.split(r"(?<=[.!?])\s+", texto) if f.strip()]
    segs, atual = [], []
    for f in frases:
        ws = f.split()
        while len(ws) > n * 1.5:  # frase longa sem pontuação (comum em transcrição): corta em blocos de n
            if atual:
                segs.append(" ".join(atual))
                atual = []
            segs.append(" ".join(ws[:n]))
            ws = ws[n:]
        atual += ws
        if len(atual) >= n:
            segs.append(" ".join(atual))
            atual = []
    if atual:
        segs.append(" ".join(atual))
    return segs


def textos(root: Path) -> tuple[list[dict], int]:
    out, vazios = [], 0
    for rede, (arq, chave) in FONTES.items():
        fala = {r["post_id"]: r["texto"] for r in ler(root / f"data/transcricoes/{rede}.csv") if r.get("status") == "ok"}
        for r in ler(root / arq):
            if r.get("janela") not in ("base", "nucleo"):
                continue
            pid = r[chave]
            t = limpar(" ".join(x for x in (r.get("texto") or r.get("titulo") or "", fala.get(pid, "")) if x))
            if len(t.split()) < 3:
                vazios += 1
                continue
            out.append({"post_id": pid, "rede": rede, "ator_id": r["ator_id"], "janela": r["janela"], "fala": pid in fala,
                        "publicado_em": r["publicado_em"], "url": r["url"], "texto": t})
    return out, vazios


def main(root: Path = RAIZ) -> int:
    ts, vazios = textos(root)
    if not ts:
        print("⛔ corpus vazio")
        return 1
    d = root / "data/corpus"
    d.mkdir(parents=True, exist_ok=True)
    var = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa: E731
    with (d / "influenciadoras_iramuteq.txt").open("w", encoding="utf-8") as f:
        for t in sorted(ts, key=lambda t: (t["ator_id"], t["publicado_em"])):
            f.write(f"**** *infl_{var(t['ator_id'])} *rede_{t['rede']} *janela_{t['janela']} *fala_{'sim' if t['fala'] else 'nao'}\n{t['texto']}\n\n")
    segs = [{"post_id": t["post_id"], "rede": t["rede"], "cand": t["ator_id"], "janela": t["janela"], "url": t["url"], "texto": s}
            for t in ts for s in segmentar(t["texto"])]
    X, voc = cr.matriz([s["texto"] for s in segs])
    n_ativos = int((X.sum(1) > 0).sum())
    mc = max(cr.MIN_CLASSE, int(cr.MIN_CLASSE_PCT * n_ativos))
    rot, arvore, escolha_k = cr.chd_iramuteq(X, min_classe=mc, n_textos=len(ts))
    cl = rot > 0
    n = int(cl.sum())
    Xc, rc = X[cl], rot[cl]
    tot = Xc.sum(0)
    infl = sorted({s["cand"] for s in segs})
    infl_arr = np.array([s["cand"] for s in segs])[cl]
    jan_arr = np.array([s["janela"] for s in segs])[cl]
    classes = []
    for k in sorted(set(rc.tolist())):
        m = rc == k
        nk = int(m.sum())
        ch = cr.chi2_assoc(Xc[m].sum(0), tot, nk, n)
        formas = [[voc[j], round(float(ch[j]), 1), int(Xc[m][:, j].sum())] for j in np.argsort(-ch)[:25] if ch[j] >= cr.CHI_CRIT]
        variaveis = {}
        for nome, arr, mods in (("influenciadora", infl_arr, infl), ("janela", jan_arr, ["base", "nucleo"])):
            for c in mods:
                em = arr == c
                vch = cr.chi2_assoc(np.array([float((em & m).sum())]), np.array([float(em.sum())]), nk, n)[0]
                variaveis[f"{nome}:{c}"] = {"segmentos": int((em & m).sum()), "pct_da_classe": round(100 * (em & m).sum() / nk, 1),
                                            "chi2": round(float(vch), 1)}
        idx = np.where(cl)[0][m]
        peso = {j: ch[j] for j in range(len(voc)) if ch[j] > 0}
        score = sorted(((sum(peso.get(j, 0) for j in np.nonzero(X[i])[0]), i) for i in idx), reverse=True)[:5]
        classes.append({"classe": k, "segmentos": nk, "pct": round(100 * nk / max(1, n), 1), "formas": formas, "variaveis": variaveis,
                        "segmentos_caracteristicos": [{"cand": segs[i]["cand"], "rede": segs[i]["rede"], "url": segs[i]["url"],
                                                       "texto": segs[i]["texto"][:300]} for _, i in score], "nome": None})
    out = {"gerado_em_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "metodo": (f"CHD de Reinert (implementação em Python/numpy, classificação simples): até {cr.K} classes, formas com "
                      f"{cr.MIN_FREQ}+ segmentos, classe mínima de {int(cr.MIN_CLASSE_PCT * 100)}% dos segmentos, formas características com "
                      f"χ² ≥ {cr.CHI_CRIT} (p < 0,05). Segmentos de ~{PALAVRAS_SEGMENTO} palavras de legenda + fala transcrita. Os nomes das classes "
                      "devem ser dados pelo pesquisador. Conferir no IRaMuTeQ com o corpus exportado."),
           "lematizacao": cr.lematizacao(), "escolha_classes": escolha_k, "textos": len(ts), "textos_sem_texto_fora": vazios,
           "textos_por_rede": {r: sum(1 for t in ts if t["rede"] == r) for r in FONTES},
           "textos_com_fala": sum(1 for t in ts if t["fala"]), "segmentos_total": len(segs), "segmentos_classificados": n,
           "pct_classificados": round(100 * n / max(1, len(segs)), 1), "formas_ativas": len(voc),
           "aproveitamento": cr.aproveitamento(rot, len(segs)), "arvore": arvore, "classes": classes}
    try:
        import similitude as sim
        res = sim.ads(X, voc, [s["cand"] for s in segs])
        if res:
            out["similitude"] = res
            sim.gexf(res, d / "similitude.gexf")
    except Exception as e:  # noqa: BLE001
        out["similitude"] = {"erro": f"{type(e).__name__}: {str(e)[:160]}"}
    (d / "chd.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"corpus: {len(ts)} textos ({out['textos_com_fala']} com fala), {len(segs)} segmentos, {n} classificados "
          f"({out['pct_classificados']}%), {len(voc)} formas, {len(classes)} classes")
    for c in classes:
        top = sorted(((v["chi2"], k) for k, v in c["variaveis"].items()), reverse=True)[:2]
        print(f"  classe {c['classe']} ({c['pct']}%): " + ", ".join(f[0] for f in c["formas"][:10]) + " | " + " ".join(f"{k} χ²{v}" for v, k in top))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
