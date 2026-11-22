# Changelog

## 22/11/2026: mensagem do panorama durante a republicação

O responsável viu, às 20h19, o caderno 01 dizer "Nenhuma coleta executada ainda". O arquivo `data/manifest/youtube_latest.json` estava íntegro no repositório. Na página publicada, conferida no Chrome logo depois, ele foi lido com status 200 e o panorama apareceu normal. A falha foi passageira: três commits seguidos (0caf3bd, 87fa738 e o run de comentários) fizeram o GitHub Pages republicar o site, e a página não leu o manifesto nesse intervalo. A mensagem antiga dizia que não havia coleta, o que era falso. Agora diz que o manifesto não pôde ser lido, explica a republicação e pede para recarregar.

## 22/11/2026: resultado das recoletas da revisão crítica

- **Acervo do YouTube com título** (run 45081857459, `gratuitas.yml`): 4 de 4 canais lidos; 87 vídeos no acervo, todos com título em `data/youtube/videos.csv`. O workflow regerou o que dizem, o engajamento, as redes e o corpus (o corpus ganhou 240 linhas). Com os títulos, um vídeo da Mariam passa a cair no tema Gaza. Em nenhuma rede há publicação sobre o acordo (0 em YouTube, Instagram e TikTok).
- **Comentários do YouTube com respostas**: o run 45081868200 leu os comentários, mas o push público falhou. O motivo foi um conflito em `data/terceiros/resumo.json`, gravado ao mesmo tempo pelo run 45081857459. O CSV privado chegou ao privado (commit e25feb7). O run 45082213196 foi disparado de novo e gravou o público (commit 0caf3bd).
  - Mariam: 16 vídeos no núcleo; universo de 2.698 comentários (soma de `commentCount`, que inclui respostas), 2.698 lidos, entre eles 599 respostas. A cobertura é completa.
  - 1.947 comentaristas distintos.
  - Temas: islamofobia 74, Israel 45, Gaza 18, acordo 1.
  - Hyatt, Carima e Fabíola não têm vídeo no núcleo.
  - Rede de respostas: 404 autores e 427 arestas (540 respostas entre autores). Os autores ficam codificados no público.
- **Pendente (humano)**: revisar os itens "a conferir" de terceiros; codificação humana e kappa; description e topics dos repositórios; CEP.

## 22/11/2026: revisão crítica de todo o trabalho e correção das lacunas

Pedido do responsável às 20h03 ("revise criticamente todo trabalho executado e veja gaps"). Lacunas encontradas e o que foi feito:

1. **Perfis sem X** (caderno 01): o cartão listava só YouTube, Instagram e TikTok. Corrigido.
2. **X no panorama** aparecia como "parcial ⛔": passa a "sem posts no período (conta parada)".
3. **X e YouTube sem posts fora do engajamento sem explicação** (caderno 04): nota com o motivo de cada ausência.
4. **Comentários do YouTube com uma influenciadora só** (caderno 05): Hyatt, Carima e Fabíola não têm vídeo no núcleo. Agora aparecem com essa explicação, em vez de sumir.
5. **Respostas dos comentários do YouTube não eram lidas** (2.098 de 2.696): o coletor passa a ler todas as respostas (comments.list), como o coletor completo do Atlas. Recoleta disparada.
6. **Acervo do YouTube sem título**: o caderno 03 não tinha texto dos vídeos da base. O coletor passa a guardar o título. Recoleta disparada.
7. **Saúde da coleta desatualizada** (caderno 10): imprensa, comentários, checagens, circulação e terceiros apareciam como "não executada". A tabela passa a ler os manifestos.
8. **Menções de terceiros sem a regra de homônimos do plano** (caderno 06): novo `build_terceiros.py`. Uma menção conta com @ ou nome + termo de contexto, em YouTube (título e descrição, pela API), X (API e navegador) e imprensa. Canal com menos de 10 mil inscritos aparece como código. Achado: vídeos a conferir, como "FUI PROCESSADO POR UMA INFLUENCIADORA MUÇULMANA" (12/08, busca pela Mariam) e "TERRORISTA MATA PESSOAS E ESQUERDISTA SE PREOCUPA COM ISLAMOFOBIA!" (Kim Kataguiri, 28/07, busca pela Fabíola). A variante "Fabiola Oliver" entra nas buscas.
9. **X pela busca avançada no navegador** (pedido às 19h50): 8 buscas no núcleo, no Chrome do responsável, sem custo. Nenhuma menção às quatro; os 2 resultados de "Fabíola Oliveira" são homônimos. Texto no privado (`data/terceiros/x_navegador.csv`), contagens em `data/manifest/terceiros_x_navegador.json`.
10. **Redes de comentários do plano não feitas** (palavras e respostas): novo `build_rede_comentarios.py` com `redes_caso.palavras()` e `respostas()` do Atlas e as estatísticas do Atlas. Palavras: YouTube 458 nós, Instagram 215, TikTok 167. A rede de respostas depende da recoleta (item 5).
11. **Filtro de tema do caderno 03 parecia não filtrar** (apontado às 20h04): agora filtra também a tabela de temas e lista todas as publicações do tema escolhido.
12. **Trends por estado coletado e não mostrado**: tabela por UF no caderno 07.
13. **Etiqueta do topo** só citava o YouTube: corrigida.

