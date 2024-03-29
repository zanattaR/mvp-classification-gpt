#### MVP - CLASSIFICATION GPT
import streamlit as st
import pandas as pd
import numpy as np
import xlsxwriter
import json
import base64
from io import BytesIO
import asyncio
import aiohttp
from utils import *

st.title("ClassificationGPT")
st.write('Esta aplicação tem como objetivo auxiliar nas classificações de reviews com o uso de IA')
st.write()

# Inserindo arquivo de reviews
reviewSheet = st.file_uploader("Insira um arquivo .xlsx com os reviews a serem classificados (Máx: 100 reviews)")
if reviewSheet is not None:
    df_reviews = pd.read_excel(reviewSheet)

    # Lendo reviews e verificando se há mais de 100 registros
    if df_reviews.shape[0] > 100:
        st.warning("Há mais de 100 reviews nesta base, a classificação só será feita com os 100 primeiros.")

    # Filtrando os 100 primeiros reviews
    df_reviews = df_reviews.iloc[:10]

# Inserindo arquivo de classificações
classSheet = st.file_uploader("Insira um arquivo .xlsx com as Subcategorias e Detalhamentos (Máx: 30 classes de cada)")
if classSheet is not None:

    # Lendo reviews e verificando se há mais de 30 registros
    df_classes = pd.read_excel(classSheet)    
    if len(df_classes['Subcategoria'].dropna()) >30:
        st.warning("Há mais de 30 Subcategorias nesta base, serão apenas considerados as 30 primeiras.")

    if len(df_classes['Detalhamento'].dropna()) >30:
        st.warning("Há mais de 30 Detalhamentos nesta base, serão apenas considerados os 30 primeiros.")
    
    # Filtrando as 30 primeriras classificações
    df_classes = df_classes.iloc[:30]

# Visualizar dados
check_reviews = st.checkbox("Visualizar Reviews")
if reviewSheet is not None:
    if check_reviews:
        st.write(df_reviews)

check_subcategory = st.checkbox("Visualizar Subcategorias")
if classSheet is not None:
    if check_subcategory:
        st.write(df_classes[['Subcategoria']].iloc[:30])

check_detail = st.checkbox("Visualizar Detalhamentos")
if classSheet is not None:
    if check_detail:
        st.write(df_classes[['Detalhamento']].iloc[:30])

############# Tratamento e preparação de dados #############
if reviewSheet and classSheet is not None:

    # Criar lista de reviews com a string 'Comentário: ' no início
    list_reviews = make_reviews(df_reviews)

    # Particionar lotes de reviews para serem enviados em conjunto na API
    lotes_reviews = coletar_lotes(list_reviews,5)

    # Criação de contexto para o modelo. A função recebe as classes para compor o texto
    system  = create_system(df_classes)

############# Tratamento e preparação de dados #############
if st.button('Gerar Classificações'):

    # Request na API p/ gerar classificações
    results = asyncio.run(get_chatgpt_responses(system, lotes_reviews))

    # Normalização de resultados recebidos pela API
    df_results = normalize_results(results)

    # Tratamento de lotes de classificação
    df_results = clean_results(df_results)

    # Acrescentar classificações no df de reviews, renomear colunas, adicionar valor Genérico caso não venha classificação da API
    df_reviews = format_results(df_reviews, df_results)

    st.write(df_reviews)
    st.write('Clique em Download para baixar o arquivo')
    st.markdown(get_table_download_link(df_reviews), unsafe_allow_html=True)


