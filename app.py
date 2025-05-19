# -*- coding: utf-8 -*-
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc  # Import necessário para o tema

# --- Leitura das bases de dados ---

# Lista dos arquivos de vendas
arquivos_vendas = [
    '/content/Base Vendas - 2020.xlsx',
    '/content/Base Vendas - 2021.xlsx',
    '/content/Base Vendas - 2022.xlsx'
]

# Padronizando colunas das vendas
colunas_vendas = ['Data da Venda', 'Ordem de Compra', 'ID Produto', 'ID Cliente', 'Qtd Vendida', 'ID Loja']

# Carregando e padronizando cada base de vendas
lista_vendas = []
for arquivo in arquivos_vendas:
    df_temp = pd.read_excel(arquivo)
    df_temp.columns = colunas_vendas
    lista_vendas.append(df_temp)

# Concatenar todas as vendas
df_vendas = pd.concat(lista_vendas, ignore_index=True)

# Leitura cadastros
df_clientes = pd.read_excel('/content/Cadastro Clientes.xlsx', skiprows=2)
df_produtos = pd.read_excel('/content/Cadastro Produtos.xlsx')
df_lojas = pd.read_excel('/content/Cadastro Lojas.xlsx')

# --- Tratamento dos dados ---

# Unificar nome completo dos clientes
if 'Primeiro Nome' in df_clientes.columns and 'Sobrenome' in df_clientes.columns:
    df_clientes['Nome Completo'] = df_clientes['Primeiro Nome'].astype(str) + ' ' + df_clientes['Sobrenome'].astype(str)
    df_clientes.drop(columns=['Primeiro Nome', 'Sobrenome'], inplace=True)

# Renomear coluna SKU para ID Produto em produtos, se existir
if 'SKU' in df_produtos.columns:
    df_produtos.rename(columns={'SKU': 'ID Produto'}, inplace=True)

# Garantir que a coluna 'ID Produto' também esteja no df_vendas
if 'SKU' in df_vendas.columns:
    df_vendas.rename(columns={'SKU': 'ID Produto'}, inplace=True)

# Converter 'Data da Venda' para datetime
df_vendas['Data da Venda'] = pd.to_datetime(df_vendas['Data da Venda'], dayfirst=True, errors='coerce')

# Mesclar todas as informações para o dataframe final
df_total = df_vendas.merge(df_clientes, on='ID Cliente', how='left') \
                   .merge(df_produtos, on='ID Produto', how='left') \
                   .merge(df_lojas, on='ID Loja', how='left')

# Criar colunas auxiliares
df_total['Ano'] = df_total['Data da Venda'].dt.year
df_total['Valor da Venda'] = df_total['Qtd Vendida'] * df_total['Preço Unitario']

# --- Preparação dos filtros para o dashboard ---

filtros = {
    "tipo": df_total["Tipo do Produto"].dropna().unique(),
    "marca": df_total["Marca"].dropna().unique(),
    "produto": df_total["Produto"].dropna().unique(),
    "loja": df_total["Nome da Loja"].dropna().unique(),
    "cliente": df_total["Nome Completo"].dropna().unique(),
}

# --- Montagem do dashboard com Dash e Bootstrap ---

app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
server = app.server

app.layout = dbc.Container([
    html.H1("📊 Dashboard de Vendas", className="text-center my-4"),

    dbc.Row([
        dbc.Col(dcc.Dropdown(
            id='filtro_tipo',
            options=[{'label': i, 'value': i} for i in sorted(filtros['tipo'])],
            placeholder="Selecione o Tipo de Produto"
        ), md=4),

        dbc.Col(dcc.Dropdown(
            id='filtro_marca',
            placeholder="Selecione a Marca"
        ), md=4),

        dbc.Col(dcc.Dropdown(
            id='filtro_produto',
            options=[{'label': i, 'value': i} for i in sorted(filtros['produto'])],
            multi=True,
            placeholder="Filtrar por Produto"
        ), md=4),

        dbc.Col(dcc.Dropdown(
            id='filtro_loja',
            options=[{'label': i, 'value': i} for i in sorted(filtros['loja'])],
            multi=True,
            placeholder="Filtrar por Loja"
        ), md=4),

        dbc.Col(dcc.Dropdown(
            id='filtro_cliente',
            options=[{'label': i, 'value': i} for i in sorted(filtros['cliente'])],
            multi=True,
            placeholder="Filtrar por Cliente"
        ), md=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico_ano'), md=6),
        dbc.Col(dcc.Graph(id='grafico_cliente'), md=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico_produto'), md=6),
        dbc.Col(dcc.Graph(id='grafico_loja'), md=6),
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='grafico_pizza_tipo'), md=6),
        dbc.Col(dcc.Graph(id='grafico_area_tempo'), md=6),
    ]),
], fluid=True)

