use("clima_energia");
db.paises.aggregate([
  { $unwind: "$anos" },
  { $match: { "anos.ano": 2019 } },
  { $unwind: "$anos.meses" },
  { $match: { "anos.meses.mudanca_temp": { $exists: true } } },
  { $group: {
      _id: {
          pais: "$nome",
          codigo: "$codigo"
      },
      Mudanca_total_temp: { $sum: "$anos.meses.mudanca_temp" },
      unidade: { $first: "$anos.meses.unidade"}
  }},
  { $sort: { Mudanca_total_temp: -1 } },
  { $limit: 10 },
  { $project: {
      pais: "$_id.pais",
      codigo: "$_id.codigo",
      Mudanca_total_temp: { $divide: ["$Mudanca_total_temp", 100] }, 
      unidade: 1,
      _id: 0
  }}
]);