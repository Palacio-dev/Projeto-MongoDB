use("clima_energia");

db.grupos.aggregate([
  { $unwind: "$anos" },
  { $match: { "anos.ano": 2019 } },
  { $unwind: "$anos.tipos_energia" },
  { $group: {
      _id: {
        grupo: "$nome",
        codigo: "$codigo"
      },
      tipos_energia: { $addToSet: "$anos.tipos_energia.tipo" }
  }},
  { $project: {
      grupo: "$_id.grupo",
      codigo: "$_id.codigo",
      quantidade_tipos: { $size: "$tipos_energia" },
      tipos_energia: 1,
      _id: 0
  }},
  { $sort: { quantidade_tipos: -1 } },
  { $limit: 5 }
]);
