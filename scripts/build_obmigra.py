"""Agrega os microdados do SISMIGRA (OBMigra / Ministério da Justiça).

Uso: python3 scripts/build_obmigra.py <caminho do CSV> [--privado <pasta do repositório privado>]

Lê o CSV inteiro (o arquivo publicado é o universo dos registros do período) e grava
data/dados_publicos/obmigra_sismigra.json só com contagens. O CSV bruto, se --privado
for dado, vai comprimido para <privado>/data/obmigra/.
"""
import argparse, collections, csv, datetime, gzip, hashlib, json, pathlib, shutil, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CFG = RAIZ / "data/config/obmigra.json"
SAIDA = RAIZ / "data/dados_publicos/obmigra_sismigra.json"
FAIXAS = [(0, 17, "0 a 17"), (18, 29, "18 a 29"), (30, 44, "30 a 44"), (45, 59, "45 a 59"), (60, 200, "60 ou mais")]


def faixa(idade):
    try:
        i = int(idade)
    except (TypeError, ValueError):
        return "não informada"
    for a, b, r in FAIXAS:
        if a <= i <= b:
            return r
    return "não informada"


def conta(xs, campo, limite=None):
    c = collections.Counter((x.get(campo) or "").strip() or "NÃO INFORMADO" for x in xs)
    return [[k, v] for k, v in c.most_common(limite)]


MIN_CELULA = 3  # profissões com menos registros que isto num país vão para "outras"


def profissoes(xs, limite=10):
    c = collections.Counter((x.get("PROFISSAO") or "").strip() or "NÃO INFORMADO" for x in xs).most_common()
    mostra = [[k, v] for k, v in c[:limite] if v >= MIN_CELULA]
    resto = sum(v for k, v in c) - sum(v for k, v in mostra)
    return mostra + ([[f"outras ({len(c) - len(mostra)} ocupações, cada uma abaixo do top {limite} ou com menos de {MIN_CELULA} registros)", resto]] if resto else [])


def agrega(linhas, cfg):
    total = len(linhas)
    nat = collections.Counter(x["PAIS_NACIONALIDADE"] for x in linhas)
    paises = {}
    for grupo in ("nucleo", "contexto"):
        for p in cfg[grupo]:
            xs = [x for x in linhas if x["PAIS_NACIONALIDADE"] == p]
            paises[p] = {
                "grupo": grupo,
                "registros": len(xs),
                "nascidos_no_pais": sum(1 for x in xs if x["PAIS_NASCIMENTO"] == p),
                "uf": conta(xs, "UNIDADE_FED_RESIDENCIA"),
                "municipios": [[m, q] for m, q in collections.Counter(
                    f'{x["MUNICIPIO_RESIDENCIA"]} ({x["UNIDADE_FED_RESIDENCIA"]})' for x in xs).most_common(15)],
                "classificacao": conta(xs, "CLASSIFICACAO_REVISADA"),
                "tipologia": conta(xs, "TIPOLOGIA_AMPAROS"),
                "sexo": conta(xs, "SEXO"),
                "idade": [[r, q] for r, q in sorted(collections.Counter(faixa(x["IDADE"]) for x in xs).items(),
                                                     key=lambda t: [f[2] for f in FAIXAS].index(t[0]) if t[0] != "não informada" else 99)],
                "ano_entrada": conta(xs, "DATAENTRADA"),
                "profissao": profissoes(xs),
                "estado_civil": conta(xs, "ESTADO_CIVIL"),
            }
    nuc = [x for x in linhas if x["PAIS_NACIONALIDADE"] in cfg["nucleo"]]
    return {
        "universo": total,
        "lidos": total,
        "anos_de_registro": conta(linhas, "DATAREGISTRO"),
        "nacionalidades_distintas": len(nat),
        "paises": paises,
        "nucleo_por_uf": conta(nuc, "UNIDADE_FED_RESIDENCIA"),
        "nucleo_total": len(nuc),
        "profissoes_distintas": len({x.get("PROFISSAO") for x in linhas}),
        "profissao_geral": profissoes(linhas),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--privado")
    a = ap.parse_args(argv)
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    caminho = pathlib.Path(a.csv)
    bruto = caminho.read_bytes()
    linhas = list(csv.DictReader(bruto.decode("utf-8-sig").splitlines(), delimiter=";"))
    meta = cfg["arquivos"]["sismigra_janeiro_julho_2026"]
    out = {
        "gerado_em": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fonte": "OBMigra / Ministério da Justiça e Segurança Pública, microdados do SISMIGRA (registros de residência, Polícia Federal)",
        "pagina": cfg["pagina"],
        "arquivo": {"nome": caminho.name, "link": meta["link"], "modificado_em": meta["modificado_em"],
                    "bytes": len(bruto), "sha256": hashlib.sha256(bruto).hexdigest(), "obtido": meta["obtido"]},
        "periodo": "janeiro a julho de 2026",
        "nota": cfg["nota"],
        "limite_temporal": "O arquivo traz só o ano do registro (DATAREGISTRO = 2026), sem mês nem dia: não dá para separar a linha de base (junho e julho) do resto do semestre, e o núcleo (23/07 a 14/08) não está coberto, porque o arquivo para em julho.",
        **agrega(linhas, cfg),
    }
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out['lidos']} registros; núcleo {out['nucleo_total']} -> {SAIDA}")
    if a.privado:
        dest = pathlib.Path(a.privado) / "data/obmigra"
        dest.mkdir(parents=True, exist_ok=True)
        alvo = dest / (caminho.name + ".gz")
        if not alvo.exists():
            with gzip.open(alvo, "wb") as g:
                g.write(bruto)
        print("bruto:", alvo)


if __name__ == "__main__":
    sys.exit(main())
