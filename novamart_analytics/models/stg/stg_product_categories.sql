with 
    source as (
        select * from {{ source('app', 'product_categories') }}
    )
select 
    id 
    , nome as nome_categoria
    , slug
    , criado_em
from source