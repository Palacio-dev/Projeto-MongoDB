
# Classe para gerenciar as operações do banco
class ClimaEnergiaManager:
    def __init__(self):
        self.db = db
        self.paises_collection = db.paises
        self.grupos_collection = db.grupos
    
    # === OPERAÇÕES COM PAÍSES ===
    
    def inserir_pais(self, pais_data: Dict) -> str:
        """Insere um país e atualiza os grupos relacionados"""
        try:
            # Inserir o país
            result = self.paises_collection.insert_one(pais_data)
            pais_id = str(result.inserted_id)
            
            # Atualizar os grupos para incluir este país
            for codigo_grupo in pais_data.get("grupos", []):
                self.grupos_collection.update_one(
                    {"codigo": codigo_grupo},
                    {"$addToSet": {"paises": pais_data["codigo"]}}
                )
            
            return pais_id
        except Exception as e:
            print(f"Erro ao inserir país: {e}")
            return None
    
    def inserir_grupo(self, grupo_data: Dict) -> str:
        """Insere um grupo e atualiza os países relacionados"""
        try:
            # Inserir o grupo
            result = self.grupos_collection.insert_one(grupo_data)
            grupo_id = str(result.inserted_id)
            
            # Atualizar os países para incluir este grupo
            for codigo_pais in grupo_data.get("paises", []):
                self.paises_collection.update_one(
                    {"codigo": codigo_pais},
                    {"$addToSet": {"grupos": grupo_data["codigo"]}}
                )
            
            return grupo_id
        except Exception as e:
            print(f"Erro ao inserir grupo: {e}")
            return None
    
    def adicionar_pais_ao_grupo(self, codigo_grupo: str, codigo_pais: str) -> bool:
        """Adiciona um país a um grupo (relação bidirecional)"""
        try:
            # Adicionar país ao grupo
            result1 = self.grupos_collection.update_one(
                {"codigo": codigo_grupo},
                {"$addToSet": {"paises": codigo_pais}}
            )
            
            # Adicionar grupo ao país
            result2 = self.paises_collection.update_one(
                {"codigo": codigo_pais},
                {"$addToSet": {"grupos": codigo_grupo}}
            )
            
            return result1.modified_count > 0 and result2.modified_count > 0
        except Exception as e:
            print(f"Erro ao adicionar país ao grupo: {e}")
            return False
    
    def remover_pais_do_grupo(self, codigo_grupo: str, codigo_pais: str) -> bool:
        """Remove um país de um grupo (relação bidirecional)"""
        try:
            # Remover país do grupo
            result1 = self.grupos_collection.update_one(
                {"codigo": codigo_grupo},
                {"$pull": {"paises": codigo_pais}}
            )
            
            # Remover grupo do país
            result2 = self.paises_collection.update_one(
                {"codigo": codigo_pais},
                {"$pull": {"grupos": codigo_grupo}}
            )
            
            return result1.modified_count > 0 and result2.modified_count > 0
        except Exception as e:
            print(f"Erro ao remover país do grupo: {e}")
            return False
    
    # === CONSULTAS ===
    
    def buscar_pais_por_codigo(self, codigo: str) -> Optional[Dict]:
        """Busca um país pelo código"""
        return self.paises_collection.find_one({"codigo": codigo})
    
    def buscar_grupo_por_codigo(self, codigo: str) -> Optional[Dict]:
        """Busca um grupo pelo código"""
        return self.grupos_collection.find_one({"codigo": codigo})
    
    def buscar_paises_de_grupo(self, codigo_grupo: str) -> List[Dict]:
        """Busca todos os países que pertencem a um grupo"""
        grupo = self.buscar_grupo_por_codigo(codigo_grupo)
        if not grupo:
            return []
        
        codigos_paises = grupo.get("paises", [])
        return list(self.paises_collection.find({"codigo": {"$in": codigos_paises}}))
    
    def buscar_grupos_de_pais(self, codigo_pais: str) -> List[Dict]:
        """Busca todos os grupos aos quais um país pertence"""
        pais = self.buscar_pais_por_codigo(codigo_pais)
        if not pais:
            return []
        
        codigos_grupos = pais.get("grupos", [])
        return list(self.grupos_collection.find({"codigo": {"$in": codigos_grupos}}))
    
    def verificar_consistencia_relacoes(self) -> Dict[str, List[str]]:
        """Verifica se as relações entre países e grupos estão consistentes"""
        inconsistencias = {"paises_orfaos": [], "grupos_orfaos": []}
        
        # Verificar países
        for pais in self.paises_collection.find():
            for codigo_grupo in pais.get("grupos", []):
                grupo = self.buscar_grupo_por_codigo(codigo_grupo)
                if not grupo or pais["codigo"] not in grupo.get("paises", []):
                    inconsistencias["paises_orfaos"].append(
                        f"País {pais['codigo']} referencia grupo {codigo_grupo} mas o grupo não referencia o país"
                    )
        
        # Verificar grupos
        for grupo in self.grupos_collection.find():
            for codigo_pais in grupo.get("paises", []):
                pais = self.buscar_pais_por_codigo(codigo_pais)
                if not pais or grupo["codigo"] not in pais.get("grupos", []):
                    inconsistencias["grupos_orfaos"].append(
                        f"Grupo {grupo['codigo']} referencia país {codigo_pais} mas o país não referencia o grupo"
                    )
        
        return inconsistencias

