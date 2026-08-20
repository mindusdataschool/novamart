-- ============================================================
--  MÓDULO 3 — SCRIPT DE EDA COM SQL
--  Mindus Data School · NovaMart · PostgreSQL
--  Execute no DBeaver conectado ao novamarket-db (RDS)
--  Use Ctrl+Enter para rodar linha a linha
-- ============================================================
--
--  INSTRUÇÕES:
--  1. Rode cada query no DBeaver
--  2. Anote suas observações no arquivo DUVIDAS_EDA.md
--  3. Sinalizado com [ANOTAR] = você deve registrar algo
--  4. Sinalizado com [BONUS] = exercício opcional
--
-- ============================================================


-- ============================================================
--  NÍVEL 1 — VOLUMETRIA
--  Objetivo: entender o tamanho e alcance do banco antes de
--  qualquer análise. Nunca pule essa etapa.
-- ============================================================

-- 1.1 Contagem de registros por tabela
SELECT 'customers'   AS tabela, COUNT(*) AS registros FROM app.customers
UNION ALL
SELECT 'sellers',              COUNT(*)               FROM app.sellers
UNION ALL
SELECT 'products',             COUNT(*)               FROM app.products
UNION ALL
SELECT 'orders',               COUNT(*)               FROM app.orders
UNION ALL
SELECT 'order_items',          COUNT(*)               FROM app.order_items
UNION ALL
SELECT 'payments',             COUNT(*)               FROM app.payments
UNION ALL
SELECT 'reviews',              COUNT(*)               FROM app.reviews
UNION ALL
SELECT 'product_categories',   COUNT(*)               FROM app.product_categories
UNION ALL
SELECT 'seller_categories',    COUNT(*)               FROM app.seller_categories
UNION ALL
SELECT 'order_statuses',       COUNT(*)               FROM app.order_statuses
UNION ALL
SELECT 'payment_methods',      COUNT(*)               FROM app.payment_methods
ORDER BY registros DESC;
-- [ANOTAR] Os números batem com o esperado? Alguma tabela surpreendeu?


-- 1.2 Período coberto pelos dados
SELECT
    MIN(data_pedido)                              AS primeiro_pedido,
    MAX(data_pedido)                              AS ultimo_pedido,
    MAX(data_pedido) - MIN(data_pedido)           AS periodo_total,
    COUNT(DISTINCT DATE_TRUNC('month', data_pedido)) AS meses_com_dados
FROM app.orders;
-- [ANOTAR] Qual o período dos dados? Tem gaps de meses?


-- 1.3 Volume de pedidos por mês
SELECT
    TO_CHAR(DATE_TRUNC('month', data_pedido), 'MM/YYYY') AS mes,
    COUNT(*)                                              AS pedidos,
    ROUND(SUM(valor_total), 2)                           AS receita
FROM app.orders
GROUP BY DATE_TRUNC('month', data_pedido)
ORDER BY DATE_TRUNC('month', data_pedido);
-- [ANOTAR] O volume é constante? Tem sazonalidade visível?


-- 1.4 Status disponíveis no banco
SELECT id, nome FROM app.order_statuses ORDER BY id;
SELECT id, nome, ativo FROM app.payment_methods ORDER BY id;
-- [ANOTAR] Quais status existem? Qual ID representa "entregue"? "cancelado"?


-- ============================================================
--  NÍVEL 2 — AUDITORIA DE NULLS
--  Objetivo: mapear onde estão os buracos. Todo analista faz
--  isso antes de construir qualquer modelo.
-- ============================================================

-- 2.1 Auditoria de NULLs em customers
SELECT
    COUNT(*)                                         AS total,
    COUNT(cpf)                                       AS cpf_preenchido,
    COUNT(*) - COUNT(cpf)                            AS cpf_null,
    COUNT(email)                                     AS email_preenchido,
    COUNT(*) - COUNT(email)                          AS email_null,
    COUNT(telefone)                                  AS telefone_preenchido,
    COUNT(*) - COUNT(telefone)                       AS telefone_null,
    COUNT(data_nascimento)                           AS nasc_preenchido,
    COUNT(*) - COUNT(data_nascimento)                AS nasc_null,
    COUNT(cep)                                       AS cep_preenchido,
    COUNT(*) - COUNT(cep)                            AS cep_null
