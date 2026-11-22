#!/usr/bin/env python3
"""Coleta gratuita do YouTube para o ODI Influenciadoras (YouTube Data API v3).

Custo em US$: zero. Gasta só a cota diária da API (10.000 unidades).
- canal de cada ator com YouTube confirmado (channels.list, 1 unidade);
- uploads do canal, do mais recente ao mais antigo, parando pela data inicial da
  janela base (playlistItems.list, 1 unidade por página);
- estatísticas dos vídeos das janelas (videos.list, 1 unidade a cada 50);
- menções de terceiros só na janela do núcleo (search.list, 100 unidades por página).
  pageInfo.totalResults é estimativa da API: não entra como universo.

Saídas:
- data/youtube/videos.csv (público): vídeos dos próprios perfis, sem descrição;
- data/manifest/youtube_<UTC>.json (público): cota, cobertura, universo, erros;
- menções de terceiros: só no repositório privado (INFL_INTERNO_DIR). Sem ele,
  nada de terceiros é gravado; o manifesto registra só as contagens.
"""
import csv
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
API = "https://www.googleapis.com/youtube/v3/"
CUSTO = {"channels.list": 1, "playlistItems.list": 1, "videos.list": 1, "search.list": 100}
CAMPOS_VIDEOS = [
    "video_id", "ator_id", "canal", "publicado_em", "janela", "visualizacoes",
    "curtidas", "comentarios", "url", "toca_nucleo", "toca_tema_amplo",
    "toca_arabe", "toca_controle", "coletado_em",
]
CAMPOS_TERCEIROS = ["chave", "ator_id", "termo", "video_id", "canal_id", "canal", "publicado_em", "titulo", "url", "coletado_em"]


def carregar(nome):
    return json.loads((RAIZ / "data/config" / nome).read_text(encoding="utf-8"))


def normalizar(texto):
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s)


def agora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ErroAPI(Exception):
    pass


class Api:
    def __init__(self, chave, custo=CUSTO):
        self.chave = chave
        self.custo = custo
        self.unidades = 0
        self.chamadas = {}

    def get(self, rota, **params):
        params = {k: v for k, v in params.items() if v is not None}
        params["key"] = self.chave
        self.unidades += self.custo[rota]
        self.chamadas[rota] = self.chamadas.get(rota, 0) + 1
        # a rota é o nome do método ("channels.list"); o endereço é só o recurso ("channels")
        url = API + rota.split(".")[0] + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            corpo = e.read().decode("utf-8", "replace")[:300].replace(self.chave, "[chave]")
            raise ErroAPI(f"{rota}: HTTP {e.code} {corpo}") from None
        except urllib.error.URLError as e:
            raise ErroAPI(f"{rota}: falha de rede ({e.reason})") from None


def resolver_canal(api, perfil):
    d = api.get("channels.list", part="id,snippet,statistics", forHandle=perfil.lstrip("@"))
    itens = d.get("items", [])
    if not itens:
        return None
    i = itens[0]
    st = i.get("statistics", {})
    return {
        "channel_id": i["id"],
        "titulo": i["snippet"]["title"],
        # total de vídeos que o próprio YouTube informa para o canal (universo do canal)
        "videos_universo": int(st["videoCount"]) if "videoCount" in st else None,
    }


def listar_uploads(api, canal_id, inicio, fim, max_paginas):
    """Lista os uploads do canal entre inicio e fim. Para quando passa da data inicial."""
    playlist = "UU" + canal_id[2:]
    itens, token, paginas = [], None, 0
    cobertura = "incompleta (limite de páginas)"
    while paginas < max_paginas:
        d = api.get("playlistItems.list", part="snippet,contentDetails",
                    playlistId=playlist, maxResults=50, pageToken=token)
        paginas += 1
        parou = False
        for it in d.get("items", []):
            pub = it["contentDetails"].get("videoPublishedAt") or it["snippet"]["publishedAt"]
            if pub < inicio:
                parou = True
                break
            if pub <= fim:
                itens.append({"video_id": it["contentDetails"]["videoId"], "publicado_em": pub})
        if parou:
            cobertura = "completa (parou pela data inicial da janela base)"
            break
        token = d.get("nextPageToken")
        if not token:
            cobertura = "completa (fim da lista de uploads)"
            break
    return itens, cobertura, paginas


