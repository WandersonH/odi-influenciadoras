"""Unidades da codificação humana (área interna): todas as publicações das quatro no núcleo (23/07 a 14/08/2026).

Cada unidade = uma publicação: legenda (Instagram, TikTok) ou título (YouTube) + transcrição do áudio, quando houver.
Tudo aqui já é público no repositório (posts das próprias influenciadoras e transcrições). Nenhum dado de terceiro.

Saída: supabase/seed/unidades.sql (insert idempotente: upsert por id). A ordem de apresentação é md5(id), fixa e
igual para todos os codificadores (sorteio único, nunca refeito).
"""
from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def ler(p: Path) -> list[dict]:
    return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []


def lit(v) -> str:
    if v is None or v == "":
        return "null"
    return "'" + str(v).replace("'", "''") + "'"


def unidades(root: Path = RAIZ) -> list[dict]:
    trans = {}
    for r in ("youtube", "instagram", "tiktok"):
        for t in ler(root / f"data/transcricoes/{r}.csv"):
            trans[(r, t["post_id"])] = t
    out = []
    for r in ("instagram", "tiktok"):
        for p in ler(root / f"data/{r}/posts.csv"):
            if p.get("janela") != "nucleo":
                continue
            t = trans.get((r, p["post_id"]), {})
            out.append({"id": f"{r}:{p['post_id']}", "ator_id": p["ator_id"], "rede": r, "publicado_em": p["publicado_em"], "tipo": p.get("tipo"),
                        "url": p.get("url"), "texto": p.get("texto"), "transcricao": t.get("texto") if t.get("status") == "ok" else None,
                        "transcricao_status": ("ok" if t.get("status") == "ok" else "falhou") if t else "sem áudio transcrito"})
    for v in ler(root / "data/youtube/videos.csv"):
        if v.get("janela") != "nucleo":
            continue
        t = trans.get(("youtube", v["video_id"]), {})
        out.append({"id": f"youtube:{v['video_id']}", "ator_id": v["ator_id"], "rede": "youtube", "publicado_em": v["publicado_em"], "tipo": "video",
                    "url": v.get("url"), "texto": v.get("titulo"), "transcricao": t.get("texto") if t.get("status") == "ok" else None,
                    "transcricao_status": ("ok" if t.get("status") == "ok" else "falhou") if t else "sem áudio transcrito"})
    for u in out:
        u["ordem"] = hashlib.md5(u["id"].encode()).hexdigest()
    return sorted(out, key=lambda u: u["ordem"])


def sql(us: list[dict]) -> str:
    cols = ["id", "ator_id", "rede", "publicado_em", "tipo", "url", "texto", "transcricao", "transcricao_status", "ordem"]
    linhas = ",\n".join("(" + ", ".join(lit(u[c]) for c in cols) + ")" for u in us)
    upd = ", ".join(f"{c} = excluded.{c}" for c in cols[1:])
    return (f"-- gerado por scripts/build_area_interna.py: {len(us)} unidades (publicações do núcleo)\n"
            f"insert into public.unidades ({', '.join(cols)}) values\n{linhas}\n"
            f"on conflict (id) do update set {upd}, carregado_em = now();\n")


def main() -> int:
    us = unidades()
    d = RAIZ / "supabase/seed"
    d.mkdir(parents=True, exist_ok=True)
    (d / "unidades.sql").write_text(sql(us), encoding="utf-8")
    from collections import Counter
    print(f"{len(us)} unidades: {dict(Counter(u['rede'] for u in us))}; com transcrição: {sum(1 for u in us if u['transcricao'])}")
    return 0 if us else 1


if __name__ == "__main__":
    sys.exit(main())
