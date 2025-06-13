'''
MC536 - Grupo 1
Este arquivo contém as funções para popular o banco MongoDB com os dados dos datasets.
'''

import pandas as pd
from pymongo import MongoClient
from bson import ObjectId

# Conectar ao MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["clima_energia"]

def load_tipos_energia():
    """Carrega os tipos de energia em um dicionário para facilitar o acesso"""
    df = pd.read_csv('../Datasets/tipos_energia.csv', usecols=['Tipo', 'Renovavel'])
    tipos_energia = {}
    for linha in df.itertuples():
        tipos_energia[linha[1]] = bool(linha[2])  # Tipo -> Renovável (bool)
    return tipos_energia

def load_mudanca_temperatura():
    """Carrega os dados de mudança de temperatura organizados por área/ano/mês"""
    # Carrega apenas o necessário
    anos = list(range(1961, 2020))
    cols_anos = [f"Y{ano}" for ano in anos]
    df = pd.read_csv("../Datasets/temperature_change.csv", encoding="ISO-8859-1",
                     usecols=["Area", "Months", "Element"] + cols_anos)

    # Melt para long: cada linha vira um único ano
    df_long = df.melt(
        id_vars=["Area", "Months", "Element"],
        value_vars=cols_anos,
        var_name="Year",
        value_name="Value"
    )

    # Pivota para ter colunas separadas para os dois elementos
    df_pivot = (
        df_long
        .pivot_table(
            index=["Area", "Months", "Year"],
            columns="Element",
            values="Value"
        )
        .reset_index()
        .rename(columns={
            "Temperature change": "mud_value",
            "Standard Deviation": "desvio_padrao",
            "Area": "area",
            "Months": "mes",
            "Year": "ano"
        })
    )

    month_name_to_num = {
        "January": 1, "February": 2, "March": 3,
        "April": 4, "May": 5, "June": 6,
        "July": 7, "August": 8, "September": 9,
        "October": 10, "November": 11, "December": 12
    }

    # Organiza os dados em estrutura hierárquica: area -> ano -> mes
    temp_data = {}
    for _, row in df_pivot.iterrows():
        mes_nome = row["mes"]
        if mes_nome not in month_name_to_num:
            continue  # Pula trimestres ou categorias desconhecidas
            
        area_nome = row['area']
        mes = month_name_to_num[mes_nome]
        ano = int(row["ano"][1:])  # Remove o 'Y' do início
        
        if area_nome not in temp_data:
            temp_data[area_nome] = {}
        if ano not in temp_data[area_nome]:
            temp_data[area_nome][ano] = {}
            
        temp_data[area_nome][ano][mes] = {
            'mudanca_temp': float(row['mud_value']) if pd.notna(row['mud_value']) else 0.0,
            'desvio_padrao': float(row['desvio_padrao']) if pd.notna(row['desvio_padrao']) else 0.0,
            'unidade': '°C'  # Assumindo que a unidade é Celsius
        }
    
    return temp_data

def load_geracao_energia():
    """Carrega os dados de geração de energia organizados por área/ano/tipo"""
    usecols = [
        "Area", "Year", "Category", "Variable",
        "Unit", "Value"
    ]
    df = pd.read_csv(
        "../Datasets/energia.csv",
        usecols=usecols,
        encoding="ISO-8859-1"
    )

    # Filtra apenas as linhas de interesse
    categorias = ["Electricity generation", "Power sector emissions"]
    df = df[df["Category"].isin(categorias)]

    # Remove as linhas com porcentagens
    df = df[~df["Unit"].str.contains("%", na=False)]

    # Organiza os dados: area -> ano -> tipo -> {geracao, emissao}
    energia_data = {}
    
    for _, row in df.iterrows():
        area = row["Area"]
        ano = int(row["Year"])
        var = row["Variable"]
        unit = row["Unit"]
        val = float(row["Value"]) if pd.notna(row["Value"]) else 0.0
        categoria = row["Category"]
        
        if area not in energia_data:
            energia_data[area] = {}
        if ano not in energia_data[area]:
            energia_data[area][ano] = {}
        if var not in energia_data[area][ano]:
            energia_data[area][ano][var] = {
                'valor_geracao': 0.0,
                'valor_emissao': 0.0,
                'unidade_geracao': '',
                'unidade_emissao': ''
            }
            
        if categoria == "Electricity generation":
            energia_data[area][ano][var]['valor_geracao'] = val
            energia_data[area][ano][var]['unidade_geracao'] = unit
        else:  # Power sector emissions
            energia_data[area][ano][var]['valor_emissao'] = val
            energia_data[area][ano][var]['unidade_emissao'] = unit
    
    return energia_data

