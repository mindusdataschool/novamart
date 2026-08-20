Pedidos sem data de entrega: marcar como delivered_at_missing = true; não descartar.
Pagamentos aprovados sem data: marcar como paid_at_missing = true; usar criado_em como proxy para pago_em quando status = 'approved'.
Produtos com margem negativa: marcar como has_negative_margin; tratar como dado suspeito (não corrigir automaticamente).

Direcionamento / Ações por caso

Pedidos sem delivered_at: inclua esses pedidos nas métricas de receita se o status for Entregue; adicione a flag delivered_at_missing, agrupe por transportadora para detectar padrões e reporte como bug para engenharia (Bruno).
Pagamentos approved sem pago_em: conte como pago para receita; crie paid_at_missing = true; documente o uso de criado_em como proxy; reporte o bug de pipeline ao time de engenharia com amostra dos registros e gateway afetado.
Margem negativa: exiba relatórios com e sem esses produtos; por padrão exclua-os do cálculo de margem média, mas mantenha nos volumes; sinalize has_negative_margin para investigação (promoção vs. erro de cadastro) e peça histórico de preço/custo por SKU/seller.

Documentação e priorização

Documente cada decisão no relatório de EDA (inclua a lógica usada, porcentagens afetadas e exemplos de registros).
Priorize correções por impacto (ex.: se os 28 pedidos representam >X% da receita, abrir bug com urgência).
Encaminhe todas as questões técnicas abertas para o Bruno, com amostra de registros e observações (transportadora, gateway, timestamps).