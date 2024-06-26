import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from logging import info, error, basicConfig, INFO


url = "http://127.0.0.1:5000/NewsApi/get_everything"
basicConfig(level=INFO, format=f'[%(asctime)s] %(message)s',datefmt='%d/%m/%Y %H:%M:%S')

def landing_step(query:str,languague:str,inicio:str,fim:str=None):
    """
    Função que extrai e salva em arquivos JSON informações de um texto usando uma API de extração de texto.

    Argumentos:
        query (str): O texto a ser extraído.
        language (str): O idioma do texto.
        inicio (str): Data inicial para a busca (formato YYYY-MM-DDTHH:MM:SS).
        fim (str, opcional): Data final para a busca (formato YYYY-MM-DDTHH:MM:SS).

    Exceções:
        Exception: Erro inesperado durante a execução da função.
    """
    try:
        info("## LANDING STEP ##")
        info("Extracting...")
        response = _extract(query=query,languague=languague,_from=inicio,_to=fim)

        info("Verificando se é necessárioa mais de uma página")
        total_results = response.get('totalResults')
        #num_of_pages = (total_results // 100) + 1
        num_of_pages = int(total_results/100) if total_results % 100 == 0 else int(total_results/100) + 1
   

        if num_of_pages == 1:
        
            info("Mais de uma página não é necessaŕio! Só um json será salvo!")
            path = f'data/raw/{inicio.split("T")[0]}.json'
            save_json_response(inicio, fim, response,path=path)
        
        elif num_of_pages > 1:
            
            info(f"Temos {num_of_pages} páginas de artigos! Serão salvos jsons individualmente!")
            
            info("Salvando a página 1!")
            path = f'data/raw/{inicio.split("T")[0]} (Page 1).json'
            save_json_response(inicio, fim, response,path=path)
            info("Página 1 salva com sucesso!!")

            for page in range(2,num_of_pages+1):
                response = _extract(query=query,languague=languague,_from=inicio,_to=fim,page=page)
                
                info(f"Salvando a página {page}!!")
                path = f'data/raw/{inicio.split("T")[0]} (Page {page}).json'
                save_json_response(inicio, fim, response,path=path)
                info(f"Página {page} salva com sucesso!!")

    except Exception as e:
        error(f"Erro ao executar a execução first: {e}")

def bronze_step():
    '''
    A função `bronze_step` é responsável por extrair dados brutos, transformá-los e carregá-los em um arquivo parquet.

    Etapas:
    1. Extração: Extrai todos os arquivos JSON do diretório "data/raw" e carrega cada arquivo em um DataFrame do pandas.
    2. Transformação: Se um arquivo parquet já existir em "data/processed/bronze.parquet", ele é carregado e anexado à lista de DataFrames. Em seguida, todos os DataFrames são concatenados em um único DataFrame. Uma coluna 'load_date' é adicionada, que registra a data e hora atuais.
    3. Carga: O DataFrame resultante é salvo (ou sobrescrito se já existir) em "data/processed/bronze.parquet".

    Retorna:
    None. O resultado é salvo em um arquivo parquet.
    '''

    info("## BRONZE STEP ##")
    ## Extract
    data_raw_path = "data/raw"
    info("Listando os jsons que estão no diretório data/raw")
    list_of_json_paths = [os.path.join(data_raw_path,json_file) for json_file in os.listdir(data_raw_path)]
    info("Verificando se o diretório data/raw está vazio")
    if len(list_of_json_paths) != 0:
        
        info("Criando uma lsita de objetos json")
        list_of_json_obj = [open(path) for path in list_of_json_paths]
        
        info("Transformando-os em dicionários Python")
        list_of_dictionary = [json.load(json_obj) for json_obj in list_of_json_obj]
        
        info("Separando somente a key articles")
        list_of_articles = [dictionary.get('articles') for dictionary in list_of_dictionary]
        
        info("Transformando em dataframes")
        list_of_dataframes = [pd.DataFrame(articles) for articles in list_of_articles]

        # Fechando os objetos de arquivo e armazenando os resultados
        close_obj = [json_obj.close() for json_obj in list_of_json_obj] 

        # Transform
        info("Concatenando os dataframes")
        df_concatened = pd.concat(list_of_dataframes)
        
        info("Inserindo a colunad 'load_date'")
        df_concatened['load_date'] = datetime.now().date()
        
        info("Removendo valores iguais para o bronze ter apenas noticias diferentes")
        df_concatened = df_concatened.drop_duplicates(subset=['title', 'publishedAt'])

        info("Criando o arquivo Bronze Diário")
        # Load
        df_concatened.to_parquet(f"data/bronze/{datetime.now().date()}.parquet")

    # Deleta cada arquivo na lista e deleta
    for file_path in list_of_json_paths:
        os.remove(file_path)       


