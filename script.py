import streamlit as st
import pandas as pd
import plotly.express as px
from scipy.stats import mode
import statsmodels.api as sm
import numpy as np

st.set_page_config(layout="wide")

# Função para carregar os dados com cache
@st.cache_data
def load_data():
    df = pd.read_csv('events.csv', nrows="10000")
    df1 = pd.read_csv('ginf.csv' nrows="10000")
    return df, df1

# Carregar os dados
df, df1 = load_data()

# Mesclar as bases de dados usando a coluna id_odsp
merged_df = pd.merge(df, df1, on='id_odsp')

# Título do dashboard
st.title('Dashboard de Eventos de Futebol')

# Função para converter os índices das partes do corpo em texto
def bodypart_converter(x):
    if x == 1:
        return 'pé direito'
    elif x == 2:
        return 'pé esquerdo'
    elif x == 3:
        return 'cabeça'
    else:
        return 'não identificado'

# Seção 1: Média de Gols por Jogo nas Diferentes Ligas
st.header('Média de Gols por Jogo nas Diferentes Ligas')

# Adicionar coluna bodypart com valores convertidos
merged_df['bodypart'] = merged_df['bodypart'].apply(bodypart_converter)

# Calcular os gols por jogo
gols_df = merged_df[merged_df['is_goal'] == 1].groupby(['league', 'id_odsp', 'bodypart']).size().reset_index(name='gols_por_jogo')

# Calcular a média de gols
media_gols = gols_df.groupby(['league', 'bodypart'])['gols_por_jogo'].mean().round(2).reset_index()

# Renomear as colunas
media_gols.columns = ['Liga', 'Parte do Corpo', 'Média de Gols']

# Mostrar a tabela de estatísticas de gols
st.write('### Estatísticas de Gols por Jogo nas Diferentes Ligas')
st.dataframe(media_gols, height=600)

# Adicionar legenda
st.write('Legenda: A tabela acima mostra a média de gols por jogo para cada liga e parte do corpo. A parte do corpo mais provável para fazer gols é "pé direito".')

# Seção de Média de Gols por Liga (removendo filtro por temporada)
st.header('Média de Gols por Jogo por Liga')

selected_liga = st.selectbox('Selecione a Liga', ['Todas'] + list(media_gols['Liga'].unique()))

# Filtrar dados
if selected_liga != 'Todas':
    filtered_df = merged_df[merged_df['league'] == selected_liga]
else:
    filtered_df = merged_df

# Calcular a média de gols por liga
media_gols_liga = filtered_df[filtered_df['is_goal'] == 1].groupby('league')['is_goal'].mean().round(2).reset_index()
media_gols_liga.columns = ['Liga', 'Média de Gols']

# Gráfico de barras das médias de gols por liga
fig_gols_liga = px.bar(media_gols_liga, x='Liga', y='Média de Gols', title='Média de Gols por Jogo por Liga',
                       labels={'Liga': 'Liga', 'Média de Gols': 'Média de Gols'})
st.plotly_chart(fig_gols_liga)

# Adicionar legenda
liga_max_gols = media_gols_liga.loc[media_gols_liga['Média de Gols'].idxmax()]['Liga']
st.write(f'Legenda: A liga com a maior média de gols é {liga_max_gols}.')

# Seção 2: Média de chutes Dentro e Fora da Área para Cada Time
st.header('Média de chutes Dentro e Fora da Área para Cada Time')

# Classificar localização dos chutes
area_loc = [3, 9, 10, 12, 13, 14]
fora_area_loc = [15, 16, 17, 18]

# Filtrar os chutes dentro e fora da área
df['dentro_area'] = df['location'].isin(area_loc)
df['fora_area'] = df['location'].isin(fora_area_loc)

# Mesclar df com df1 para ter acesso à coluna 'league'
df = pd.merge(df, df1[['id_odsp', 'league']], on='id_odsp', how='left')

# Calcular a média de chutes dentro e fora da área por time e liga
media_chutes = df.groupby(['league', 'event_team']).agg(
    media_dentro_area=pd.NamedAgg(column='dentro_area', aggfunc='mean'),
    media_fora_area=pd.NamedAgg(column='fora_area', aggfunc='mean')
).reset_index()

# Adicionar coluna de eficiência
media_chutes['eficiencia'] = media_chutes['media_dentro_area'] / (media_chutes['media_dentro_area'] + media_chutes['media_fora_area'])
media_chutes = media_chutes.round(2)

# Ajustar tamanho das tabelas para caber na tela
st.write('### Eficiência de Chutes Dentro e Fora da Área por Time')
for liga in media_chutes['league'].unique():
    st.write(f'#### {liga}')
    liga_df = media_chutes[media_chutes['league'] == liga].sort_values(by='eficiencia', ascending=False)
    st.dataframe(liga_df[['event_team', 'media_dentro_area', 'media_fora_area', 'eficiencia']], height=200)

# Adicionar legenda
st.write('Legenda: A eficiência representa a proporção de chutes dentro da área em relação ao total de chutes (dentro + fora da área).')

# Seção 3: Média de Faltas e Cartões por Jogo em Cada Liga
st.header('Média de Faltas e Cartões por Jogo em Cada Liga')

# Filtrar eventos de falta
faltas_df = merged_df[merged_df['event_type'] == 3]

# Calcular a média de faltas por jogo e liga
media_faltas = faltas_df.groupby(['league', 'id_odsp']).size().groupby('league').mean().reset_index()
media_faltas.columns = ['Liga', 'Média de Faltas por Jogo']

