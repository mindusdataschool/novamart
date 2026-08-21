{{ config(
    materialized='incremental',
    unique_key='id_item',
    incremental_strategy='delete+insert',
) }}

with itens as (
    select * from {{ ref('stg_order_items') }}
    {% if is_incremental() %}
    where criado_em >= (select max(criado_em) - interval '3 days' from {{ this }})
    {% endif %}
),
produtos as ( 
    select * from {{ ref('stg_products') }} 
),
sellers  as (
     select * from {{ ref('stg_sellers') }} 
),

enriquecido as (
    select
        i.id_item
        , i.id_pedido
        , i.id_produto
        , i.criado_em
        , i.quantidade * i.preco_unitario as receita_item
        , coalesce(s.taxa_comissao, 0.15) as taxa_comissao_aplicada
        , (i.quantidade * i.preco_unitario) * coalesce(s.taxa_comissao, 0.15) as comissao
        , (i.quantidade * i.preco_unitario) - (i.quantidade * coalesce(p.preco_custo, 0))  as margem_item
        , case 
            when s.taxa_comissao is null then true 
            else false 
        end as flag_comissao_padrao
        -- regra da Marina: margem negativa não é corrigida automaticamente —
        -- só sinalizada como dado suspeito (promoção vs. erro de cadastro)
        , case 
            when (i.quantidade * i.preco_unitario) - (i.quantidade * coalesce(p.preco_custo, 0)) < 0 then true 
            else false 
        end as has_negative_margin
    from itens i
    join produtos p on i.id_produto = p.id_produto
    join sellers s  on i.id_vendedor = s.id_vendedor
)

-- criado_em precisa estar no select final: {{ this }} depende dela pro filtro incremental
select * from enriquecido