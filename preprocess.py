import os,sys
import argparse
import numpy as np
import pandas as pd
from tqdm import tqdm
import geopandas as gpd
from shapely.geometry import Point

sys.path.append('..')
from config import *
from utils import grupo_dias_dict


# - Parser de argumentos
parser = argparse.ArgumentParser()
parser.add_argument('--GrupoTempo','-g',help='Agrupamento de tempo desejado',default=0)
parser.add_argument('--DiscrEspacial','-e',help='Tipo de discretização espacial a ser aplicada',default='divisas')
parser.add_argument('--DiscrTemporal','-t',help='Tipo de discretização temporal a ser aplicada',default='meiahora')
parser.add_argument('--NX','-x',help='Número de divisões no eixo x para discretização geográfica em retângulos',default=10)
parser.add_argument('--NY','-y',help='Número de divisões no eixo y para discretização geográfica em retângulos',default=10)
args = parser.parse_args()


# - Funções auxiliares
def agrupar_dias(df,group=0):
    '''
    Função que agrupa dias em categorias de grupo

    Parâmetros
    ----------
    df : {pandas.DataFrame}
        Dados utilizados para agrupar. Deve possuir a coluna 'data' com formato de datetime
    group : {int}
        Tipo de agrupamento a ser feito.
            0 => semana vs fim de semana
            1 => semana vs sabado vs domingo
            2 => cada um dos 7 dias
    '''
    wd = df['data'].dt.weekday
    return wd.map(grupo_dias_dict[group])

def temp_discretizar(df,w='meiahora'):
    '''
    Discretiza os dados temporais no dataframe
    
    Parâmetros
    ----------
    df : {pandas.DataFrame}
        dataframe com dados caracterizados por latitude e longitude
    w : {str ou int}
        tipo de janela de tempo (a partir da primeira data às zero horas) usada na discretização:
            meiahora => janelas de 30 minutos
            hora      => janelas de 60 minutos
            dia       => janelas de 24 horas
    '''
    # o que importa é a hora do dia (em segundos)
    dt_seconds = (df['data_idx'].dt.hour*3600) + (df['data_idx'].dt.minute*60) + (df['data_idx'].dt.second*1)
    # variação de tempo em janelas de meia hora
    if w == 'meiahora':
        st = (dt_seconds / (60*30)).astype(int)
    elif w == 'hora':
        st = (dt_seconds / (60*60)).astype(int)
    elif w == 'dia':
        st = (dt_seconds / (60*60*24)).astype(int)
    elif type(w) is int:
        st = (w*dt_seconds / (60*60*24)).astype(int)
    else:
        print('Tipo de janela inválida:',w)
    df['t'] = st - st.min() + 1
    
    return df

def geo_discretizar(df,tipo_discretizacao,nx=None,ny=None):
    '''
    Discretiza os dados geograficos de latitude e longitude no dataframe
    
    Parâmetros
    ----------
    df : {pandas.DataFrame}
        dataframe com dados caracterizados por latitude e longitude
    tipo_discretizacao : {str}
        tipo de discretização a ser aplicada
            divisas => leitura de arquivo de divisas de bairros do rio de janeiro
            retangulos => divisão em retangulos
    nx : {int}
        número de divisões no espaço de latitudes
    ny : {int}
        número de divisões no espaço de longitudes
    '''
    
    if tipo_discretizacao == 'retangulos':
        # latitude
        lat_min = df['latitude'].min()
        lat_max = df['latitude'].max()
        lat_delta = (lat_max - lat_min) / nx
        
        df['discr_x'] = ((df['latitude'] - lat_min) / lat_delta).astype(int)
        
        # longitude
        lon_min = df['longitude'].min()
        lon_max = df['longitude'].max()
        lon_delta = (lon_max - lon_min) / ny
        
        df['discr_y'] = ((df['longitude'] - lon_min) / lon_delta).astype(int)
        
        # numerar discretizações
        enum_df = df.sort_values(['discr_x','discr_y'])[['discr_x','discr_y']]\
                                    .drop_duplicates().reset_index(drop=True).reset_index()
        enum_df.columns = ['geo_discr','discr_x','discr_y']
        enum_df['geo_discr'] = 'd-'+(enum_df['geo_discr']+1).astype(str)
        
        # merge para pegar enumeração
        if 'geo_discr' in df.columns:
            df.drop('geo_discr',axis=1,inplace=True)
            
        df = pd.merge(
            df,
            enum_df,
            on=['discr_x','discr_y'],
            how='left'
        )
    elif tipo_discretizacao == 'divisas':
        # Leitura de dados de divisas
        bairros = gpd.read_file(os.path.join(ENTR_DATA_PATH,'Bairros_rio_de_janeiro.shp')).reset_index()
        # possíveis CRS iniciais: 22522,29193,31983,32723
        bairros = bairros.set_crs(epsg=29183)
        bairros = bairros.to_crs(epsg=4326)

        # Dados de eventos - tratamento de coordenadas
        df[['lat','lon']] = df['Coordenadas']\
            .str.replace("POINT \(","",regex=True)\
            .str.replace(")","",regex=True)\
            .str.strip()\
            .str.split(' ',expand=True).astype(float)
        df['geometry'] = [Point((lat,lon)) for (lat,lon) in tqdm(df[['lat','lon']].values,desc='Formatando coordenadas geográficas')]
        df = gpd.GeoDataFrame(df).set_crs(epsg=4326)

        df = gpd.sjoin(df,bairros,how='left',op='within')[list(df.columns)+['CODBAIRRO','NOME']]
        df.rename({'CODBAIRRO':'i','NOME':'nome_bairro'},axis=1,inplace=True)
        df['i'] = df['i'].fillna(0).astype(int)
    
    return df

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
    df['g'] = agrupar_dias(df,group=group)
    df.rename({'TipoViatura':'p'},axis=1,inplace=True)
    return df

def main():
    print('Lendo dados de entrada e fazendo tratamentos iniciais...',end='')
    df = leitura_eventos(group=int(args.GrupoTempo))
    print('ok')
    
    print('Executando discretização espacial...',end='')
    df = geo_discretizar(df,args.DiscrEspacial,nx=args.NX,ny=args.NY)
    print('ok')

    print('Executando discretização temporal...',end='')
    df = temp_discretizar(df,w=args.DiscrTemporal)
    print('ok')

    print('Escrevendo dados tratados...',end='')
    df.to_pickle(os.path.join(TRTD_DATA_PATH,'eventos.pkl'))
    print('ok')

if __name__ == '__main__':
    main()
    