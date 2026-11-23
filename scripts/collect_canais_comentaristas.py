"""Canais do YouTube: quem comenta nos vídeos do núcleo e os canais das próprias influenciadoras (API oficial, sem custo).

1. comments.list (id=, até 50 por chamada, 1 unidade): o canal de cada autor de comentário lido (authorChannelId).
2. channels.list (id=, até 50 por chamada, 1 unidade): data de criação do canal (snippet.publishedAt) e país declarado
   (snippet.country, campo opcional que o dono preenche se quiser).
3. channels.list dos canais das influenciadoras (snippet, statistics): inscritos, vídeos, visualizações e criação.

Entrada: <privado>/data/comentarios/youtube.csv. Saídas:
- privado: data/canais/youtube_comentaristas.csv (autor, canal, criação, país) — identifica pessoas, não vai ao público;
- público: data/publico/canais_proprios.json (só os canais das quatro).
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _get(rota: str, q: dict) -> dict:
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{rota}?" + urllib.parse.urlencode(q), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def lotes(xs: list, n: int = 50):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def canais_dos_comentarios(ids: list[str], chave: str, get=_get) -> tuple[dict, int, list]:
    """comment_id -> channel_id."""
    out, chamadas, erros = {}, 0, []
    for lote in lotes(ids):
        try:
            d = get("comments", {"part": "snippet", "id": ",".join(lote), "maxResults": 50, "key": chave})
        except urllib.error.HTTPError as e:
            erros.append(f"comments.list HTTP {e.code}")
            continue
        chamadas += 1
        for it in d.get("items", []):
            cid = ((it.get("snippet") or {}).get("authorChannelId") or {}).get("value")
            if cid:
                out[it["id"]] = cid
    return out, chamadas, erros


def dados_dos_canais(ids: list[str], chave: str, parte: str = "snippet", get=_get) -> tuple[dict, int, list]:
    out, chamadas, erros = {}, 0, []
    for lote in lotes(sorted(set(ids))):
        try:
            d = get("channels", {"part": parte, "id": ",".join(lote), "maxResults": 50, "key": chave})
        except urllib.error.HTTPError as e:
            erros.append(f"channels.list HTTP {e.code}")
            continue
        chamadas += 1
        for it in d.get("items", []):
            sn, st = it.get("snippet") or {}, it.get("statistics") or {}
            out[it["id"]] = {"criado_em": sn.get("publishedAt", ""), "pais": sn.get("country", ""), "titulo": sn.get("title", ""),
                             "inscritos": None if st.get("hiddenSubscriberCount") else st.get("subscriberCount"),
                             "videos": st.get("videoCount"), "visualizacoes": st.get("viewCount")}
    return out, chamadas, erros


def main() -> int:
    interno = os.environ.get("INFL_INTERNO_DIR", "").strip()
    chave = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not interno or not Path(interno).is_dir():
        print("⛔ repositório privado indisponível: nada lido")
        return 1
    if not chave:
        print("⛔ YOUTUBE_API_KEY ausente: nada lido")
        return 1
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    linhas = list(csv.DictReader(open(Path(interno) / "data/comentarios/youtube.csv", encoding="utf-8")))
    c2c, ch1, e1 = canais_dos_comentarios([r["comment_id"] for r in linhas], chave)
    canais, ch2, e2 = dados_dos_canais(list(c2c.values()), chave)
    dest = Path(interno) / "data/canais"
    dest.mkdir(parents=True, exist_ok=True)
    vistos = {}
    for r in linhas:
        a = (r.get("autor") or "").strip().lower()
        cid = c2c.get(r["comment_id"])
        if a and cid and a not in vistos:
            vistos[a] = {"autor": a, "canal_id": cid, "criado_em": canais.get(cid, {}).get("criado_em", ""),
                         "pais": canais.get(cid, {}).get("pais", ""), "coletado_em": agora}
    with open(dest / "youtube_comentaristas.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["autor", "canal_id", "criado_em", "pais", "coletado_em"])
        w.writeheader()
        w.writerows(vistos.values())
    man = json.loads((RAIZ / "data/manifest/youtube_latest.json").read_text(encoding="utf-8"))
    proprios_ids = {a["canal_id"]: a["ator"] for a in man["atores"] if a.get("canal_id")}
    prop, ch3, e3 = dados_dos_canais(list(proprios_ids), chave, "snippet,statistics")
    pub = RAIZ / "data/publico"
    pub.mkdir(parents=True, exist_ok=True)
    (pub / "canais_proprios.json").write_text(json.dumps({
        "gerado_em": agora, "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "fonte": "YouTube Data API v3, channels.list (snippet, statistics)",
        "canais": {proprios_ids[k]: {"canal_id": k, **{c: v[c] for c in ("titulo", "criado_em", "pais", "inscritos", "videos", "visualizacoes")}}
                   for k, v in prop.items()}}, ensure_ascii=False, indent=1), encoding="utf-8")
    (pub / "canais_comentaristas_execucao.json").write_text(json.dumps({
        "gerado_em": agora, "run_id": os.environ.get("GITHUB_RUN_ID", "local"), "comentarios_lidos": len(linhas),
        "comentarios_com_canal": len(c2c), "autores": len({(r.get('autor') or '').strip().lower() for r in linhas} - {""}),
        "autores_com_canal": len(vistos), "canais_com_dados": sum(1 for v in vistos.values() if v["criado_em"]),
        "chamadas": {"comments.list": ch1, "channels.list": ch2 + ch3}, "cota_unidades": ch1 + ch2 + ch3, "custo_usd": 0,
        "erros": e1 + e2 + e3}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(linhas)} comentários; canal de {len(c2c)}; {len(vistos)} autores com canal; cota {ch1 + ch2 + ch3} unidades; erros {len(e1 + e2 + e3)}")
    return 0 if vistos else 1


if __name__ == "__main__":
    sys.exit(main())
