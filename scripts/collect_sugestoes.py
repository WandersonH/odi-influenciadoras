#!/usr/bin/env python3
"""O que se busca junto com o nome de cada influenciadora: sugestões do autocompletar do Google (Brasil). Sem custo.

Motivo: o Google Trends não devolveu série para os nomes (volume abaixo do mínimo que ele mostra). O autocompletar
mostra as buscas que o Google associa ao nome hoje, a partir do volume de buscas de todos os usuários.
Consulta: suggestqueries.google.com (client=firefox, hl=pt-BR, gl=br), para o nome entre aspas e sem aspas, e para
"nome + letra" de a a z (técnica de varredura do autocompletar). Cada sugestão conta quantas consultas a devolveram.
Limites: retrato do dia da coleta, não do período do evento; o Google não informa volume nem universo (⛔); filtra
sugestões que considera sensíveis. Saída: data/buscas/sugestoes.json (agregados do Google, sem dado pessoal).
"""
from __future__ import annotations

import json
import os
import string
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
URL = "https://suggestqueries.google.com/complete/search?client=firefox&hl=pt-BR&gl=br&q="


def sugerir(q: str) -> list[str]:
    req = urllib.request.Request(URL + urllib.parse.quote(q), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        dado = json.loads(r.read().decode("utf-8", "replace"))
    return [s for s in dado[1] if isinstance(s, str)]


def consultas(nome: str) -> list[str]:
    return [nome, f'"{nome}"'] + [f"{nome} {c}" for c in string.ascii_lowercase]


def main(busca=sugerir) -> int:
    atores = json.loads((RAIZ / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    saida, erros = {}, []
    for a in atores:
        cont, feitas = Counter(), 0
        for q in consultas(a["nome"]):
            try:
                for s in busca(q):
                    cont[s.lower().strip()] += 1
                feitas += 1
            except Exception as e:  # noqa: BLE001
                erros.append(f"{q}: {type(e).__name__}: {str(e)[:120]}")
            time.sleep(0.4)
        saida[a["id"]] = {"nome": a["nome"], "consultas_feitas": feitas, "consultas_previstas": len(consultas(a["nome"])),
                          "sugestoes": [[s, n] for s, n in sorted(cont.items(), key=lambda x: (-x[1], x[0]))]}
    out = {"gerado_em": agora, "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "metodo": " ".join(__doc__.split("\n", 1)[1].split("\n")).strip(),
           "universo": "⛔ o Google não informa volume nem quantas sugestões existem", "por_influenciadora": saida, "erros": erros, "custo_usd": 0}
    d = RAIZ / "data/buscas"
    d.mkdir(parents=True, exist_ok=True)
    (d / "sugestoes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in saida.items():
        print(f"{v['nome']}: {v['consultas_feitas']}/{v['consultas_previstas']} consultas, {len(v['sugestoes'])} sugestões distintas; "
              + ", ".join(s for s, _ in v["sugestoes"][:8]))
    if erros:
        print(f"{len(erros)} erro(s): {erros[:2]}")
    return 0 if any(v["consultas_feitas"] for v in saida.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