**Ainda pendente (depende de pessoas ou de decisão):** codificação humana e kappa (livro de códigos a validar); revisão humana dos vídeos "a conferir"; descrição e tópicos dos repositórios (o proxy desta sessão não deixa editar configurações); confirmação de CEP com o PPGCOM.

**Executado.** 35 testes unitários; `node --check`; página inteira renderizada no Chrome headless, com todos os cadernos preenchidos.

## 22/11/2026: menções no X — teste do apidojo~tweet-scraper

**Contexto.** Com o período nos campos since/until (run 45077239872), o xquik devolveu de novo só 2 itens. Sem datas, devolve as menções recentes, mas não chega ao núcleo.

**O que mudou.** `collect_terceiros_x.py --ator apidojo~tweet-scraper` põe `since:2026-07-23 until:2026-08-15` dentro de cada busca separada (nome; @), `sort: Latest`, até 600 por influenciadora. Preço da loja: US$ 0,40 por mil tweets, mínimo de 50 por busca. Teto de US$ 0,50 por execução, na etapa de terceiros. Pedido do responsável às 19h23.

## 22/11/2026: menções no X sem datas (run 45076755782) e nova tentativa com datas

**Resultado.** Busca separada por nome e por @, sem datas: 1.716 itens, US$ 0,26. Mencionam as influenciadoras: Mariam 313, Hyatt 651, Carima 34, Fabíola 126. Só 1 está no núcleo. A leitura vai do mais recente para trás e, ao que parece, não chegou a julho e agosto. O manifesto passa a registrar o período lido por influenciadora.

**O que mudou.** Opção `--com-datas`: as mesmas buscas separadas, com o núcleo nos campos since/until do ator. É o padrão na etapa "posts" do workflow.

## 22/11/2026: imprensa, rede de circulação do caso Hamas, estatísticas na página, destaques e método completo

**Imprensa** (`collect_imprensa.py`, run 45076870902, sem custo): os 10 primeiros do Google Notícias (RSS, Brasil) para 6 termos do tema e para os 4 nomes, em dois recortes: dia do anúncio (30/07 a 02/08) e núcleo. No dia do anúncio aparecem G1, BBC, CNN Brasil, Folha, Agência Brasil e Brasil de Fato. Nenhuma matéria cita Mariam, Hyatt ou Carima; os resultados de "Fabíola Oliveira" são de homônimos. Universo ⛔.

**Rede de circulação** (`build_circulacao.py`, mesmo run, cerca de 404 unidades de cota): YouTube search.list de 30/07 a 02/08 em 4 termos, com 87 vídeos de 60 canais (CBN News, Rede Gospel, BBC News, Band Jornalismo, SBT News, Jovem Pan…), mais 55 notícias de 22 veículos. Rede pela `redes_caso.circulacao()` do Atlas: 92 nós, 189 arestas, Q 0,234, 3 comunidades. Nenhum canal das influenciadoras está na rede. Pedido do responsável às 19h14.

