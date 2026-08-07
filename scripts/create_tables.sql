-- Create schema
CREATE SCHEMA IF NOT EXISTS app;

SET search_path = app, public;

-- ======================== LOOKUP / DIMENSION TABLES ========================

CREATE TABLE IF NOT EXISTS app.seller_categories (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.product_categories (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    slug VARCHAR(100),
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.product_subcategories (
    id SERIAL PRIMARY KEY,
    id_categoria INTEGER REFERENCES app.product_categories(id),
    nome VARCHAR(100) NOT NULL,
    slug VARCHAR(100),
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.shipping_companies (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    padrao_url_rastreamento VARCHAR(255),
    media_dias_entrega INTEGER,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.payment_methods (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL,
    codigo VARCHAR(20) NOT NULL,
    max_parcelas INTEGER DEFAULT 1,
    ativo BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS app.order_statuses (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL,
    codigo VARCHAR(30) NOT NULL,
    descricao TEXT,
    ordem_exibicao INTEGER
);

CREATE TABLE IF NOT EXISTS app.platform_config (
    id SERIAL PRIMARY KEY,
    chave VARCHAR(100) NOT NULL UNIQUE,
    valor VARCHAR(255) NOT NULL,
    descricao TEXT,
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- ======================== MAIN ENTITY TABLES ========================

CREATE TABLE IF NOT EXISTS app.customers (
    id SERIAL PRIMARY KEY,
    id_uuid UUID DEFAULT gen_random_uuid(),
    nome_completo VARCHAR(200) NOT NULL,
    email VARCHAR(200),
    telefone VARCHAR(50),
    cpf VARCHAR(20),
    data_nascimento DATE,
    endereco_raw TEXT,
    cidade VARCHAR(100),
    estado VARCHAR(2),
    cep VARCHAR(15),
    status VARCHAR(20) DEFAULT 'active',
    codigo_indicacao VARCHAR(20),
    indicado_por_id_cliente INTEGER,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.sellers (
    id SERIAL PRIMARY KEY,
    id_uuid UUID DEFAULT gen_random_uuid(),
    nome_empresa VARCHAR(200) NOT NULL,
    nome_fantasia VARCHAR(200),
    cnpj VARCHAR(25),
    email_contato VARCHAR(200),
    telefone_contato VARCHAR(50),
    id_categoria INTEGER REFERENCES app.seller_categories(id),
    taxa_comissao NUMERIC(5,4),
    endereco_raw TEXT,
    cidade VARCHAR(100),
    estado VARCHAR(2),
    avaliacao NUMERIC(3,2),
    status VARCHAR(20) DEFAULT 'active',
    data_cadastro DATE,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.products (
    id SERIAL PRIMARY KEY,
    id_uuid UUID DEFAULT gen_random_uuid(),
    id_vendedor INTEGER REFERENCES app.sellers(id),
    nome VARCHAR(300) NOT NULL,
    sku VARCHAR(50),
    descricao TEXT,
    preco NUMERIC(12,2) NOT NULL,
    preco_custo NUMERIC(12,2),
    id_categoria INTEGER REFERENCES app.product_categories(id),
    id_subcategoria INTEGER REFERENCES app.product_subcategories(id),
    quantidade_estoque INTEGER DEFAULT 0,
    weight_kg NUMERIC(8,3),
    id_externo VARCHAR(50),
    nome_externo VARCHAR(200),
    status VARCHAR(20) DEFAULT 'active',
    e_digital BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.coupons (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL,
    tipo_desconto VARCHAR(20) NOT NULL,
    valor_desconto NUMERIC(10,2) NOT NULL,
    valor_minimo_pedido NUMERIC(10,2),
    valor_max_desconto NUMERIC(10,2),
    max_usos INTEGER,
    usos_atuais INTEGER DEFAULT 0,
    valido_de TIMESTAMP,
    valido_ate TIMESTAMP,
    id_vendedor INTEGER REFERENCES app.sellers(id),
    status VARCHAR(20) DEFAULT 'active',
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.orders (
    id SERIAL PRIMARY KEY,
    id_uuid UUID DEFAULT gen_random_uuid(),
    id_cliente INTEGER REFERENCES app.customers(id),
    data_pedido TIMESTAMP NOT NULL,
    id_status INTEGER REFERENCES app.order_statuses(id),
    id_metodo_pagamento INTEGER REFERENCES app.payment_methods(id),
    id_cupom INTEGER REFERENCES app.coupons(id),
    valor_desconto NUMERIC(10,2) DEFAULT 0,
    custo_frete NUMERIC(10,2) DEFAULT 0,
    subtotal NUMERIC(12,2) NOT NULL,
    valor_total NUMERIC(12,2) NOT NULL,
    endereco_entrega_raw TEXT,
    id_transportadora INTEGER REFERENCES app.shipping_companies(id),
    codigo_rastreamento VARCHAR(50),
    previsao_entrega DATE,
    entregue_em TIMESTAMP,
    cancelado_em TIMESTAMP,
    motivo_cancelamento TEXT,
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.order_items (
    id SERIAL PRIMARY KEY,
    id_pedido INTEGER REFERENCES app.orders(id),
    id_produto INTEGER REFERENCES app.products(id),
    id_vendedor INTEGER REFERENCES app.sellers(id),
    quantidade INTEGER NOT NULL,
    preco_unitario NUMERIC(12,2) NOT NULL,
    preco_total NUMERIC(12,2) NOT NULL,
    valor_desconto NUMERIC(10,2) DEFAULT 0,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.payments (
    id SERIAL PRIMARY KEY,
    id_uuid UUID DEFAULT gen_random_uuid(),
    id_pedido INTEGER REFERENCES app.orders(id),
    id_metodo_pagamento INTEGER REFERENCES app.payment_methods(id),
    id_transacao_gateway VARCHAR(100),
    status VARCHAR(30) NOT NULL,
    valor NUMERIC(12,2) NOT NULL,
    parcelas INTEGER DEFAULT 1,
    valor_parcela NUMERIC(12,2),
    pago_em TIMESTAMP,
    reembolsado_em TIMESTAMP,
    valor_reembolso NUMERIC(12,2),
    resposta_raw_gateway TEXT,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.reviews (
    id SERIAL PRIMARY KEY,
    id_item_pedido INTEGER REFERENCES app.order_items(id),
    id_cliente INTEGER REFERENCES app.customers(id),
    id_produto INTEGER REFERENCES app.products(id),
    id_vendedor INTEGER REFERENCES app.sellers(id),
    avaliacao INTEGER NOT NULL CHECK (avaliacao BETWEEN 1 AND 5),
    titulo VARCHAR(200),
    comentario TEXT,
    compra_verificada BOOLEAN DEFAULT TRUE,
    votos_uteis INTEGER DEFAULT 0,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.seller_payouts (
    id SERIAL PRIMARY KEY,
    id_vendedor INTEGER REFERENCES app.sellers(id),
    mes_referencia VARCHAR(7) NOT NULL,
    valor_bruto NUMERIC(12,2) NOT NULL,
    valor_comissao NUMERIC(12,2) NOT NULL,
    valor_impostos NUMERIC(12,2) NOT NULL,
    valor_liquido NUMERIC(12,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    pago_em TIMESTAMP,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_customers_status ON app.customers(status);
CREATE INDEX IF NOT EXISTS idx_customers_state ON app.customers(estado);
CREATE INDEX IF NOT EXISTS idx_products_seller ON app.products(id_vendedor);
CREATE INDEX IF NOT EXISTS idx_products_category ON app.products(id_categoria);
CREATE INDEX IF NOT EXISTS idx_products_status ON app.products(status);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON app.orders(id_cliente);
CREATE INDEX IF NOT EXISTS idx_orders_status ON app.orders(id_status);
CREATE INDEX IF NOT EXISTS idx_orders_date ON app.orders(data_pedido);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON app.order_items(id_pedido);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON app.order_items(id_produto);
CREATE INDEX IF NOT EXISTS idx_payments_order ON app.payments(id_pedido);
CREATE INDEX IF NOT EXISTS idx_reviews_product ON app.reviews(id_produto);
CREATE INDEX IF NOT EXISTS idx_reviews_seller ON app.reviews(id_vendedor);
CREATE INDEX IF NOT EXISTS idx_seller_payouts_seller ON app.seller_payouts(id_vendedor);
