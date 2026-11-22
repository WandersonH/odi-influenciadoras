#!/usr/bin/env python3
"""Checagens publicadas (ClaimReview) sobre o acordo do Hamas e sobre as influenciadoras: Google Fact Check Tools API (grátis).

Porta do collect_checagens.py do ODI Atlas. Fonte: https://factchecktools.googleapis.com/v1alpha1/claims:search, que
agrega as checagens publicadas pelas agências no formato ClaimReview. O estudo não dá veredito: mostra o que cada
agência checou, com o rótulo dela, a data e o link.

Chave: FACTCHECK_API_KEY; sem ela, a do YouTube (vale se a Fact Check Tools API estiver ativa no mesmo projeto do
Google Cloud e a chave não estiver restrita a outra API).

A API só filtra por idade (maxAgeDays, contada a partir de hoje). O coletor pede desde o início da linha de base e
marca a janela de cada checagem pela data da checagem.

Universo: a API não informa o total de checagens existentes (⛔); o manifesto registra quanto foi lido por consulta.
Saída pública: data/checagens/checagens.json. Nome de pessoa comum em "quem disse" é omitido, como no Atlas.
"""
from __future__ import annotations

import json
import os
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
MAX_PAGINAS = 5
TEMA = ["Hamas", "desarmamento Hamas", "Gaza", "Palestina", "cessar-fogo Gaza", "Israel Hamas acordo"]
GENERICOS = ("boato", "rede", "desinforma", "varias fontes", "usuario", "post", "perfis", "internet", "whatsapp", "video",
             "site", "blog", "tiktok", "instagram", "facebook", "x (antigo twitter)", "twitter", "youtube")


def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower()) if unicodedata.category(c) != "Mn")


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def achatar(claims, consulta, grupo):
    out = []
    for c in claims or []:
        for r in c.get("claimReview") or []:
            pub = r.get("publisher") or {}
            out.append({"afirmacao": " ".join(str(c.get("text") or "").split()), "quem_disse": c.get("claimant"),
                        "data_afirmacao": (c.get("claimDate") or "")[:10] or None,
                        "agencia": pub.get("name") or pub.get("site"), "site": pub.get("site"),
                        "titulo": r.get("title"), "url": r.get("url"), "data_checagem": (r.get("reviewDate") or "")[:10] or None,
                        "rotulo": r.get("textualRating"), "idioma": r.get("languageCode"),
                        "consulta": [consulta], "grupo": [grupo]})
    return out


def buscar(chave, consulta, grupo, dias, erros, get=get_json):
    itens, token, paginas = [], None, 0
    for _ in range(MAX_PAGINAS):
        q = {"query": consulta, "languageCode": "pt", "maxAgeDays": dias, "pageSize": 100, "key": chave}
        if token:
            q["pageToken"] = token
        try:
            d = get(URL + "?" + urllib.parse.urlencode(q))
        except urllib.error.HTTPError as e:
            corpo = e.read().decode("utf-8", "replace")[:300] if hasattr(e, "read") else ""
            erros.append(f"{consulta}: HTTP {e.code} {corpo.replace(chave, '[chave]')}")
            break
        except Exception as e:  # noqa: BLE001
            erros.append(f"{consulta}: {type(e).__name__} {str(e)[:200].replace(chave, '[chave]')}")
            break
        paginas += 1
        itens += achatar(d.get("claims"), consulta, grupo)
        token = d.get("nextPageToken")
        if not token:
            break
    return itens, paginas


def quem_publico(quem, nomes_monitorados):
    if not quem:
        return None
    q = norm(quem)
    if any(norm(n) in q for n in nomes_monitorados) or any(g in q for g in GENERICOS):
        return quem
    return "pessoa ou perfil (nome omitido)"