FROM app.customers;
-- [ANOTAR] Quais campos têm NULLs? São esperados ou problemáticos?


-- 2.2 Auditoria de NULLs em products (foco em preco_custo)
SELECT
    COUNT(*)                                         AS total_produtos,
    COUNT(preco_custo)                               AS com_custo,
    COUNT(*) - COUNT(preco_custo)                    AS custo_null,
    ROUND(100.0 * (COUNT(*) - COUNT(preco_custo)) / COUNT(*), 1) AS pct_null,
    COUNT(descricao)                                 AS com_descricao,
    COUNT(*) - COUNT(descricao)                      AS descricao_null,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END)   AS ativos,
    SUM(CASE WHEN status != 'active' THEN 1 ELSE 0 END)  AS inativos
FROM app.products;
-- [ANOTAR] O % de custo NULL parece intencional ou bug? O que significa preco_custo NULL?


-- 2.3 Auditoria de NULLs em orders (foco em datas)
SELECT
    COUNT(*)                                         AS total_pedidos,
    COUNT(data_pedido)                               AS com_data_pedido,
    COUNT(entregue_em)                               AS com_data_entrega,
    COUNT(*) - COUNT(entregue_em)                    AS sem_data_entrega,
    COUNT(codigo_rastreamento)                       AS com_rastreio,
    COUNT(*) - COUNT(codigo_rastreamento)            AS sem_rastreio,
    COUNT(previsao_entrega)                          AS com_previsao,
    COUNT(custo_frete)                               AS com_frete
FROM app.orders;
-- [ANOTAR] Faz sentido ter pedidos sem entregue_em? Em quais situações?


-- 2.4 Auditoria de NULLs em payments
SELECT
    status,
    COUNT(*)                                         AS total,
    COUNT(pago_em)                                   AS com_data_pagamento,
    COUNT(*) - COUNT(pago_em)                        AS sem_data_pagamento,
    COUNT(valor_parcela)                             AS com_valor_parcela
FROM app.payments
GROUP BY status
ORDER BY total DESC;
-- [ANOTAR] Pagamentos 'approved' sem pago_em — bug ou regra de negócio?


-- 2.5 Auditoria de NULLs em sellers
SELECT
    COUNT(*)                                         AS total_sellers,
    COUNT(taxa_comissao)                             AS com_taxa,
    COUNT(*) - COUNT(taxa_comissao)                  AS taxa_null,
    COUNT(avaliacao)                                 AS com_avaliacao,
    COUNT(*) - COUNT(avaliacao)                      AS avaliacao_null
FROM app.sellers;
-- [ANOTAR] Taxa NULL em sellers — qual valor devemos usar? Perguntar no stakeholder.


-- ============================================================
--  NÍVEL 3 — DISTRIBUIÇÕES
--  Objetivo: entender como os dados se distribuem.
--  É aqui que aparecem concentrações inesperadas e outliers.
-- ============================================================

-- 3.1 Pedidos por status (distribuição)
SELECT
    os.nome                                          AS status_nome,
    COUNT(o.id)                                      AS total_pedidos,
    ROUND(100.0 * COUNT(o.id) / SUM(COUNT(o.id)) OVER (), 1) AS pct
FROM app.orders o
JOIN app.order_statuses os ON os.id = o.id_status
GROUP BY os.id, os.nome
ORDER BY total_pedidos DESC;
-- [ANOTAR] A distribuição de status parece saudável? Há muitos cancelados/pendentes?


-- 3.2 Receita e pedidos por estado
SELECT
    c.estado,
    COUNT(o.id)                                      AS pedidos,
    ROUND(SUM(o.valor_total), 2)                     AS receita_total,
    ROUND(AVG(o.valor_total), 2)                     AS ticket_medio
FROM app.orders o
JOIN app.customers c ON c.id = o.id_cliente
GROUP BY c.estado
ORDER BY receita_total DESC
LIMIT 15;
-- [ANOTAR] Qual estado lidera em receita? O ticket médio varia muito entre estados?


