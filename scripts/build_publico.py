"""Público: quem comenta nas quatro, contas de quem comenta no YouTube e ficha das quatro contas.

Só contagens e códigos anônimos vão ao público (os mesmos do corpus de comentários: A0001 no YouTube, IG0001, TT0001).

1. Público em comum: por rede, autores distintos que comentaram nas publicações do núcleo de cada influenciadora e
   quantos comentaram em duas ou mais. A comparação é dentro da mesma rede: o mesmo @ em redes diferentes não prova que
   é a mesma pessoa, e por isso não entra.
2. Criação das contas (YouTube): data de criação do canal de cada autor (channels.list snippet.publishedAt), por faixa,
   com destaque para os canais criados na linha de base (01/06 a 22/07/2026) e no núcleo (23/07 a 14/08/2026).
3. País declarado (YouTube): snippet.country, campo opcional; o universo é o total de canais lidos.
4. Ficha das quatro: TikTok (seguidores, curtidas, vídeos, criação da conta, do item mais recente lido pela Apify na coleta
   de publicações; sem custo novo) e YouTube (channels.list). Instagram: o coletor de publicações não traz seguidores (⛔).

Entradas no privado: data/comentarios/*.csv, data/canais/youtube_comentaristas.csv, data/apify/tiktok/bruto_posts_*.json.
Saída: data/publico/publico.json.
"""
from __future__ import annotations

import collections
import csv
import glob
import itertools
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_corpus_comentarios import FONTES, PREFIXO, codigos, ler  # noqa: E402

BASE = ("2026-06-01", "2026-07-22")
NUCLEO = ("2026-07-23", "2026-08-14")
FAIXAS = [("até 2019", None, "2019-12-31"), ("2020 a 2023", "2020-01-01", "2023-12-31"), ("2024", "2024-01-01", "2024-12-31"),
          ("2025", "2025-01-01", "2025-12-31"), ("2026, até 31/05", "2026-01-01", "2026-05-31"),
          ("linha de base (01/06 a 22/07/2026)", *BASE), ("núcleo (23/07 a 14/08/2026)", *NUCLEO), ("depois de 14/08/2026", "2026-08-15", None)]


def faixa(data: str) -> str | None:
    d = (data or "")[:10]
    if not d:
        return None
    for rot, ini, fim in FAIXAS:
        if (ini is None or d >= ini) and (fim is None or d <= fim):
            return rot
    return None


def comum(por_autor: dict[str, set], cod: dict[str, str]) -> dict:
    """por_autor: influenciadora -> conjunto de autores (minúsculo)."""
    atores = sorted(por_autor)
    pares = []
    for a, b in itertools.combinations(atores, 2):
        i = por_autor[a] & por_autor[b]
        u = por_autor[a] | por_autor[b]
        pares.append({"a": a, "b": b, "comum": len(i), "jaccard_pct": round(100 * len(i) / len(u), 2) if u else 0,
                      "codigos": sorted(cod.get(x, "?") for x in i)})
    cont = collections.Counter(x for v in por_autor.values() for x in v)
    multi = sorted(cod.get(x, "?") for x, q in cont.items() if q >= 2)
    return {"autores": {a: len(v) for a, v in por_autor.items()}, "autores_distintos": len(cont),
            "em_duas_ou_mais": len(multi), "codigos_duas_ou_mais": multi,
            "pares": sorted(pares, key=lambda p: -p["comum"])}


def contas(canais: list[dict], cod: dict[str, str], primeiro: dict[str, str]) -> dict:
    lidos = [c for c in canais if c.get("criado_em")]
    por_faixa = collections.defaultdict(list)
    for c in lidos:
        por_faixa[faixa(c["criado_em"])].append(cod.get(c["autor"], "?"))
    recentes = []
    for c in lidos:
        p = primeiro.get(c["autor"])
        if p:
            dias = (datetime.fromisoformat(p[:19]) - datetime.fromisoformat(c["criado_em"][:19])).days
            if 0 <= dias <= 30:
                recentes.append(cod.get(c["autor"], "?"))
    paises = collections.defaultdict(list)
    for c in lidos:
        if c.get("pais"):
            paises[c["pais"]].append(cod.get(c["autor"], "?"))
    return {"canais_lidos": len(lidos),
            "faixas": [{"faixa": rot, "canais": len(por_faixa.get(rot, [])), "codigos": sorted(por_faixa.get(rot, []))} for rot, _, _ in FAIXAS],
            "criados_ate_30_dias_antes_do_1o_comentario": len(recentes), "codigos_recentes": sorted(recentes),
            "com_pais": sum(len(v) for v in paises.values()),
            "paises": [{"pais": k, "canais": len(v), "codigos": sorted(v)} for k, v in sorted(paises.items(), key=lambda t: -len(t[1]))]}