# Função para criar dados de exemplo
def criar_dados_exemplo():
    manager = ClimaEnergiaManager()
    
    # Exemplo de país - Brasil
    brasil = {
        "nome": "Brasil",
        "codigo": "BR",
        "grupos": ["AMERICA_SUL", "BRICS"],
        "anos": [{
            "ano": 2023,
            "meses": [
                {
                    "mes": 1,
                    "mudanca_temp": 1.2,
                    "desvio_padrao": 0.3,
                    "unidade": "°C"
                },
                {
                    "mes": 2,
                    "mudanca_temp": 1.5,
                    "desvio_padrao": 0.4,
                    "unidade": "°C"
                }
                # ... outros meses
            ],
            "tipos_energia": [
                {
                    "tipo": "solar",
                    "renovavel": True,
                    "valor_geracao": 15000.0,
                    "valor_emissao": 0.0,
                    "unidade_geracao": "GWh",
                    "unidade_emissao": "tCO2"
                },
                {
                    "tipo": "carvao",
                    "renovavel": False,
                    "valor_geracao": 35000.0,
                    "valor_emissao": 820.0,
                    "unidade_geracao": "GWh",
                    "unidade_emissao": "tCO2"
                }
            ]
        }]
    }
    
    # Exemplo de grupo - América do Sul
    america_sul = {
        "nome": "América do Sul",
        "codigo": "AMERICA_SUL",
        "paises": ["BR", "AR", "CL"],
        "anos": [{
            "ano": 2023,
            "meses": [
                {
                    "mes": 1,
                    "mudanca_temp": 1.1,  # Média dos países do grupo
                    "desvio_padrao": 0.5,
                    "unidade": "°C"
                }
                # ... outros meses
            ],
            "tipos_energia": [
                {
                    "tipo": "hidrica",
                    "renovavel": True,
                    "valor_geracao": 250000.0,  # Soma dos países do grupo
                    "valor_emissao": 0.0,
                    "unidade_geracao": "GWh",
                    "unidade_emissao": "tCO2"
                }
            ]
        }]
    }
    
    # Inserir dados
    pais_id = manager.inserir_pais(brasil)
    grupo_id = manager.inserir_grupo(america_sul)
    
    print(f"Brasil inserido com ID: {pais_id}")
    print(f"América do Sul inserida com ID: {grupo_id}")
    
    return manager

# Executar a criação das coleções e dados de exemplo