**Página.** O caderno 07 ganhou a seção de imprensa (por recorte e termo, com alerta de homônimos). O caderno 08 ganhou a circulação (desenho, canais de maior audiência, estatísticas, comunidades, centralidades e downloads) e as estatísticas do Atlas na rede de marcações. Os cadernos 01 e 05 ganharam um destaque dos comentários (o público levou o tema ao YouTube da Mariam). O caderno 10 foi reescrito com o método completo (`data/config/metodologia.json`, a partir do plano aprovado): pergunta, hipóteses, recorte, desenho amostral, coleta e situação real de cada frente, dicionário, livro de códigos, análises, ética, limites e referências. Pedidos do responsável às 19h14 e 19h15.

**Correções.** Erro de ordem no script (função usada antes de definida) deixava em branco os cadernos a partir do 08 na versão local; títulos do YouTube com entidades HTML (&#39;).

**Executado.** 34 testes unitários; `node --check`; cadernos 01, 07, 08 e 10 abertos no Chrome headless.

## 22/11/2026: similitude no desenho do Atlas, estatísticas de rede do Atlas e menções no X refeitas

**Similitude.** O desenho estava quebrado: o raio virava texto e a soma com a posição jogava os rótulos para a margem (apontado pelo responsável às 19h14). Agora segue o desenho do ODI Atlas e do IRaMuTeQ: a palavra é o nó, o tamanho é a frequência, a espessura é a coocorrência e a cor é a influenciadora em que a forma é específica, com halo por comunidade (Louvain). Na cópia de `similitude.py`, a árvore usa Kamada-Kawai, porque o spring amontoava o centro.

**Estatísticas de rede.** `estatisticas_redes.py` foi copiado do ODI Atlas sem mudança (indicadores do painel Statistics do Gephi, Louvain com semente 42, E-I das duas maiores comunidades e top 5 por grau ponderado, PageRank, intermediação e autovetor). `build_redes.py` grava `estatisticas_redes.csv`, `centralidades_redes.csv` e `comunidades_redes.csv`. Na rede de marcações: densidade 0,031, diâmetro 6, assortatividade −0,76, Q 0,375, E-I das duas maiores −0,886.

**Menções no X.** O responsável encontrou menções às influenciadoras no X, e a busca só tinha trazido 2. Agora são duas buscas por influenciadora (nome entre aspas; @), sem OR e sem datas no ator, com o núcleo filtrado pela data de cada post. Disparado logo após este commit.

## 22/11/2026: comentários coletados (run 45071626874) e menções no X (run 45071871689)

**Comentários do núcleo.** YouTube: 2.098 lidos de um universo de 2.696 (a API conta as respostas, que não foram lidas), 1.771 comentaristas, sem custo; citam islamofobia 48, Israel e guerra 29, Gaza e Palestina 11, acordo/Hamas 1. Instagram: 1.524 lidos em 48 publicações (universo ⛔), US$ 2,44; islamofobia 9, Gaza e Palestina 7, Israel 2. TikTok: 950 lidos em 28 vídeos, US$ 1,18; islamofobia 21, Gaza 1. Texto e autor estão no privado (`data/comentarios/`). Etapa de comentários: US$ 3,62 de 5,00.

**Menções no X** (núcleo, campos since/until do ator): 2 itens, 1 menção a Fabíola Oliveira só pelo nome (revisão de homônimos pendente), US$ 0,0003. Não está confirmado se o número baixo é real ou limite da busca do ator; falta testar a mesma busca sem datas.

**Gasto total na Apify** (manifestos): cerca de US$ 4,43 de 10.

## 22/11/2026: caderno 05 lê os comentários (só contagens)

**O que mudou.** O caderno 05 mostra, por rede e por influenciadora: publicações, universo de comentários, lidos, comentaristas distintos, quantos comentários citam acordo/Hamas, Gaza e Palestina, Israel ou islamofobia, e a nuvem de palavras dos comentários. Não mostra texto nem autor.

**Pergunta do responsável às 18h21.** O corpus usa o mesmo `lexique_pt.txt` do ODI Atlas (dicionário de português da instalação do IRaMuTeQ do responsável, 142.615 formas), conferido byte a byte com `cmp`, e as mesmas formas ativas (nome, verbo, adjetivo e formas não reconhecidas).

**Executado.** `node --check`; testes unitários.

## 22/11/2026: coletor de comentários do núcleo

**O que mudou.** Novo `scripts/collect_comentarios.py`, com o workflow `comentarios.yml`. YouTube pela API oficial (todos os comentários, sem custo); Instagram (datadoping) e TikTok (clockworks), atores do ODI Atlas, com até 50 comentários por publicação. Usa a etapa "comentarios" do teto (US$ 5,00): até US$ 3,60 no Instagram e US$ 1,20 no TikTok. Texto e autor vão só para o privado; o público recebe `data/comentarios/<rede>_resumo.json`, com universo × lido por publicação, comentaristas distintos, nuvem e quantos comentários citam acordo/Hamas, Gaza e Palestina, Israel ou islamofobia.

**Por quê.** O responsável apontou às 18h13 que o caderno 05 dizia que dependia de teto, que já estava aprovado.

**Executado.** 32 testes unitários aprovados. Coleta disparada logo após este commit.

## 22/11/2026: X sem posts no recorte (contas paradas) e checagens coletadas

**X** (run 45071140887, com os campos since/until do ator): 0 posts no recorte, US$ 0,0001. Conferido no teste sem filtro (run 45070964861): o post mais recente de cada conta é anterior ao recorte (Mariam, 30/09/2016; Carima, 31/03/2020; Fabíola, 09/06/2025; Hyatt, 01/10/2025). O zero é real: as contas estão paradas no X. A cobertura com 0 lidos deixa de aparecer como "completa".

**Checagens** (Fact Check Tools, depois de o responsável ativar a API às 18h08): 17 checagens únicas desde 01/06 (Gaza 11, Palestina 6, Hamas 2), nenhuma checada no núcleo e nenhuma citando as influenciadoras. Universo ⛔: a API não informa o total.

## 22/11/2026: redes para o Gephi (caderno 08) e corpus IRaMuTeQ com CHD e similitude (caderno 09)

**Redes.** Novo `scripts/build_redes.py`: rede bipartida das influenciadoras com os @ e # que elas mesmas marcam no recorte, em todas as redes. Comunidades por Louvain (resolução 1,0, semente 42). Exporta GEXF, GraphML e CSV de nós e de arestas completas, sem corte. Resultado: 74 nós, 85 arestas, 4 comunidades, modularidade 0,375. Mariam e Hyatt partilham #arabe, #islam, #hijab, #muculmana, @hudabeauty e @sephorabrasil; Mariam e Carima partilham @naturabroficial, @oboticario e #naturaessencialsafran. Fabíola não marca ninguém (nó isolado). As redes de terceiros e de comentaristas, e o índice E-I, ficam ⛔ até a revisão de homônimos e a coleta de comentários.

**Corpus.** `chd_reinert.py`, `similitude.py`, `redes_caso.py` e `data/config/lexique_pt.txt` copiados do ODI Atlas sem mudança no método. `build_conteudo.py` é um módulo mínimo com as mesmas norm, STOP e EMOJI_TAG do Atlas. Novo `scripts/build_corpus.py`: legenda + fala de 251 textos, 71 deles com fala; exporta `data/corpus/influenciadoras_iramuteq.txt` com as variáveis *infl_, *rede_, *janela_ e *fala_; gera 636 segmentos de cerca de 40 palavras. CHD: 9 classes e 70% de segmentos classificados, abaixo dos 75% de Camargo & Justo, o que fica sinalizado na página. Similitude em GEXF. Nenhuma classe trata do acordo, de Hamas ou de Gaza. A classe 9 (mulher, islã, hijab, oprimida, governo, obrigar) é a mais próxima de posicionamento e está associada a Mariam.

**Pedidos do responsável** às 18h14: os cadernos 08 e 09 continuavam em ⛔ com os dados já disponíveis.

**Executado.** Os dois scripts rodaram localmente; `node --check`; cadernos 08 e 09 abertos no Chrome headless; testes unitários. Os workflows passam a regerar rede e corpus.

## 22/11/2026: X com o período nos campos do ator

**O que aconteceu.** Nos posts do X com `since:` na busca, com e sem `until:` (runs 45070655413 e 45070885494), vieram 0 itens. Nas menções de terceiros (run 45070739356), vieram só 2. Sem filtro de data (run 45070964861, teste), vieram 60 posts das quatro por US$ 0,0002. A página de entrada do ator (apify.com/xquik/x-tweet-scraper/input-schema) traz campos próprios `since` e `until`.

**O que mudou.** Posts e menções passam a usar esses campos, com `maxItemsPerTarget`. Os posts do teste (60, mais recentes, fora do recorte) ficam no acervo com janela "fora".

**Executado.** Testes unitários. Posts e menções disparados de novo.

## 22/11/2026: índice de engajamento relativo (caderno 04)

**O que mudou.** Novo `scripts/build_engajamento.py`, que grava `data/engajamento.json`: índice = interações da publicação ÷ mediana da mesma influenciadora, na mesma rede, na linha de base. Interações por rede: YouTube, curtidas + comentários; Instagram, só curtidas (o ator não devolve comentários); TikTok e X, curtidas + comentários + compartilhamentos. Com menos de 3 publicações na base, o índice fica ⛔. O caderno 04 traz o resumo por influenciadora e rede, um gráfico por rede (escala logarítmica, 1× e 31/07 marcados) e as 10 publicações mais acima do habitual. O índice é regerado nos workflows de coleta.

**Resultado.** Índice mediano no núcleo: Mariam, YouTube 3,74× (15 de 16 acima), TikTok 2,25×, Instagram 0,81×; Hyatt, Instagram 0,83× e TikTok 0,96×; Carima, Instagram 0,74× e TikTok 0,51×; Fabíola, TikTok 4,14× (base de só 5) e Instagram ⛔ (base de 1). Maior pico: Carima, TikTok, 14/08 (hijab em Copacabana), 462× o habitual. Nenhuma dessas publicações trata do acordo.

**Pendência apontada pelo responsável às 18h12.** O caderno dizia "próxima etapa", mas os dados já estavam coletados.

**Executado.** 30 testes unitários; `node --check`; caderno 04 aberto no Chrome headless.

## 22/11/2026: X das quatro confirmado; posts do X e citações de terceiros no X

**O que mudou.** `atores.json`: X confirmado para @eumariamchami, @hyattomar_, @CarimaOrra e @fabiola_oliver (links do responsável às 18h08). `collect_apify_posts.py --rede x` usa xquik~x-tweet-scraper com a busca do X `from:perfil since:2026-06-01 until:2026-08-15 -filter:retweets`; o universo é o `statusesCount` do perfil. Novo `collect_terceiros_x.py`: busca nome entre aspas OU @ de cada uma, sem a própria conta e sem reposts, só no núcleo, dentro da etapa `terceiros_transcricoes`. Texto e autor vão só para o privado (`data/terceiros/x_mencoes.csv`); ao público vão contagens por tipo (@ ou só nome), por dia e de autores distintos. `quando()` passa a ler a data do X ("Fri Jul 31 10:00:00 +0000 2026"). O caderno 06 mostra as menções no X; panorama, caderno 03 e saúde incluem o X.

**Por quê.** O responsável enviou os perfis e lembrou que as citações dos nomes por terceiros não tinham sido coletadas fora do YouTube.

**Gasto até aqui** (painel da Apify, informado pelo responsável às 18h10): US$ 0,81 de US$ 10, quase todo no TikTok (clockworks: 0,223 + 0,546).

**Executado.** 29 testes unitários aprovados; `node --check`. Posts do X e menções no X disparados logo após este commit.

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
