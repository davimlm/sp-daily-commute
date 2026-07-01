# Trajeto Diário na Metrópole de São Paulo — Redes Origem-Destino

Trabalho acadêmico que modela os deslocamentos diários dos moradores da Região
Metropolitana de São Paulo (RMSP) como redes complexas, a partir dos dados da
**Pesquisa Origem e Destino 2023 (OD 2023)**, realizada pela Companhia do
Metropolitano de São Paulo (Metrô-SP).

## Sobre o projeto

A partir do microdado de viagens da Pesquisa OD 2023, foram construídas quatro
redes dirigidas e ponderadas, todas compartilhando os mesmos vértices (zonas
de tráfego), mas com pesos de aresta diferentes:

| Rede | Peso da aresta | Significado |
|---|---|---|
| **Viagens** | `viagens_estimadas` | Nº estimado de viagens/dia entre a zona de origem e a de destino (expandido pelo fator amostral da pesquisa) |
| **Distância** | `distancia_media_m` | Distância média em linha reta (metros) entre origem e destino |
| **Tempo** | `tempo_medio_min` | Duração média da viagem (minutos) |
| **Classe social** | `classe_media` / `classe_moda` | Classificação econômica média (escala 1=A a 6=D-E, Critério Brasil) das pessoas que fazem o trajeto |

## Fonte dos dados

- **Origem**: Pesquisa Origem e Destino 2023, Companhia do Metropolitano de
  São Paulo (Metrô-SP). Pesquisa domiciliar de mobilidade urbana realizada
  desde 1967, a cada ~10 anos, cobrindo os 39 municípios da RMSP.
- **Link oficial**: https://www.metro.sp.gov.br/pt_BR/pesquisa-od/
- **Portal de dados abertos**: https://transparencia.metrosp.com.br/dataset/pesquisa-origem-e-destino
- **Arquivo usado**: `Banco2023_divulgacao_190225.sav` (microdado em nível de
  viagem individual, ~143 mil registros). **Não incluído neste repositório**
  por ser um arquivo grande (~77 MB) e de download público — baixe direto do
  portal do Metrô-SP.

## O que é vértice, aresta e peso

- **Vértice**: uma zona OD (zona de tráfego definida pelo Metrô-SP para a
  pesquisa), identificada por um código numérico e associada a um município
  da RMSP. Cada vértice tem como atributo as coordenadas do centróide
  (projeção UTM/SIRGAS 2000) e o nome do município.
- **Aresta**: uma ligação dirigida `origem → destino` entre duas zonas,
  existente sempre que houve pelo menos uma viagem amostrada nesse sentido
  (respeitando o filtro de amostra mínima, ver abaixo). O grafo é **dirigido**
  porque o fluxo de A para B não é necessariamente igual ao de B para A
  (ex: deslocamento pendular casa-trabalho pela manhã vs. retorno à tarde).
- **Peso**: varia conforme a rede (ver tabela acima). Cada aresta também
  carrega o atributo `n_amostras`, indicando quantas viagens da amostra bruta
  sustentam aquele peso — útil para avaliar a confiabilidade estatística de
  cada ligação.

## Limitações metodológicas

- **Amostra mínima por par origem-destino**: pares de zonas com menos de
  5 viagens amostradas foram descartados. Com 500+ zonas, muitos pares têm
  poucas observações na amostra, o que tornaria médias de distância/tempo/
  classe social estatisticamente frágeis (calculadas em cima de 1-2 casos).
  Esse corte reduz o dataset de ~32.700 para ~3.500 pares, priorizando
  ligações com suporte amostral mais robusto.
- **Viagens intrazona removidas**: viagens com origem = destino (deslocamento
  dentro da própria zona) foram excluídas, por não representarem
  deslocamento entre regiões distintas.
- **Coordenadas em projeção UTM (metros), não em graus decimais**: os
  centróides usados no grafo vêm diretamente do microdado original (SIRGAS
  2000 / UTM), não em latitude/longitude. Para uso em ferramentas de
  geolocalização (ex: plugin Geo Layout do Gephi), é necessário reprojetar.
- **Amostra expandida, não censo**: a Pesquisa OD é uma pesquisa amostral;
  os pesos de "viagens estimadas" usam o fator de expansão da própria
  pesquisa (`Fe_via`) para aproximar o total real da população, mas ainda
  assim carregam a margem de erro amostral típica de pesquisas domiciliares.

## Estrutura do repositório

```
sp-daily-commute/
├── README.md
├── scripts/
│   └── gerar_grafos.py          # script Python que processa o microdado e gera os CSVs/GraphML
├── data/
│   ├── vertices.csv             # atributos das zonas (nós)
│   ├── arestas_viagens.csv
│   ├── arestas_distancia.csv
│   ├── arestas_tempo.csv
│   └── arestas_classe_social.csv
├── grafo/
│   └── grafo_viagens.graphml    # grafo consolidado (todas as métricas), pronto para Gephi/NetworkX
└── imagens/
    └── grafo_viagens.png        # visualização gerada no Gephi
```

## Como reproduzir

1. Baixe o microdado `Banco2023_divulgacao_190225.sav` no portal do Metrô-SP
   (link acima) e coloque na raiz do projeto (ou ajuste o caminho no script).
2. Instale as dependências:
   ```bash
   pip install pandas numpy pyreadstat networkx
   ```
3. Rode o script:
   ```bash
   python scripts/gerar_grafos.py
   ```
4. Os arquivos serão gerados na pasta `saida/` (CSVs + GraphML).
5. Abra `grafo_viagens.graphml` no [Gephi](https://gephi.org/) para
   visualização e análise de rede (grau, centralidade, comunidades etc.).

## Autores
Davi Monteiro Lima e Guilherme Siqueira


Trabalho desenvolvido para a disciplina de Comunicação e Redes — UFABC, 2026.
