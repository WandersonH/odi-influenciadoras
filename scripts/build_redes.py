#!/usr/bin/env python3
"""Redes para o Gephi (seção 8.2 do plano; mesmo desenho dos casos do ODI Atlas).

Rede "marcações e hashtags": bipartida, com as quatro influenciadoras e o que elas marcam nas próprias publicações do
recorte (01/06 a 14/08/2026), em todas as redes coletadas:
  influenciadora → @perfil marcado (marcas, parceiros, outras influenciadoras)  e  influenciadora → #hashtag.
Peso da aresta = número de publicações. Mostra com quem e com que temas cada uma se liga; perfis e hashtags partilhados
aproximam as influenciadoras.

Comunidades: Louvain (networkx.community.louvain_communities, resolução 1,0, semente 42), como no plano; posições para
o desenho na página (spring layout por componente, redes_caso._layout do Atlas). No Gephi: ForceAtlas 2 para as
comunidades e Modularity com resolução 1,0. Os @ marcados são perfis citados pelas próprias influenciadoras em
publicações públicas; nenhum dado de comentarista entra aqui.

Saídas: data/redes/marcacoes.json (página), .gexf (Gephi), .graphml, _nos.csv e _arestas.csv (NodeXL e planilhas).
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

RAIZ = Path(__file__).resolve().parent.parent
FONTES = {"youtube": "data/youtube/videos.csv", "instagram": "data/instagram/posts.csv", "tiktok": "data/tiktok/posts.csv", "x": "data/x/posts.csv"}
ARROBA = re.compile(r"(?<![\w.])@([A-Za-z0-9_.]{2,30})")
HASH = re.compile(r"#([0-9A-Za-zÀ-ÿ_]{3,})")
GENERICAS = {"fyp", "foryou", "foryoupage", "fy", "viral", "parati", "pravoce", "explore", "reels", "trend", "xyzbca", "fypシ"}
MIN_PESO_NO = 2  # perfil ou hashtag usado em 2+ publicações (o resto vira ruído no desenho; fica nos CSV completos)


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main(root: Path = RAIZ) -> int:
    import networkx as nx
    from redes_caso import _layout
    atores = json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    nomes = {a["id"]: a["nome"] for a in atores}
    proprios = {str(p.get("perfil") or "").lstrip("@").lower(): a["id"] for a in atores for p in a["perfis"].values() if p.get("perfil")}
    arestas, por_rede = Counter(), Counter()
    for rede, arq in FONTES.items():
        for r in ler(root / arq):
            if r.get("janela") not in ("base", "nucleo"):
                continue
            t = r.get("texto") or ""
            alvos = {("@" + m.lower().rstrip(".")) for m in ARROBA.findall(t)} | {("#" + h.lower()) for h in HASH.findall(t) if h.lower() not in GENERICAS}
            for alvo in alvos:
                aid_alvo = proprios.get(alvo[1:]) if alvo.startswith("@") else None
                if aid_alvo == r["ator_id"]:
                    continue  # marcar a si mesma não é ligação
                destino = aid_alvo or alvo  # marcar outra influenciadora do estudo liga as duas diretamente
                arestas[(r["ator_id"], destino)] += 1
                por_rede[rede] += 1
    peso_no = Counter()
    for (a, b), w in arestas.items():
        peso_no[b] += w
    G = nx.Graph()
    for aid, nome in nomes.items():
        G.add_node(aid, rotulo=nome, tipo="influenciadora")
    for (a, b), w in arestas.items():
        if b in nomes or peso_no[b] >= MIN_PESO_NO:
            if b not in G:
                G.add_node(b, rotulo=b, tipo="perfil marcado" if b.startswith("@") else "hashtag")
            G.add_edge(a, b, weight=w)
    G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0 and n not in nomes])
    louv = nx.community.louvain_communities(G, weight="weight", resolution=1.0, seed=42) if G.number_of_edges() else []
    com = {n: i + 1 for i, c in enumerate(sorted(louv, key=len, reverse=True)) for n in c}
    _, pos = _layout(G) if G.number_of_edges() else ({}, {n: (0.0, 0.0) for n in G})
    mod = round(nx.community.modularity(G, louv, weight="weight"), 3) if louv else None
    partilhados = sorted(((n, sorted(nb for nb in G.neighbors(n) if nb in nomes)) for n in G if n not in nomes
                          and sum(1 for nb in G.neighbors(n) if nb in nomes) >= 2), key=lambda x: (-len(x[1]), x[0]))
    d = root / "data/redes"
    d.mkdir(parents=True, exist_ok=True)
    nos = [{"id": n, "rotulo": G.nodes[n]["rotulo"], "tipo": G.nodes[n]["tipo"], "grau": G.degree(n),
            "peso": int(G.degree(n, weight="weight")), "comunidade": com.get(n, 0),
            "x": round(float(pos[n][0]), 4), "y": round(float(pos[n][1]), 4)} for n in G]
    out = {"gerado_em_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "metodo": __doc__.split("\n\n")[1].strip() + " " + __doc__.split("\n\n")[2].strip(),
           "nos": nos, "arestas": [[a, b, d_["weight"]] for a, b, d_ in G.edges(data=True)],
           "estatisticas": {"nos": G.number_of_nodes(), "arestas": G.number_of_edges(), "comunidades": len(louv), "modularidade": mod,
                            "densidade": round(nx.density(G), 4), "ligacoes_por_rede": dict(por_rede),
                            "ligacoes_totais_antes_do_corte": len(arestas), "corte": f"perfil ou hashtag em {MIN_PESO_NO}+ publicações"},
           "partilhados": [{"no": n, "influenciadoras": [nomes[x] for x in xs]} for n, xs in partilhados]}
    (d / "marcacoes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for n in G:
        G.nodes[n]["comunidade"] = com.get(n, 0)
        G.nodes[n]["label"] = G.nodes[n]["rotulo"]
    nx.write_gexf(G, d / "marcacoes.gexf")
    nx.write_graphml(G, d / "marcacoes.graphml")
    # estatísticas do ODI Atlas (scripts/estatisticas_redes.py, cópia sem mudança: os indicadores do painel Statistics do
    # Gephi, Louvain com semente 42, E-I das duas maiores comunidades e as 5 maiores centralidades por medida)
    import estatisticas_redes as er
    lin, coms_ = er.estatisticas(str(d / "marcacoes.gexf"))
    cent = lin.pop("_centralidades", [])
    out["estatisticas_atlas"] = {k: v for k, v in lin.items() if k not in ("arquivo", "caso")}
    out["centralidades"] = cent
    out["comunidades_atlas"] = coms_
    (d / "marcacoes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for nome, linhas in (("estatisticas_redes.csv", [out["estatisticas_atlas"]]), ("centralidades_redes.csv", cent), ("comunidades_redes.csv", coms_)):
        if linhas:
            with (d / nome).open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
                w.writeheader()
                w.writerows(linhas)
    with (d / "marcacoes_nos.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "rotulo", "tipo", "grau", "peso", "comunidade"], extrasaction="ignore")
        w.writeheader()
        w.writerows(nos)
    with (d / "marcacoes_arestas.csv").open("w", encoding="utf-8", newline="") as f:  # completo, sem o corte de peso
        w = csv.writer(f)
        w.writerow(["origem", "destino", "peso"])
        for (a, b), p in sorted(arestas.items(), key=lambda x: -x[1]):
            w.writerow([a, b, p])
    print(f"redes: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas, {len(louv)} comunidades (modularidade {mod}); "
          f"partilhados por 2+: {', '.join(n for n, _ in partilhados[:10])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
