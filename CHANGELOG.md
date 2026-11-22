# Changelog

## 22/11/2026: caderno "O que dizem" por rede, no método do ODI Atlas e do ODI Espanha; checagens bloqueadas (403)

**O que mudou.** Novo `scripts/build_o_que_dizem.py`, porta do ODI Espanha, que gera `data/<rede>/conteudo.json`, e `scripts/texto.py` com palavras vazias do português falado. Novo dicionário `data/config/temas.json` v0 (rascunho), com 11 temas: acordo/Hamas, Gaza e Palestina, Israel e guerra, islamofobia, religião, cultura árabe, moda, família, culinária, publicidade e viagem. O dicionário é aplicado à legenda e à fala transcrita. Termos sem letra latina (árabe, emoji) são buscados literalmente: na primeira versão eles viravam texto vazio e casavam com tudo (72 falsos "acordo/Hamas" no YouTube). O caderno 03 ganhou filtro por rede e por tema, tabela de números, linha do tempo semana a semana e por publicação (núcleo sombreado, 31/07 marcado), tabela de temas, nuvens, hashtags e as 5 publicações de maior audiência. A lista de publicações do núcleo continua embaixo. Os três workflows de coleta passam a regerar o caderno.

**Resultado** (recorte inteiro, 01/06 a 14/08): o tema "Acordo/Hamas" não aparece em nenhuma publicação. "Gaza e Palestina" aparece em 5: Mariam (YouTube 23/07, lista de países árabes; TikTok 28/07, prato palestino), Carima (Instagram 09/08, perfil derrubado por falar da Palestina; Instagram 19/06, base, por emoji) e Fabíola (Instagram 12/06, base, comentário sobre um homem com kufiya palestina).

**Limites.** O acervo do YouTube não guarda título nem descrição; os temas vêm só da fala (vídeos do núcleo). O ator do Instagram não devolveu `commentsCount`, então os comentários do Instagram aparecem como ⛔ não informado.

**Checagens** (run 45069732315): a Google Fact Check Tools API recusou as 10 consultas com HTTP 403 "Permission denied on the service". A API não está ativada no projeto do Google Cloud da chave do YouTube. Falta o responsável ativá-la ou cadastrar FACTCHECK_API_KEY.

**Executado.** Builder rodado localmente; `node --check`; caderno 03 aberto no Chrome headless; testes unitários.

## 22/11/2026: checagens pela Google Fact Check Tools API

**O que mudou.** Novo `scripts/collect_checagens.py`, porta do coletor do ODI Atlas, com workflow `checagens.yml` de disparo manual. As consultas cobrem o tema (Hamas, desarmamento Hamas, Gaza, Palestina, cessar-fogo Gaza, Israel Hamas acordo) e o nome das quatro influenciadoras, desde 01/06/2026 (maxAgeDays). A janela de cada checagem é marcada pela data em que foi publicada. Nome de pessoa comum em "quem disse" é omitido. O caderno 07 ganhou a seção de checagens.

**Por quê.** Pedido do responsável às 18h00 ("api fact check integrada").

**Executado.** 23 testes unitários aprovados (janela, omissão de nome, citação de influenciadora, sem chave nada roda); `node --check` na página. Coleta disparada logo após este commit, com FACTCHECK_API_KEY ou, sem ela, a chave do YouTube.

## 22/11/2026: YouTube transcrito (run 45068995637) e página atualizada

**Resultado.** 16 de 16 vídeos de Mariam Chami no núcleo transcritos (cerca de 26 min de áudio; Whisper small, a partir do áudio baixado pelo responsável). Nenhuma fala trata do acordo, de Hamas, desarmamento, Gaza, Israel ou cessar-fogo. Aparecem: Palestina numa lista de países árabes (23/07), "já nos chamaram de terrorista" num vídeo sobre ser muçulmana no Brasil (26/07) e Líbano num vestido e num perfume (02/08 e 08/08).

**Página.** O caderno 02 passa a ler também `data/transcricoes/youtube.csv`. A pendência agora conta qualquer vídeo sem transcrição: resta 1, o do Instagram (Dbb6xCOx3Q-), cujo áudio não foi lido.

**Executado.** `node --check` e página aberta no Chrome headless; testes unitários.

## 22/11/2026: YouTube transcrito a partir de áudio baixado pelo responsável