def estatisticas(api, ids):
    out = {}
    for i in range(0, len(ids), 50):
        d = api.get("videos.list", part="statistics,snippet", id=",".join(ids[i:i + 50]), maxResults=50)
        for v in d.get("items", []):
            s = v.get("statistics", {})
            out[v["id"]] = {
                "titulo": v["snippet"]["title"],
                "descricao": v["snippet"].get("description", ""),
                "visualizacoes": int(s.get("viewCount", 0)),
                "curtidas": int(s["likeCount"]) if "likeCount" in s else "",
                "comentarios": int(s["commentCount"]) if "commentCount" in s else "",
            }
    return out


def buscar_terceiros(api, termo, inicio, fim, proprios, max_paginas):
    """Menções de outros canais no período. Ordem por relevância: é amostra, não censo."""
    itens, token, paginas, estimativa = [], None, 0, None
    while paginas < max_paginas:
        d = api.get("search.list", part="snippet", q=termo, type="video",
                    publishedAfter=inicio, publishedBefore=fim, maxResults=50, pageToken=token)
        paginas += 1
        if estimativa is None:
            estimativa = d.get("pageInfo", {}).get("totalResults")
        for it in d.get("items", []):
            sn = it["snippet"]
            if sn["channelId"] in proprios:
                continue
            vid = it["id"]["videoId"]
            itens.append({
                "termo": termo, "video_id": vid, "canal_id": sn["channelId"],
                "canal": sn["channelTitle"], "publicado_em": sn["publishedAt"],
                "titulo": sn["title"], "url": "https://www.youtube.com/watch?v=" + vid,
            })
        token = d.get("nextPageToken")
        if not token:
            break
    return itens, estimativa, paginas


def gravar_merge(caminho, linhas, campos, chave):
    """Junta às linhas já gravadas: a chave repetida é atualizada, nada é apagado."""
    existentes = {}
    if caminho.exists():
        with caminho.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                existentes[r[chave]] = r
    novos = 0
    for linha in linhas:
        if linha[chave] not in existentes:
            novos += 1
        existentes[linha[chave]] = linha
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for r in sorted(existentes.values(), key=lambda r: r.get("publicado_em", "")):
            w.writerow(r)
    return novos, len(existentes)


