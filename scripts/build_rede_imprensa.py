#!/usr/bin/env python3
"""Rede da imprensa (caderno 07): veículo × termo de busca, a partir dos 10 primeiros do Google Notícias.

Fonte: data/imprensa/resultados.json (collect_imprensa.py): os 10 primeiros resultados do Google Notícias (RSS,
Brasil) por termo, nos recortes "dia do anúncio" (30/07 a 02/08) e "núcleo" (23/07 a 14/08/2026). Entram só as
buscas do tema (Hamas, desarmamento, Gaza…). As buscas pelos nomes das influenciadoras ficam de fora porque nenhuma
matéria as cita: os resultados de "Fabíola Oliveira" são de homônimos. Uma matéria que aparece nos dois recortes
para o mesmo termo conta uma vez. Rede: redes_caso.circulacao() (veículo ligado ao termo
pelo qual apareceu; peso = número de matérias). Estatísticas: estatisticas_redes.py (Gephi Statistics,
Louvain semente 42, E-I, centralidades). Universo ⛔: o Google Notícias não informa quantas matérias existem; a
amostra é a dos 10 primeiros por termo, na ordem do Google.

Saídas: data/redes/imprensa.json, .gexf, .graphml e imprensa_estatisticas.csv, imprensa_centralidades.csv,
imprensa_comunidades.csv.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))


def noticias_do_tema(resultados: dict) -> list[dict]:
    vistos, saida = set(), []
    for c in resultados.get("consultas", []):
        if c.get("grupo") != "tema":
            continue
        for r in c.get("resultados", []):
            chave = (c["consulta"], r.get("link") or r.get("titulo"))
            if chave in vistos:
                continue
            vistos.add(chave)
            saida.append({"veiculo": r.get("veiculo") or "?", "consulta": c["consulta"], "titulo": r.get("titulo"),
                          "link": r.get("link"), "recorte": c["recorte"]})
    return saida


def main(root: Path = RAIZ) -> int:
    import networkx as nx
    import estatisticas_redes as er
    import redes_caso as rc
    imp = root / "data/imprensa/resultados.json"
    if not imp.exists():
        print("⛔ data/imprensa/resultados.json ausente: rode collect_imprensa.py")
        return 1
    res = json.loads(imp.read_text(encoding="utf-8"))
    noticias = noticias_do_tema(res)
    if not noticias:
        print("⛔ nenhuma matéria do tema nos resultados")
        return 1
    nos, arestas, desenho = rc.circulacao([], noticias, [])
    d = root / "data/redes"
    d.mkdir(parents=True, exist_ok=True)
    G = nx.Graph()
    for k, v in nos.items():
        G.add_node(k, label=v["rotulo"], tipo=v["tipo"], peso=v["n"])
    for (a, b), w in arestas.items():
        G.add_edge(a, b, weight=w)
    nx.write_gexf(G, d / "imprensa.gexf")
    nx.write_graphml(G, d / "imprensa.graphml")
    lin, coms = er.estatisticas(str(d / "imprensa.gexf"))
    cent = lin.pop("_centralidades", [])
    por_veiculo = {}
    for x in noticias:
        por_veiculo.setdefault(x["veiculo"], set()).add(x["consulta"])
    top = sorted(({"veiculo": v, "materias": sum(1 for x in noticias if x["veiculo"] == v), "termos": len(t)}
                  for v, t in por_veiculo.items()), key=lambda x: (-x["materias"], x["veiculo"]))[:15]
    out = {"gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
           "fonte_coleta": {"run_id": res.get("run_id"), "gerado_em": res.get("gerado_em")},
           "metodo": __doc__.split("\n\n")[1].strip(),
           "universo": "⛔ o Google Notícias não informa o total; amostra = 10 primeiros por termo",
           "materias": len(noticias), "veiculos": len(por_veiculo), "termos": sorted({x["consulta"] for x in noticias}),
           "por_recorte": {r: sum(1 for x in noticias if x["recorte"] == r) for r in sorted({x["recorte"] for x in noticias})},
           "influenciadoras_na_rede": [], "top_veiculos": top,
           "desenho": desenho, "total_nos": len(nos), "total_arestas": len(arestas),
           "estatisticas_rede": {k: v for k, v in lin.items() if k not in ("arquivo", "caso")}, "centralidades": cent, "comunidades_rede": coms}
    (d / "imprensa.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for nome, linhas in (("imprensa_estatisticas.csv", [out["estatisticas_rede"]]), ("imprensa_centralidades.csv", cent), ("imprensa_comunidades.csv", coms)):
        if linhas:
            with (d / nome).open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
                w.writeheader()
                w.writerows(linhas)
    print(f"imprensa: {len(noticias)} matérias de {len(por_veiculo)} veículos em {len(out['termos'])} termos; "
          f"rede {G.number_of_nodes()} nós, {G.number_of_edges()} arestas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
