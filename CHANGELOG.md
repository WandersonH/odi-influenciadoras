# Changelog

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