def _extract(query:str,languague:str,_from:str,_to:str,page:int=None,pageSize:int=100):
    """
    Função que extrai informações de um texto usando uma API de extração de texto.

    Argumentos:
        query (str): O texto a ser extraído.
        language (str): O idioma do texto.
        _from (str): Data inicial para a busca (formato YYYY-MM-DDTHH:MM:SS).
        _to (str): Data final para a busca (formato YYYY-MM-DDTHH:MM:SS).
        page (int, opcional): Número da página a ser retornada (padrão: 1).
        pageSize (int, opcional): Tamanho da página (padrão: 100).

    Retorno:
        dict: Dicionário contendo as informações extraídas do texto.

    Exceções:
        requests.RequestException: Erro ao executar a requisição HTTP.
        Exception: Erro inesperado durante a execução da função.
    """
    info("Construindo os dados a serem enviados na requisição")
    data = {
        "q":query,
        "language":languague,
        "from": _from,
        "to":_to,
        "page":page
        }
    
    try:
        info("Enviando a requisição")
        response = requests.post(url=url,json=data)

        response.raise_for_status()

        info("Requisição feita com sucesso!!")
        return response.json()
    
    except requests.RequestException as erro:
        error(f"Erro ao executar a requisição: {erro}")
        raise erro
    except Exception as e:
        error(f"Erro inesperado ao efetuar a requisção ao webhook: {e}")
        raise e
    
def save_json_response(inicio, fim, response, path:str):
    articles = response.get('articles')
    if len(articles) == 0:
        info(f"Não há novos artigos no periodo de {inicio} a {fim}")
    else:
        info("Saving response in data/raw")
        with open(path,'w') as file:
            file.write(json.dumps(response,indent=1))

def silver_step():
    """
    A função `silver_step` é responsável por realizar o processamento e limpeza dos dados de notícias coletados na etapa anterior (bronze_step).

    Etapas:
    1. Carrega o arquivo parquet mais recente do diretório de bronze.
    2. Remove as notícias com título "[Removed]" (possivelmente deletadas).
    3. Preenche valores ausentes na coluna "author" com "Não Informado".
    4. Trata a coluna "publishedAt":
      - Converte para datetime.
      - Extrai ano, mês e dia.
      - Remove a informação de hora.
    5. Redistribui dados da coluna "source" em "source_id" e "source_name".
    6. Remove a coluna "source".
    7. Verifica se já existe um arquivo silver:
      - Se sim, carrega o arquivo anterior, concatena com o novo DataFrame e remove duplicados.
    8. Salva o DataFrame final como um arquivo parquet no diretório de silver.

    Retorna:
    None. O resultado é salvo em um arquivo parquet.
    """
    bronze_path = "data/bronze"
    data_silver_path = "data/silver/silver.parquet"
    
    # Lista todos os arquivos no diretório de bronze
    list_of_files = os.listdir(bronze_path)
    
    # Filtra apenas os arquivos parquet
    list_of_parquet_files = [file for file in list_of_files if file.endswith('.parquet')]
    
    # Se houver algum arquivo parquet
    if list_of_parquet_files:
        # Encontra o arquivo mais recente baseado na data de modificação
        latest_file = max(list_of_parquet_files, key=lambda x: os.path.getmtime(os.path.join(bronze_path, x)))
        
        # Caminho completo para o arquivo mais recente
        latest_file_path = os.path.join(bronze_path, latest_file)
        
        # Lê o arquivo mais recente como DataFrame
        df_silver = pd.read_parquet(latest_file_path)
    
    #Remove as linhas com noticias que possivelmente foram deletadas pelo author ou API
    df_silver = df_silver.loc[df_silver['title'] != "[Removed]"]
    
    #tratando a coluna 'author'
    authorNoneOrNull = (df_silver['author'].isna() ) 
    df_silver['author'][authorNoneOrNull] = 'Não Informado'
    
    #tratando a coluna de data de publicação. removendo o time
    df_silver['publishedAt'] = pd.to_datetime(df_silver['publishedAt'])
    df_silver['year'] = df_silver['publishedAt'].dt.year
    df_silver['month'] = df_silver['publishedAt'].dt.month
    df_silver['day'] = df_silver['publishedAt'].dt.day
    
    df_silver['publishedAt'] = df_silver['publishedAt'].dt.date

    
    
    #tratando a coluna source. Redistribuindo os dados (poderia usar json_normalize)
    df_silver['source_id'] = df_silver['source']
    df_silver['source_name'] = df_silver['source']
    
    for i in range(0, len(df_silver['author'])):
        df_silver['source_id'].iloc[i] = df_silver['source'].iloc[i]['id']
        df_silver['source_name'].iloc[i] = df_silver['source'].iloc[i]['name']
        
    #remover colunas
    delete_columns = ['source']
    df_silver.drop(columns = delete_columns, inplace=True)
    
    
    
    info("Verificando se já tem um arquivo silver")
    
    if os.path.exists(data_silver_path):        
        df_parquet = pd.read_parquet(data_silver_path)
        df_silver = pd.concat([df_silver, df_parquet])
        df_silver.drop_duplicates(inplace=True)
    # save
    df_silver.to_parquet(data_silver_path)


