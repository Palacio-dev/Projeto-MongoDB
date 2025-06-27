// Consulta que lista as porcentagens de energia renovavel
// para todos os  paises pertencentes a determinado grupo, para todos os grupos

use("clima_energia");
db.grupos.aggregate([
    {"$lookup": {
        "from": "paises",
        "localField": "paises",
        "foreignField": "_id",
        "as": "dados_paises"
    }
    },
    {"$unwind": "$dados_paises"},
    {"$unwind": "$dados_paises.anos"},
    {"$unwind": "$dados_paises.anos.tipos_energia"},
    {"$group": {
        "_id": {
            "grupo": "$nome",
            "pais": "$dados_paises.nome",
            "ano": "$dados_paises.anos.ano"
        },
        "total": {"$sum": "$dados_paises.anos.tipos_energia.valor_geracao"},
        "renovavel": {
            "$sum": {
                "$cond": [
                    {"$eq": ["$dados_paises.anos.tipos_energia.renovavel", true]},
                    "$dados_paises.anos.tipos_energia.valor_geracao",
                    0
                ]
            }
        }
    }
    },
    {"$addFields": {
        "porcentagem": {
            "$cond": [
                {"$gt": ["$total", 0]},
                {"$multiply": [{"$divide": ["$renovavel", "$total"]}, 100]},
                0
            ]
        }
    }
    },
    {"$group": {
        "_id": {
            "grupo": "$_id.grupo",
            "pais": "$_id.pais"
        },
        "porcentagem_renovavel": {"$first": "$porcentagem"},
        "ano": {"$first": "$_id.ano"}
    }
    },
    {"$group": {
        "_id": "$_id.grupo",
        "paises": {
            "$push": {
                "nome": "$_id.pais",
                "porcentagem": {"$round": ["$porcentagem_renovavel", 2]},
                "ano": "$ano"
            }
        }
    }
    },
    {"$sort": {"_id": 1}}
])