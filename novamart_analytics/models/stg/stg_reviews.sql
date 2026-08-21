with source as (
    select * from {{ source('app', 'reviews') }}
),
padronizado as (
    select
        id      as id_review,
        id_item_pedido,
        avaliacao,
        criado_em
    from source
)
select * from padronizado