'''
MC536 - Grupo 1 - Adaptação para MongoDB
Este arquivo contém todas as funções para carregar os dados dos datasets para o MongoDB.
'''

import pandas as pd
from pymongo import MongoClient
from typing import Dict, List, Set
import numpy as np
from collections import defaultdict

class MongoDataLoader:
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", db_name: str = "clima_energia"):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.paises_collection = self.db.paises
        self.grupos_collection = self.db.grupos
        
        # Cache para mapear nomes para códigos
        self.paises_cache = {}
        self.grupos_cache = {}
        self.tipos_energia_map = {}
    
    def load_tipos_energia_map(self):
        """Carrega o mapeamento de tipos de energia"""
        try:
            df = pd.read_csv('../Datasets/tipos_energia.csv', usecols=['Tipo', 'Renovavel'])
            for _, row in df.iterrows():
                self.tipos_energia_map[row['Tipo']] = bool(row['Renovavel'])
            print(f"Carregados {len(self.tipos_energia_map)} tipos de energia")
        except FileNotFoundError:
            print("Arquivo tipos_energia.csv não encontrado. Usando valores padrão.")
            # Valores padrão baseados no conhecimento comum
            self.tipos_energia_map = {
                'Solar': True, 'Wind': True, 'Hydro': True, 'Geothermal': True,
                'Bioenergy': True, 'Nuclear': False, 'Coal': False, 'Oil': False,
                'Gas': False, 'Other fossil': False
            }
    
    def create_base_structure(self):
        """Cria a estrutura base de países e grupos a partir do dataset energia.csv"""
        df = pd.read_csv('../Datasets/energia.csv', usecols=['Area', 'Country code', 'Area type'])
        
        # Remove duplicatas
        df_unique = df.drop_duplicates(subset=['Area'])
        
        paises_para_inserir = []
        grupos_para_inserir = []
        
        for _, row in df_unique.iterrows():
            area_nome = row['Area']
            code = row['Country code']
            tipo = row['Area type']
            
            base_doc = {
                "nome": area_nome,
                "codigo": code,
                "anos": []
            }
            
            if tipo == 'Country':
                base_doc["grupos"] = []
                paises_para_inserir.append(base_doc)
                self.paises_cache[area_nome] = code
            elif tipo == 'Region':
                base_doc["paises"] = []
                grupos_para_inserir.append(base_doc)
                self.grupos_cache[area_nome] = code
        
        # Inserir em lote
        if paises_para_inserir:
            self.paises_collection.insert_many(paises_para_inserir)
            print(f"Inseridos {len(paises_para_inserir)} países")
        
        if grupos_para_inserir:
            self.grupos_collection.insert_many(grupos_para_inserir)
            print(f"Inseridos {len(grupos_para_inserir)} grupos")
    
    def load_pais_grupo_relations(self):
        """Carrega as relações entre países e grupos"""
        usecols = ["Area", "EU", "OECD", "G20", "G7", "ASEAN"]
        df = pd.read_csv("Datasets/energia.csv", usecols=usecols, encoding="ISO-8859-1")
        
        grupos_nomes = ["EU", "OECD", "G20", "G7", "ASEAN"]
        relacoes = defaultdict(list)  # codigo_pais -> [codigos_grupos]
        
        for _, row in df.iterrows():
            pais_nome = row["Area"]
            if pais_nome not in self.paises_cache:
                continue
                
            codigo_pais = self.paises_cache[pais_nome]
            
            for grupo_nome in grupos_nomes:
                flag = float(row[grupo_nome]) if pd.notna(row[grupo_nome]) else 0.0
                if flag > 0 and grupo_nome in self.grupos_cache.values():
                    # Encontrar o código do grupo
                    codigo_grupo = grupo_nome  # Os grupos já têm código igual ao nome
                    relacoes[codigo_pais].append(codigo_grupo)
        
        # Atualizar países com seus grupos
        for codigo_pais, codigos_grupos in relacoes.items():
            self.paises_collection.update_one(
                {"codigo": codigo_pais},
                {"$set": {"grupos": list(set(codigos_grupos))}}
            )
        
        # Atualizar grupos com seus países
        grupos_paises = defaultdict(list)
        for codigo_pais, codigos_grupos in relacoes.items():
            for codigo_grupo in codigos_grupos:
                grupos_paises[codigo_grupo].append(codigo_pais)
        
        for codigo_grupo, codigos_paises in grupos_paises.items():
            self.grupos_collection.update_one(
                {"codigo": codigo_grupo},
                {"$set": {"paises": list(set(codigos_paises))}}
            )
        
        print(f"Relações carregadas para {len(relacoes)} países")
    
    def load_temperature_data(self):
        """Carrega os dados de mudança de temperatura"""
        print("Carregando dados de temperatura...")
        
        # Carregar dados
        anos = list(range(1961, 2020))
        cols_anos = [f"Y{ano}" for ano in anos]
        df = pd.read_csv("../Datasets/temperature_change.csv", encoding="ISO-8859-1",
                        usecols=["Area", "Months", "Element"] + cols_anos)
        
        # Transformar para formato longo
        df_long = df.melt(
            id_vars=["Area", "Months", "Element"],
            value_vars=cols_anos,
            var_name="Year",
            value_name="Value"
        )
        
        # Pivotar para ter colunas separadas
        df_pivot = (
            df_long
            .pivot_table(
                index=["Area", "Months", "Year"],
                columns="Element",
                values="Value"
            )
            .reset_index()
            .rename(columns={
                "Temperature change": "mudanca_temp",
                "Standard Deviation": "desvio_padrao"
            })
        )
        
        # Mapeamento de meses
        month_name_to_num = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        
        # Organizar dados por área e ano
        temp_data = defaultdict(lambda: defaultdict(list))  # area -> ano -> [meses]
        
        for _, row in df_pivot.iterrows():
            area_nome = row["Area"]
            mes_nome = row["Months"]
            ano = int(row["Year"][1:])  # Remove 'Y' do início
            
            if mes_nome not in month_name_to_num:
                continue
            
            if pd.isna(row["mudanca_temp"]) or pd.isna(row["desvio_padrao"]):
                continue
            
            mes_data = {
                "mes": month_name_to_num[mes_nome],
                "mudanca_temp": float(row["mudanca_temp"]),
                "desvio_padrao": float(row["desvio_padrao"]),
                "unidade": "°C"
            }
            
            temp_data[area_nome][ano].append(mes_data)
        
        # Atualizar documentos
        updates_count = 0
        for area_nome, anos_data in temp_data.items():
            # Verificar se é país ou grupo
            is_pais = area_nome in self.paises_cache
            collection = self.paises_collection if is_pais else self.grupos_collection
            
            if not is_pais and area_nome not in self.grupos_cache:
                continue
            
            codigo = self.paises_cache.get(area_nome) or self.grupos_cache.get(area_nome)
            if not codigo:
                continue
            
            # Preparar dados dos anos
            anos_para_inserir = []
            for ano, meses_list in anos_data.items():
                if len(meses_list) == 12:  # Só adicionar se tiver todos os 12 meses
                    meses_list.sort(key=lambda x: x["mes"])
                    anos_para_inserir.append({
                        "ano": ano,
                        "meses": meses_list,
                        "tipos_energia": []  # Será preenchido depois
                    })
            
            if anos_para_inserir:
                collection.update_one(
                    {"codigo": codigo},
                    {"$set": {"anos": anos_para_inserir}}
                )
                updates_count += 1
        
        print(f"Dados de temperatura atualizados para {updates_count} áreas")
    
    def load_energy_data(self):
        """Carrega os dados de geração de energia e emissões"""
        print("Carregando dados de energia...")
        
        # Ler dataset
        usecols = ["Area", "Year", "Category", "Variable", "Unit", "Value"]
        df = pd.read_csv("../Datasets/energia.csv", usecols=usecols, encoding="ISO-8859-1")
        
        # Filtrar dados relevantes
        categorias = ["Electricity generation", "Power sector emissions"]
        df = df[df["Category"].isin(categorias)]
        df = df[~df["Unit"].str.contains("%", na=False)]
        df = df[df["Variable"].isin(self.tipos_energia_map.keys())]
        
        # Organizar dados por área, ano e tipo de energia
        energy_data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        # Estrutura: area -> ano -> tipo_energia -> {geracao/emissao: valor}
        
        for _, row in df.iterrows():
            area_nome = row["Area"]
            ano = int(row["Year"])
            variavel = row["Variable"]
            unidade = row["Unit"]
            valor = float(row["Value"])
            categoria = row["Category"]
            
            if categoria == "Electricity generation":
                energy_data[area_nome][ano][variavel]["geracao"] = {
                    "valor": valor,
                    "unidade": unidade
                }
            else:  # Power sector emissions
                energy_data[area_nome][ano][variavel]["emissao"] = {
                    "valor": valor,
                    "unidade": unidade
                }
        
        # Atualizar documentos
        updates_count = 0
        for area_nome, anos_data in energy_data.items():
            # Verificar se é país ou grupo
            is_pais = area_nome in self.paises_cache
            collection = self.paises_collection if is_pais else self.grupos_collection
            
            if not is_pais and area_nome not in self.grupos_cache:
                continue
            
            codigo = self.paises_cache.get(area_nome) or self.grupos_cache.get(area_nome)
            if not codigo:
                continue
            
            # Buscar documento existente
            doc = collection.find_one({"codigo": codigo})
            if not doc:
                continue
            
            # Atualizar anos existentes com dados de energia
            anos_atualizados = []
            for ano_doc in doc.get("anos", []):
                ano = ano_doc["ano"]
                
                if ano in anos_data:
                    tipos_energia = []
                    for tipo, dados in anos_data[ano].items():
                        tipo_energia = {
                            "tipo": tipo,
                            "renovavel": self.tipos_energia_map.get(tipo, False),
                            "valor_geracao": dados.get("geracao", {}).get("valor", 0.0),
                            "unidade_geracao": dados.get("geracao", {}).get("unidade", ""),
                            "valor_emissao": dados.get("emissao", {}).get("valor", 0.0),
                            "unidade_emissao": dados.get("emissao", {}).get("unidade", "")
                        }
                        tipos_energia.append(tipo_energia)
                    
                    ano_doc["tipos_energia"] = tipos_energia
                
                anos_atualizados.append(ano_doc)
            
            # Atualizar documento
            collection.update_one(
                {"codigo": codigo},
                {"$set": {"anos": anos_atualizados}}
            )
            updates_count += 1
        
        print(f"Dados de energia atualizados para {updates_count} áreas")
    
    def load_all_data(self):
        """Carrega todos os dados na ordem correta"""
        print("=== Iniciando carregamento de dados ===")
        
        # Limpar coleções existentes
        self.paises_collection.delete_many({})
        self.grupos_collection.delete_many({})
        print("Coleções limpas")
        
        # 1. Carregar mapeamento de tipos de energia
        self.load_tipos_energia_map()
        
        # 2. Criar estrutura base (países e grupos)
        self.create_base_structure()
        
        # 3. Carregar relações país-grupo
        self.load_pais_grupo_relations()
        
        # 4. Carregar dados de temperatura
        self.load_temperature_data()
        
        # 5. Carregar dados de energia
        self.load_energy_data()
        
        print("=== Carregamento concluído ===")
        
        # Estatísticas finais
        total_paises = self.paises_collection.count_documents({})
        total_grupos = self.grupos_collection.count_documents({})
        print(f"Total de países: {total_paises}")
        print(f"Total de grupos: {total_grupos}")
    
    

# Função principal para executar o carregamento
def main():
    loader = MongoDataLoader()
    loader.load_all_data()

if __name__ == "__main__":
    main()