#!/usr/bin/env python3
"""Imprensa: os 10 primeiros resultados do Google Notícias para cada termo (RSS público, sem chave e sem custo).

Pedido do responsável (22/11/2026, 19h14): "os 10 primeiros resultados do Google para cada" termo, e os resultados do
caso Hamas. Fonte: https://news.google.com/rss/search (Brasil, português), com os operadores de data do Google
(after:/before:). A ordem é a do Google (relevância), lida na data da coleta: é uma amostra dos 10 primeiros, não o
universo (o Google não informa o total: ⛔).

Recortes:
  - "dia do anúncio": 30/07 a 02/08/2026 (caso Hamas: o acordo foi anunciado em 31/07);
  - "núcleo": 23/07 a 14/08/2026.
Termos: o tema (palavras do grupo "núcleo" e "tema amplo") e o nome de cada influenciadora.
Saída pública: data/imprensa/resultados.json (título, veículo, data, link, posição) e manifesto.
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TOP = 10
RECORTES = {"dia do anúncio": ("2026-07-30", "2026-08-03"), "núcleo": ("2026-07-23", "2026-08-15")}  # before: exclusivo
TERMOS_TEMA = ["Hamas desarmamento", "Hamas aceita desarmamento", "acordo Hamas Israel", "Gaza", "Palestina", "cessar-fogo Gaza"]


def buscar(q: str, after: str, before: str, get=None) -> list[dict]:
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{q} after:{after} before:{before}", "hl": "pt-BR", "gl": "BR", "ceid": "BR:pt-419"})
    if get:
        xml = get(url)
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (pesquisa acadêmica ODI)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            xml = r.read().decode("utf-8", "replace")
    out = []
    for i, it in enumerate(ET.fromstring(xml).iter("item"), 1):
        if i > TOP:
            break
        fonte = it.find("source")
        titulo = html.unescape(it.findtext("title") or "")
        veiculo = fonte.text if fonte is not None and fonte.text else (titulo.rsplit(" - ", 1)[-1] if " - " in titulo else "")
        if veiculo and titulo.endswith(" - " + veiculo):
            titulo = titulo[: -len(veiculo) - 3]
        try:
            data = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            data = ""
        out.append({"posicao": i, "titulo": titulo, "veiculo": veiculo, "site": fonte.get("url") if fonte is not None else "",
                    "publicado_em": data, "link": it.findtext("link") or ""})
    return out


def main(root: Path = RAIZ, get=None) -> int:
    atores = json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    consultas = [(t, "tema") for t in TERMOS_TEMA] + [(f'"{a["nome"]}"', "influenciadora") for a in atores]
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    res, erros = [], []
    for rec, (a, b) in RECORTES.items():
        for q, grupo in consultas:
            try:
                itens = buscar(q, a, b, get)
            except Exception as e:  # noqa: BLE001
                erros.append(f"{rec} · {q}: {type(e).__name__} {str(e)[:120]}")
                continue
            res.append({"recorte": rec, "de": a, "ate_exclusivo": b, "consulta": q, "grupo": grupo, "lidos": len(itens), "resultados": itens})
    d = root / "data/imprensa"
    d.mkdir(parents=True, exist_ok=True)
    out = {"gerado_em": agora, "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "fonte": "Google Notícias (RSS, Brasil, pt-BR)",
           "metodo": __doc__.split("\n\n")[1].strip(), "universo": "⛔ o Google não informa o total de resultados",
           "consultas": res, "erros": erros}
    (d / "resultados.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (root / "data/manifest").mkdir(parents=True, exist_ok=True)
    (root / "data/manifest/imprensa_latest.json").write_text(json.dumps({k: v for k, v in out.items() if k != "consultas"} | {
        "consultas": [{k: v for k, v in c.items() if k != "resultados"} for c in res]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"imprensa: {len(res)} consultas, {sum(c['lidos'] for c in res)} resultados; {len(erros)} erro(s)")
    for e in erros[:3]:
        print("  erro:", e)
    return 0 if res else 1


if __name__ == "__main__":
    raise SystemExit(main())
