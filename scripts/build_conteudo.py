"""Funções de texto do ODI Atlas (scripts/build_conteudo.py) usadas pela CHD de Reinert portada (chd_reinert.py):
norm, EMOJI_TAG e STOP, copiadas sem mudança para que a CHD daqui seja a mesma do Atlas."""
from __future__ import annotations

import re
import unicodedata

# Emojis que o Kwai entrega como texto entre colchetes ("[heart]", "[heart_eyes]"): não são palavras
EMOJI_TAG = re.compile(r"\[[a-z_]{2,30}\]", re.I)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", EMOJI_TAG.sub(" ", s or "")).lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " " + re.sub(r"[^a-z0-9#]+", " ", s).strip() + " "



STOP = set(norm("""a o e é de da do das dos em no na nos nas um uma uns umas para pra pro por pelo pela pelos pelas com sem
que se não nao mais mas ou como ao aos à às já ja foi ser são sao está esta estão estao isso essa esse este esta isto
aquele aquela ele ela eles elas nós nos você voce vocês voces eu me meu minha meus minhas seu sua seus suas nosso nossa
nossos nossas lhe te tu dele dela deles delas quem qual quais quando onde porque porquê sobre entre até ate também tambem
muito muita muitos muitas pouco todo toda todos todas tudo nada aqui ali lá la agora hoje ontem amanhã amanha vai vão vao
vamos ter tem têm tinha teve fazer faz fez feito ver vê vou estou estamos são sou era eram será sera seria há ha pode podem
dia dias ano anos vez vezes cada outro outra outros outras mesmo mesma só so ainda então entao assim bem sim também
https http www com br youtube video vídeo vídeos videos canal inscreva inscrevase inscreva-se ative sininho link bio
shorts short live ao vivo assista confira acompanhe veja siga redes sociais instagram facebook tiktok twitter kwai
fyp foryou foryoupage fy parati paravoce pravoce viral viralizar viralizou trend trending explore explorar reels kwaivideo kwaibrasil capcut
whatsapp telegram x clique aqui completo íntegra integra parte episódio episodio programa acesse site conheça conheca
obrigado obrigada pronto fim gente quer quero precisa contra lado enquanto nunca sempre grande novo nova tempo seguir bora
propaganda eleitoral horário horario gratuito janeiro fevereiro março marco abril maio junho julho agosto setembro outubro
novembro dezembro segunda terça terca quarta quinta sexta sábado sabado domingo
neste nesta nesse nessa deste desta desse dessa disso nisso daquele daquela aquilo num numa pois sobre sob após apos
""").split())
