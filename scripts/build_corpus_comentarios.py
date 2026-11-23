#!/usr/bin/env python3
"""Corpus anonimizado dos comentários, para a página abrir os comentários ao clicar num tema ou numa palavra (caderno 05).

Autorizado pelo responsável em 22/11/2026, 22h42 e 22h45 ("ao clicar sobre o número exiba o corpus com nome
anonimizado"; "mesma coisa nas palavras"). Entrada: o CSV privado de cada rede (INFL_INTERNO_DIR/data/comentarios/<rede>.csv),
só comentários de publicações do núcleo, os mesmos que entram nas contagens do resumo.

Anonimização, antes de ir ao público:
- autor vira código por rede, na ordem do primeiro comentário (YT0001, IG0001, TT0001); o nome e o @ do autor não saem;
- todo @ no texto vira "@perfil", menos o @ das quatro influenciadoras monitoradas (perfis públicos do estudo);
- links, e-mails e sequências de 8 ou mais dígitos (telefone, documento) são retirados;
- sem identificador do comentário na plataforma (não dá para achar o autor pelo endereço do comentário).
Cada comentário leva os temas do dicionário (mesma regra das contagens) e as palavras da nuvem da influenciadora que
contém (mesma regra da nuvem: texto.termos). Saída: data/comentarios/corpus_<rede>.json.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import texto as tx  # noqa: E402
from collect_comentarios import TEMAS_COMENTARIO, FONTES  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
PREFIXO = {"youtube": "YT", "instagram": "IG", "tiktok": "TT"}
URL = re.compile(r"(https?://\S+|www\.\S+)", re.I)
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
ARROBA = re.compile(r"@([\w.]{2,})")
DIGITOS = re.compile(r"\d[\d .()-]{6,}\d")
csv.field_size_limit(10_000_000)


def ler(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def anonimizar(texto: str, proprios: set[str]) -> str:
    t = EMAIL.sub("[e-mail]", texto or "")
    t = URL.sub("[link]", t)
    t = ARROBA.sub(lambda m: m.group(0) if m.group(1).lower().rstrip(".") in proprios else "@perfil", t)
    t = DIGITOS.sub(lambda m: "[número]" if sum(c.isdigit() for c in m.group(0)) >= 8 else m.group(0), t)
    return re.sub(r"\s+", " ", t).strip()


def codigos(linhas: list[dict], prefixo: str) -> dict[str, str]:
    ordem = []
    for r in sorted(linhas, key=lambda r: (r.get("publicado_em") or "", r.get("comment_id") or "")):
        a = (r.get("autor") or "").strip().lower()
        if a and a not in ordem:
            ordem.append(a)
    return {a: f"{prefixo}{i + 1:04d}" for i, a in enumerate(ordem)}


def main(root: Path = RAIZ) -> int:
    interno = os.environ.get("INFL_INTERNO_DIR", "").strip()
    if not interno or not Path(interno).is_dir():
        print("⛔ repositório privado indisponível: corpus dos comentários não gerado")
        return 1
    cfg = json.loads((root / "data/config/temas.json").read_text(encoding="utf-8"))
    latinos = {k: [tx.term_regex(t) for t in cfg["temas"][k] if tx.norm(t.rstrip("*")).strip()] for k in TEMAS_COMENTARIO}
    literais = {k: [t for t in cfg["temas"][k] if not tx.norm(t.rstrip("*")).strip()] for k in TEMAS_COMENTARIO}
    atores = json.loads((root / "data/config/atores.json").read_text(encoding="utf-8"))["atores"]
    proprios = set()
    for a in atores:
        for p in (a.get("perfis") or {}).values():
            h = p.get("perfil") if isinstance(p, dict) else None
            if h:
                proprios.add(h.lower().lstrip("@"))
    for rede, (arq, chave) in FONTES.items():
        resumo_p = root / f"data/comentarios/{rede}_resumo.json"
        if not resumo_p.exists():
            continue
        resumo = json.loads(resumo_p.read_text(encoding="utf-8"))
        posts = {r[chave]: r for r in ler(root / arq) if r.get("janela") == "nucleo"}
        linhas = [r for r in ler(Path(interno) / f"data/comentarios/{rede}.csv") if r.get("post_id") in posts]
        cod = codigos(linhas, PREFIXO[rede])
        nuvens = {a: {t for t, _ in (v.get("nuvem") or [])} for a, v in resumo["por_influenciadora"].items()}
        saida = []
        for r in sorted(linhas, key=lambda r: (r["ator_id"], r.get("publicado_em") or "")):
            bruto = r.get("texto") or ""
            n_ = tx.norm(bruto)
            temas = [k for k in TEMAS_COMENTARIO if any(x.search(n_) for x in latinos[k]) or any(x in bruto for x in literais[k])]
            palavras = sorted(tx.termos(bruto, set()) & nuvens.get(r["ator_id"], set()))
            saida.append({"a": r["ator_id"], "u": cod.get((r.get("autor") or "").strip().lower(), f"{PREFIXO[rede]}0000"),
                          "d": (r.get("publicado_em") or "")[:10], "p": posts[r["post_id"]].get("url"),
                          "r": 1 if r.get("parent_id") else 0, "c": r.get("curtidas") or "",
                          "t": anonimizar(bruto, proprios), "tm": temas, "w": palavras})
        out = {"rede": rede, "gerado_em": resumo.get("gerado_em"), "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
               "metodo": __doc__.split("\n\n")[2].strip(), "comentarios": len(saida), "autores_codificados": len(cod), "itens": saida}
        (root / f"data/comentarios/corpus_{rede}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        cont = {k: sum(1 for x in saida if k in x["tm"]) for k in TEMAS_COMENTARIO}
        print(f"corpus {rede}: {len(saida)} comentários, {len(cod)} autores codificados; temas {cont}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
