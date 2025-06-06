from pymongo import MongoClient

# Conecta ao MongoDB local (por padrão, na porta 27017)
client = MongoClient('mongodb://localhost:27017/')

# Lista os bancos disponíveis
print(client.list_database_names())

# Acessa um banco de dados
db = client['nome_do_banco']

# Acessa uma collection
collection = db['nome_da_collection']

# Exemplo: insere um documento
collection.insert_one({"nome": "Lucas", "idade": 25})

# Exemplo: busca todos os documentos
for doc in collection.find():
    print(doc)

