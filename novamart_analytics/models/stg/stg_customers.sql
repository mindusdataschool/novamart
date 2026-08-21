with source as (
    select * from {{ source('app', 'customers') }}
),
padronizado as (
    select
        id           as id_cliente,
        nome_completo         as nome_cliente,
        lower(email) as email,
        cidade,
        estado,
        criado_em
    from source
)
select * from padronizado