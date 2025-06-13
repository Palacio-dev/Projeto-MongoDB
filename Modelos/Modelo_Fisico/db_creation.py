from pymongo import MongoClient

# Conectar ao MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["clima_energia"]

# Schema base que será usado tanto para países quanto para grupos
base_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["nome", "codigo", "anos"],
        "properties": {
            "nome": {"bsonType": "string"},
            "codigo": {"bsonType": "string"},
            "anos": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["ano", "meses", "tipos_energia"],
                    "properties": {
                        "ano": {"bsonType": "int"},
                        "meses": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "object",
                                "required": ["mes", "mudanca_temp", "desvio_padrao", "unidade"],
                                "properties": {
                                    "mes": {"bsonType": "int", "minimum": 1, "maximum": 12},
                                    "mudanca_temp": {"bsonType": "double"},
                                    "desvio_padrao": {"bsonType": "double"},
                                    "unidade": {"bsonType": "string"}
                                }
                            }
                        },
                        "tipos_energia": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "object",
                                "required": ["tipo", "renovavel", "valor_geracao", "valor_emissao", "unidade_geracao", "unidade_emissao"],
                                "properties": {
                                    "tipo": {"bsonType": "string"},
                                    "renovavel": {"bsonType": "bool"},
                                    "valor_geracao": {"bsonType": "double"},
                                    "valor_emissao": {"bsonType": "double"},
                                    "unidade_geracao": {"bsonType": "string"},
                                    "unidade_emissao": {"bsonType": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# Schema específico para países (adiciona campo 'grupos')
paises_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["nome", "codigo", "anos", "grupos"],
        "properties": {
            "nome": {"bsonType": "string"},
            "codigo": {"bsonType": "string"},
            "grupos": {
                "bsonType": "array",
                "items": {"bsonType": "objectId"}
            },
            "anos": base_schema["$jsonSchema"]["properties"]["anos"]
        }
    }
}

# Schema específico para grupos (adiciona campo 'paises')
grupos_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["nome", "codigo", "anos", "paises"],
        "properties": {
            "nome": {"bsonType": "string"},
            "codigo": {"bsonType": "string"},
            "paises": {
                "bsonType": "array",
                "items": {"bsonType": "objectId"}
            },
            "anos": base_schema["$jsonSchema"]["properties"]["anos"]
        }
    }
}

# Função para criar as coleções com tratamento de erro
def criar_colecoes():
    # Remove coleções existentes se existirem
    try:
        db.drop_collection("paises")
        db.drop_collection("grupos")
        print("Coleções existentes removidas.")
    except:
        pass
    
    # Cria as novas coleções
    db.create_collection("paises", validator=paises_schema)
    db.create_collection("grupos", validator=grupos_schema)
    print("Coleções criadas com sucesso!")

if __name__ == "__main__":
    # Criar as coleções
    criar_colecoes()