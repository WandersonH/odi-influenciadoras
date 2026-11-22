#!/usr/bin/env python3
"""Redes dos comentários (seção 8.2 do plano): palavras e respostas, com as funções do ODI Atlas (redes_caso.palavras e
redes_caso.respostas, sem mudança) e as estatísticas do Atlas (estatisticas_redes.py).

- Palavras: coocorrência de formas no mesmo comentário (lematizadas pelo lexique_pt.txt do IRaMuTeQ, como na CHD),
  formas em 5+ comentários, arestas com 3+ comentários em comum. Uma rede por rede social e uma com tudo.
- Respostas: quem responde a quem nos comentários do YouTube (o único com respostas lidas); autores SEMPRE como código
  (A0001…), nunca nome.
Lê o privado (INFL_INTERNO_DIR, data/comentarios/<rede>.csv); grava no público só palavras, códigos e contagens:
data/redes/comentarios_palavras_<rede>.json/.gexf, comentarios_respostas_youtube.json/.gexf.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

RAIZ = Path(__file__).resolve().parent.parent


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def salvar(nome: str, nos: dict, arestas: dict, desenho, extra: dict, d: Path, dirigida: bool = False) -> dict:
    import networkx as nx
    import estatisticas_redes as er
    G = nx.DiGraph() if dirigida else nx.Graph()
    for k, v in nos.items():
        G.add_node(k, label=v["rotulo"], tipo=v["tipo"], peso=v["n"])
    for (a, b), w in arestas.items():
        G.add_edge(a, b, weight=w)
    G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
    nx.write_gexf(G, d / f"{nome}.gexf")
    lin, coms = er.estatisticas(str(d / f"{nome}.gexf")) if G.number_of_nodes() else ({}, [])
    cent = lin.pop("_centralidades", []) if lin else []
    out = {"gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "metodo": __doc__.split("\n\n")[1].strip(),
           "desenho": desenho, "estatisticas_atlas": {k: v for k, v in lin.items() if k not in ("arquivo", "caso")},
           "centralidades": cent, "comunidades_atlas": coms, **extra}
    (d / f"{nome}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main(root: Path = RAIZ) -> int:
    import redes_caso as rc
    interno = os.environ.get("INFL_INTERNO_DIR", "")
    if not interno or not Path(interno).is_dir():
        print("comentários: repositório privado indisponível")
        return 1
    d = root / "data/redes"
    d.mkdir(parents=True, exist_ok=True)
    todos = []
    for rede in ("youtube", "instagram", "tiktok"):
        rows = ler(Path(interno) / f"data/comentarios/{rede}.csv")
        todos += rows
        if len(rows) < 50:
            continue
        nos, ar, des = rc.palavras([r["texto"] for r in rows])
        o = salvar(f"comentarios_palavras_{rede}", nos, ar, des, {"rede": rede, "comentarios": len(rows)}, d)
        print(f"palavras {rede}: {len(rows)} comentários, {o['estatisticas_atlas'].get('nos')} nós, {o['estatisticas_atlas'].get('arestas')} arestas")
    nos, ar, des = rc.palavras([r["texto"] for r in todos])
    salvar("comentarios_palavras_todas", nos, ar, des, {"rede": "todas", "comentarios": len(todos)}, d)
    yt = ler(Path(interno) / "data/comentarios/youtube.csv")
    for r in yt:
        r["tipo"] = "resposta" if r.get("parent_id") else "comentario"
        r["autor_nome"] = r.get("autor", "")
    nos, ar, resumo = rc.respostas(yt)
    des = resumo.pop("desenho")
    o = salvar("comentarios_respostas_youtube", nos, ar, des, {"rede": "youtube", "comentarios": len(yt),
                                                                "respostas_lidas": sum(1 for r in yt if r.get("parent_id")), **resumo}, d, dirigida=True)
    print(f"respostas youtube: {resumo.get('autores_na_rede')} autores, {resumo.get('respostas_entre_autores')} respostas entre autores")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
