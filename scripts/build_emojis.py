#!/usr/bin/env python3
"""Mapa de emojis: publicações das influenciadoras e comentários do público, com o texto por trás de cada emoji.

Pedido do responsável em 22/11/2026, 23h27. Fontes (todas já públicas no repositório):
- publicações das quatro na linha de base e no núcleo: legenda (Instagram, TikTok, X) e título (YouTube);
- comentários das publicações do núcleo, do corpus anonimizado (data/comentarios/corpus_<rede>.json).
Método:
- extração com a biblioteca emoji (Unicode/CLDR); variantes unidas (seletor de variação e tons de pele somados ao emoji-base);
- posição no texto: início, meio, fim ou texto só com emoji (Paiva, 2016);
- repetição: % das ocorrências coladas a outra do mesmo emoji (😂😂), uso como intensificador;
- sentimento: (positivos − negativos) / ocorrências no Emoji Sentiment Ranking v1.0 (Kralj Novak et al., 2015, tweets em
  13 línguas europeias, 2013–2015; data/config/emoji_sentiment_ranking_v1.csv). Emoji fora do ranking fica sem escore (⛔).
Classificação automática: sugestão, a validar pelos pesquisadores. Percentuais valem para os textos lidos.
Para o clique na página: cada emoji leva os índices das publicações e dos comentários em que aparece.
Saída: data/emojis.json.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import emoji

RAIZ = Path(__file__).resolve().parents[1]
TOP = 120
VAR = re.compile("[️\U0001F3FB-\U0001F3FF]")
ROT_POS = ("início", "meio", "fim", "só emoji")
REDES = {"youtube": "YouTube", "instagram": "Instagram", "tiktok": "TikTok", "x": "X"}
POSTS = {"youtube": ("data/youtube/videos.csv", "titulo"), "instagram": ("data/instagram/posts.csv", "texto"),
         "tiktok": ("data/tiktok/posts.csv", "texto"), "x": ("data/x/posts.csv", "texto")}


def norm(e: str) -> str:
    return VAR.sub("", e)


def sentimento(root: Path) -> dict[str, float]:
    out = {}
    with (root / "data/config/emoji_sentiment_ranking_v1.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            n = int(r["Occurrences"])
            if n:
                out[norm(r["Emoji"])] = round((int(r["Positive"]) - int(r["Negative"])) / n, 3)
    return out


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def analisa(t: str):
    """Emojis do texto: [(emoji normalizado, forma original, posição, colado ao anterior igual)]."""
    es = emoji.emoji_list(t)
    if not es:
        return []
    so = not emoji.replace_emoji(t, "").strip()
    cobre = set()
    for e in es:
        cobre.update(range(e["match_start"], e["match_end"]))
    idx = [i for i, ch in enumerate(t) if i not in cobre and not ch.isspace() and ch != "️"]
    pri, ult = (idx[0], idx[-1]) if idx else (-1, -1)
    out, ant, fim_ant = [], None, -1
    for e in es:
        k = norm(e["emoji"])
        p = "só emoji" if so else ("fim" if e["match_start"] > ult else ("início" if e["match_end"] <= pri else "meio"))
        out.append((k, e["emoji"], p, k == ant and e["match_start"] == fim_ant))
        ant, fim_ant = k, e["match_end"]
    return out


def main(root: Path = RAIZ) -> int:
    esr = sentimento(root)
    textos = []  # (fonte, ator, ref, texto)
    publicacoes = []
    for rede, (arq, col) in POSTS.items():
        for r in ler(root / arq):
            if r.get("janela") not in ("base", "nucleo"):
                continue
            t = r.get(col) or ""
            publicacoes.append({"a": r["ator_id"], "r": rede, "d": (r.get("publicado_em") or "")[:10], "u": r.get("url"), "j": r.get("janela"),
                                "t": re.sub(r"\s+", " ", t)[:600]})
            textos.append((f"Publicações · {REDES[rede]}", r["ator_id"], ("p", len(publicacoes) - 1), t))
    universo_com = {}
    for rede in ("youtube", "instagram", "tiktok"):
        p = root / f"data/comentarios/corpus_{rede}.json"
        if not p.exists():
            continue
        C = json.loads(p.read_text(encoding="utf-8"))
        for i, x in enumerate(C["itens"]):
            textos.append((f"Comentários · {REDES[rede]}", x["a"], ("c", rede, i, x["a"]), x.get("t") or ""))
        res = root / f"data/comentarios/{rede}_resumo.json"
        if res.exists():
            us = [v.get("universo") for v in json.loads(res.read_text(encoding="utf-8"))["por_influenciadora"].values() if v.get("publicacoes")]
            universo_com[f"Comentários · {REDES[rede]}"] = None if any(u is None for u in us) else sum(us)
    fontes = {}
    occ, txts, pos, rep, por_fonte, por_ator, variantes = Counter(), Counter(), defaultdict(Counter), Counter(), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    refs = defaultdict(list)
    for fonte, ator, ref, t in textos:
        F = fontes.setdefault(fonte, {"lidos": 0, "com_emoji": 0, "ocorrencias": 0})
        F["lidos"] += 1
        es = analisa(t)
        if not es:
            continue
        F["com_emoji"] += 1
        F["ocorrencias"] += len(es)
        vistos = set()
        for k, orig, p, colado in es:
            variantes[k][orig] += 1
            occ[k] += 1
            por_fonte[k][fonte] += 1
            por_ator[k][ator] += 1
            pos[k][p] += 1
            if colado:
                rep[k] += 1
            if k not in vistos:
                txts[k] += 1
                vistos.add(k)
                refs[k].append(list(ref))
    lidos = sum(F["lidos"] for F in fontes.values())
    lista = []
    for k, n in occ.most_common(TOP):
        rot = variantes[k].most_common(1)[0][0]
        if "️" not in rot and (rot + "️") in emoji.EMOJI_DATA:
            rot += "️"
        nome = emoji.demojize(rot, language="pt").strip(":").replace("_", " ")
        lista.append({"e": rot, "chave": k, "nome": nome if not nome.startswith(rot) else None, "ocorrencias": n, "textos": txts[k],
                      "pct_textos_lidos": round(100 * txts[k] / lidos, 2) if lidos else 0,
                      "posicao": {p: pos[k][p] for p in ROT_POS if pos[k][p]}, "repeticao_pct": round(100 * rep[k] / n, 1),
                      "por_fonte": dict(por_fonte[k].most_common()), "por_influenciadora": dict(por_ator[k].most_common()),
                      "sentimento": esr.get(k), "refs": refs[k]})
    soma = sum(occ.values())
    out = {"gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "metodo": " ".join(__doc__.split("\n\n")[1:3]).replace("\n", " "),
           "fontes": [{"fonte": k, "universo": universo_com.get(k), "lidos": F["lidos"], "com_emoji": F["com_emoji"], "ocorrencias": F["ocorrencias"]}
                      for k, F in sorted(fontes.items())],
           "total": {"lidos": lidos, "com_emoji": sum(F["com_emoji"] for F in fontes.values()), "ocorrencias": soma, "distintos": len(occ),
                     "cobertura_sentimento_pct": round(100 * sum(n for k, n in occ.items() if k in esr) / soma, 1) if soma else None},
           "emojis": lista, "publicacoes": publicacoes,
           "aviso": "Classificação automática: sugestão, ainda não validada pelos pesquisadores. Percentuais valem para os textos lidos."}
    (root / "data/emojis.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for F in out["fontes"]:
        print(f"{F['fonte']}: {F['lidos']} textos, {F['com_emoji']} com emoji, {F['ocorrencias']} ocorrências")
    print("mais usados:", " ".join(f"{e['e']}{e['ocorrencias']}" for e in lista[:15]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
