#!/usr/bin/env python3
"""Resultados indexados do Google para o nome de cada influenciadora: agregado público (caderno do Trends).

Motivo: o Google Trends não devolveu série para os nomes. Coleta: busca do Google no Chrome do responsável em
22/11/2026 (nome entre aspas, hl=pt-BR, gl=br, pws=0), os 10 primeiros resultados orgânicos, em dois recortes:
sem data ("geral") e só páginas datadas de 23/07 a 14/08/2026 ("núcleo", filtro de data do próprio Google).
Cada resultado recebe uma categoria (pelo endereço e pelo título, a revisar por uma pessoa): proprio (perfil
confirmado em atores.json ou publicação dele), proprio_nao_confirmado (página que parece dela, fora de atores.json),
terceiro_sobre_ela, homonimo e a_conferir.
Privacidade: título e endereço completos ficam no privado (INFL_INTERNO_DIR/data/buscas/google_resultados.csv).
No público vão a posição, o domínio e a categoria; o título só aparece para páginas de terceiros que não são redes
sociais (imprensa e sites), como no caderno da imprensa. Universo ⛔: o Google não informa quantas páginas existem.
Limite: os resultados variam com o dia, o lugar e a conta; é retrato de 22/11/2026.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[1]
REDES_SOCIAIS = ("instagram.com", "facebook.com", "tiktok.com", "youtube.com", "x.com", "twitter.com", "linkedin.com", "threads.net", "kwai.com")
ROTULO = {"proprio": "perfil ou publicação dela", "proprio_nao_confirmado": "parece dela, perfil não confirmado",
          "terceiro_sobre_ela": "terceiro falando dela", "homonimo": "homônimo", "a_conferir": "a conferir"}


def dominio(url: str) -> str:
    h = urlparse(url).netloc.lower()
    return h[4:] if h.startswith("www.") else h


def social(dom: str) -> bool:
    return any(dom == s or dom.endswith("." + s) for s in REDES_SOCIAIS)


def main(root: Path = RAIZ) -> int:
    interno = os.environ.get("INFL_INTERNO_DIR", "").strip()
    fonte = Path(interno) / "data/buscas/google_resultados.csv" if interno else None
    if not fonte or not fonte.exists():
        print("⛔ resultados do Google indisponíveis (privado)")
        return 1
    linhas = list(csv.DictReader(fonte.open(encoding="utf-8")))
    atores = {a["id"]: a["nome"] for a in json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]}
    out = {"coletado_em": max(r["coletado_em"] for r in linhas), "metodo": " ".join(__doc__.split("\n\n")[1:4]).replace("\n", " "),
           "universo": "⛔ o Google não informa quantas páginas existem", "categorias": ROTULO, "por_influenciadora": {}}
    for aid, nome in atores.items():
        out["por_influenciadora"][aid] = {"nome": nome, "recortes": {}}
        for rec in ("geral", "nucleo"):
            rs = sorted((r for r in linhas if r["ator_id"] == aid and r["recorte"] == rec), key=lambda r: int(r["posicao"]))
            itens = []
            for r in rs:
                d = dominio(r["url"])
                mostra_titulo = r["categoria"] in ("terceiro_sobre_ela",) and not social(d)
                itens.append({"posicao": int(r["posicao"]), "dominio": d, "categoria": r["categoria"],
                              "titulo": r["titulo"] if mostra_titulo else None, "url": r["url"] if mostra_titulo else None})
            out["por_influenciadora"][aid]["recortes"][rec] = {"lidos": len(rs), "por_categoria": dict(Counter(r["categoria"] for r in rs)), "itens": itens}
    d = root / "data/buscas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "google.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for aid, v in out["por_influenciadora"].items():
        print(v["nome"], {k: (x["lidos"], x["por_categoria"]) for k, x in v["recortes"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
