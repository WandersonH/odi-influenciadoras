#!/usr/bin/env python3
"""Rede de circulação do caso Hamas no dia do anúncio (30/07 a 02/08/2026), no padrão dos casos do ODI Atlas.

Pedido do responsável (22/11/2026, 19h14): "uma rede de circulação do Hamas com canais [que] publicaram notícias no dia".
- YouTube (API oficial, sem custo): search.list por termo do caso, publishedAfter 2026-07-30 e publishedBefore 2026-08-03,
  ordem de relevância, até 50 vídeos por termo; visualizações (videos.list) e inscritos do canal (channels.list).
- Imprensa: os 10 primeiros do Google Notícias no recorte "dia do anúncio" (data/imprensa/resultados.json).
- Rede: redes_caso.circulacao() do ODI Atlas, sem mudança: quem publicou (canal do YouTube ou veículo) × termo que o
  trouxe; peso = visualizações (ou 1 por notícia). Canal com menos de 10 mil inscritos aparece como código (P0001…).
- Estatísticas: estatisticas_redes.py do ODI Atlas (Gephi Statistics, Louvain semente 42, E-I, centralidades).
- Cruzamento: se algum canal da rede é de uma das influenciadoras (canal próprio) — resposta direta à pergunta do estudo.
Universo: a busca do YouTube não informa o total (pageInfo.totalResults é estimativa: não é universo, ⛔).
Saídas: data/redes/circulacao_hamas.json, .gexf, .graphml e CSVs de estatísticas.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

RAIZ = Path(__file__).resolve().parent.parent
TERMOS = ["Hamas desarmamento", "Hamas aceita desarmamento", "acordo Hamas Israel", "desarmamento do Hamas"]
DE, ATE = "2026-07-30T00:00:00Z", "2026-08-03T00:00:00Z"
API = "https://www.googleapis.com/youtube/v3/"


def api(rota, chave, **p):
    p["key"] = chave
    with urllib.request.urlopen(API + rota + "?" + urllib.parse.urlencode(p), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def coletar_youtube(chave):
    vids, estimativas, unidades = {}, {}, 0
    for t in TERMOS:
        d = api("search", chave, part="snippet", q=t, type="video", publishedAfter=DE, publishedBefore=ATE, maxResults=50,
                order="relevance", regionCode="BR", relevanceLanguage="pt")
        unidades += 100
        estimativas[t] = d.get("pageInfo", {}).get("totalResults")
        for it in d.get("items", []):
            v = vids.setdefault(it["id"]["videoId"], {"video_id": it["id"]["videoId"], "canal_id": it["snippet"]["channelId"],
                                                       "canal": it["snippet"]["channelTitle"], "titulo": it["snippet"]["title"],
                                                       "publicado_em": it["snippet"]["publishedAt"], "termos": []})
            v["termos"].append(t)
    ids = list(vids)
    for i in range(0, len(ids), 50):
        d = api("videos", chave, part="statistics", id=",".join(ids[i:i + 50]))
        unidades += 1
        for it in d.get("items", []):
            vids[it["id"]]["visualizacoes"] = int(it["statistics"].get("viewCount", 0))
    canais = sorted({v["canal_id"] for v in vids.values()})
    insc = {}
    for i in range(0, len(canais), 50):
        d = api("channels", chave, part="statistics", id=",".join(canais[i:i + 50]))
        unidades += 1
        for it in d.get("items", []):
            s = it["statistics"]
            insc[it["id"]] = None if s.get("hiddenSubscriberCount") else int(s.get("subscriberCount", 0))
    for v in vids.values():
        v["inscritos"] = insc.get(v["canal_id"])
    return list(vids.values()), estimativas, unidades


def main(root: Path = RAIZ) -> int:
    import networkx as nx
    import estatisticas_redes as er
    import redes_caso as rc
    chave = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not chave:
        print("⛔ YOUTUBE_API_KEY ausente")
        return 1
    vids, estimativas, unidades = coletar_youtube(chave)
    imp = root / "data/imprensa/resultados.json"
    noticias = []
    if imp.exists():
        for c in json.loads(imp.read_text(encoding="utf-8"))["consultas"]:
            if c["recorte"] == "dia do anúncio" and c["grupo"] == "tema":
                noticias += [{"veiculo": r["veiculo"], "consulta": c["consulta"], "titulo": r["titulo"], "link": r["link"]} for r in c["resultados"]]
    # uma linha por (vídeo, termo), como no Atlas
    linhas_v = [dict(v, consulta=t) for v in vids for t in v["termos"]]
    nos, arestas, desenho = rc.circulacao(linhas_v, noticias, [])
    d = root / "data/redes"
    d.mkdir(parents=True, exist_ok=True)
    G = nx.Graph()
    for k, v in nos.items():
        G.add_node(k, label=v["rotulo"], tipo=v["tipo"], peso=v["n"])
    for (a, b), w in arestas.items():
        G.add_edge(a, b, weight=w)
    nx.write_gexf(G, d / "circulacao_hamas.gexf")
    nx.write_graphml(G, d / "circulacao_hamas.graphml")
    lin, coms = er.estatisticas(str(d / "circulacao_hamas.gexf"))
    cent = lin.pop("_centralidades", [])
    atores = json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    proprios = {}
    for a in atores:
        man = root / "data/manifest/youtube_latest.json"
        if man.exists():
            for x in json.loads(man.read_text(encoding="utf-8")).get("atores", []):
                if x.get("canal_id"):
                    proprios[x["canal_id"]] = x["ator"]
    das_influenciadoras = sorted({proprios[v["canal_id"]] for v in vids if v["canal_id"] in proprios})
    top_canais = sorted(({"canal": v["canal"] if (v.get("inscritos") or 0) >= rc.MIN_PUBLICO else "canal pequeno (código na rede)",
                          "inscritos": v.get("inscritos"), "visualizacoes": v.get("visualizacoes"), "titulo": v["titulo"] if (v.get("inscritos") or 0) >= rc.MIN_PUBLICO else "",
                          "publicado_em": v["publicado_em"], "url": "https://www.youtube.com/watch?v=" + v["video_id"] if (v.get("inscritos") or 0) >= rc.MIN_PUBLICO else ""}
                         for v in vids), key=lambda x: -(x["visualizacoes"] or 0))[:15]
    out = {"gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
           "metodo": __doc__.split("\n\n")[1].strip(), "recorte": {"de": DE, "ate_exclusivo": ATE}, "termos": TERMOS,
           "youtube": {"videos": len(vids), "canais": len({v["canal_id"] for v in vids}), "estimativa_api_por_termo": estimativas,
                       "universo": "⛔ a busca do YouTube não informa o total (a estimativa da API não é universo)", "cota_unidades": unidades},
           "imprensa": {"noticias": len(noticias), "veiculos": len({x["veiculo"] for x in noticias})},
           "influenciadoras_na_rede": das_influenciadoras, "top_canais": top_canais,
           "desenho": desenho, "total_nos": len(nos), "total_arestas": len(arestas),
           "estatisticas_atlas": {k: v for k, v in lin.items() if k not in ("arquivo", "caso")}, "centralidades": cent, "comunidades_atlas": coms}
    (d / "circulacao_hamas.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for nome, linhas in (("circulacao_estatisticas.csv", [out["estatisticas_atlas"]]), ("circulacao_centralidades.csv", cent), ("circulacao_comunidades.csv", coms)):
        if linhas:
            with (d / nome).open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
                w.writeheader()
                w.writerows(linhas)
    print(f"circulação: {len(vids)} vídeos de {out['youtube']['canais']} canais, {len(noticias)} notícias; rede {G.number_of_nodes()} nós, "
          f"{G.number_of_edges()} arestas; influenciadoras na rede: {das_influenciadoras or 'nenhuma'}; cota ~{unidades}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