-- 3.3 Distribuição de preços dos produtos
SELECT
    CASE
        WHEN preco < 50   THEN 'Até R$50'
        WHEN preco < 100  THEN 'R$50 a R$100'
        WHEN preco < 300  THEN 'R$100 a R$300'
        WHEN preco < 1000 THEN 'R$300 a R$1.000'
        ELSE 'Acima de R$1.000'
    END                                              AS faixa_preco,
    COUNT(*)                                         AS total_produtos,
    ROUND(AVG(preco), 2)                             AS preco_medio
FROM app.products
WHERE status = 'active'
GROUP BY 1
ORDER BY MIN(preco);
-- [ANOTAR] Como os produtos se distribuem por faixa de preço?


-- 3.4 Top 10 produtos mais vendidos (por quantidade)
SELECT
    p.nome,
    p.sku,
    pc.nome                                          AS categoria,
    SUM(oi.quantidade)                               AS unidades_vendidas,
    ROUND(SUM(oi.preco_unitario * oi.quantidade), 2) AS receita_gerada
FROM app.products p
JOIN app.order_items oi ON oi.id_produto = p.id
JOIN app.orders o       ON o.id = oi.id_pedido
JOIN app.product_categories pc ON pc.id = p.id_categoria
WHERE o.id_status = 5  -- só entregues
GROUP BY p.id, p.nome, p.sku, pc.nome
ORDER BY unidades_vendidas DESC
LIMIT 10;
-- [ANOTAR] Os top produtos fazem sentido? Têm boa margem?


-- 3.5 Sellers por número de pedidos (volume)
SELECT
    s.nome_empresa,
    s.avaliacao,
    COUNT(DISTINCT o.id)                             AS pedidos,
    ROUND(SUM(oi.preco_unitario * oi.quantidade), 2) AS receita_bruta
FROM app.sellers s
JOIN app.products p     ON p.id_vendedor = s.id
JOIN app.order_items oi ON oi.id_produto = p.id
JOIN app.orders o       ON o.id = oi.id_pedido
WHERE o.id_status = 5
GROUP BY s.id, s.nome_empresa, s.avaliacao
ORDER BY receita_bruta DESC
LIMIT 15;
-- [ANOTAR] Tem sellers com avaliação alta e volume baixo? (pergunta chave do módulo)


-- 3.6 Distribuição de avaliações (reviews)
SELECT
    avaliacao,
    COUNT(*)                                         AS total,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM app.reviews
WHERE avaliacao IS NOT NULL
GROUP BY avaliacao
ORDER BY avaliacao DESC;
-- [ANOTAR] A distribuição de notas parece real? Tem concentração em notas extremas?


-- ============================================================
--  NÍVEL 4 — CONSISTÊNCIA DE CHAVES ESTRANGEIRAS
--  Objetivo: garantir que as tabelas se conectam corretamente.
--  Orphan records quebram qualquer JOIN.
-- ============================================================

-- 4.1 Pedidos sem cliente correspondente
SELECT COUNT(*) AS pedidos_sem_cliente
FROM app.orders o
LEFT JOIN app.customers c ON c.id = o.id_cliente
WHERE c.id IS NULL;
-- [ANOTAR] Há pedidos órfãos? Isso indicaria problema de integridade referencial.


-- 4.2 Itens de pedido sem produto
SELECT COUNT(*) AS itens_sem_produto
FROM app.order_items oi
LEFT JOIN app.products p ON p.id = oi.id_produto
WHERE p.id IS NULL;
-- [ANOTAR] Produto deletado após pedido feito? O que fazer com esses itens?


-- 4.3 Pedidos sem pagamento registrado
SELECT COUNT(*) AS pedidos_sem_pagamento
FROM app.orders o
LEFT JOIN app.payments p ON p.id_pedido = o.id
WHERE p.id IS NULL;
-- [ANOTAR] Pedido sem pagamento é esperado? Em qual status estariam?


-- 4.4 Pedidos com mais de um pagamento
SELECT id_pedido, COUNT(*) AS pagamentos
FROM app.payments
GROUP BY id_pedido
HAVING COUNT(*) > 1
ORDER BY pagamentos DESC;
-- [ANOTAR] Pedido com dois pagamentos é possível? Retentativa? Estorno?