**O que aconteceu.** O YouTube bloqueia o download vindo do GitHub e do ambiente de nuvem. O responsável baixou o áudio dos 16 vídeos de Mariam no núcleo pelo Terminal do próprio Mac (yt-dlp; corrigido antes o erro de certificado do Python dele), em `~/Downloads/trascricao` (16 arquivos m4a, cerca de 25 MB). Os arquivos foram guardados no repositório privado (`odi-secret-infl-/audio/youtube`, commit f70b797).

**O que mudou.** `transcrever.py --audio-dir` usa o áudio local antes de tentar legenda ou download. A fonte registra "áudio baixado pelo responsável no próprio computador". O workflow de transcrição clona o privado na tarefa do YouTube e ganhou a opção `so_youtube`.

**Executado.** 20 testes unitários aprovados. Transcrição disparada logo após este commit.

## 22/11/2026: página lê Trends e transcrições (cadernos 02, 07 e 10)

**O que mudou.** O caderno 02 mostra, por influenciadora, as publicações do núcleo, quantas têm o tema na legenda, quantos vídeos tiveram a fala transcrita, quantas falas citam um termo e os trechos com contexto. Isso ainda não é posição codificada. O caderno 07 traz os gráficos do Trends com o núcleo sombreado e 31/07 marcado. O caderno 10 registra a saúde do Trends e das transcrições. `collect_trends.py` grava `pasta` no manifesto para a página achar os CSVs (preenchido à mão no manifesto atual). A página abre o caderno pelo endereço (`#trends`, `#posicao`).

**Por quê.** O responsável perguntou às 17h38 por que a página não mostrava esses dados: a coleta tinha sido ligada sem ligar a página.

**Observação.** Os números do Trends na página são da segunda coleta (run 45066425369). As palavras do tema variam um pouco em relação à primeira (Hamas em 31/07: 19 na primeira, 22 na segunda), o que é esperado: cada consulta do Trends é uma amostra. Na segunda coleta, os nomes das influenciadoras não tiveram série (0 pontos).

**Executado.** `node --check`; cadernos 02 e 07 abertos no Chrome headless servido localmente; testes unitários.

## 22/11/2026: transcrições de Instagram e TikTok (run 45065517835) e tópicos do Trends (run 45066425369)

**Transcrição** (Whisper small, sem custo): Instagram, 29 de 30 vídeos do núcleo (1 falha de áudio no download; 18 publicações sem vídeo ficaram fora); TikTok, 28 de 28. Nenhuma fala cita Hamas, desarmamento, Gaza, Israel, cessar-fogo, guerra ou genocídio. Menções a Palestina e Oriente Médio só fora do tema do acordo: Carima Orra (Instagram, 09/08) conta que o Instagram já derrubou o perfil dela "por conta das coisas que eu falava sobre a Palestina"; Mariam Chami (TikTok, 28/07) cita um prato palestino; Mariam (Instagram, 31/07) usa um vestido do Líbano; Fabíola Oliveira (TikTok, 27/07) fala de costumes do Oriente Médio. YouTube: 16 vídeos de Mariam sem transcrição (download bloqueado e sem legenda pela Apify).

**Trends, tópicos.** Hamas (tópico, índice relativo à consulta): pico em 21/06 (100); 39 em 30/07, 67 em 31/07, 57 em 01/08. Faixa de Gaza: pico em 21/06 (42) e 27 em 31/07.

## 22/11/2026: primeira coleta do Trends (run 45066153210) e correção dos tópicos

**Resultado** (`data/manifest/trends_latest.json`). Palavras do tema e nomes das influenciadoras: ok nos dois períodos. Tópicos: bloqueados, porque o Google classifica "Faixa de Gaza" como "Assunto" e a configuração esperava "Território". Na série do estudo (índice 0–100 relativo à consulta), Hamas teve pico em 21/06 (37) e ficou em 19 em 31/07; Gaza teve pico em 20/06 (100) e 22 em 31/07. Mariam Chami teve pico em 09/06 (100) e 0 em 31/07. Hyatt Omar, Carima Orra e Fabíola Oliveira ficaram em 0 o período todo (volume abaixo do mínimo do Trends).

**Correção.** "Assunto" foi aceito como tipo dos tópicos. Nova coleta disparada logo após este commit.

## 22/11/2026: Google Trends (Brasil) e resultado das legendas do YouTube pela Apify

