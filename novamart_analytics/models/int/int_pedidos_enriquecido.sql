{{ config(
    materialized='incremental',
    unique_key='id_pedido',
    incremental_strategy='delete+insert',
    on_schema_change='sync_all_columns'
)}}

with pedidos as (
    select * from {{ ref('stg_orders') }}
    {% if is_incremental() %}
        where criado_em > (select max(criado_em) - interval '3 days' from {{ this }})
    {% endif %}
),
dedup as ( 
    select *,
    row_number() over (partition by id_pedido order by criado_em desc) as rn
    from pedidos
),
enriquecido as (
    select 
        id_pedido
        , id_status 
        , id_cliente
        , data_pedido 
        , entregue_em 
        , id_transportadora
        , criado_em 
        , case 
            when id_status = 5 and entregue_em is null then true 
            else false
        end as delivered_at_missing
    from dedup
    where rn = 1
)
select * from enriquecido