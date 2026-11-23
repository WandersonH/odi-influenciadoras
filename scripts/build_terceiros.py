#!/usr/bin/env python3
"""Menções de terceiros no núcleo, com a regra de homônimos do plano (seção 5), em todas as fontes coletadas.

Regra: uma menção conta se trouxer o @ da influenciadora, ou o nome junto de um termo de contexto
(data/config/palavras.json → contexto_homonimos: islã, muçulmana, hijab, revertida, Palestina, árabe…). O resto fica
"a conferir" (homônimo provável), fora da contagem, até conferência humana.

Fontes: YouTube (search.list por nome; título do vídeo, no privado), X pela API (xquik; privado), X pela busca do
navegador (privado) e imprensa (Google Notícias, público). Lê o privado (INFL_INTERNO_DIR); grava no público só
contagens e, para canais e veículos com 10 mil+ inscritos ou imprensa, o nome.
Saída: data/terceiros/resumo.json.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def classificar(texto: str, nomes: list[str], handles: list[str], contexto: list[str]) -> str:
    t = norm(texto)
    if any(("@" + norm(h)) in t for h in handles):
        return "confirmada (@)"
    if any(norm(n) in t for n in nomes):
        return "confirmada (nome + contexto)" if any(c in t for c in contexto) else "a conferir (homônimo provável)"
    if any(c in t for c in contexto):
        return "a conferir (o nome não está no título, mas há termo de contexto; a busca achou o nome na descrição ou na fala)"
    return "sem o nome no texto"


def descricoes(ids: list[str]) -> dict:
    """Título + descrição dos vídeos pela API do YouTube (1 unidade por 50 vídeos), para checar o nome fora do título."""
    import urllib.parse
    import urllib.request
    chave = os.environ.get("YOUTUBE_API_KEY", "").strip()
    out = {}
    if not chave:
        return out
    for i in range(0, len(ids), 50):
        q = urllib.parse.urlencode({"part": "snippet", "id": ",".join(ids[i:i + 50]), "key": chave})
        with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/videos?" + q, timeout=60) as r:
            for it in json.loads(r.read().decode("utf-8")).get("items", []):
                out[it["id"]] = (it["snippet"]["title"] + " " + it["snippet"].get("description", ""), it["snippet"]["channelId"])
    canais = sorted({c for _, c in out.values()})
    insc = {}
    for i in range(0, len(canais), 50):
        q = urllib.parse.urlencode({"part": "statistics", "id": ",".join(canais[i:i + 50]), "key": chave})
        with urllib.request.urlopen("https://www.googleapis.com/youtube/v3/channels?" + q, timeout=60) as r:
            for it in json.loads(r.read().decode("utf-8")).get("items", []):
                st = it["statistics"]
                insc[it["id"]] = None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0))
    return {v: (t, insc.get(c)) for v, (t, c) in out.items()}


MIN_PUBLICO = 10000
_COD = {}


def canal_publico(nome: str, inscritos) -> str:
    """Canal com menos de 10 mil inscritos (ou sem número) aparece só como código."""
    if inscritos is not None and inscritos >= MIN_PUBLICO:
        return nome
    _COD.setdefault(nome, f"canal pequeno C{len(_COD) + 1:03d}")
    return _COD[nome]


def main(root: Path = RAIZ) -> int:
    interno = os.environ.get("INFL_INTERNO_DIR", "")
    if not interno or not Path(interno).is_dir():
        print("terceiros: repositório privado indisponível")
        return 1
    priv = Path(interno) / "data"
    atores = json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    pal = json.loads((root / "data/config/palavras.json").read_text(encoding="utf-8"))
    ctx = pal.get("contexto_homonimos", [])
    nuc = json.loads((root / "data/config/projeto.json").read_text(encoding="utf-8"))["janelas"]["nucleo"]
    ini, fim = nuc["inicio"][:10], nuc["fim"][:10]
    yt = ler(priv / "terceiros_youtube.csv")
    xa = ler(priv / "terceiros/x_mencoes.csv")
    xn = ler(priv / "terceiros/x_navegador.csv")
    imp = json.loads((root / "data/imprensa/resultados.json").read_text(encoding="utf-8")) if (root / "data/imprensa/resultados.json").exists() else {"consultas": []}
    out = {}
    for a in atores:
        nomes = [a["nome"]] + (["Fabiola Oliver"] if a["id"] == "fabiola-oliveira" else [])
        handles = [str(p.get("perfil") or "").lstrip("@") for p in a["perfis"].values() if p.get("perfil")]
        fontes = {}
        # YouTube (título)
        meus = {r["video_id"]: r for r in yt if r["ator_id"] == a["id"] and ini <= r["publicado_em"][:10] <= fim}
        desc = descricoes(list(meus))
        cls = [classificar(desc.get(v, (r["titulo"], None))[0], nomes, handles, ctx) for v, r in meus.items()]
        pub = {v: canal_publico(r["canal"], desc.get(v, ("", None))[1]) for v, r in meus.items()}
        pub_ok = {v: desc.get(v, ("", None))[1] is not None and desc[v][1] >= MIN_PUBLICO for v in meus}
        fontes["YouTube (busca por nome)"] = {"lidos": len(meus), "descricoes_lidas": len(desc),
                                             "confirmadas_lista": [{"canal": pub[v], "titulo": r["titulo"] if pub_ok[v] else "", "publicado_em": r["publicado_em"][:10], "url": r["url"] if pub_ok[v] else "", "como": c}
                                                                   for (v, r), c in zip(meus.items(), cls) if c.startswith("confirmada")], "confirmadas": sum(c.startswith("confirmada") for c in cls),
                                             "a_conferir": sum(c.startswith("a conferir") for c in cls), "sem_nome_no_titulo": sum(c.startswith("sem") for c in cls),
                                             "a_conferir_com_contexto": [{"canal": pub[v], "titulo": r["titulo"] if pub_ok[v] else "", "publicado_em": r["publicado_em"][:10], "url": r["url"] if pub_ok[v] else ""}
                                                                         for (v, r), c in zip(meus.items(), cls) if "termo de contexto" in c]}
        # X API
        xs = [r for r in xa if r["ator_id"] == a["id"] and ini <= r["publicado_em"][:10] <= fim]
        cls = [classificar(r["texto"], nomes, handles, ctx) for r in xs]
        fontes["X (API, xquik)"] = {"lidos": len(xs), "confirmadas": sum(c.startswith("confirmada") for c in cls), "a_conferir": sum(c.startswith("a conferir") for c in cls)}
        # X navegador
        q_nome = [r for r in xn if any(norm(n) in norm(r["consulta"]) for n in nomes) or any(norm(h) in norm(r["consulta"]) for h in handles)]
        cls = [classificar(r["texto"], nomes, handles, ctx) for r in q_nome]
        fontes["X (busca avançada no navegador)"] = {"lidos": len(q_nome), "confirmadas": sum(c.startswith("confirmada") for c in cls),
                                                     "a_conferir": sum(c.startswith("a conferir") for c in cls)}
        # imprensa (núcleo)
        res = [r for c in imp["consultas"] if c["recorte"] == "núcleo" and c["grupo"] == "influenciadora" and any(norm(n) in norm(c["consulta"]) for n in nomes) for r in c["resultados"]]
        cls = [classificar(r["titulo"], nomes, handles, ctx) for r in res]
        fontes["Imprensa (Google Notícias, 10 primeiros)"] = {"lidos": len(res), "confirmadas": sum(c.startswith("confirmada") for c in cls),
                                                              "a_conferir": sum(c.startswith("a conferir") for c in cls),
                                                              "veiculos_confirmados": sorted({r["veiculo"] for r, c in zip(res, cls) if c.startswith("confirmada")})}
        out[a["id"]] = {"nome": a["nome"], "fontes": fontes, "confirmadas_total": sum(f["confirmadas"] for f in fontes.values()),
                        "a_conferir_total": sum(f["a_conferir"] for f in fontes.values())}
    d = root / "data/terceiros"
    d.mkdir(parents=True, exist_ok=True)
    (d / "resumo.json").write_text(json.dumps({"gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "janela": "núcleo",
                                               "regra": pal.get("contexto_nota"), "contexto": ctx, "universo": "⛔ nenhuma busca informa o total",
                                               "metodo": __doc__.split("\n\n")[1].strip(), "por_influenciadora": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, "confirmadas", v["confirmadas_total"], "a conferir", v["a_conferir_total"], {f: (x["lidos"], x["confirmadas"]) for f, x in v["fontes"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