**Trends.** O coletor do ODI Espanha (`collect_trends.py`, `net.py`) foi copiado e ajustado para o Brasil (pt-BR, UTC-3, geo BR), com workflow `trends.yml` de disparo manual. `data/config/trends.json` tem três grupos: tópicos (Hamas, Faixa de Gaza), palavras do tema (Hamas, desarmamento, Gaza, Palestina, cessar-fogo) e os nomes das quatro influenciadoras. São dois períodos: o estudo inteiro (01/06 a 14/08) e só o núcleo (23/07 a 14/08). O Trends ainda não tinha sido coletado porque o coletor não existia neste repositório; o responsável perguntou às 17h22.

**Legendas do YouTube pela Apify** (run 45065594426): pedidas para os 16 vídeos do núcleo, nenhuma veio com texto; custo de US$ 0,0001 (`apify_youtube_transcricao_*.json`). Os vídeos de Mariam no núcleo seguem sem transcrição.

**Executado.** 22 testes unitários aprovados (região, períodos, até 5 termos por grupo). Trends disparado logo após este commit.

## 22/11/2026: legendas do YouTube pela Apify (etapa de terceiros e transcrições)

**O que mudou.** `transcrever.py --rede youtube --apify` pede as legendas dos vídeos pendentes ao `seemuapps~youtube-transcript-scraper`, o mesmo ator do ODI Atlas (que mediu US$ 0,0001 por transcrição mais o início). O pedido usa a etapa `terceiros_transcricoes` (US$ 1,00), com teto de US$ 0,50 por execução, e grava o custo em `apify_youtube_transcricao_*.json`. O workflow ganhou a opção `youtube_apify`.

**Por quê.** No run 45065082432 o YouTube bloqueou o download no runner do GitHub. Usar a Apify nesse caso já estava previsto no plano aprovado.

**Executado.** 19 testes unitários aprovados. Disparado logo após este commit.

## 22/11/2026: primeira transcrição falhou (run 45065082432); correção

**Resultado.** Instagram (30 vídeos; 18 publicações sem vídeo fora) e TikTok (28 vídeos): o download funcionou, mas todas as transcrições falharam com `open() got an unexpected keyword argument 'metadata_errors'`, uma incompatibilidade entre o faster-whisper e a versão nova do PyAV. YouTube (16 vídeos): legenda indisponível e download bloqueado pelo YouTube no runner do GitHub ("Sign in to confirm you're not a bot"), risco que já estava previsto no plano.

**Correção.** O áudio passa a ser decodificado com o ffmpeg (16 kHz, mono) e entregue ao Whisper como vetor, sem passar pelo PyAV. Instagram e TikTok disparados de novo. O YouTube fica para a Apify, dentro da etapa de terceiros e transcrições (US$ 1,00).

**Executado.** 18 testes unitários aprovados.

## 22/11/2026: transcrição dos vídeos do núcleo (sem custo)

**O que mudou.** Novo `scripts/transcrever.py` e workflow `transcricao.yml` (uma tarefa por rede, em paralelo). No YouTube, usa primeiro a legenda do próprio vídeo; sem ela, e no Instagram e no TikTok, baixa o áudio com yt-dlp e transcreve com faster-whisper na CPU do runner, detectando o idioma. Imagem e carrossel ficam fora (não têm fala) e são contados no manifesto. Retoma de onde parou e grava a cada vídeo.

**Por quê.** As legendas do núcleo não citam o tema; para saber se elas falaram do acordo é preciso ouvir os vídeos. O responsável autorizou às 17h11. Sem custo em US$; a Apify (US$ 1,00 da etapa de terceiros e transcrições) só entra se alguma plataforma bloquear o download.

**Executado.** 18 testes unitários aprovados (só vídeos do núcleo, retomada, legenda do YouTube antes do áudio). Workflow disparado logo após este commit.

## 22/11/2026: posts do recorte coletados (run 45064535261) e página com Instagram e TikTok

**Resultado** (`instagram_latest.json` e `tiktok_latest.json`, etapa posts):
- Instagram (execução zy5eI85W6wGJeXfng): 337 itens, 9 de outros perfis fora do acervo. Base/núcleo: Mariam 48/21, Hyatt 8/5, Carima 31/20, Fabíola 1/2. Universo ⛔ (o ator não informa). Custo gravado de novo como 0,0, mesmo relendo a execução: esse ator não devolve a cobrança; pelo preço de referência (US$ 0,05 por mil), 337 itens dão cerca de US$ 0,02 (estimativa).
- TikTok (execução jywrkdCGySox9KfbG, filtro de 01/06 a 14/08): 109 itens, US$ 0,546 medidos. Base/núcleo: Mariam 68/17 (universo 3.628), Hyatt 4/4 (226), Carima 4/3 (570), Fabíola 5/4 (941).
- "Completa" aqui significa que o ator devolveu menos itens que o limite sem atingir o teto, usando o próprio filtro de data. A leitura não foi conferida pela data mais antiga, como no YouTube.
- Nenhuma das 76 legendas do núcleo no Instagram e no TikTok contém Hamas, desarmamento, Gaza, Palestina ou os termos em árabe. Isso só cobre a legenda: falta a fala dos vídeos.

