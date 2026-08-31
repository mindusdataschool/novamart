with
    receita_produto as (
        select
            id_produto
            , nome_produto
            , sum(receita_item) as receita_total
        from {{ ref('fct_itens_pedido') }}
        group by 1,2
    ),
ordenado as (
    select 
        id_produto 
        , receita_total 
        , nome_produto
        , row_number() over (order by receita_total desc) as ranking
        , sum(receita_total) over (order by receita_total desc) as receita_acumulada
        , sum(receita_total) over () as receita_geral 
    from receita_produto
)
select
    id_produto
    , receita_total
    , ranking
    , nome_produto
    , round(100.0 * receita_acumulada / receita_geral, 2) as percentual_acumulado
    , case
        when 100.0 * receita_acumulada / receita_geral <= 80 then 'A'
        else 'B'
    end as categoria_pareto
from ordenado
order by ranking