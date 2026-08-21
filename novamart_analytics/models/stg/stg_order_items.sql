with source as (
    select * from {{ source('app', 'order_items') }}
),
padronizado as (
    select
        id              as id_item,
        id_pedido,
        id_produto,
        id_vendedor,
        quantidade,
        preco_unitario,
        criado_em
    from source
)
select * from padronizado