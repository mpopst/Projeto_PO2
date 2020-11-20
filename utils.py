import os,sys
import numpy as np
import pandas as pd
from tqdm import tqdm

# - Variaveis de pre processamento
grupo_dias_dict = {
        0: {
            0:1,1:1,2:1,3:1,4:1,5:2,6:2
        },
        1: {
            0:1,1:1,2:1,3:1,4:1,5:2,6:3
        },
        2: {
            0:1,1:2,2:3,3:4,4:5,5:6,6:7
        }
    }

def calcular_distribuicao(df,t,g,i,p,
                        tipo_discretizacao_temp=0,col1='t',
                        col2='g',col3='i',col4='p',
                        dt_range=None):
    '''
    Calcula a distribuição de número de chamadas para um conjunto de filtros

    Parâmetros
    ----------
    df : {pandas.DataFrame}
        Dataframe com chamadas.
    t : {int}
        Período de tempo do dia (ex: 30 em 30 min).
    g : {int}
        Grupo de dias (ex: dias de semana).
    i : {int}
        Grupo geográfico discretizado.
    p : {int}
        Indicador de prioridade (1 a 3).

    cols: {str's}
        Nome das colunas em df para match dos valores
    '''
    filtro = df.copy()
    # aplicar filtros
    filtro = filtro[
        (filtro[col1]==t) &
        (filtro[col2]==g) &
        (filtro[col3]==i) &
        (filtro[col4]==p)
    ]
    
    # pegar datas com chamadas
    datas = filtro.groupby('data')['hora'].count()
    
    # adicionar datas sem chamadas (com zero)
    if dt_range is None:
        dt_range = pd.date_range(df['data'].min(),df['data'].max(),freq='D')
        
    for dt in dt_range:
        # se a data passa no filtro de grupo
        if grupo_dias_dict[tipo_discretizacao_temp][dt.weekday()] == g:
            if not(dt in datas.index):
                datas[dt] = 0

    datas.sort_index(inplace=True)

    return datas.values