#!/usr/bin/env python3
"""Caderno "O que dizem": publicações de cada influenciadora por tema, por rede. Mesmo método do caderno "O que dizem"
do ODI Espanha e "O que as campanhas dizem" do ODI Atlas (dicionário aberto por regras, nuvem por nº de publicações,
hashtags, taxa de interação), aplicado à LEGENDA e à FALA TRANSCRITA de cada publicação, quando houver.

Entrada: data/youtube/videos.csv, data/instagram/posts.csv, data/tiktok/posts.csv, data/transcricoes/<rede>.csv,
data/config/temas.json, data/config/atores.json, data/config/projeto.json.
Saída: data/<rede>/conteudo.json (público: as publicações das próprias influenciadoras).

Taxa de interação = (curtidas + comentários + compartilhamentos) ÷ visualizações (interação por visualização; não mede
apoio). Publicações fora do recorte (01/06 a 14/08/2026) ficam fora.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import texto as tx  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
FONTES = {"youtube": ("data/youtube/videos.csv", "video_id"), "instagram": ("data/instagram/posts.csv", "post_id"),
          "tiktok": ("data/tiktok/posts.csv", "post_id")}
ROTULO = {"youtube": "YouTube", "instagram": "Instagram", "tiktok": "TikTok"}


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    s = str(v if v is not None else "").strip()
    return int(float(s)) if s.replace(".", "", 1).lstrip("-").isdigit() else None


def taxa(p: dict):
    v = p["visualizacoes"]
    return None if not v else sum(p[k] or 0 for k in ("curtidas", "comentarios", "compartilhamentos")) / v


def main(argv=None, root: Path = RAIZ) -> int:
    cfg = json.loads((root / "data/config/temas.json").read_text(encoding="utf-8"))
    # termos sem letra latina (árabe, emoji) somem na normalização e casariam com tudo: viram busca literal no texto original
    latinos = {k: [tx.term_regex(t) for t in v if tx.norm(t.rstrip("*")).strip()] for k, v in cfg["temas"].items()}
    literais = {k: [t for t in v if not tx.norm(t.rstrip("*")).strip()] for k, v in cfg["temas"].items()}
    atores = json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    jan = json.loads((root / "data/config/projeto.json").read_text(encoding="utf-8"))["janelas"]
    desde, ate = jan["base"]["inicio"][:10], jan["nucleo"]["fim"][:10]
    for rede, (arq, chave) in FONTES.items():
        rows = [r for r in ler(root / arq) if r.get("janela") in ("base", "nucleo")]
        if not rows:
            print(f"{rede}: ⛔ sem acervo no recorte, conteudo.json não gerado")
            continue
        fala = {r["post_id"]: r["texto"] for r in ler(root / f"data/transcricoes/{rede}.csv") if r.get("status") == "ok"}
        for r in rows:
            r["post_id"] = r[chave]
            r.setdefault("perfil", rede)
            r["legenda"] = r.get("texto") or r.get("titulo") or ""
            r["texto"] = r["legenda"]
        padrao = tx.texto_padrao(rows)
        out = {"schema_version": 1, "gerado_em_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rede": rede,
               "fonte": f"{ROTULO[rede]} público: perfis confirmados em data/config/atores.json",
               "metodo": cfg["nota"] + f" Links removidos e trechos repetidos em {tx.LIMIAR_REPETICAO}+ publicações do mesmo perfil descartados."
                         " Taxa de interação = (curtidas + comentários + compartilhamentos) ÷ visualizações; não mede apoio.",
               "dicionario": {"versao": cfg["versao"], "estado": cfg["estado"]}, "temas": list(cfg["temas"]) + ["sem_tema"],
               "desde": desde, "ate": ate, "fases": cfg["fases"], "fases_nota": cfg.get("fases_nota"), "evento": cfg.get("evento"), "atores": {}}
        com_tema = com_fala = 0
        for a in atores:
            meus = sorted([r for r in rows if r["ator_id"] == a["id"]], key=lambda r: r["publicado_em"], reverse=True)
            if not meus:
                continue
            nome = tx.norm(a["nome"]).split()
            excluir = set(nome) | {"".join(nome)} | {tx.tag_key(r["perfil"]) for r in meus}
            pubs, textos, tags = [], [], []
            for r in meus:
                util = tx.texto_util(r, padrao)
                f = fala.get(r["post_id"], "")
                textos.append(f"{util} {f}")
                tg = {tx.tag_key(t) for t in tx.HASHTAG.findall(r["legenda"])} - excluir
                tags.append(tg)
                ach = tx.norm(f"{util} {f}")
                bruto = f"{r['legenda']} {f}"
                achados = [k for k in cfg["temas"] if any(rg.search(ach) for rg in latinos[k]) or any(t in bruto for t in literais[k])]
                p = {"post_id": r["post_id"], "url": r["url"], "texto": r["legenda"][:400], "tipo": r.get("tipo") or "vídeo",
                     "publicado_em": r["publicado_em"], "janela": r["janela"], "tem_fala": bool(f),
                     **{k: num(r.get(k)) for k in ("visualizacoes", "curtidas", "comentarios", "compartilhamentos")},
                     "hashtags": sorted(tg), "temas": achados or ["sem_tema"]}
                t_ = taxa(p)
                p["taxa_interacao"] = round(t_, 4) if t_ is not None else None
                pubs.append(p)
            com_tema += sum(1 for p in pubs if p["temas"] != ["sem_tema"])
            com_fala += sum(1 for p in pubs if p["tem_fala"])
            taxas = [p["taxa_interacao"] for p in pubs if p["taxa_interacao"] is not None]
            fase = {}
            for fz in cfg["fases"]:
                ps = [p for p in pubs if fz["de"] <= p["publicado_em"][:10] <= fz["ate"]]
                tf = [p["taxa_interacao"] for p in ps if p["taxa_interacao"] is not None]
                fase[fz["id"]] = {"rotulo": fz["rotulo"], "publicacoes": len(ps), "visualizacoes": sum(p["visualizacoes"] or 0 for p in ps),
                                  "taxa_interacao_mediana": round(statistics.median(tf), 4) if tf else None,
                                  "por_tema": dict(Counter(t for p in ps for t in p["temas"]).most_common())}
            out["atores"][a["id"]] = {
                "nome": a["nome"], "total_publicacoes": len(pubs), "com_fala": sum(p["tem_fala"] for p in pubs),
                "totais": {k: sum(p[k] or 0 for p in pubs) for k in ("visualizacoes", "curtidas", "comentarios", "compartilhamentos")},
                "com_o_numero": {k: sum(1 for p in pubs if p[k] is not None) for k in ("visualizacoes", "curtidas", "comentarios", "compartilhamentos")},
                "taxa_interacao_mediana": round(statistics.median(taxas), 4) if taxas else None,
                "por_tema": dict(Counter(t for p in pubs for t in p["temas"]).most_common()),
                "nuvem": tx.nuvem(textos, excluir), "hashtags": [[t, n] for t, n in Counter(t for s in tags for t in s).most_common(40) if n >= 2],
                "por_fase": fase, "publicacoes": pubs}
        out["cobertura_do_dicionario"] = {"publicacoes": len(rows), "com_tema": com_tema, "sem_tema": len(rows) - com_tema,
                                          "pct_com_tema": round(100 * com_tema / len(rows), 1), "com_fala_transcrita": com_fala}
        (root / f"data/{rede}").mkdir(parents=True, exist_ok=True)
        (root / f"data/{rede}/conteudo.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tot = Counter(t for a in out["atores"].values() for t, n in a["por_tema"].items() for _ in range(n))
        print(f"{rede}: {len(rows)} publicações · {out['cobertura_do_dicionario']['pct_com_tema']}% com tema · {com_fala} com fala · "
              + " · ".join(f"{t} {n}" for t, n in tot.most_common(6)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
