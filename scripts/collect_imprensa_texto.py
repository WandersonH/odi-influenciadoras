#!/usr/bin/env python3
"""Texto completo das matérias da imprensa, para o corpus do IRaMuTeQ (caderno 07). Sem custo.

Entrada: data/imprensa/resultados.json (collect_imprensa.py), só as buscas do tema. Cada matéria distinta (pelo
link) é lida uma vez. O link do Google Notícias é convertido no endereço do veículo (googlenewsdecoder) e o texto
da página é extraído com trafilatura (sem menus, comentários nem anúncios).

Privacidade e direito autoral: o texto das matérias é de terceiros e fica só no repositório privado
(INFL_INTERNO_DIR/data/imprensa/textos.csv). No público vai só o manifesto, com contagens e motivos de falha.
Sem o privado, o coletor não roda.

Status por matéria: ok; curto (menos de 600 caracteres extraídos: paywall, vídeo ou página só com resumo);
sem_link (não foi possível converter o link do Google); falha_download; sem_texto.
Saídas: privado data/imprensa/textos.csv; público data/manifest/imprensa_texto_latest.json.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MIN_CARACTERES = 600
CAMPOS = ["link_google", "url", "veiculo", "titulo", "publicado_em", "recortes", "consultas", "status", "caracteres", "texto", "coletado_em"]


def materias(resultados: dict) -> list[dict]:
    """Uma linha por matéria distinta das buscas do tema, com os recortes e termos em que apareceu."""
    por_link: dict[str, dict] = {}
    for c in resultados.get("consultas", []):
        if c.get("grupo") != "tema":
            continue
        for r in c.get("resultados", []):
            k = r.get("link") or r.get("titulo")
            m = por_link.setdefault(k, {"link_google": r.get("link"), "veiculo": r.get("veiculo"), "titulo": r.get("titulo"),
                                        "publicado_em": r.get("publicado_em"), "recortes": set(), "consultas": set()})
            m["recortes"].add(c["recorte"])
            m["consultas"].add(c["consulta"])
    return list(por_link.values())


def classificar(texto: str | None) -> str:
    if not texto:
        return "sem_texto"
    return "ok" if len(texto) >= MIN_CARACTERES else "curto"


def main() -> int:
    interno = os.environ.get("INFL_INTERNO_DIR", "").strip()
    if not interno or not Path(interno).is_dir():
        print("⛔ repositório privado indisponível (INFL_INTERNO_DIR): o texto das matérias não é lido")
        return 1
    res = json.loads((RAIZ / "data/imprensa/resultados.json").read_text(encoding="utf-8"))
    ms = materias(res)
    from googlenewsdecoder import gnewsdecoder
    import trafilatura
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    linhas, erros_link = [], []
    for m in ms:
        url, texto, status, erro = "", None, "", ""
        try:
            d = gnewsdecoder(m["link_google"], interval=1)
            ok = d.get("status") if "status" in d else d.get("success")  # a biblioteca usa "status" ou "success" conforme a versão
            url = d.get("decoded_url") or "" if ok else ""
            erro = "" if ok else str(d.get("message") or "")[:200]
        except Exception as e:  # noqa: BLE001
            url, erro = "", f"{type(e).__name__}: {str(e)[:160]}"
        if not url:
            status = "sem_link"
            erros_link.append(erro)
        else:
            try:
                html = trafilatura.fetch_url(url)
            except Exception:  # noqa: BLE001
                html = None
            if not html:
                status = "falha_download"
            else:
                texto = trafilatura.extract(html, include_comments=False, include_tables=False, favor_precision=True)
                status = classificar(texto)
        linhas.append({"link_google": m["link_google"], "url": url, "veiculo": m["veiculo"], "titulo": m["titulo"],
                       "publicado_em": m["publicado_em"], "recortes": "|".join(sorted(m["recortes"])),
                       "consultas": "|".join(sorted(m["consultas"])), "status": status,
                       "caracteres": len(texto or ""), "texto": (texto or "").replace("\r", " "), "coletado_em": agora})
        time.sleep(0.5)
    d = Path(interno) / "data/imprensa"
    d.mkdir(parents=True, exist_ok=True)
    with (d / "textos.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(linhas)
    cont = {}
    for x in linhas:
        cont[x["status"]] = cont.get(x["status"], 0) + 1
    man = {"gerado_em": agora, "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
           "fonte_coleta": {"run_id": res.get("run_id"), "gerado_em": res.get("gerado_em")},
           "metodo": __doc__.split("\n\n")[1].strip(),
           "universo": "⛔ o Google Notícias não informa o total; base = matérias distintas entre os 10 primeiros por termo do tema",
           "materias": len(linhas), "por_status": cont,
           "por_veiculo": {v: {"materias": sum(1 for x in linhas if x["veiculo"] == v), "com_texto": sum(1 for x in linhas if x["veiculo"] == v and x["status"] == "ok")}
                           for v in sorted({x["veiculo"] for x in linhas})},
           "erros_de_link_exemplos": sorted({e for e in erros_link if e})[:5],
           "custo_usd": 0}
    p = RAIZ / "data/manifest"
    p.mkdir(parents=True, exist_ok=True)
    (p / "imprensa_texto_latest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"matérias: {len(linhas)} distintas; status: {cont}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
