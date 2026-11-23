#!/usr/bin/env python3
"""Regras de texto do caderno "O que dizem":
normalização (minúsculas, sem acento), dicionário aberto de temas por regras (termo com * casa por prefixo),
descarte de trechos repetidos em 10+ publicações do mesmo perfil, nuvem por nº de publicações (não de ocorrências) e
hashtags. Aqui as palavras vazias são as do português falado (legendas e transcrições). Classificação por regras, NÃO por IA:
auditável e replicável, mas não entende ironia nem contexto.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

URL = re.compile(r"(https?://\S+|www\.\S+)", re.I)
SEG = re.compile(r"(?<=[.!?])\s+|\s[|•]\s|\s-\s|\s—\s|\s*[\U0001F300-\U0001FAFF☀-➿]+\s*|\n")  # emojis também separam trechos
LIMIAR_REPETICAO = 10   # trecho presente em 10+ publicações do mesmo perfil = texto padrão (rodapé, institucional)
NUVEM_TOP, NUVEM_MIN = 60, 3
HASHTAG = re.compile(r"#([0-9A-Za-zÀ-ÿ_]{3,})")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", URL.sub(" ", s or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " " + re.sub(r"[^a-z0-9#]+", " ", s).strip() + " "


STOP = set(norm("""a ao aos aquela aquelas aquele aqueles aquilo as ate com como da das de dela delas dele deles depois do dos e ela elas
ele eles em entre era eram essa essas esse esses esta estas este estes esta estao estava estavam eu foi foram ha isso isto ja la lhe lhes
mais mas me mesmo meu meus minha minhas muito muita muitos muitas na nas nao nem no nos nossa nossas nosso nossos num numa o os ou para
pela pelas pelo pelos por porque pra pro qual quando que quem se sem ser seu seus si so sua suas tambem te tem tinha to tu tua tuas um uma
umas uns vai vao voce voces vou ai aqui ali assim bem ainda agora entao gente coisa coisas fazer faz fiz feito ter tenho tava ta tô to ne
sabe sei vez vezes cada todo toda todos todas outro outra outros outras ano anos dia dias hoje ontem amanha semana mes hora horas
segunda terca quarta quinta sexta sabado domingo janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro
video videos canal youtube instagram tiktok reels link bio segue siga inscreva comenta comente curte curta salva salve compartilha
olha olhe vamos vem veio vou dar deu disse fala falar falando falou acho achei gosto quero queria pode posso nada tudo algo alguem
eh ah oh uh hum tipo cara mano meu deus nossa obrigada obrigado oi ola tchau beijo beijos gente""").split())


def term_regex(t: str) -> re.Pattern:
    """Termo do dicionário → expressão sobre o texto normalizado. 'inmigra*' casa por prefixo; '#' antes é aceito."""
    n = norm(t.rstrip("*")).strip()
    return re.compile(r"(?<=[ #])" + re.escape(n).replace(r"\ ", " ") + (r"[a-z0-9]*" if t.endswith("*") else "") + r"(?= )")


def segmentos(texto: str) -> list[str]:
    return [s.strip() for s in SEG.split(URL.sub(" ", texto or "")) if s and len(s.strip()) >= 12]


def texto_padrao(pubs: list[dict]) -> dict[str, set]:
    """Por perfil, os trechos repetidos em LIMIAR_REPETICAO ou mais publicações."""
    cont: dict[str, Counter] = {}
    for r in pubs:
        cont.setdefault(r["perfil"], Counter()).update(set(segmentos(r["texto"])))
    return {p: {s for s, n in c.items() if n >= LIMIAR_REPETICAO} for p, c in cont.items()}


def texto_util(r: dict, padrao: dict[str, set]) -> str:
    fora = padrao.get(r["perfil"], set())
    segs = segmentos(r["texto"])
    return " ".join(s for s in segs if s not in fora) if segs else (r["texto"] or "")


def termos(texto: str, excluir: set) -> set:
    """Palavras e pares de palavras vizinhas (sem palavras vazias, números e os nomes do próprio ator)."""
    ok = lambda t: len(t) >= 3 and t not in STOP and t not in excluir and not t.isdigit()  # noqa: E731
    toks = [t for t in norm(texto).split() if not t.startswith("#")]
    return {t for t in toks if ok(t)} | {f"{a} {b}" for a, b in zip(toks, toks[1:]) if ok(a) and ok(b)}


def nuvem(textos: list[str], excluir: set, top: int = NUVEM_TOP, minimo: int = NUVEM_MIN) -> list[list]:
    df = Counter()
    for tx in textos:
        df.update(termos(tx, excluir))
    df = {t: n for t, n in df.items() if n >= minimo}
    for t, n in list(df.items()):  # o par absorve a palavra solta quando cobre 80%+ das ocorrências dela
        if " " in t:
            for w in t.split():
                if w in df and n >= 0.8 * df[w]:
                    df.pop(w, None)
    return [[t, n] for t, n in sorted(df.items(), key=lambda x: (-x[1], x[0]))[:top]]


def tag_key(t: str) -> str:
    return norm(t).replace(" ", "").lstrip("#")


def compilar(cfg: dict):
    temas = {k: [term_regex(t) for t in v] for k, v in cfg["temas"].items()}
    return temas, [term_regex(t) for t in cfg["adversarios"]], [term_regex(t) for t in cfg["pede_voto"]]


def compilar_brasil(cfg: dict) -> list:
    """Termos da etiqueta 'cita o Brasil' (Brasil, Lula, família Bolsonaro), de data/config/temas.json."""
    return [term_regex(t) for t in cfg.get("cita_brasil", [])]


def classificar(texto: str, temas, adv, voto, brasil=()) -> dict:
    t = norm(texto)
    achados = [k for k, regs in temas.items() if any(r.search(t) for r in regs)]
    br = sorted({m.group(0).strip() for r in brasil for m in r.finditer(t)})  # o que foi encontrado, para conferência
    return {"temas": achados or ["sem_tema"], "cita_adversario": any(r.search(t) for r in adv), "pede_voto": any(r.search(t) for r in voto),
            "cita_brasil": bool(br), "brasil_termos": br}