# Atualizar opções da marca conforme o tipo selecionado
@app.callback(
    Output('filtro_marca', 'options'),
    Input('filtro_tipo', 'value')
)
def atualizar_marcas(tipo):
    if tipo:
        marcas = df_total[df_total['Tipo do Produto'] == tipo]['Marca'].dropna().unique()
        return [{'label': m, 'value': m} for m in sorted(marcas)]
    return []

# Atualizar gráficos conforme filtros selecionados
@app.callback(
    [Output('grafico_ano', 'figure'),
     Output('grafico_cliente', 'figure'),
     Output('grafico_produto', 'figure'),
     Output('grafico_loja', 'figure'),
     Output('grafico_pizza_tipo', 'figure'),
     Output('grafico_area_tempo', 'figure')],
    [Input('filtro_tipo', 'value'),
     Input('filtro_marca', 'value'),
     Input('filtro_produto', 'value'),
     Input('filtro_loja', 'value'),
     Input('filtro_cliente', 'value')]
)
def atualizar_graficos(tipo, marca, produtos, lojas, clientes):
    df = df_total.copy()

    if tipo:
        df = df[df['Tipo do Produto'] == tipo]
    if marca:
        df = df[df['Marca'] == marca]
    if produtos:
        df = df[df['Produto'].isin(produtos)]
    if lojas:
        df = df[df['Nome da Loja'].isin(lojas)]
    if clientes:
        df = df[df['Nome Completo'].isin(clientes)]

    # Garantir que a coluna 'Data da Venda' é datetime
    df['Data da Venda'] = pd.to_datetime(df['Data da Venda'], errors='coerce')

    # Gráfico 1 - Vendas por Ano
    fig1 = px.bar(
        df.groupby('Ano')['Valor da Venda'].sum().reset_index(),
        x='Ano', y='Valor da Venda',
        title='Vendas por Ano',
        color_discrete_sequence=['#00BFFF'],
        template='plotly_dark'
    )

    # Gráfico 2 - Top 10 Clientes
    top_clientes = df.groupby('Nome Completo')['Valor da Venda'].sum().nlargest(10).reset_index()
    fig2 = px.bar(
        top_clientes,
        x='Valor da Venda', y='Nome Completo',
        orientation='h',
        title='Top 10 Clientes',
        color_discrete_sequence=['#FF7F50'],
        template='plotly_dark'
    )

    # Gráfico 3 - Top 10 Produtos
    top_produtos = df.groupby('Produto')['Valor da Venda'].sum().nlargest(10).reset_index()
    fig3 = px.line(
        top_produtos,
        x='Produto', y='Valor da Venda',
        title='Top 10 Produtos',
        markers=True,
        color_discrete_sequence=['#32CD32'],
        template='plotly_dark'
    )

    # Gráfico 4 - Vendas por Loja
    vendas_lojas = df.groupby('Nome da Loja')['Valor da Venda'].sum().reset_index()
    fig4 = px.bar(
        vendas_lojas,
        x='Nome da Loja', y='Valor da Venda',
        title='Vendas por Loja',
        color_discrete_sequence=['#FFD700'],
        template='plotly_dark'
    )

    # Gráfico 5 - Distribuição por Tipo de Produto
    fig5 = px.pie(
        df,
        names='Tipo do Produto', values='Valor da Venda',
        title='Distribuição por Tipo de Produto',
        color_discrete_sequence=px.colors.qualitative.Set3,
        template='plotly_dark'
    )

    # Gráfico 6 - Evolução Mensal de Vendas
    df['Mês'] = df['Data da Venda'].dt.to_period('M').astype(str)
    vendas_mes = df.groupby('Mês')['Valor da Venda'].sum().reset_index()
    fig6 = px.area(
        vendas_mes,
        x='Mês', y='Valor da Venda',
        title='Evolução Mensal de Vendas',
        color_discrete_sequence=['#1E90FF'],
        template='plotly_dark'
    )

    return fig1, fig2, fig3, fig4, fig5, fig6


if __name__ == '__main__':
    app.run_server(debug=True)
from dash import Dash, html

app = Dash(__name__)
server = app.server  # Exporta o servidor Flask para Gunicorn

app.layout = html.Div([
    html.H1("Hello Dash")
])

if __name__ == "__main__":
    app.run_server(debug=True)