def load_pais_grupo_relations():
    """Carrega as relações entre países e grupos"""
    usecols = ["Area", "Area type", "EU", "OECD", "G20", "G7", "ASEAN"]
    df = pd.read_csv(
        "../Datasets/energia.csv",
        usecols=usecols,
        encoding="ISO-8859-1"
    )
    
    # Separa países de grupos
    paises_df = df[df["Area type"] == "Country"]
    grupos_nomes = ["EU", "OECD", "G20", "G7", "ASEAN"]
    
    # Mapeia país -> grupos
    pais_grupos = {}
    for _, row in paises_df.iterrows():
        pais = row["Area"]
        grupos_do_pais = []
        
        for grupo in grupos_nomes:
            flag = float(row[grupo]) if pd.notna(row[grupo]) else 0.0
            if flag > 0:
                grupos_do_pais.append(grupo)
        
        if grupos_do_pais:
            pais_grupos[pais] = grupos_do_pais
    
    return pais_grupos

def populate_mongodb():
    """Função principal para popular o MongoDB"""
    print("Carregando dados dos datasets...")
    
    # Carrega dados auxiliares
    tipos_energia = load_tipos_energia()
    temp_data = load_mudanca_temperatura()
    energia_data = load_geracao_energia()
    pais_grupos_relations = load_pais_grupo_relations()
    
    # Carrega informações das áreas
    df_areas = pd.read_csv('../Datasets/energia.csv', usecols=['Area', 'Country code', 'Area type'])
    areas = df_areas.drop_duplicates('Area')
    
    # Limpa as coleções existentes
    db.paises.delete_many({})
    db.grupos.delete_many({})
    
    print("Populando coleção de grupos...")
    
    # Primeiro, insere os grupos para obter seus ObjectIds
    grupos_ids = {}
    grupos_df = areas[areas['Area type'] == 'Region']
    
    for _, row in grupos_df.iterrows():
        grupo_nome = row['Area']
        grupo_codigo = row['Country code'] if pd.notna(row['Country code']) else "N/A"
        
        # Monta estrutura de anos para o grupo
        anos_grupo = []
        if grupo_nome in temp_data and grupo_nome in energia_data:
            # Encontra anos comuns entre temperatura e energia
            anos_temp = set(temp_data[grupo_nome].keys())
            anos_energia = set(energia_data[grupo_nome].keys())
            anos_comuns = sorted(anos_temp.intersection(anos_energia))
            
            for ano in anos_comuns:
                # Monta meses
                meses = []
                if ano in temp_data[grupo_nome]:
                    for mes in range(1, 13):
                        if mes in temp_data[grupo_nome][ano]:
                            temp_info = temp_data[grupo_nome][ano][mes]
                            meses.append({
                                "mes": mes,
                                "mudanca_temp": temp_info['mudanca_temp'],
                                "desvio_padrao": temp_info['desvio_padrao'],
                                "unidade": temp_info['unidade']
                            })
                
                # Monta tipos de energia
                tipos_energia_ano = []
                if ano in energia_data[grupo_nome]:
                    for tipo, dados in energia_data[grupo_nome][ano].items():
                        if tipo in tipos_energia:
                            tipos_energia_ano.append({
                                "tipo": tipo,
                                "renovavel": tipos_energia[tipo],
                                "valor_geracao": dados['valor_geracao'],
                                "valor_emissao": dados['valor_emissao'],
                                "unidade_geracao": dados['unidade_geracao'],
                                "unidade_emissao": dados['unidade_emissao']
                            })
                
                if meses and tipos_energia_ano:  # Só adiciona se tiver dados
                    anos_grupo.append({
                        "ano": ano,
                        "meses": meses,
                        "tipos_energia": tipos_energia_ano
                    })
        
        grupo_doc = {
            "nome": grupo_nome,
            "codigo": grupo_codigo,
            "anos": anos_grupo,
            "paises": []  # Será preenchido depois
        }
        
        result = db.grupos.insert_one(grupo_doc)
        grupos_ids[grupo_nome] = result.inserted_id
        print(f"Grupo inserido: {grupo_nome}")
    
    print("Populando coleção de países...")
    
    # Depois, insere os países
    paises_df = areas[areas['Area type'] == 'Country']
    
    for _, row in paises_df.iterrows():
        pais_nome = row['Area']
        pais_codigo = row['Country code'] if pd.notna(row['Country code']) else "N/A"
        
        # Monta estrutura de anos para o país
        anos_pais = []
        if pais_nome in temp_data and pais_nome in energia_data:
            # Encontra anos comuns entre temperatura e energia
            anos_temp = set(temp_data[pais_nome].keys())
            anos_energia = set(energia_data[pais_nome].keys())
            anos_comuns = sorted(anos_temp.intersection(anos_energia))
            
            for ano in anos_comuns:
                # Monta meses
                meses = []
                if ano in temp_data[pais_nome]:
                    for mes in range(1, 13):
                        if mes in temp_data[pais_nome][ano]:
                            temp_info = temp_data[pais_nome][ano][mes]
                            meses.append({
                                "mes": mes,
                                "mudanca_temp": temp_info['mudanca_temp'],
                                "desvio_padrao": temp_info['desvio_padrao'],
                                "unidade": temp_info['unidade']
                            })
                
                # Monta tipos de energia
                tipos_energia_ano = []
                if ano in energia_data[pais_nome]:
                    for tipo, dados in energia_data[pais_nome][ano].items():
                        if tipo in tipos_energia:
                            tipos_energia_ano.append({
                                "tipo": tipo,
                                "renovavel": tipos_energia[tipo],
                                "valor_geracao": dados['valor_geracao'],
                                "valor_emissao": dados['valor_emissao'],
                                "unidade_geracao": dados['unidade_geracao'],
                                "unidade_emissao": dados['unidade_emissao']
                            })
                
                if meses and tipos_energia_ano:  # Só adiciona se tiver dados
                    anos_pais.append({
                        "ano": ano,
                        "meses": meses,
                        "tipos_energia": tipos_energia_ano
                    })
        
        # Encontra grupos do país
        grupos_do_pais = []
        if pais_nome in pais_grupos_relations:
            for grupo_nome in pais_grupos_relations[pais_nome]:
                if grupo_nome in grupos_ids:
                    grupos_do_pais.append(grupos_ids[grupo_nome])
        
        pais_doc = {
            "nome": pais_nome,
            "codigo": pais_codigo,
            "anos": anos_pais,
            "grupos": grupos_do_pais
        }
        
        result = db.paises.insert_one(pais_doc)
        pais_id = result.inserted_id
        
        # Atualiza os grupos com o ID do país
        for grupo_nome in pais_grupos_relations.get(pais_nome, []):
            if grupo_nome in grupos_ids:
                db.grupos.update_one(
                    {"_id": grupos_ids[grupo_nome]},
                    {"$push": {"paises": pais_id}}
                )
        
        print(f"País inserido: {pais_nome}")
    
    print("População do MongoDB concluída!")
    
    # Estatísticas finais
    total_paises = db.paises.count_documents({})
    total_grupos = db.grupos.count_documents({})
    print(f"Total de países inseridos: {total_paises}")
    print(f"Total de grupos inseridos: {total_grupos}")

if __name__ == "__main__":
    populate_mongodb()