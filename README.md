# ODI Influenciadoras

Posicionamento de influenciadoras muçulmanas brasileiras sobre o acordo de desarmamento gradual do Hamas, aceito em 31/07/2026. Mede o que cada uma publicou, o grau de interação e as menções de terceiros no período do evento.

As regras de coleta, universo e privacidade estão em [CLAUDE.md](CLAUDE.md). Mudanças no [CHANGELOG.md](CHANGELOG.md).

## Janelas

- **Linha de base:** 01/06/2026 a 22/07/2026
- **Núcleo (evento):** 23/07/2026 a 14/08/2026. Menções de terceiros só aqui.

## Coleta

- **YouTube** (gratuita, cota da API): `scripts/collect_youtube.py`, disparado pelo workflow "Coleta gratuita — YouTube".
- **Instagram, TikTok, X, imprensa, Google Trends:** a fazer. Dependem de confirmação de perfil e de teto de gasto aprovado, quando pagos.

## Testes

```
python3 -m unittest discover -s tests -v
```
