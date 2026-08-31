with pedidos as (
    select * from {{ ref('stg_orders') }}
),
produtos as ( 
    select * from {{ ref('stg_products') }} 
),
order_statuses as (
    select * from {{ ref('stg_order_statuses') }}
),
categorias as (
    select * from {{ ref('stg_product_categories') }}
)
select 
    f.id_item
    , f.id_pedido
    , f.id_produto
    , pr.nome_produto
    , f.receita_item
    , f.comissao
    , f.margem_item
    , f.flag_comissao_padrao
    , p.data_pedido
    , p.id_status
    , os.nome_status
    , pr.id_categoria
    , c.nome_categoria
from {{ ref('int_itens_pedido_enriquecido') }} f
join pedidos p on f.id_pedido = p.id_pedido
join produtos pr on f.id_produto = pr.id_produto
join order_statuses os on p.id_status = os.id
join categorias c on pr.id_categoria = c.id