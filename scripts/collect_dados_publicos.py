#!/usr/bin/env python3
"""Caderno de dados públicos: bases oficiais abertas que dão contexto ao estudo. Sem custo.

1. IBGE, Censos Demográficos (API de agregados, servicodados.ibge.gov.br/api/v3):
   - tabela 137 (População residente, por religião, 1991–2010): Islâmica (2000, categoria 95271) e Islamismo (2010,
     categoria 100426), Brasil e estados;
   - tabela 10201 (Censo 2022, 10 anos ou mais, grandes grupos de religião), Brasil e estados. Em 2022 o IBGE só abre os
     grandes grupos: o islamismo fica dentro de "outras religiosidades" (o detalhe está nos microdados de acesso
     controlado, nota metodológica 06/2026). Por isso 2022 não tem número de muçulmanos aqui (⛔).
2. Disque 100 (Ouvidoria Nacional de Direitos Humanos, dados.gov.br, conjunto "ouvidoria-nacional-de-direitos-humanos--ondh"):
   CSV por semestre ou trimestre. Primeiro run em modo --diagnostico: baixa o arquivo, grava o cabeçalho e a contagem dos
   valores das colunas de religião, motivação e violação, para a regra de filtro ser escrita sobre as colunas reais.
Saídas: data/dados_publicos/ibge.json, data/dados_publicos/disque100_diagnostico.json (e, depois, disque100.json).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
IBGE = "https://servicodados.ibge.gov.br/api/v3/agregados"
DISQUE100 = {
    "2026-S1": "https://www.gov.br/mdh/pt-br/acesso-a-informacao/dados-abertos/disque100/disque100-primeiro-semestre-2026",
    "2026-T3": "https://www.gov.br/mdh/pt-br/acesso-a-informacao/dados-abertos/disque100/disque100-terceiro-trimestre-2026",
    "2025-S2": "https://www.gov.br/mdh/pt-br/acesso-a-informacao/dados-abertos/disque100/disque100-segundo-semestre-2025",
}
UA = {"User-Agent": "odi-influenciadoras-coletor/1.0 (+https://github.com/WandersonH/odi-influenciadoras)"}
csv.field_size_limit(10_000_000)


def get(url: str, timeout: int = 300) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.geturl(), r.headers.get("Content-Type", "")


def ibge_serie(tabela: int, periodos: str, variavel: int, nivel: str, classif: str) -> list:
    url = f"{IBGE}/{tabela}/periodos/{periodos}/variaveis/{variavel}?localidades={nivel}[all]&classificacao={classif}"
    dado, _, _ = get(url, 120)
    return json.loads(dado)


def achatar(res: list) -> list[dict]:
    out = []
    for v in res:
        for r in v["resultados"]:
            cat = next(iter(r["classificacoes"][0]["categoria"].values())) if r["classificacoes"] else "Total"
            for s in r["series"]:
                for ano, val in s["serie"].items():
                    out.append({"variavel": v["variavel"], "categoria": cat, "local": s["localidade"]["nome"], "local_id": s["localidade"]["id"],
                                "nivel": s["localidade"]["nivel"]["id"], "ano": ano,
                                "valor": int(val) if str(val).isdigit() else None, "valor_bruto": val})
    return out


def coletar_ibge() -> dict:
    meta137, _, _ = get(f"{IBGE}/137/metadados", 120)
    cats = next(c for c in json.loads(meta137)["classificacoes"] if str(c["id"]) == "133")["categorias"]
    total = next(k["id"] for k in cats if k["nome"].strip().lower() == "total")  # o código do total muda de tabela para tabela
    t137 = []
    for nivel in ("N1", "N3"):
        t137 += achatar(ibge_serie(137, "2000|2010", 93, nivel, f"133[95271,100426,{total}]"))
    t2022 = []
    # a tabela 10201 tem variável própria: descobre pelo metadado em vez de supor
    meta, _, _ = get(f"{IBGE}/10201/metadados", 120)
    m = m22 = json.loads(meta)
    var = m["variaveis"][0]["id"]
    for nivel in ("N1", "N3"):
        t2022 += achatar(ibge_serie(10201, "2022", var, nivel, "133[all]"))
    # malhas do IBGE (qualidade mínima) para o mapa da página: estados (contorno) e municípios (cor)
    base = "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?qualidade=minima&formato=application/vnd.geo%2Bjson&intrarregiao="
    for nivel, arq in (("UF", "malha_uf.geojson"), ("municipio", "malha_municipios.geojson")):
        malha, _, _ = get(base + nivel, 300)
        (RAIZ / "data/dados_publicos" / arq).write_bytes(malha)
        print(f"malha {nivel}: {len(malha) // 1024} KB")
    # municípios em formato compacto: código → [nome, islamismo 2010, população 2010, outras religiosidades 2022, 10+ anos 2022]
    mun = {}
    for x in achatar(ibge_serie(137, "2010", 93, "N6", f"133[100426,{total}]")):
        mm = mun.setdefault(str(x["local_id"]), [x["local"], None, None, None, None])
        mm[1 if x["categoria"] == "Islamismo" else 2] = x["valor"]
    cats22 = next(c for c in m22["classificacoes"] if str(c["id"]) == "133")["categorias"]
    ids22 = {k["nome"]: k["id"] for k in cats22}
    for x in achatar(ibge_serie(10201, "2022", var, "N6", f"133[{ids22['Outras religiosidades']},{ids22['Total']}]")):
        mm = mun.setdefault(str(x["local_id"]), [x["local"], None, None, None, None])
        mm[3 if x["categoria"] == "Outras religiosidades" else 4] = x["valor"]
    (RAIZ / "data/dados_publicos/municipios.json").write_text(json.dumps({"campos": ["nome", "islamismo_2010", "populacao_2010", "outras_religiosidades_2022", "pessoas_10_anos_ou_mais_2022"], "municipios": mun}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"municípios: {len(mun)}; com muçulmanos em 2010: {sum(1 for v in mun.values() if v[1])}")
    return {"tabela_137": t137, "tabela_10201": t2022, "tabela_10201_nome": m["nome"], "tabela_10201_variavel": m["variaveis"][0]["nome"]}


def ler_csv(dado: bytes) -> tuple[list[str], list[list[str]]]:
    if dado[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(dado))
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        dado = z.read(nome)
    for enc in ("utf-8-sig", "latin-1"):
        try:
            txt = dado.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    amostra = txt[:5000]
    sep = ";" if amostra.count(";") > amostra.count(",") else ","
    linhas = list(csv.reader(io.StringIO(txt), delimiter=sep))
    return linhas[0], linhas[1:]


def diagnosticar_disque100() -> dict:
    out = {}
    for rotulo, url in DISQUE100.items():
        try:
            dado, final, tipo = get(url)
            if b"<html" in dado[:2000].lower():
                links = re.findall(rb'href="([^"]+?(?:\.csv|\.zip|@@download/file)[^"]*)"', dado)
                if links:
                    alvo = links[0].decode()
                    alvo = alvo if alvo.startswith("http") else "https://www.gov.br" + alvo
                    dado, final, tipo = get(alvo)
            cab, linhas = ler_csv(dado)
            cols = {}
            for i, c in enumerate(cab):
                if re.search(r"relig|motiv|viola|intoler|data|uf|tipo|grupo|cen[aá]rio|canal", c, re.I):
                    cols[c] = Counter(l[i] for l in linhas if i < len(l)).most_common(25)
            out[rotulo] = {"url_final": final, "content_type": tipo, "bytes": len(dado), "linhas": len(linhas),
                           "cabecalho": cab, "exemplo": linhas[:2], "valores": cols}
            print(f"{rotulo}: {len(linhas)} linhas, {len(cab)} colunas; colunas: {cab}")
        except Exception as e:  # noqa: BLE001
            out[rotulo] = {"erro": f"{type(e).__name__}: {str(e)[:200]}"}
            print(f"{rotulo}: erro {e}")
    return out


FTP22 = "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Microdados_e_Areas_de_Ponderacao/"


def diagnosticar_censo2022() -> dict:
    """Microdados de acesso público do Censo 2022 (ago/2026): a variável de religião traz o islamismo separado?
    Lê o layout (xlsx) e o dicionário (PDF) e grava as linhas e o trecho que falam de religião."""
    import urllib.parse
    out = {}
    lay, _, _ = get(FTP22 + "Documentacao/" + urllib.parse.quote("Layout e dicionário/Layout Microdados CD2022 - acesso Público.xlsx"), 300)
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(lay), read_only=True, data_only=True)
    linhas = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            txt = " | ".join(str(c) for c in row if c is not None)
            if re.search(r"relig|culto|peso|munic|v0001|v0002|ponder", txt, re.I):
                linhas.append(f"[{ws.title}] {txt[:300]}")
    out["layout_publico"] = linhas[:80]
    dic, _, _ = get(FTP22 + "Documentacao/" + urllib.parse.quote("Layout e dicionário/Dicionário de Variáveis - Microdados CD2022.pdf"), 300)
    from pypdf import PdfReader
    texto = "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(dic)).pages)
    trechos = [texto[max(0, m.start() - 300): m.start() + 2500] for m in re.finditer(r"(?i)religi[aã]o ou culto", texto)][:3]
    out["dicionario_trechos"] = trechos
    out["dicionario_menciona_islamismo"] = bool(re.search(r"(?i)islam", texto))
    for l in linhas[:40]:
        print(l)
    print("dicionário menciona islamismo:", out["dicionario_menciona_islamismo"])
    for t in trechos[:1]:
        print(t[:2000].replace("\n", " / "))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnostico", action="store_true")
    ap.add_argument("--censo2022", action="store_true", help="diagnóstico da variável de religião nos microdados públicos do Censo 2022")
    a = ap.parse_args(argv)
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    d = RAIZ / "data/dados_publicos"
    d.mkdir(parents=True, exist_ok=True)
    rc = 0
    try:
        ib = coletar_ibge()
        ib.update({"gerado_em": agora, "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "fonte": IBGE,
                   "metodo": __doc__.split("\n\n")[1].strip()})
        (d / "ibge.json").write_text(json.dumps(ib, ensure_ascii=False, indent=1), encoding="utf-8")
        br = [x for x in ib["tabela_137"] if x["nivel"] == "N1" and x["valor"] and x["categoria"] != "Total"]
        print("IBGE 137 Brasil:", [(x["categoria"], x["ano"], x["valor"]) for x in br])
        print("IBGE 10201 Brasil:", [(x["categoria"], x["valor"]) for x in ib["tabela_10201"] if x["nivel"] == "N1"])
    except Exception as e:  # noqa: BLE001
        print(f"IBGE: erro {type(e).__name__}: {e}")
        rc = 1
    if a.censo2022:
        try:
            cg = diagnosticar_censo2022()
            (d / "censo2022_diagnostico.json").write_text(json.dumps({"gerado_em": agora, **cg}, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            print(f"Censo 2022: erro {type(e).__name__}: {e}")
            rc = 1
        return rc
    if a.diagnostico:
        dg = diagnosticar_disque100()
        (d / "disque100_diagnostico.json").write_text(json.dumps({"gerado_em": agora, "arquivos": dg}, ensure_ascii=False, indent=1), encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
