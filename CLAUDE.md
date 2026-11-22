# Instruções para qualquer IA ou pessoa que trabalhe neste repositório

Este projeto herda a arquitetura e as regras do ODI Atlas (`WandersonH/odi-atlas`) e do ODI Espanha (`WandersonH/odi-espanha`). Objeto: posicionamento de influenciadoras muçulmanas brasileiras sobre o acordo de desarmamento do Hamas aceito em 31/07/2026.

1. **Atualize o `CHANGELOG.md` em toda mudança**, no mesmo commit: o que mudou, por quê, o que foi executado de verdade (com ID do run ou comando), o que ficou pendente e onde está a evidência.
2. Não declare pronto nada que não foi executado com dados reais. Dado ausente é bloqueio (⛔), não sucesso. Sem coleta, a página mostra ⛔, nunca zero.
3. Não invente números. Todo número vem de arquivo, manifesto ou run identificável.
4. Rode `python3 -m unittest discover -s tests -v` antes de cada commit.
5. Nunca coloque tokens ou chaves em código, commits, mensagens ou logs.
6. **Nunca apagar dados** (`data/`, repositório privado, histórico do git) nem reescrever histórico sem autorização explícita do responsável naquele momento.
7. **Toda amostra aparece com o universo.** Quanto a plataforma informa que existe (com a fonte), quanto foi lido e como a amostra foi tirada. Universo que a plataforma não informa é ⛔, nunca estimado. Estimativas aproximadas da API (ex.: `pageInfo.totalResults` da busca) não são universo. Cobertura "completa" só quando a leitura para pela data inicial do período, e não pelo limite.
8. **Gasto só com teto autorizado.** Nenhuma coleta paga roda sem teto maior que zero em `data/config/coleta.json`, gravado junto com a frase de autorização (quem, quando, o quê) em `autorizacao`. Conta Apify dedicada (segredo `APIFY_TOKEN_INFL`); nenhuma consulta de saldo ou de limites. O custo fica nos manifestos e nunca aparece na página.
9. **Só perfil confirmado é coletado.** Cada perfil em `data/config/atores.json` tem a fonte onde o endereço foi conferido. Endereço provável sem fonte é candidato e fica fora da coleta até uma pessoa abrir o perfil e confirmar.
10. **Privacidade.** O repositório público guarda só as publicações dos perfis monitorados (as próprias influenciadoras). Menções de terceiros (outros canais, podcasts, notícias citando as influenciadoras) vão só para o repositório privado (`WandersonH/odi-secret-infl-`, com hífen no fim). Sem o privado disponível, o coletor não grava terceiros. Ao público vão só contagens e agregados. A ficha de um perfil candidato (nome, bio, números) nunca vai ao público: pode ser a conta de outra pessoa.
11. **Janela das menções de terceiros.** Só no núcleo (23/07 a 14/08/2026), conforme pedido do responsável em 22/11/2026. A linha de base (01/06 a 22/07/2026) serve só ao índice de engajamento das próprias publicações.
12. **Menção de terceiros exige revisão de homônimos** antes de contar como menção (`revisao_homonimos`).
