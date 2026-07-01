"""
Gera as redes (grafos) origem-destino da Pesquisa OD 2023 (Metrô-SP) a partir
do microdado de viagens (Banco2023_divulgacao_190225.sav).

Saídas (em ./saida):
  - vertices.csv                 -> atributos de cada zona (nó)
  - arestas_viagens.csv          -> peso = nº de viagens estimado (Fe_via)
  - arestas_distancia.csv        -> peso = distância média em linha reta (m)
  - arestas_tempo.csv            -> peso = duração média da viagem (min)
  - arestas_classe_social.csv    -> peso = classe social média (escala 1-6) + moda
  - grafo_viagens.graphml        -> grafo consolidado (todas as métricas como
                                     atributos de aresta) pronto para Gephi/NetworkX

Regra de limpeza aplicada (documentar no relatório):
  - Descartadas viagens sem zona de origem/destino (pessoa não viajou no dia)
  - Descartados pares origem-destino com menos de MIN_AMOSTRAS registros na
    amostra bruta (evita médias de distância/tempo/classe estatisticamente
    frágeis, calculadas em cima de 1 ou 2 observações)
  - Pesos de contagem de viagem usam o fator de expansão (Fe_via) da pesquisa,
    para representar o total estimado da população, não o tamanho da amostra
"""

import pandas as pd
import numpy as np
import pyreadstat
import networkx as nx
from pathlib import Path

# ------------------------------------------------------------------
# Configuração
# ------------------------------------------------------------------
ARQUIVO_SAV = r"D:\UFABC\Anos\2026\Q2.2026\CR\Trabalho\XLSX\Banco2023_divulgacao_190225.sav"
PASTA_SAIDA = Path("saida")
PASTA_SAIDA.mkdir(exist_ok=True)

MIN_AMOSTRAS = 5  # nº mínimo de viagens amostradas por par origem-destino

# Mapeamento da classe social (Critério Brasil) para escala numérica ordinal
# (A = classe mais alta -> 1, D-E = classe mais baixa -> 6)
MAPA_CLASSE = {1.0: "A", 2.0: "B1", 3.0: "B2", 4.0: "C1", 5.0: "C2", 6.0: "D-E"}

# ------------------------------------------------------------------
# 1. Leitura do microdado
# ------------------------------------------------------------------
print("Lendo microdado (.sav)...")
colunas = [
    "zona_o", "zona_d", "muni_o", "muni_d",
    "co_o_x", "co_o_y", "co_d_x", "co_d_y",
    "distancia", "duracao", "criteriobr", "Fe_via",
]
df, meta = pyreadstat.read_sav(ARQUIVO_SAV, usecols=colunas)
labels_muni = meta.variable_value_labels.get("muni_o", {})

print(f"  {len(df):,} registros brutos (nível viagem)".replace(",", "."))

# ------------------------------------------------------------------
# 2. Limpeza: remove quem não viajou no dia (zona_o/zona_d nulos)
# ------------------------------------------------------------------
viagens = df.dropna(subset=["zona_o", "zona_d", "distancia", "duracao"]).copy()
viagens["zona_o"] = viagens["zona_o"].astype(int)
viagens["zona_d"] = viagens["zona_d"].astype(int)
print(f"  {len(viagens):,} viagens válidas após remover não-viajantes".replace(",", "."))

# Remove viagens intrazona (origem == destino), pois não formam aresta
# em um grafo de deslocamento entre regiões. Documentar essa escolha.
antes = len(viagens)
viagens = viagens[viagens["zona_o"] != viagens["zona_d"]]
print(f"  {antes - len(viagens):,} viagens intrazona (origem=destino) removidas".replace(",", "."))

# ------------------------------------------------------------------
# 3. Agregação por par origem-destino
# ------------------------------------------------------------------
print("Agregando por par origem-destino...")

def moda_classe(serie):
    m = serie.mode()
    return m.iloc[0] if not m.empty else np.nan

agrupado = viagens.groupby(["zona_o", "zona_d"]).agg(
    n_amostras=("Fe_via", "size"),
    viagens_estimadas=("Fe_via", "sum"),
    distancia_media_m=("distancia", "mean"),
    tempo_medio_min=("duracao", "mean"),
    classe_media=("criteriobr", "mean"),
    classe_moda_num=("criteriobr", moda_classe),
).reset_index()

print(f"  {len(agrupado):,} pares origem-destino distintos (antes do filtro)".replace(",", "."))

# ------------------------------------------------------------------
# 4. Filtro da limitação metodológica (amostra mínima)
# ------------------------------------------------------------------
antes = len(agrupado)
agrupado = agrupado[agrupado["n_amostras"] >= MIN_AMOSTRAS].copy()
print(f"  {antes - len(agrupado):,} pares removidos por terem menos de "
      f"{MIN_AMOSTRAS} viagens amostradas".replace(",", "."))
