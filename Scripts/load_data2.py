import pandas as pd
from pymongo import MongoClient
from collections import defaultdict

# ======================== CONFIG ==========================
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "clima_energia"
DATASETS_DIR = "../Datasets"

# ===================== CONEXÃO MONGO =======================
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
paises_collection = db.paises
grupos_collection = db.grupos

# ================== TIPOS DE ENERGIA =======================
def load_tipos_energia():
    tipos = {}
    try:
        df = pd.read_csv(f"{DATASETS_DIR}/tipos_energia.csv", usecols=['Tipo', 'Renovavel'])
        tipos = {row['Tipo']: bool(row['Renovavel']) for _, row in df.iterrows()}
        print(f"✔ Carregados {len(tipos)} tipos de energia")
    except FileNotFoundError:
        print("⚠ tipos_energia.csv não encontrado. Usando valores padrão.")
        tipos = {
            'Solar': True, 'Wind': True, 'Hydro': True, 'Geothermal': True,
            'Bioenergy': True, 'Nuclear': False, 'Coal': False, 'Oil': False,
            'Gas': False, 'Other fossil': False
        }
    return tipos

# ================== BASE DE PAÍSES E GRUPOS =================
def criar_base_paises_grupos():
    df = pd.read_csv(f"{DATASETS_DIR}/energia.csv", usecols=["Area", "Country code", "Area type"])
    df = df.drop_duplicates(subset=['Area'])

    paises, grupos = [], []
    paises_cache, grupos_cache = {}, {}

    for _, row in df.iterrows():
        base_doc = {
            "nome": row["Area"],
            "codigo": row["Country code"],
            "anos": []
        }

        if row["Area type"] == "Country":
            base_doc["grupos"] = []
            paises.append(base_doc)
            paises_cache[row["Area"]] = row["Country code"]
        elif row["Area type"] == "Region":
            base_doc["paises"] = []
            grupos.append(base_doc)
            grupos_cache[row["Area"]] = row["Country code"]

    paises_collection.insert_many(paises)
    grupos_collection.insert_many(grupos)

    print(f"✔ {len(paises)} países e {len(grupos)} grupos inseridos.")
    return paises_cache, grupos_cache

# ==================== RELAÇÃO PAÍS-GRUPO =====================
def carregar_relacoes(paises_cache, grupos_cache):
    df = pd.read_csv(f"{DATASETS_DIR}/energia.csv", usecols=["Area", "EU", "OECD", "G20", "G7", "ASEAN"], encoding="ISO-8859-1")
    grupos_nomes = ["EU", "OECD", "G20", "G7", "ASEAN"]

    relacoes = defaultdict(list)

    for _, row in df.iterrows():
        pais = row["Area"]
        if pais not in paises_cache:
            continue

        for grupo in grupos_nomes:
            if pd.notna(row[grupo]) and float(row[grupo]) > 0 and grupo in grupos_cache.values():
                relacoes[paises_cache[pais]].append(grupo)

    # Atualiza países com grupos
    for codigo_pais, grupos in relacoes.items():
        paises_collection.update_one({"codigo": codigo_pais}, {"$set": {"grupos": grupos}})

    # Atualiza grupos com países
    grupos_invertido = defaultdict(list)
    for pais, grupos in relacoes.items():
        for grupo in grupos:
            grupos_invertido[grupo].append(pais)

    for codigo_grupo, paises in grupos_invertido.items():
        grupos_collection.update_one({"codigo": codigo_grupo}, {"$set": {"paises": paises}})

    print(f"✔ Relações país-grupo carregadas ({len(relacoes)} países).")

# ==================== FUNÇÃO PRINCIPAL ======================
def main():
    print("== Iniciando carregamento ==")

    paises_collection.delete_many({})
    grupos_collection.delete_many({})
    print("✔ Coleções limpas")

    tipos_energia = load_tipos_energia()
    paises_cache, grupos_cache = criar_base_paises_grupos()
    carregar_relacoes(paises_cache, grupos_cache)

    print("✔ Banco estruturado com sucesso (sem OOP)")

if __name__ == "__main__":
    main()
