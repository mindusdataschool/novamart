with source as (
    select * from {{ source('app', 'payments') }}
),
padronizado as (
    select
        id                     as id_pagamento,
        id_pedido,
        id_transacao_gateway,
        status,
        pago_em,
        criado_em
    from source
)
select * from padronizado