print(f"  {len(agrupado):,} pares origem-destino restantes (dataset final)".replace(",", "."))
agrupado["classe_moda"] = agrupado["classe_moda_num"].map(MAPA_CLASSE)

# ------------------------------------------------------------------
# 5. Tabela de vértices (zonas) com atributos e coordenadas de centróide
# ------------------------------------------------------------------
print("Construindo tabela de vértices (zonas)...")

origem_coords = df.dropna(subset=["zona_o"])[["zona_o", "muni_o", "co_o_x", "co_o_y"]].rename(
    columns={"zona_o": "zona", "muni_o": "municipio_cod", "co_o_x": "x", "co_o_y": "y"}
)
destino_coords = df.dropna(subset=["zona_d"])[["zona_d", "muni_d", "co_d_x", "co_d_y"]].rename(
    columns={"zona_d": "zona", "muni_d": "municipio_cod", "co_d_x": "x", "co_d_y": "y"}
)
todas_coords = pd.concat([origem_coords, destino_coords], ignore_index=True)
todas_coords["zona"] = todas_coords["zona"].astype(int)

vertices = todas_coords.groupby("zona").agg(
    municipio_cod=("municipio_cod", moda_classe),
    x_centroide=("x", "mean"),
    y_centroide=("y", "mean"),
).reset_index()
vertices["municipio"] = vertices["municipio_cod"].map(labels_muni)

# só mantém zonas que sobraram no grafo (aparecem em pelo menos uma aresta)
zonas_no_grafo = set(agrupado["zona_o"]) | set(agrupado["zona_d"])
vertices = vertices[vertices["zona"].isin(zonas_no_grafo)].sort_values("zona")

# ------------------------------------------------------------------
# 6. Exporta CSVs de arestas (um por métrica, formato origem/destino/peso)
# ------------------------------------------------------------------
print("Exportando CSVs...")

vertices.to_csv(PASTA_SAIDA / "vertices.csv", index=False, encoding="utf-8-sig")

agrupado.rename(columns={"zona_o": "origem", "zona_d": "destino"})[
    ["origem", "destino", "viagens_estimadas", "n_amostras"]
].to_csv(PASTA_SAIDA / "arestas_viagens.csv", index=False, encoding="utf-8-sig")

agrupado.rename(columns={"zona_o": "origem", "zona_d": "destino"})[
    ["origem", "destino", "distancia_media_m", "n_amostras"]
].to_csv(PASTA_SAIDA / "arestas_distancia.csv", index=False, encoding="utf-8-sig")

agrupado.rename(columns={"zona_o": "origem", "zona_d": "destino"})[
    ["origem", "destino", "tempo_medio_min", "n_amostras"]
].to_csv(PASTA_SAIDA / "arestas_tempo.csv", index=False, encoding="utf-8-sig")

agrupado.rename(columns={"zona_o": "origem", "zona_d": "destino"})[
    ["origem", "destino", "classe_media", "classe_moda", "n_amostras"]
].to_csv(PASTA_SAIDA / "arestas_classe_social.csv", index=False, encoding="utf-8-sig")

# ------------------------------------------------------------------
# 7. Monta um grafo consolidado (NetworkX) com todas as métricas juntas
#    e exporta em GraphML (abre direto no Gephi)
# ------------------------------------------------------------------
print("Montando grafo consolidado (NetworkX)...")

G = nx.DiGraph()

for _, row in vertices.iterrows():
    G.add_node(
        int(row["zona"]),
        municipio=str(row["municipio"]) if pd.notna(row["municipio"]) else "desconhecido",
        x=float(row["x_centroide"]) if pd.notna(row["x_centroide"]) else 0.0,
        y=float(row["y_centroide"]) if pd.notna(row["y_centroide"]) else 0.0,
    )

for _, row in agrupado.iterrows():
    G.add_edge(
        int(row["zona_o"]),
        int(row["zona_d"]),
        viagens_estimadas=float(row["viagens_estimadas"]),
        distancia_media_m=float(row["distancia_media_m"]),
        tempo_medio_min=float(row["tempo_medio_min"]),
        classe_media=float(row["classe_media"]),
        classe_moda=str(row["classe_moda"]),
        n_amostras=int(row["n_amostras"]),
    )

nx.write_graphml(G, PASTA_SAIDA / "grafo_viagens.graphml")

# ------------------------------------------------------------------
# 8. Resumo final
# ------------------------------------------------------------------
print("\n===== RESUMO =====")
print(f"Vértices (zonas):     {G.number_of_nodes()}")
print(f"Arestas (pares O-D):  {G.number_of_edges()}")
print(f"Amostra mínima usada: {MIN_AMOSTRAS} viagens por par")
print(f"Arquivos gerados em:  {PASTA_SAIDA.resolve()}")
