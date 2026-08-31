with
    source as (
        select * from {{ source('app', 'order_statuses') }}
    )
select
    id 
    , nome as nome_status
    , codigo
    , descricao
    , ordem_exibicao
from source