def main():
    chave = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not chave:
        print("YOUTUBE_API_KEY ausente: nada coletado (não é falha).")
        return 0
    projeto = carregar("projeto.json")
    atores = carregar("atores.json")
    palavras = carregar("palavras.json")
    yt = carregar("coleta.json")["youtube"]
    base, nuc = projeto["janelas"]["base"], projeto["janelas"]["nucleo"]
    api = Api(chave, yt["custo_unidades"])
    erros, por_ator, linhas_videos, proprios = [], [], [], set()
    coletado_em = agora_iso()

    for ator in atores["atores"]:
        perfil = ator["perfis"].get("youtube", {})
        if not perfil.get("confirmado"):
            por_ator.append({"ator": ator["id"], "status": "sem perfil YouTube confirmado: fora da coleta"})
            continue
        try:
            canal = resolver_canal(api, perfil["perfil"])
            if canal is None:
                raise ErroAPI("canal não encontrado para " + perfil["perfil"])
            proprios.add(canal["channel_id"])
            uploads, cobertura, paginas = listar_uploads(
                api, canal["channel_id"], base["inicio"], nuc["fim"], yt["max_paginas_uploads"])
            stats = estatisticas(api, [u["video_id"] for u in uploads])
        except ErroAPI as e:
            erros.append(f"{ator['id']}: {e}")
            por_ator.append({"ator": ator["id"], "status": f"erro na leitura: {e}"})
            continue
        lidos = {"base": 0, "nucleo": 0}
        for u in uploads:
            s = stats.get(u["video_id"])
            if not s:
                continue
            janela = "nucleo" if nuc["inicio"] <= u["publicado_em"] <= nuc["fim"] else "base"
            lidos[janela] += 1
            texto = normalizar(s["titulo"] + " " + s["descricao"])
            flags = {f: any(normalizar(k) in texto for k in termos)
                     for f, termos in palavras["familias_video"].items()}
            linhas_videos.append({
                "video_id": u["video_id"], "ator_id": ator["id"], "canal": canal["titulo"],
                "publicado_em": u["publicado_em"], "janela": janela,
                "visualizacoes": s["visualizacoes"], "curtidas": s["curtidas"],
                "comentarios": s["comentarios"],
                "url": "https://www.youtube.com/watch?v=" + u["video_id"],
                "toca_nucleo": flags["nucleo"], "toca_tema_amplo": flags["tema_amplo"],
                "toca_arabe": flags["arabe"], "toca_controle": flags["controle"],
                "coletado_em": coletado_em,
            })
        por_ator.append({
            "ator": ator["id"], "canal": canal["titulo"], "canal_id": canal["channel_id"],
            "universo_canal": canal["videos_universo"],
            "universo_fonte": "channels.list statistics.videoCount (total informado pelo YouTube para o canal)",
            "lidos_base": lidos["base"], "lidos_nucleo": lidos["nucleo"],
            "cobertura": cobertura, "paginas": paginas,
        })

    terceiros_linhas, terceiros_resumo = [], []
    for ator_id, termos in palavras["terceiros"].items():
        for termo in termos:
            try:
                itens, estimativa, paginas = buscar_terceiros(
                    api, termo, nuc["inicio"], nuc["fim"], proprios, yt["max_paginas_terceiros"])
            except ErroAPI as e:
                erros.append(f"terceiros {ator_id}: {e}")
                continue
            terceiros_linhas += [dict(i, ator_id=ator_id, chave=f"{termo}|{i['video_id']}", coletado_em=coletado_em)
                                 for i in itens]
            terceiros_resumo.append({
                "ator": ator_id, "termo": termo, "janela": "núcleo", "lidos": len(itens),
                "paginas": paginas, "estimativa_api": estimativa,
                "universo": "não informado pela API (estimativa acima é aproximada e não é universo)",
                "revisao_homonimos": "pendente",
            })

    destino = "não gravado"
    interno = os.environ.get("INFL_INTERNO_DIR", "")
    if terceiros_linhas and interno and Path(interno).is_dir():
        gravar_merge(Path(interno) / "data/terceiros_youtube.csv", terceiros_linhas, CAMPOS_TERCEIROS, "chave")
        destino = "repositório privado"
    elif terceiros_linhas:
        erros.append("menções de terceiros não gravadas: repositório privado indisponível (INFL_INTERNO_DIR)")

    novos, total = gravar_merge(RAIZ / "data/youtube/videos.csv", linhas_videos, CAMPOS_VIDEOS, "video_id")
    manifesto = {
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "gerado_em": coletado_em,
        "janelas": {"base": base, "nucleo": nuc},
        "custo_usd": 0,
        "cota_unidades_estimadas": api.unidades,
        "chamadas": api.chamadas,
        "atores": por_ator,
        "terceiros": terceiros_resumo,
        "terceiros_destino": destino,
        "videos_gravados": {"novos": novos, "total_no_acervo": total},
        "erros": erros,
    }
    nome = "youtube_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
    (RAIZ / "data/manifest").mkdir(parents=True, exist_ok=True)
    texto_manifesto = json.dumps(manifesto, ensure_ascii=False, indent=1)
    (RAIZ / "data/manifest" / nome).write_text(texto_manifesto, encoding="utf-8")
    # cópia de nome fixo para a página ler (a página estática não lista pastas)
    (RAIZ / "data/manifest/youtube_latest.json").write_text(texto_manifesto, encoding="utf-8")
    lidos_ok = sum(1 for a in por_ator if a.get("canal"))
    confirmados = sum(1 for a in atores["atores"] if a["perfis"].get("youtube", {}).get("confirmado"))
    print(f"YouTube: {lidos_ok} de {confirmados} canais lidos; {novos} vídeos novos ({total} no acervo); "
          f"cota ~{api.unidades} unidades; {len(erros)} erro(s); manifesto {nome}")
    if confirmados and not lidos_ok:
        print("Nenhum canal confirmado foi lido: execução marcada como falha.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
