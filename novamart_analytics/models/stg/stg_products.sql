with source as (
    select * from {{ source('app', 'products') }}
),
padronizado as (
    select
        id           as id_produto,
        nome         as nome_produto,
        id_categoria,
        preco,
        preco_custo,
        criado_em
    from source
)
select * from padronizado