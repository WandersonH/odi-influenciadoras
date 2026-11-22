#!/usr/bin/env python3
"""Índice de engajamento relativo (seção 8.1 do plano, mesmo método dos casos do ODI Atlas).

Para cada publicação do núcleo:  índice = interações da publicação ÷ mediana das interações da MESMA influenciadora,
na MESMA rede, na linha de base (01/06 a 22/07/2026). Acima de 1, rendeu mais que o habitual dela naquela rede.

Interações = curtidas + comentários + compartilhamentos, com o que a rede informa:
  YouTube: curtidas + comentários · Instagram: curtidas (o ator não devolve comentários) · TikTok e X: curtidas +
  comentários + compartilhamentos. Por isso o índice compara cada publicação só com a própria base, nunca entre redes.
Sem base (menos de 3 publicações com interação na linha de base) o índice fica ⛔ (None), nunca estimado.

Saída pública: data/engajamento.json.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import statistics
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTES = {"youtube": ("data/youtube/videos.csv", "video_id"), "instagram": ("data/instagram/posts.csv", "post_id"),
          "tiktok": ("data/tiktok/posts.csv", "post_id"), "x": ("data/x/posts.csv", "post_id")}
COMPONENTES = {"youtube": ("curtidas", "comentarios"), "instagram": ("curtidas",),
               "tiktok": ("curtidas", "comentarios", "compartilhamentos"), "x": ("curtidas", "comentarios", "compartilhamentos")}
MIN_BASE = 3


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    s = str(v if v is not None else "").strip()
    try:
        return int(float(s))
    except ValueError:
        return None


def interacoes(r: dict, rede: str):
    vals = [num(r.get(k)) for k in COMPONENTES[rede]]
    return None if all(v is None for v in vals) else sum(v or 0 for v in vals)


def main(root: Path = RAIZ) -> int:
    atores = json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    nomes = {a["id"]: a["nome"] for a in atores}
    grupos, posts = [], []
    for rede, (arq, chave) in FONTES.items():
        rows = ler(root / arq)
        for aid in nomes:
            meus = [r for r in rows if r["ator_id"] == aid and r.get("janela") in ("base", "nucleo")]
            if not meus:
                continue
            base = [i for i in (interacoes(r, rede) for r in meus if r["janela"] == "base") if i is not None]
            med = statistics.median(base) if len(base) >= MIN_BASE else None
            nuc = [r for r in meus if r["janela"] == "nucleo"]
            idx = []
            for r in nuc:
                i = interacoes(r, rede)
                ind = round(i / med, 2) if med and i is not None else None
                if ind is not None:
                    idx.append(ind)
                posts.append({"ator_id": aid, "rede": rede, "post_id": r[chave], "url": r["url"], "publicado_em": r["publicado_em"],
                              "interacoes": i, "visualizacoes": num(r.get("visualizacoes")), "indice": ind,
                              "texto": (r.get("texto") or "")[:160]})
            grupos.append({"ator_id": aid, "nome": nomes[aid], "rede": rede, "componentes": list(COMPONENTES[rede]),
                           "base_publicacoes": len(base), "base_mediana_interacoes": med, "nucleo_publicacoes": len(nuc),
                           "nucleo_indice_mediano": round(statistics.median(idx), 2) if idx else None,
                           "nucleo_acima_de_1": sum(1 for x in idx if x > 1), "nucleo_com_indice": len(idx),
                           "status": "ok" if med else f"⛔ linha de base com menos de {MIN_BASE} publicações com interação"})
    out = {"gerado_em_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "metodo": __doc__.split("\n\n")[1].strip() if __doc__ else "", "grupos": grupos,
           "publicacoes": sorted(posts, key=lambda p: p["publicado_em"])}
    (root / "data/engajamento.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for g in grupos:
        print(f"{g['rede']:9} {g['ator_id']:16} base {g['base_publicacoes']:3} med {g['base_mediana_interacoes']} · núcleo {g['nucleo_publicacoes']:3} "
              f"índice mediano {g['nucleo_indice_mediano']} · acima de 1: {g['nucleo_acima_de_1']}/{g['nucleo_com_indice']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