def janela(d, janelas):
    if not d:
        return "sem data"
    b, n = janelas["base"], janelas["nucleo"]
    if n["inicio"][:10] <= d <= n["fim"][:10]:
        return "nucleo"
    if b["inicio"][:10] <= d <= b["fim"][:10]:
        return "base"
    return "depois" if d > n["fim"][:10] else "antes"


def juntar(itens, janelas, nomes):
    por = {}
    for x in itens:
        k = x["url"] or (x["agencia"], x["afirmacao"])
        if k in por:
            por[k]["consulta"] = sorted(set(por[k]["consulta"]) | set(x["consulta"]))
            por[k]["grupo"] = sorted(set(por[k]["grupo"]) | set(x["grupo"]))
        else:
            por[k] = dict(x)
    out = list(por.values())
    for x in out:
        texto = norm(f"{x['afirmacao']} {x['titulo'] or ''} {x['quem_disse'] or ''}")
        x["cita_influenciadora"] = [n for n in nomes if norm(n) in texto]
        x["janela"] = janela(x["data_checagem"], janelas)
        x["quem_disse"] = quem_publico(x["quem_disse"], nomes)
    out.sort(key=lambda x: (x["data_checagem"] or "", x["agencia"] or ""), reverse=True)
    return out


def main(argv=None, raiz: Path = RAIZ, get=get_json, hoje: date | None = None) -> int:
    chave = (os.environ.get("FACTCHECK_API_KEY") or os.environ.get("YOUTUBE_API_KEY") or "").strip()
    if not chave:
        print("⛔ falta a chave do Google Cloud (FACTCHECK_API_KEY ou YOUTUBE_API_KEY): nada coletado")
        return 1
    projeto = json.loads((raiz / "data/config/projeto.json").read_text(encoding="utf-8"))
    atores = json.loads((raiz / "data/config/atores.json").read_text(encoding="utf-8"))
    janelas = projeto["janelas"]
    nomes = [a["nome"] for a in atores["atores"]]
    hoje = hoje or datetime.now(timezone.utc).date()
    dias = (hoje - date.fromisoformat(janelas["base"]["inicio"][:10])).days + 1
    consultas = [(c, "tema") for c in TEMA] + [(f'"{n}"', "influenciadora") for n in nomes]
    erros, itens, por_consulta = [], [], []
    for c, grupo in consultas:
        lidos, paginas = buscar(chave, c, grupo, dias, erros, get)
        itens += lidos
        por_consulta.append({"consulta": c, "grupo": grupo, "lidos": len(lidos), "paginas": paginas,
                             "limite_paginas": paginas >= MAX_PAGINAS})
    todas = juntar(itens, janelas, nomes)
    destino = raiz / "data/checagens"
    destino.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    falhou_tudo = len(erros) == len(consultas)
    if not falhou_tudo:
        (destino / "checagens.json").write_text(json.dumps({"gerado_em": agora, "checagens": todas}, ensure_ascii=False, indent=1), encoding="utf-8")
    manifesto = {"gerado_em": agora, "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "fonte": URL, "custo_usd": 0,
                 "max_age_days": dias, "universo": "⛔ a API não informa o total de checagens existentes",
                 "consultas": por_consulta, "checagens_unicas": len(todas),
                 "no_nucleo": sum(1 for x in todas if x["janela"] == "nucleo"),
                 "citam_influenciadora": sum(1 for x in todas if x["cita_influenciadora"]), "erros": erros,
                 "status": "bloqueado" if falhou_tudo else "ok" if not erros else "parcial"}
    (raiz / "data/manifest").mkdir(parents=True, exist_ok=True)
    (raiz / "data/manifest/checagens_latest.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"checagens: {len(todas)} únicas ({manifesto['no_nucleo']} no núcleo; {manifesto['citam_influenciadora']} citam influenciadora); "
          f"{len(erros)} erro(s); status {manifesto['status']}")
    for e in erros[:3]:
        print("  erro:", e)
    return 1 if falhou_tudo else 0


if __name__ == "__main__":
    raise SystemExit(main())
