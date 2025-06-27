use("clima_energia");
db.paises.aggregate([
    {$unwind: "$anos"},
    {$unwind: "$anos.tipos_energia"},
    {$unwind: "$anos.meses"},
    {$group: {
        _id: {
        pais: "$nome",
      },
      total_geracao: { $sum: "$anos.tipos_energia.valor_geracao" },
      energia_renovavel: {
        $sum: {
          $cond: [
            { $eq: ["$anos.tipos_energia.renovavel", true] },
            "$anos.tipos_energia.valor_geracao",
            0
          ]
        }
      },
      unidade_geracao: { $first: "$anos.tipos_energia.unidade_geracao" },
      media_mudanca_temp: { $avg: "$anos.meses.mudanca_temp" },
      unidade_temp: { $first: "$anos.meses.unidade" }
    }},
    {$sort: { total_geracao: -1 }},
    {$project: {
        _id: 0,
        pais: "$_id.pais",
        media_mudanca_temp: 1,
        unidade_temp: 1,
        energia_renovavel: 1,
        tipos_renovaveis: 1,
        unidade: 1,
        total_geracao: 1,
        porcentagem: {
            $cond: [
              { $gt: ["$total_geracao", 0] },
              { $multiply: [{ $divide: ["$energia_renovavel", "$total_geracao"] }, 100] },
              0
            ]
          },
        unidade_geracao: 1
    }}
])