def ficha_tiktok(interno: Path, root: Path = RAIZ) -> dict:
    arqs = sorted(glob.glob(str(interno / "data/apify/tiktok/bruto_posts_*.json")))
    if not arqs:
        return {}
    itens = json.loads(Path(arqs[-1]).read_text(encoding="utf-8"))
    out = {}
    for x in sorted(itens, key=lambda x: x.get("createTimeISO") or ""):
        m = x.get("authorMeta") or {}
        if m.get("name"):
            out[m["name"].lower()] = {"perfil": "@" + m["name"], "seguidores": m.get("fans"), "seguindo": m.get("following"),
                                      "curtidas": m.get("heart"), "videos": m.get("video"), "verificada": m.get("verified"),
                                      "criada_em": datetime.fromtimestamp(m["createTime"], timezone.utc).strftime("%Y-%m-%d") if m.get("createTime") else None}
    ator = {}
    for a in json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]:
        h = ((a.get("perfis") or {}).get("tiktok") or {}).get("perfil")
        if h:
            ator[h.lower().lstrip("@")] = a["id"]
    st = Path(arqs[-1]).stem.split("_")[-1]
    return {"fonte": "Apify (clockworks/tiktok-scraper), dados do perfil que vêm junto de cada publicação; o mais recente lido",
            "coletado_em": f"{st[:4]}-{st[4:6]}-{st[6:8]}", "perfis": {ator.get(k, k): v for k, v in out.items()}}


def main(root: Path = RAIZ) -> int:
    interno = os.environ.get("INFL_INTERNO_DIR", "").strip()
    if not interno or not Path(interno).is_dir():
        print("⛔ repositório privado indisponível: nada gerado")
        return 1
    interno = Path(interno)
    cod_resp = {}
    cp = interno / "data/redes/respostas_youtube_codigos.json"
    if cp.exists():
        cod_resp = {k.strip().lower(): v for k, v in json.loads(cp.read_text(encoding="utf-8")).items()}
    saida = {"gerado_em": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
             "metodo": __doc__.split("\n\n")[1].strip() + "\n" + __doc__.split("\n\n")[2].strip(), "comum": {}}
    codigos_rede, primeiro_yt = {}, {}
    for rede, (arq, chave) in FONTES.items():
        p = interno / f"data/comentarios/{rede}.csv"
        if not p.exists():
            continue
        posts = {r[chave] for r in ler(root / arq) if r.get("janela") == "nucleo"}
        linhas = [r for r in ler(p) if r.get("post_id") in posts]
        cod = codigos(linhas, PREFIXO[rede], cod_resp if rede == "youtube" else None)
        codigos_rede[rede] = cod
        por = collections.defaultdict(set)
        for r in linhas:
            a = (r.get("autor") or "").strip().lower()
            if a:
                por[r["ator_id"]].add(a)
                if rede == "youtube":
                    d = r.get("publicado_em") or ""
                    if d and (a not in primeiro_yt or d < primeiro_yt[a]):
                        primeiro_yt[a] = d
        saida["comum"][rede] = {"comentarios": len(linhas), **comum(dict(por), cod)}
    cc = interno / "data/canais/youtube_comentaristas.csv"
    if cc.exists():
        canais = list(csv.DictReader(open(cc, encoding="utf-8")))
        saida["contas_youtube"] = {"autores": len(primeiro_yt), **contas(canais, codigos_rede.get("youtube", {}), primeiro_yt),
                                   "coletado_em": max((c.get("coletado_em") or "" for c in canais), default="")}
    tt = ficha_tiktok(interno)
    yt_p = root / "data/publico/canais_proprios.json"
    ig_p = root / "data/publico/instagram_perfis.json"  # leitura manual da página pública de cada perfil
    saida["ficha"] = {"tiktok": tt, "youtube": json.loads(yt_p.read_text(encoding="utf-8")) if yt_p.exists() else None,
                      "instagram": (json.loads(ig_p.read_text(encoding="utf-8")) if ig_p.exists() else
                                    "⛔ o coletor de publicações do Instagram não traz o número de seguidores")}
    (root / "data/publico").mkdir(parents=True, exist_ok=True)
    (root / "data/publico/publico.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    for rede, c in saida["comum"].items():
        print(f"{rede}: {c['autores_distintos']} autores; {c['em_duas_ou_mais']} em duas ou mais")
    if "contas_youtube" in saida:
        print(f"youtube: {saida['contas_youtube']['canais_lidos']} canais com data; país declarado em {saida['contas_youtube']['com_pais']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
