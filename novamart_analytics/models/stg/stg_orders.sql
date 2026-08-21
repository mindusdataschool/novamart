with source as (
    select * from {{ source('app', 'orders') }}
),
padronizado as (
    select 
        id as id_pedido
        , id_cliente
        , id_status
        , data_pedido::date as data_pedido 
        , entregue_em
        , id_transportadora
        , criado_em
    from source
)
select * from padronizado