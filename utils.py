import pandas as pd
import xlsxwriter
import base64
from io import BytesIO
import asyncio
import aiohttp
import json
import streamlit as st

# Função para transformar df em excel
def to_excel(df):
	output = BytesIO()
	writer = pd.ExcelWriter(output, engine='xlsxwriter')
	df.to_excel(writer, sheet_name='Planilha1',index=False)
	writer.close()
	processed_data = output.getvalue()
	return processed_data
	
# Função para gerar link de download
def get_table_download_link(df):
	val = to_excel(df)
	b64 = base64.b64encode(val)
	return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="extract.xlsx">Download</a>'

# Função que recebe o dataframe de reviews e adiciona a string 'Comentário: ', retornando uma lista dos reviews
def make_reviews(df_reviews):
    list_reviews = []
    for i in list(df_reviews['Review']):
        review = "Comentário: " + i
        list_reviews.append(review)
        
    return list_reviews

# Função para criar lotes de reviews
def coletar_lotes(lista, tamanho_lote):
    lotes = [lista[i:i + tamanho_lote] for i in range(0, len(lista), tamanho_lote)]
    return lotes

# Função que cria contexto para o modelo com as subcategorizações e detalhamentos
def create_system(df_classes):
    
    list_sub = list(df_classes['Subcategoria'].dropna())
    list_detail = list(df_classes['Detalhamento'].dropna())

    string_sub = ', '.join(list_sub)
    string_detail = ', '.join(list_detail)
    
    system = f"""Haja como um classificador de textos. Irei fornecer alguns textos de comentários de uma loja de aplicativos e 
    seu objetivo será classificar cada comentário em 4 grupos de classes pré-estabelecidas que eu também vou fornecer. 
    A classificação feita deve ser exclusivamente com o que está dentro do grupo. A classificação deve ser feita com a classe mais próxima em seu respectivo grupo
    Grupos:
    \nSentimento: Positivo, Negativo, Neutro, Misto
    \nCategoria: Elogio, Reclamação, Sugestão, Dúvida, Indefinido
    \nSubcategoria: {string_sub}
    \nDetalhamento: {string_detail}
    \nTodos os itens devem obrigatoriamente conter um Sentimento, Categoria, Subcategoria e Detalhamento."""
    
    return system

async def get_data(session, body_mensagem):
    
    API_KEY = st.secrets["TOKEN_API"]

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    url = "/v1/chat/completions"
    
    response = await session.post(url, headers=headers, data=body_mensagem)
    body = await response.json()
    response.close()
    return body

# chatGPT - criação de respostas
async def get_chatgpt_responses(system, lotes_reviews):
    
    url_base = "https://api.openai.com"
    id_modelo = "gpt-3.5-turbo"
    
    session = aiohttp.ClientSession(url_base)
    tasks = []
    for review in lotes_reviews:
        
        review_string = '\n'.join(review)
        
        body_mensagem = {

            "model": id_modelo,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f'''Sua resposta deve ser apenas as classificações geradas dentro de um array, nada mais.
                \nComentário: É bom, mas está com problemas
                \nComentário: excelente'''},
                {"role": "assistant", "content": "['Misto', 'Reclamação', 'Genérico', 'Comentário  genérico']\n['Positivo', 'Elogio', 'Genérico', 'Comentário  genérico']"},
                {"role": "user", "content": '''Sua resposta deve ser apenas as classificações geradas dentro de um array,
                nada mais. ''' + review_string}
            ],
            "max_tokens":500
        }

        body_mensagem = json.dumps(body_mensagem)
        tasks.append(get_data(session,body_mensagem))

    data = await asyncio.gather(*tasks)

    await session.close()

    return data

# Normalização de resultados recebidos pela API
def normalize_results(results):
    df_results = pd.DataFrame(results)
    df_replies = pd.json_normalize(pd.DataFrame(df_results.explode('choices')['choices'])['choices'])

    return df_replies

# Tratamento de lotes de classificação
def clean_results(df_results):
    
    df_results['message.content'] = df_results['message.content'].str.replace("\n", ',')
    df_results['message.content'] = df_results['message.content'].apply(lambda x: eval('[' + x + ']'))
    df_results = df_results.explode('message.content').reset_index(drop=True)
    
    return df_results

# Acrescentar classificações no df de reviews, renomear colunas, adicionar valor Genérico caso não venha classificação da API
def format_results(df_reviews, df_results):
    
    df_reviews['results'] = df_results['message.content']
    df_reviews = pd.concat([df_reviews.drop('results', axis=1), df_reviews['results'].apply(pd.Series)], axis=1)
    df_reviews = df_reviews.rename(columns={0: 'Sentiment_pred', 1: 'Category_pred', 2: 'Subcategory_pred', 3: 'Detailing_pred'})

    df_reviews['Subcategory_pred'] = df_reviews['Subcategory_pred'].fillna('Genérico')
    df_reviews['Detailing_pred'] = df_reviews['Detailing_pred'].fillna('Genérico')
    df_reviews['Sentiment_pred'] = df_reviews['Sentiment_pred'].fillna('Genérico')
    df_reviews['Category_pred'] = df_reviews['Category_pred'].fillna('Genérico')
    
    df_reviews = df_reviews[['Review', 'Sentiment_pred', 'Category_pred', 'Subcategory_pred', 'Detailing_pred']]
    
    return df_reviews













