{{ config(
    materialized='incremental',
    unique_key='id_pagamento',
    incremental_strategy='delete+insert'
) }}

with pagamentos as (
    select * from {{ ref('stg_payments') }}
    {% if is_incremental() %}
    where criado_em >= (select max(criado_em) - interval '3 days' from {{ this }})
    {% endif %}
),

enriquecido as (
    select
        id_pagamento
        , id_pedido
        , id_transacao_gateway
        , status
        , criado_em
        , coalesce(pago_em, case when status = 'approved' then criado_em end) as pago_em_ajustado
        , case
            when status = 'approved' and pago_em is null then true 
            else false end as paid_at_missing
    from pagamentos
)

select * from enriquecido