-- 4.5 Reviews sem pedido correspondente
SELECT COUNT(*) AS reviews_sem_pedido
FROM app.reviews r
LEFT JOIN app.order_items oi ON oi.id = r.id_item_pedido
LEFT JOIN app.orders o ON o.id = oi.id_pedido
WHERE o.id IS NULL;
-- [ANOTAR] Review sem pedido associado?


-- 4.6 Produtos sem categoria
SELECT COUNT(*) AS produtos_sem_categoria
FROM app.products p
LEFT JOIN app.product_categories pc ON pc.id = p.id_categoria
WHERE pc.id IS NULL;


-- ============================================================
--  NÍVEL 5 — INVESTIGAÇÃO DE ANOMALIAS
--  Objetivo: quantificar e entender as inconsistências do banco.
--  Estas são as perguntas que você vai levar pro stakeholder.
-- ============================================================

-- 5.1 BUG: Pedidos "entregues" sem data de entrega
SELECT
    os.nome                                          AS status,
    COUNT(o.id)                                      AS total_pedidos,
    COUNT(o.entregue_em)                             AS com_data,
    COUNT(o.id) - COUNT(o.entregue_em)               AS sem_data,
    ROUND(100.0 * (COUNT(o.id) - COUNT(o.entregue_em)) / COUNT(o.id), 1) AS pct_sem_data
FROM app.orders o
JOIN app.order_statuses os ON os.id = o.id_status
GROUP BY os.id, os.nome
ORDER BY os.id;
-- [ANOTAR] Qual status tem pedidos sem entregue_em? É bug ou comportamento esperado?
-- PERGUNTA PRO STAKEHOLDER: o que define um pedido como "entregue" no sistema?