**Página.** Panorama, caderno 03 e saúde da coleta agora leem Instagram e TikTok. Conferida no Chrome headless servida localmente: 92 publicações no núcleo (YouTube 16, Instagram 48, TikTok 28).

**Executado.** 16 testes unitários aprovados; `node --check` no script da página.

## 22/11/2026: etapa de posts no recorte (01/06 a 14/08/2026)

**O que mudou.** `apify.py` relê a execução depois que ela termina, até três vezes, para gravar o custo de fato cobrado (o responsável informou que o teste custou cerca de US$ 0,25; os manifestos mediram US$ 0,223). O TikTok passa a pedir `oldestPostDateUnified` 2026-06-01 e `newestPostDate` 2026-08-14; o Instagram, `onlyPostsNewerThan` 2026-06-01 (o que vier depois de 14/08 fica fora do acervo). Se o custo chega a 95% do teto da execução, a cobertura é marcada como "parcial ⛔ (parou no teto)".

**Por quê.** O responsável pediu às 17h06 os posts do recorte, dentro do teto aprovado (etapa de posts: US$ 1,50).

**Executado.** 16 testes unitários aprovados. Etapa de posts disparada logo após este commit (Instagram primeiro e, em seguida, TikTok com o que restar).

## 22/11/2026: teste do apidojo no TikTok (run 45063770407)

**Resultado** (`apify_tiktok_teste_apidojo_20261122T195900Z.json`, execução NchRIPfoMBH9XlZ7I): pedi 60 itens para quatro perfis e vieram 10, todos de Mariam. As outras três ficaram com 0. Universo de Mariam: 3.627 (`channel.videos`), o mesmo do clockworks.

**Problema de medição.** Três execuções registraram custo 0,0 (Instagram Nhg2oM10cgWdHAZNQ, apidojo NchRIPfoMBH9XlZ7I e uma do clockworks não, essa mediu US$ 0,223). O custo é lido da resposta da execução logo ao terminar, e a cobrança ainda não aparece nela. Gasto medido na etapa de teste: US$ 0,223; o real é um pouco maior. Pelos preços de referência, Instagram (60 itens) e apidojo (10 itens) somam menos de US$ 0,01, mas isso é estimativa.

**Pendente.** Reler a execução depois de terminada (GET /actor-runs/{id}, que não é consulta de saldo) para gravar o custo cobrado. Decidir o ator do TikTok para a etapa de posts.

## 22/11/2026: resultado do teste pago (run 45063550727), correções e teste de ator mais barato no TikTok

**Resultado do teste** (manifestos `instagram_latest.json` e `tiktok_latest.json` desse run): 15 itens mais recentes por perfil.
- Instagram (esdrasdw, execução Nhg2oM10cgWdHAZNQ): 60 itens; 54 das próprias influenciadoras e 6 de outros perfis, deixados fora do acervo. O manifesto registra custo 0,0: o valor real não foi medido (a execução não devolveu cobrança). Universo ⛔: o ator não informa o total de posts do perfil.
- TikTok (clockworks, execução txaO3NUnCk9NkL8Ma): 60 itens, US$ 0,223, ou cerca de US$ 3,70 por mil, muito acima do previsto. Universo informado: Mariam 3.627, Hyatt 226, Carima 570 e Fabíola 941 vídeos.

**Correções.** Datas do TikTok com fração de segundo eram gravadas cortadas ("…:34."); `quando()` agora converte de verdade para UTC. O tipo do Instagram vinha como código (1, 2, 8) e agora sai como imagem, vídeo ou carrossel. As 114 linhas já gravadas tiveram data, tipo e janela reescritos no lugar, sem apagar nenhuma. A etapa de teste deixa de ser dividida meio a meio entre as redes: cada execução usa o que resta, até US$ 0,50.

