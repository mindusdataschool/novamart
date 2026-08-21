with source as (
    select * from {{ source('app', 'sellers') }}
),
padronizado as (
    select
        id             as id_vendedor,
        nome_empresa           as nome_vendedor,
        taxa_comissao,
        avaliacao,
        criado_em
    from source
)
select * from padronizado