def gold_step():
    """
    A função `gold_step` é responsável por gerar as métricas finais a partir dos dados processados na etapa silver.

    Etapas:
    1. Carrega o arquivo parquet mais recente do diretório de silver.
    2. Cria as seguintes métricas:
        - **4.1 - Quantidade de notícias por ano, mês e dia de publicação:**
            - 4.1.1 - Quantidade de notícias por ano (agrupado por ano).
            - 4.1.2 - Quantidade de notícias por mês (agrupado por mês).
            - 4.1.3 - Quantidade de notícias por dia (agrupado por dia).
            - 4.1.4 - Quantidade de notícias por ano, mês e dia (agrupado por ano, mês e dia).
        - **4.2 - Quantidade de notícias por fonte e autor:**
            - 4.2.1 - Quantidade de notícias por fonte (agrupado por fonte).
            - 4.2.2 - Quantidade de notícias por autor (agrupado por autor).
            - 4.2.3 - Quantidade de notícias por fonte e autor (agrupado por fonte e autor).
        - **4.3 - Quantidade de aparições de 3 palavras chaves por ano, mês e dia de publicação:**
            - **(Ainda não implementado)**
    3. Salva cada métrica em um arquivo parquet separado no diretório de gold.
    4. Cria as dimensões `author` e `source` (tabelas de referência) e as salva em arquivos parquet separados.

    Retorna:
    None. O resultado é salvo em arquivos parquet.
    """
    data_silver_path = "data/silver/silver.parquet"

    df_silver = pd.read_parquet(data_silver_path)
    df_gold = df_silver.copy()
    
        
    #### 4.1 - Quantidade de notícias por ano, mês e dia de publicação;
    #### 4.1.1 - Quantidade de notícias por ano, mês e dia de publicação;
    df_aggregateByYear = df_gold.groupby(by=['year'], as_index=False, dropna=False)['content'].count()
    df_aggregateByYear = df_aggregateByYear.rename({'content':'number_articles'}, axis='columns')
    
    aggregateByYear_path = "data/gold/aggregateByYear.parquet"    
    df_aggregateByYear.to_parquet(aggregateByYear_path) # save
    
    #### 4.1.2 - Quantidade de notícias por mês de publicação;
    df_aggregateByMonth = df_gold.groupby(by=['month'], as_index=False, dropna=False)['content'].count()
    df_aggregateByMonth = df_aggregateByMonth.rename({'content':'number_articles'}, axis='columns')
    
    aggregateByMonth_path = "data/gold/aggregateByMonth.parquet"    
    df_aggregateByMonth.to_parquet(aggregateByMonth_path) # save
    
    #### 4.1.3 - Quantidade de notícias por mês de publicação;
    df_aggregateByDay = df_gold.groupby(by=['day'], as_index=False, dropna=False)['content'].count()
    df_aggregateByDay = df_aggregateByDay.rename({'content':'number_articles'}, axis='columns')
    
    aggregateByDay_path = "data/gold/aggregateByDay.parquet"    
    df_aggregateByDay.to_parquet(aggregateByDay_path) # save
    
    #### 4.1.4 - Quantidade de notícias por ano, mês e dia de publicação;
    df_aggregateByYearMonthDay = df_gold.groupby(by=['year', 'month','day'], as_index=False, dropna=False)['content'].count()
    df_aggregateByYearMonthDay = df_aggregateByYearMonthDay.rename({'content':'number_articles'}, axis='columns')
    
    aggregateByYearMonthDay_path = "data/gold/aggregateByYearMonthDay_path.parquet"    
    df_aggregateByYearMonthDay.to_parquet(aggregateByMonth_path) # save
    
    
    
    #### 4.2 - Quantidade de notícias por fonte e autor;
    #### 4.2.1 - Quantidade de notícias por fonte;
    df_aggregateBySource = df_gold.groupby(by=['source_name'], as_index=False, dropna=False)['content'].count()
    df_aggregateBySource = df_aggregateBySource.rename({'content':'number_articles'}, axis='columns')
    
    aggregateBySource_path  = "data/gold/aggregateBySource.parquet"    
    df_aggregateBySource.to_parquet(aggregateBySource_path) # save 

    #### 4.2.2 - Quantidade de notícias por autor;
    df_aggregateByAuthor = df_gold.groupby(by=['author'], as_index=False, dropna=False)['content'].count()
    df_aggregateByAuthor = df_aggregateByAuthor.rename({'content':'number_articles'}, axis='columns')
    
    aggregateByAuthor_path = "data/gold/aggregateByAuthor.parquet"    
    df_aggregateByAuthor.to_parquet(aggregateByAuthor_path) # save
    
    #### 4.2.3 - Quantidade de notícias por fonte e autor;
    df_aggregateBySourceAuthor = df_gold.groupby(by=['source_name','author'], as_index=False, dropna=False)['content'].count()
    df_aggregateBySourceAuthor = df_aggregateBySourceAuthor.rename({'content':'number_articles'}, axis='columns')
  
    
    aggregateBySourceAuthor_path = "data/gold/aggregateBySourceAuthor.parquet"    
    df_aggregateBySourceAuthor.to_parquet(aggregateBySourceAuthor_path) # save
    
    #### 4.3 - Quantidade de aparições de 3 palavras chaves por ano, mês e dia de publicação 
    # (as 3 palavras chaves serão as mesmas usadas para fazer os filtros de relevância do item 2 
    # (2. Definir Critérios de Relevância))
    
      
    
    # Criaçãos de Dimensões    
    # Criando dimensao Author
    array_authors = df_gold['author'].unique()
    id_authors = np.array(range(len(array_authors)))
    df_author = pd.DataFrame({'id_authors':id_authors, 'author':array_authors})
    df_gold = pd.merge(df_gold, df_author, on='author', how='left')
    
    data_authors_path = "data/gold/dim_author.parquet"    
    # save
    df_author.to_parquet(data_authors_path)
    '''Não verifico se o arquivo do authors ja existe porque sempre irei reescreve-lo. 
    Como ele tem um identificador que é criando dependendendo do dados do df silver, então o identificador por mudar.
    Pra evitar isso sempre reescrevemos o valor do id. 
    Porém isso pode gerar problemas na camada de visualização no momento da criação de métricas ous filtros que utilizam
    o identificador do author    
    '''
    
    
    # Criando dataframe Source
    array_source_name = df_gold['source_name'].unique()
    id_source = np.array(range(len(array_source_name)))
    df_source = pd.DataFrame({'source_id':id_source, 'source_name':array_source_name})
    df_gold.drop(columns=['source_id'], inplace=True)

    df_gold = pd.merge(df_gold, df_source, on='source_name', how='left')
    
    data_source_path = "data/gold/dim_source.parquet"    
    # save
    df_source.to_parquet(data_source_path)
    '''Não verifico se o arquivo do source ja existe porque sempre irei reescreve-lo. 
    Como ele tem um identificador que é criando dependendendo do dados do df silver, então o identificador por mudar.
    Pra evitar isso sempre reescrevemos o valor do id. 
    Porém isso pode gerar problemas na camada de visualização no momento da criação de métricas ous filtros que utilizam
    o identificador do author        
    '''
    
    df_articles = df_gold.copy()
    drop_columns = ['author','source_name']
    for i in drop_columns:
        if i in df_articles.columns:
            df_articles.drop(columns=[i], inplace=True)
    data_articles_path = "data/gold/articles.parquet"        
    df_articles.to_parquet(data_articles_path)
    

    # Quais as palavras mais recorrentes em todas as matérias


# função criada para saber quais as palavras mais presentes
def contagem_palavras():
    df = pd.read_parquet("data/silver/silver.parquet")

    # Trabalhar com a coluna "description"
    descriptions = df["description"]

    # Separar cada descrição em palavras e expandir para várias colunas
    split_descriptions = descriptions.str.split(expand=True)

    # Converter todas as colunas em uma única coluna (uma longa Series)
    coluna_unica = split_descriptions.stack()

    # Filtrar palavras com mais de 3 letras
    coluna_unica_filtrada = coluna_unica[coluna_unica.str.len() > 4]

    # Contar a frequência das palavras após a filtragem
    contagem_palavras = coluna_unica_filtrada.value_counts().reset_index()
    contagem_palavras.columns = ['Palavra', 'Quantidade']

    return contagem_palavras

