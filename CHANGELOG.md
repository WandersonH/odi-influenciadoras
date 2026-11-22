# Changelog

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
