import os,sys
import numpy as np
import pandas as pd

sys.path.append('..')
from config import *
from utils import *

def leitura_eventos(group=0):
    '''
    Leitura e tratamento inicial dos dados de eventos

    Parâmetros
    ---------
    group : {int}
        Parâmetro de tipo de agrupamento de dias.
            0 => semana vs fim de semana
            1 => semana vs sabado vs domingo
            2 => cada um dos 7 dias
    '''
    # - Leitura do data frame
    df = pd.read_csv(os.path.join(ENTR_DATA_PATH,'eventos_desagregados.csv'),index_col=0)

    # - Dados geográficos
    # faltantes
    df.drop(df.loc[
        (df['latitude'].isna()) |
        (df['longitude'].isna())
    ].index,axis=0,inplace=True)
    # outliers
    df.drop(df[df['longitude']>0].index,axis=0,inplace=True)

    # - Descartar prioridade zero
    df.drop(df.loc[
        df['TipoViatura']==0
    ].index,axis=0,inplace=True)

    # - Tratar dados temporais
    df['data']      =  pd.to_datetime(df['data'],format='%m/%d/%y')
    df['data_idx']  = pd.to_datetime(df['data_idx'],format='%m/%d/%y %H:%M')
    # agrupar dias
    df['grupo_dia'] = agrupar_dias(df,group=group)

    return df

def main():
    print('Lendo dados de entrada e fazendo tratamentos iniciais...',end='')
    df = leitura_eventos(group=0)
    print('ok')
    
    # print('Executando discretização espacial...',end='')
    # df = geo_discretizar(df,30,30)
    # print('ok')
    print('Executando discretização espacial em bairros...',end='')
    info_bairros = pd.read_excel(os.path.join(ENTR_DATA_PATH,'info_bairros.xlsx'),index_col=0)
    df = definir_bairros(df,info_bairros)
    print('ok')

    print('Executando discretização temporal...',end='')
    df = temp_discretizar(df,w='meia hora')
    print('ok')

    print('Escrevendo dados tratados...',end='')
    df.to_pickle(os.path.join(TRTD_DATA_PATH,'eventos.pkl'))
    print('ok')

if __name__ == '__main__':
    main()
    