# Filtrar eventos de cartões amarelos e vermelhos
cartoes_df = merged_df[merged_df['event_type'].isin([4, 5, 6])]
cartoes_df['tipo_cartao'] = cartoes_df['event_type'].map({4: 'Amarelo', 5: 'Segundo Amarelo', 6: 'Vermelho'})

# Calcular a média de cartões por liga
media_cartoes = cartoes_df.groupby(['league', 'tipo_cartao']).size().unstack(fill_value=0).reset_index()

# Definir os nomes das colunas
colunas = ['Liga'] + media_cartoes.columns[1:].tolist()
media_cartoes.columns = colunas
media_cartoes = media_cartoes.round(2)

# Unir os resultados
faltas_cartoes_stats = pd.merge(media_faltas, media_cartoes, on='Liga')

# Mostrar a tabela de média de faltas e cartões
st.write('### Média de Faltas e Cartões por Jogo em Cada Liga')
st.dataframe(faltas_cartoes_stats, height=400)

# Adicionar legenda
# Verificar se as colunas existem antes de acessá-las
cartao_cols = ['Amarelo', 'Segundo Amarelo', 'Vermelho']
cartao_cols_presentes = [col for col in cartao_cols if col in faltas_cartoes_stats.columns]
faltas_cartoes_stats[cartao_cols_presentes] = faltas_cartoes_stats[cartao_cols_presentes].fillna(0)

liga_max_cartoes = faltas_cartoes_stats.loc[
    (faltas_cartoes_stats[cartao_cols_presentes].sum(axis=1)) > 2.5, 'Liga'
].tolist()
st.write(f'Legenda: As ligas mais propensas a terem mais de 2.5 cartões por jogo são: {", ".join(liga_max_cartoes)}.')

# Gráfico de barras da média de faltas e cartões
fig_faltas_cartoes = px.bar(faltas_cartoes_stats, x='Liga', y=faltas_cartoes_stats.columns[1:], 
                            title='Média de Faltas e Cartões por Jogo em Cada Liga',
                            labels={'value': 'Média', 'Liga': 'Liga'},
                            barmode='group')
st.plotly_chart(fig_faltas_cartoes)

# Seção 4: Correlação entre o Número de Chutes e o Número de Gols Marcados
st.header('Correlação entre o Número de Chutes e o Número de Gols Marcados')

# Calcular o número de chutes e gols por jogo
chutes_gols_df = df.groupby('id_odsp').agg(
    total_chutes=pd.NamedAgg(column='shot_outcome', aggfunc=lambda x: sum(x.isin([1, 2, 3]))),
    total_gols=pd.NamedAgg(column='is_goal', aggfunc='sum')
).reset_index()

# Calcular a correlação
correlacao = chutes_gols_df['total_chutes'].corr(chutes_gols_df['total_gols'])
st.write(f'A correlação entre o número de chutes e o número de gols marcados é {correlacao:.2f}')
st.write('A correlação de 0.27 indica uma relação positiva moderada entre o número de chutes e o número de gols.')

# Gráfico de dispersão da correlação
fig_correlacao = px.scatter(chutes_gols_df, x='total_chutes', y='total_gols', trendline='ols',
                            title='Correlação entre o Número de Chutes e o Número de Gols Marcados',
                            labels={'total_chutes': 'Total de Chutes', 'total_gols': 'Total de Gols'})
st.plotly_chart(fig_correlacao)

# Seção 5: Probabilidade de Vitória entre Ligas
st.header('Probabilidade de Vitória entre Ligas')

# Função para calcular a probabilidade de vitória
def calcular_probabilidade_vitoria(media_gols_ofensivo_a, media_gols_defensivo_b):
    return media_gols_ofensivo_a / (media_gols_ofensivo_a + media_gols_defensivo_b)

# Calcular médias ofensivas e defensivas por liga
medias_liga = merged_df.groupby('league').agg(
    media_gols_ofensivo=pd.NamedAgg(column='is_goal', aggfunc='mean'),
    media_gols_defensivo=pd.NamedAgg(column='is_goal', aggfunc=lambda x: 1 - x.mean())
).reset_index()

# Calcular probabilidades de vitória
probabilidades_vitoria = []
for i, liga_a in medias_liga.iterrows():
    for j, liga_b in medias_liga.iterrows():
        if i != j:
            prob_a = calcular_probabilidade_vitoria(liga_a['media_gols_ofensivo'], liga_b['media_gols_defensivo'])
            prob_b = calcular_probabilidade_vitoria(liga_b['media_gols_ofensivo'], liga_a['media_gols_defensivo'])
            probabilidades_vitoria.append({
                'Liga A': liga_a['league'],
                'Liga B': liga_b['league'],
                'Probabilidade de Vitória A (%)': round(prob_a * 100, 2),
                'Probabilidade de Vitória B (%)': round(prob_b * 100, 2)
            })

# Converter para DataFrame e mostrar tabela
probabilidades_vitoria_df = pd.DataFrame(probabilidades_vitoria)
st.write('### Probabilidade de Vitória entre Ligas')
st.dataframe(probabilidades_vitoria_df, height=400)

# Adicionar legenda
liga_max_vantagem = probabilidades_vitoria_df.groupby('Liga A')['Probabilidade de Vitória A (%)'].mean().idxmax()
st.write(f'Legenda: A liga com mais vantagem entre as outras é {liga_max_vantagem}.')