-- 5.2 BUG: Pagamentos aprovados sem data
SELECT
    status,
    COUNT(*)                                         AS total,
    SUM(CASE WHEN pago_em IS NULL THEN 1 ELSE 0 END) AS sem_data,
    ROUND(100.0 * SUM(CASE WHEN pago_em IS NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct
FROM app.payments
GROUP BY status;
-- [ANOTAR] % de approved sem pago_em. É bug de pipeline ou regra de negócio?
-- PERGUNTA PRO STAKEHOLDER: pagamento aprovado sem data — devemos ignorar ou alertar?


-- 5.3 BUG: Produtos com margem negativa
SELECT
    COUNT(*)                                         AS total_produtos,
    SUM(CASE WHEN preco_custo > preco THEN 1 ELSE 0 END) AS margem_negativa,
    SUM(CASE WHEN preco_custo IS NULL THEN 1 ELSE 0 END) AS custo_null,
    SUM(CASE WHEN preco_custo <= preco THEN 1 ELSE 0 END) AS margem_positiva
FROM app.products
WHERE status = 'active';

-- Quais produtos têm margem negativa?
SELECT nome, sku, preco, preco_custo,
       ROUND(preco - preco_custo, 2)                 AS margem_absoluta,
       ROUND(100.0 * (preco - preco_custo) / preco, 1) AS margem_pct
FROM app.products
WHERE preco_custo IS NOT NULL
  AND preco_custo > preco
ORDER BY margem_pct ASC
LIMIT 20;
-- [ANOTAR] Os produtos com margem negativa são de categorias específicas?
-- PERGUNTA PRO STAKEHOLDER: produto com custo > preço — erro de cadastro ou promoção?


-- 5.4 BUG: CPF em múltiplos formatos
SELECT
    SUM(CASE WHEN cpf ~ '^\d{3}\.\d{3}\.\d{3}-\d{2}$' THEN 1 ELSE 0 END) AS formato_mascara,
    SUM(CASE WHEN cpf ~ '^\d{11}$' THEN 1 ELSE 0 END)                     AS formato_numerico,
    SUM(CASE WHEN cpf IS NULL THEN 1 ELSE 0 END)                           AS cpf_null,
    SUM(CASE WHEN cpf IS NOT NULL
              AND cpf !~ '^\d{3}\.\d{3}\.\d{3}-\d{2}$'
              AND cpf !~ '^\d{11}$' THEN 1 ELSE 0 END)                    AS formato_invalido,
    COUNT(*)                                                                AS total
FROM app.customers;
-- [ANOTAR] Qual % está em formato inválido? De onde vieram os 3 formatos?
-- PERGUNTA PRO STAKEHOLDER: qual é o formato canônico do CPF? Normalizar no dbt?


-- 5.5 BUG: Emails inválidos
SELECT
    COUNT(*) FILTER (WHERE email NOT LIKE '%@%')     AS sem_arroba,
    COUNT(*) FILTER (WHERE email LIKE '%@%'
                       AND email NOT LIKE '%@%.%')   AS sem_dominio,
    COUNT(*) FILTER (WHERE email IS NULL)            AS email_null,
    COUNT(*)                                         AS total
FROM app.customers;
-- [ANOTAR] Quantos emails são inválidos? Vêm de qual origem (sistema legado)?
-- PERGUNTA PRO STAKEHOLDER: email inválido — bloquear cadastro ou marcar como inválido?


-- 5.6 BONUS — Sellers sem vendas (período completo)
SELECT s.nome_empresa, s.avaliacao, s.taxa_comissao
FROM app.sellers s
LEFT JOIN app.products p     ON p.id_vendedor = s.id
LEFT JOIN app.order_items oi ON oi.id_produto = p.id
LEFT JOIN app.orders o       ON o.id = oi.id_pedido AND o.id_status = 5
WHERE o.id IS NULL
ORDER BY s.nome_empresa;
-- [ANOTAR] Sellers sem nenhuma venda entregue. São novos ou inativos?
-- PERGUNTA PRO STAKEHOLDER: como definimos um "seller ativo"?


-- 5.7 BONUS — Tempo médio de entrega por estado
SELECT
    c.estado,
    COUNT(o.id)                                      AS pedidos_entregues,
    ROUND(AVG(o.entregue_em - o.data_pedido), 1)     AS dias_medio_entrega,
    MIN(o.entregue_em - o.data_pedido)               AS mais_rapido,
    MAX(o.entregue_em - o.data_pedido)               AS mais_lento
FROM app.orders o
JOIN app.customers c ON c.id = o.id_cliente
WHERE o.id_status = 5
  AND o.entregue_em IS NOT NULL
GROUP BY c.estado
ORDER BY dias_medio_entrega;
-- [ANOTAR] O SLA de entrega varia por estado? Tem outliers (entrega em 0 dias)?


-- ============================================================
--  QUERY FINAL — PANORAMA GERAL DO BANCO
--  Use depois de completar todos os níveis para ter uma visão
--  consolidada das anomalias encontradas.
-- ============================================================

SELECT 'pedidos_sem_data_entrega'  AS anomalia,
       COUNT(*) AS total
FROM app.orders
WHERE id_status = 5 AND entregue_em IS NULL

UNION ALL

SELECT 'pagamentos_approved_sem_data',
       COUNT(*)
FROM app.payments
WHERE status = 'approved' AND pago_em IS NULL

UNION ALL

SELECT 'produtos_margem_negativa',
       COUNT(*)
FROM app.products
WHERE preco_custo IS NOT NULL AND preco_custo > preco

UNION ALL

SELECT 'produtos_custo_null',
       COUNT(*)
FROM app.products
WHERE preco_custo IS NULL AND status = 'active'

UNION ALL

SELECT 'emails_invalidos',
       COUNT(*)
FROM app.customers
WHERE email NOT LIKE '%@%.%' OR email IS NULL

UNION ALL

SELECT 'cpf_formato_invalido',
       COUNT(*)
FROM app.customers
WHERE cpf IS NOT NULL
  AND cpf !~ '^\d{3}\.\d{3}\.\d{3}-\d{2}$'
  AND cpf !~ '^\d{11}$'

ORDER BY total DESC;

-- ============================================================
--  FIM DO SCRIPT
--  Próximo passo: abra o DUVIDAS_EDA.md e registre tudo que
--  você encontrou. Depois leve as dúvidas pro stakeholder.
-- ============================================================