**Novo.** Opção `--ator` e suporte a `apidojo~tiktok-profile-scraper` (o Atlas mediu US$ 0,0003 por item). Teste comparativo no TikTok disparado logo após este commit, dentro do teto da etapa de teste (restam US$ 0,777).

**Executado.** 15 testes unitários aprovados.

## 22/11/2026: teste pago recusado pela Apify (sem custo) e correção

**O que aconteceu.** Run 45063428772: as duas redes foram recusadas na entrada, antes de executar; custo de US$ 0,00 nos manifestos `apify_instagram_teste_20261122T195502Z.json` e `apify_tiktok_teste_20261122T195503Z.json`. Instagram: o campo `videoViewCount` não é aceito em `selectedFields`. TikTok: o teto de US$ 0,125 por execução estava abaixo do mínimo de US$ 0,50 exigido pela Apify.

**O que mudou.** Passa a ser uma execução por rede com os quatro perfis juntos (teto de US$ 0,50 cada; o teste continua somando no máximo US$ 1,00), e os itens são separados por dono. Com menos de US$ 0,50 sobrando na etapa, nada roda. Os campos do Instagram agora são os mesmos do ODI Espanha, mais `videoPlayCount`.

**Executado.** 13 testes unitários aprovados. Novo disparo do teste logo após este commit.

## 22/11/2026: orçamento de US$ 10 autorizado e coletor pago de Instagram e TikTok

**O que mudou.** `data/config/coleta.json`: teto de US$ 10 por etapa (teste 1,00; posts 1,50; terceiros e transcrições 1,00; comentários 5,00; reserva 1,50), com a autorização do responsável. Novo `scripts/collect_apify_posts.py` (Instagram: esdrasdw~instagram-content-scraper; TikTok: clockworks~tiktok-scraper), `scripts/apify.py` (copiado do ODI Espanha, sem consulta de saldo) e o workflow `pagas.yml`, com disparo manual.

**Por quê.** O responsável aprovou o orçamento da seção 11 do plano em 22/11/2026, às 16h53 ("ta aprovado").

**Trava de gasto.** O coletor soma o custo dos manifestos da etapa; no teste, cada rede usa no máximo metade de US$ 1,00, dividida entre os perfis (maxTotalChargeUsd por execução).

**Executado.** 12 testes unitários aprovados (sem autorização nada roda; o teto por execução considera o gasto anterior; curtida oculta vira vazio; post de outro perfil fica fora; janela e universo do TikTok). Teste pago disparado logo após este commit.

## 22/11/2026: primeira coleta do YouTube com dados (run 45062903853)

**Resultado** (manifesto `data/manifest/youtube_latest.json`): 4 de 4 canais lidos, nenhum erro, cerca de 612 unidades de cota, cobertura completa nos quatro.
- Mariam Chami: universo de 2.036 vídeos; 71 na base e 16 no núcleo. Nenhum dos 16 tem termo das famílias "núcleo", "tema amplo" ou "árabe" no título ou na descrição.
- Hyatt Omar (universo de 5), Carima Orra (32) e Fabíola Oliveira (145): nenhum vídeo entre 01/06 e 14/08/2026.
- Terceiros no núcleo, gravados só no privado e antes da revisão de homônimos: Mariam 5, Hyatt 50, Carima 2, Fabíola 93.

**Leitura.** Ausência de termo no título ou na descrição não prova silêncio: falta ler a fala (transcrição) dos 16 vídeos de Mariam no núcleo.

## 22/11/2026: correção do endereço da API do YouTube

**O que mudou.** `collect_youtube.py` montava o endereço com o nome do método (`/channels.list`) em vez do recurso (`/channels`). Corrigido. Perfil com erro passa a aparecer no manifesto com o motivo, e a execução falha quando nenhum canal confirmado é lido.

**Por quê.** Run 45062821933 (primeira coleta real): as 8 chamadas voltaram HTTP 404, nenhum canal lido, e o workflow terminou como "success". O manifesto `data/manifest/youtube_20261122T194830Z.json` registra os 8 erros. Os segredos não eram o problema.

**Executado.** 7 testes unitários aprovados, incluindo um novo que confere o endereço montado. Nova execução disparada logo após este commit.

## 22/11/2026: workflow aponta para o privado `odi-secret-infl-`

**O que mudou.** `gratuitas.yml` e `CLAUDE.md` passam a usar `WandersonH/odi-secret-infl-`, o nome com que o repositório privado foi criado.

