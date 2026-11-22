#!/usr/bin/env python3
"""Chamadas à Apify, portadas do ODI Atlas (collect_meta_apify.py e collect_meta_anuncios_apify.py).

Diferença deliberada: aqui NÃO existe consulta de saldo nem de limites da conta (/users/me/limits). O gasto é
controlado por dois freios que não dependem dela: o teto de cada execução (maxTotalChargeUsd) e a soma dos custos
gravados nos manifestos. O token vem só de variável de ambiente e nunca é gravado nem impresso.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

API = "https://api.apify.com/v2"


def api(method: str, path: str, token: str, body=None, timeout: int = 360):
    req = urllib.request.Request(f"{API}{path}", method=method,
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        # motivo informado pela Apify (tipo e mensagem; nunca contém o token), para diagnosticar 401/402/403
        try:
            err = (json.loads(e.read() or b"{}") or {}).get("error") or {}
            print(f"Apify HTTP {e.code}: {err.get('type')}: {str(err.get('message'))[:160]}", file=sys.stderr)
            e.msg = f"{e.msg} [{err.get('type')}]"
        except Exception:  # noqa: BLE001
            pass
        raise


class ErroDepoisDaExecucao(Exception):
    """A execução na Apify aconteceu (e pode ter sido cobrada), mas o resultado não pôde ser baixado."""

    def __init__(self, run: dict, causa: Exception):
        super().__init__(f"execução {run.get('id')} feita, resultado não baixado: {type(causa).__name__}")
        self.run = run


def baixar_itens(token: str, dataset_id: str, pagina: int = 500) -> list:
    """Baixa o resultado em páginas, com nova tentativa: um resultado grande não se perde por uma queda de conexão."""
    itens, offset = [], 0
    while True:
        for tentativa in range(4):
            try:
                lote = api("GET", f"/datasets/{dataset_id}/items?clean=true&format=json&limit={pagina}&offset={offset}", token) or []
                break
            except Exception:  # noqa: BLE001
                if tentativa == 3:
                    raise
                time.sleep(5 * (tentativa + 1))
        itens += lote
        if len(lote) < pagina:
            return itens
        offset += pagina


def run_actor(token: str, actor: str, payload: dict, cap: float):
    """Roda o ator com teto de cobrança `cap` (US$) e devolve (execução, itens)."""
    run = api("POST", f"/acts/{actor}/runs?waitForFinish=300&maxTotalChargeUsd={cap}", token, payload)["data"]
    while run.get("status") in ("READY", "RUNNING"):
        run = api("GET", f"/actor-runs/{run['id']}?waitForFinish=300", token)["data"]
    try:
        return run, baixar_itens(token, run["defaultDatasetId"])
    except Exception as e:  # noqa: BLE001
        raise ErroDepoisDaExecucao(run, e) from e


LIMITES = ("resultsLimit", "maxItems")


def execucao_anterior(token: str, actor: str, payload: dict, desde_utc: str):
    """Procura uma execução já feita (e paga) deste ator, desde `desde_utc`, com o mesmo pedido (fora o limite de itens),
    e devolve (execução, itens) sem rodar nada de novo. None se não houver. Não consulta saldo: só lista execuções do ator."""
    alvo = {k: v for k, v in payload.items() if k not in LIMITES}
    for r in (api("GET", f"/acts/{actor}/runs?desc=1&limit=40", token)["data"].get("items") or []):
        if (r.get("startedAt") or "") < desde_utc or r.get("status") != "SUCCEEDED":
            continue
        run = api("GET", f"/actor-runs/{r['id']}", token)["data"]
        try:
            entrada = api("GET", f"/key-value-stores/{run['defaultKeyValueStoreId']}/records/INPUT", token) or {}
        except Exception:  # noqa: BLE001
            continue
        if {k: v for k, v in entrada.items() if k not in LIMITES} == alvo:
            return run, baixar_itens(token, run["defaultDatasetId"])
    return None


def custo_run(run: dict) -> float:
    """Custo cobrado: eventos cobrados × preço do evento (faixa FREE quando há faixas); senão usageTotalUsd."""
    ev = ((run.get("pricingInfo") or {}).get("pricingPerEvent") or {}).get("actorChargeEvents") or {}
    tot = 0.0
    for nome, n in (run.get("chargedEventCounts") or {}).items():
        e = ev.get(nome) or {}
        preco = e.get("eventPriceUsd")
        if preco is None:
            preco = ((e.get("eventTieredPricingUsd") or {}).get("FREE") or {}).get("tieredEventPriceUsd") or 0
        tot += float(n or 0) * float(preco or 0)
    return round(tot or float(run.get("usageTotalUsd") or 0), 4)


def erro_curto(e: Exception) -> str:
    """Descrição do erro sem cabeçalhos nem token."""
    return f"{type(e).__name__} {getattr(e, 'code', '')} {getattr(e, 'msg', '') if getattr(e, 'code', None) else ''}".strip()[:160]
