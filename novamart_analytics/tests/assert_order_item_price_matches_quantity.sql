-- Falha se o preço total do item não bater
-- com quantidade * preço unitário
select
    id_pedido,
    id_produto,
    quantidade,
    preco_unitario,
    preco_total
from {{ ref('stg_order_items') }}
where abs(preco_total - (quantidade * preco_unitario)) > 0.01
and id_pedido != 87