**Por quê.** O workflow apontava para `odi-secret-infl`, sem hífen, que não existe; as menções de terceiros não seriam gravadas.

**Executado.** Testes unitários (6, aprovados). Disparo do workflow logo após este commit (ID do run na próxima entrada).

## 22/11/2026: TikTok das quatro confirmado

**O que mudou.** `data/config/atores.json`: TikTok confirmado para Mariam Chami (@mariamchami1), Carima Orra (@carimaorra1), Fabíola Oliveira (@fabiolaoliver) e Hyatt Omar (@hyattomar).

**Por quê.** O responsável enviou os quatro links no chat às 16h47.

**Executado.** Testes unitários (6, aprovados). Nenhuma coleta de TikTok rodou: é paga (Apify) e o teto continua em 0.

**Pendente.** Teto e autorização para o teste pago; escolha do ator de perfil do TikTok no teste.

## 22/11/2026: Instagram das quatro confirmado

**O que mudou.** `data/config/atores.json`: Instagram de Mariam Chami (@mariamchami_), Hyatt Omar (@hyattomar), Carima Orra (@carimaorra) e Fabíola Oliveira (@fabiolaoliver) passa de candidato para confirmado.

**Por quê.** Os quatro endereços estavam na segunda mensagem do responsável e tinham ficado de fora por erro de leitura; ele reafirmou às 16h43.

**Executado.** Testes unitários (6, aprovados). Nenhuma coleta de Instagram rodou: ela é paga (Apify) e o teto continua em 0.

**Pendente.** TikTok segue como candidato; teto e autorização para o teste pago de Instagram.

## 22/11/2026: página com a identidade do ODI (10 cadernos)

**O que mudou.** `index.html` com a folha de estilo do ODI Atlas (`assets/odi-atlas.css`, copiada do ODI Espanha), marca e favicons, e os dez cadernos da seção 9 do plano. `.nojekyll` para o GitHub Pages servir a página em vez do README. O coletor do YouTube passa a gravar também `data/manifest/youtube_latest.json`, que a página lê.

**Por quê.** O GitHub Pages foi ativado pelo responsável e mostrava só o README.

**Executado como teste.** `python3 -m unittest discover -s tests -v` (6 testes, aprovados); `node --check` no script da página; página aberta no Chrome headless servida localmente: cadernos e perfis aparecem, e o panorama mostra ⛔ "nenhuma coleta executada", pois ainda não há dados.

**Pendente.** Todos os cadernos mostram ⛔ até a primeira coleta. O caderno 04 (índice de engajamento) ainda não tem script.

## 22/11/2026: estrutura inicial e coleta gratuita do YouTube (sem execução ainda)

**O que mudou.** Repositório criado a partir da arquitetura do ODI Espanha. Inclui: configuração do projeto (janelas base e núcleo), atores com endereço de YouTube confirmado pelo responsável, famílias de palavras-chave (rascunho), coletor gratuito do YouTube, teste unitário e workflow de disparo manual.

**Por quê.** Plano aprovado em 22/11/2026 (documento "ODI Influenciadoras — Plano de coleta, método e páginas"): começar pelo que é gratuito, antes de qualquer gasto na conta Apify.

**Executado como teste.** `python3 -m unittest discover -s tests -v`: 6 testes, todos aprovados (paginação parada pela data inicial, limite de páginas sem marcar cobertura como completa, exclusão do canal próprio em menções de terceiros, atualização sem apagar acervo, chave não exposta em erro HTTP, normalização com acentos e árabe).

**Não executado.** Nenhuma coleta real. O workflow depende dos segredos `YOUTUBE_API_KEY` e `ODI_INTERNO_TOKEN`, cadastrados pelo responsável. Teste real: disparo manual de "Coleta gratuita — YouTube".

**Pendente.**
- Repositório privado: o GitHub do responsável tem `odi-secret-infl-` (com hífen final), não `odi-secret-infl`. Confirmar o nome antes de cadastrar o token; o workflow aponta para `odi-secret-infl`.
- Perfis de Instagram (Mariam, Hyatt, Carima, Fabíola) e TikTok: candidatos, sem coleta até confirmação.
- Livro de códigos e famílias de palavras: rascunho, sem validação (kappa ≥ 0,70 não medido).
- Comentários do YouTube e rede de menções: fora desta etapa.
- Coleta paga (Apify): teto 0 em `data/config/coleta.json`; nenhum ator roda sem teto e autorização.

**Evidência.** Este commit; testes em `tests/test_youtube.py`.
