# NovaMart - Regras de Negócio dos Dados Seed

## Visão Geral

O NovaMart é um **marketplace e-commerce** fictício brasileiro. Múltiplos sellers cadastram produtos e clientes compram através da plataforma. A plataforma cobra comissão, processa pagamentos e gerencia entregas.

---

## 1. Tabelas e Relacionamentos

### Diagrama de Entidades

```
seller_categories (1) ──< (N) sellers (1) ──< (N) products
                                    │                  │
                                    │       product_categories (1) ──< products
                                    │       product_subcategories (1) ──< products
                                    │
                                    ├──< (N) seller_payouts
                                    └──< (N) order_items ──> orders
                                                               │
customers (1) ──< (N) orders ──< (N) order_items              │
                     │              │                           │
                     ├──< payments  └──< reviews               │
                     │                                         │
                     ├──> order_statuses                       │
                     ├──> payment_methods                      │
                     ├──> shipping_companies                   │
                     └──> coupons                              │
                                                               │
                          platform_config (parametrização)
```

---

## 2. Regras por Tabela

### 2.1 `app.customers` — Clientes

| Campo | Regra | Problema de Dados Intencional |
|-------|-------|-------------------------------|
| `full_name` | Nome completo do cliente | — |
| `email` | Email do cliente | **5% com problemas**: sem ponto no domínio (`@gmailcom`), emails incompletos (`user@`), espaços extras, vazios ou NULL |
| `phone` | Telefone de contato | **Formatos variados para regex**: `(11) 91234-5678`, `11912345678`, `+5511912345678`, `11 912345678`, `+55 11 91234 5678` |
| `cpf` | CPF do cliente | **70% formatado** (`123.456.789-00`), **20% apenas dígitos** (`12345678900`), **10% com problemas**: formato parcial, espaços extras ou NULL (estrangeiros) |
| `birth_date` | Data de nascimento | 18-75 anos |
| `address_raw` | Endereço completo como string | **4 formatos diferentes**: `Rua X, 123, Apt 45, Bairro, Cidade - UF, CEP: 12345-678` / `Rua X, 123, Bairro, Cidade/UF` / `Rua X 123 - Bairro - Cidade UF 12345678` / `Rua X \| 123 \| Bairro \| Cidade \| UF` |
| `status` | Status do cliente | **85% active, 10% inactive, 5% blocked** |
| `referral_code` | Código de indicação do cliente | 30% possuem código |
| `referred_by_customer_id` | ID de quem indicou | 15% são indicados. FK para `customers.id` |

**Tratamentos necessários no dbt:**
- Regex para padronizar CPF (remover tudo que não é dígito)
- Regex para padronizar telefone (formato `+55XXXXXXXXXXX`)
- Cálculo de idade a partir de `birth_date`
- Classificação em faixa etária
- Flag de indicação

---

### 2.2 `app.sellers` — Sellers/Vendedores

| Campo | Regra | Observação |
|-------|-------|------------|
| `company_name` | Razão social | — |
| `trade_name` | Nome fantasia | Sufixos: Store, Shop, Brasil, Online, Digital |
| `cnpj` | CNPJ | **75% formatado** (`12.345.678/0001-00`), **25% apenas dígitos** |
| `category_id` | FK para `seller_categories` | 10 categorias possíveis |
| `commission_rate` | Taxa de comissão individual | **Base 15%**, 20% dos sellers têm taxa negociada (8-12%), 10% têm taxa premium (18-25%) |
| `rating` | Avaliação média (1-5) | Distribuição normal centrada em 4.0 (σ=0.7) |
| `status` | Status | **80% active, 12% inactive, 8% suspended** |

**Tratamentos necessários no dbt:**
- Regex para CNPJ
- Classificação de rating (Excelente >= 4.5, Muito Bom >= 4.0, etc.)
- Cálculo de dias desde onboarding

---

### 2.3 `app.products` — Produtos

| Campo | Regra | Problema de Dados Intencional |
|-------|-------|-------------------------------|
| `seller_id` | FK para sellers | — |
| `sku` | Código no formato `CAT-SUB-XXXXX` | **Parseável com `split_part`**: 3 primeiras letras da categoria + 3 da subcategoria + sequencial |
| `price` | Preço de venda | R$ 5 a R$ 9.000 dependendo da subcategoria |
| `cost_price` | Preço de custo | **5% com custo > preço** (margem negativa — anomalia intencional). **10% NULL** (custo não registrado) |
| `stock_quantity` | Quantidade em estoque | Distribuição exponencial (média 50). **8% com estoque = 0** |
| `third_party_id` | ID de fornecedor terceiro | **70% NULL** (produto próprio do seller). **30% preenchido** (produto de terceiro) |
| `third_party_name` | Nome do fornecedor terceiro | **Quando third_party_id preenchido**: maioria tem nome, mas **alguns são NULL** (anomalia: tem ID sem nome) |
| `weight_kg` | Peso em kg | 10% NULL |
| `is_digital` | Se é produto digital | True apenas para livros e games |
| `status` | Status | **75% active, 10% inactive, 10% discontinued, 5% pending_review** |

**Tratamentos necessários no dbt:**
- Análise de margem (percentual e classificação)
- Flag de anomalia: custo > preço
- Flag de anomalia: third_party_id sem third_party_name
- Parsing do SKU
- Classificação de estoque (sem estoque, baixo, médio, alto)

---

### 2.4 `app.orders` — Pedidos

| Campo | Regra | Problema de Dados Intencional |
|-------|-------|-------------------------------|
| `customer_id` | FK clientes | — |
| `order_date` | Data do pedido | Jul/2024 a Dez/2025 |
| `status_id` | FK para `order_statuses` | Progressão: pending → payment_confirmed → processing → shipped → delivered (ou cancelled/refunded/returned) |
| `coupon_id` | FK para cupons | **80% NULL** (sem cupom). 20% usam cupom |
| `discount_amount` | Desconto do cupom | 0 quando sem cupom |
| `shipping_cost` | Frete | **R$ 0 quando subtotal >= R$ 150** (frete grátis). Caso contrário, R$ 8-45 |
| `tracking_code` | Código de rastreio | **NULL** para status < shipped. **3% dos status "delivered" têm tracking NULL** (anomalia) |
| `delivered_at` | Data de entrega | **5% dos status "delivered" têm delivered_at NULL** (anomalia) |
| `cancelled_at` | Data de cancelamento | Preenchido quando cancelled/refunded |
| `cancellation_reason` | Motivo | **Alguns cancelamentos sem motivo** (NULL — anomalia) |

**Distribuição de status baseada na idade do pedido:**
- Pedidos > 30 dias: 70% entregue, 8% cancelado
- Pedidos 14-30 dias: 35% entregue, 30% enviado
- Pedidos 5-14 dias: 30% processando, 25% enviado
- Pedidos < 5 dias: 40% pendente, 30% pagamento confirmado

---

### 2.5 `app.order_items` — Itens do Pedido

| Campo | Regra |
|-------|-------|
| `order_id` | FK para orders |
| `product_id` | FK para products |
| `seller_id` | FK para sellers (desnormalizado para facilitar consultas) |
| `quantity` | 1-5 (60% compram 1 unidade) |
| `unit_price` | Preço unitário no momento da compra. **15% com variação** de ±15% do preço atual do produto |
| `discount_amount` | Desconto no item. 20% dos itens têm algum desconto (0-10% do total) |

**Items por pedido:** 1-6, distribuição: 35% têm 1, 30% têm 2, 18% têm 3, etc.

---

### 2.6 `app.payments` — Pagamentos

| Campo | Regra | Problema de Dados Intencional |
|-------|-------|-------------------------------|
| `payment_method_id` | FK métodos | Distribuição: 35% crédito, 35% PIX, 12% boleto, 10% débito, 8% wallet |
| `gateway_transaction_id` | ID da transação no gateway | NULL quando status = pending |
| `status` | Status do pagamento | Mapeado ao status do pedido (pending, approved, cancelled, refunded) |
| `installments` | Parcelas | 1-12 (apenas para crédito). Distribuição realista |
| `paid_at` | Data de pagamento | **3% dos pagamentos "approved" têm paid_at NULL** (anomalia) |
| `refunded_at` | Data do reembolso | Preenchido em refunded. 80% reembolso total, 20% parcial |
| `gateway_raw_response` | JSON do gateway | String JSON com gateway, tid, status, amount, installments. **Parseável com regex/JSON functions**. Gateways: pagarme, mercadopago, stripe, asaas |

---

### 2.7 `app.reviews` — Avaliações

| Campo | Regra |
|-------|-------|
| `order_item_id` | FK para order_items. **Apenas para pedidos entregues** |
| `rating` | 1-5. Distribuição: 42% nota 5, 30% nota 4, 15% nota 3, 8% nota 2, 5% nota 1 |
| `title` | Título da avaliação. Varia por nota. **40% NULL** |
| `comment` | Texto. **30% NULL** |
| `is_verified_purchase` | Se é compra verificada. **95% true** |

**Cobertura:** ~40% dos itens entregues recebem avaliação.

---

### 2.8 `app.coupons` — Cupons de Desconto

| Campo | Regra |
|-------|-------|
| `code` | Formato: PREFIXO + 2 dígitos (ex: NOVA15, PROMO22) |
| `discount_type` | `percentage` ou `fixed` |
| `discount_value` | 5-30% para percentual, R$ 10-100 para fixo |
| `min_order_value` | Valor mínimo do pedido. **30% NULL** (sem mínimo) |
| `max_discount_amount` | Desconto máximo (apenas para percentual) |
| `seller_id` | FK sellers. **70% NULL** (cupom geral do marketplace) |

---

### 2.9 `app.seller_payouts` — Repasses aos Sellers

| Campo | Regra |
|-------|-------|
| `reference_month` | Formato `YYYY-MM` |
| `gross_amount` | Receita bruta do seller no mês |
| `commission_amount` | Comissão retida (gross × commission_rate do seller) |
| `tax_amount` | Imposto (gross × SELLER_TAX_RATE) |
| `net_amount` | Valor líquido (gross - commission - tax) |
| `status` | `paid` para meses anteriores a Nov/2025, `pending` para meses mais recentes |

---

### 2.10 `app.platform_config` — Configurações da Plataforma

| Key | Value | Descrição |
|-----|-------|-----------|
| `MARKETPLACE_COMMISSION_RATE` | `0.15` | Taxa de comissão padrão (15%) |
| `SELLER_TAX_RATE` | `0.0825` | Alíquota de imposto sobre vendas (8.25%) |
| `FREE_SHIPPING_THRESHOLD` | `150.00` | Valor mínimo para frete grátis (R$ 150) |
| `MAX_INSTALLMENTS_NO_INTEREST` | `3` | Máximo de parcelas sem juros |
| `INTEREST_RATE_PER_INSTALLMENT` | `0.0199` | Taxa de juros por parcela (1.99%) |
| `REVIEW_BONUS_RATING_THRESHOLD` | `4.5` | Rating mínimo para bônus do seller |
| `SELLER_BONUS_PERCENTAGE` | `0.02` | Percentual de bônus (2%) |
| `REFUND_WINDOW_DAYS` | `30` | Prazo para reembolso (30 dias) |
| `MAX_COUPON_DISCOUNT_PERCENTAGE` | `0.30` | Desconto máximo por cupom (30%) |
| `PAYOUT_PROCESSING_DAYS` | `15` | Dias para processar repasse |

---

## 3. Tabelas de Lookup (Dimensões Estáticas)

### 3.1 `app.seller_categories` (10 registros)
Eletrônicos, Moda e Vestuário, Casa e Decoração, Esportes e Lazer, Saúde e Beleza, Alimentos e Bebidas, Livros e Papelaria, Brinquedos, Automotivo, Pet Shop

### 3.2 `app.product_categories` (15 registros)
Smartphones, Informática, Eletrodomésticos, Moda Feminina, Moda Masculina, Calçados, Móveis, Decoração, Esportes, Beleza, Livros, Brinquedos e Games, Automotivo, Pet, Alimentos

### 3.3 `app.product_subcategories` (47 registros)
2-4 subcategorias por categoria (ex: Smartphones → Celulares, Capas e Películas, Carregadores)

### 3.4 `app.shipping_companies` (5 registros)
Correios PAC (8d), Correios SEDEX (3d), Jadlog (5d), Loggi (4d), Azul Cargo (6d)

### 3.5 `app.payment_methods` (5 registros)
Cartão de Crédito (12x), Cartão de Débito (1x), PIX (1x), Boleto (1x), Carteira Digital (1x)

### 3.6 `app.order_statuses` (8 registros)
Pendente → Pagamento Confirmado → Em Processamento → Enviado → Entregue / Cancelado / Reembolsado / Devolvido

---

## 4. Volume de Dados Iniciais

| Tabela | Registros |
|--------|-----------|
| customers | ~600 |
| sellers | ~45 |
| products | ~350 |
| orders | ~2.500 |
| order_items | ~5.000-8.000 |
| payments | ~2.500 |
| reviews | ~800-1.200 |
| coupons | ~40 |
| seller_payouts | ~200-400 |

---

## 5. Ingestão Contínua (`continuous_ingestion.py`)

O script simula atividade real do marketplace a cada execução:

| Ação | Volume por Ciclo |
|------|-----------------|
| Novos pedidos | 5 (configurável com `--orders`) |
| Progressão de status | Até 15 pedidos avançam no pipeline |
| Novas avaliações | Até 5 reviews para pedidos entregues |
| Novos clientes | 1-3 clientes (30% de chance) |
| Atualização de estoque | Decrementa produtos vendidos |

**Regras específicas da ingestão contínua:**
- Pedidos PIX são automaticamente aprovados na criação
- Outros métodos ficam como "pending" e são aprovados na próxima execução (85%) ou cancelados (15%)
- Status progride: pending → confirmed (30min) → processing (1h) → shipped (4h) → delivered (2 dias)
- Reviews são geradas apenas para itens entregues sem review anterior

---

## 6. Cálculos de Negócio (dbt)

### 6.1 Comissão da Plataforma
```
platform_commission = total_amount × MARKETPLACE_COMMISSION_RATE (15%)
```
Cada seller pode ter taxa negociada (`sellers.commission_rate`).

### 6.2 Imposto sobre Seller
```
seller_tax = total_amount × SELLER_TAX_RATE (8.25%)
```

### 6.3 Receita Líquida do Seller
```
seller_net = total_amount × (1 - commission_rate - SELLER_TAX_RATE)
```

### 6.4 Bônus de Rating
```
if seller.avg_rating >= REVIEW_BONUS_RATING_THRESHOLD (4.5):
    bonus = gross_revenue × SELLER_BONUS_PERCENTAGE (2%)
```

### 6.5 GMV (Gross Merchandise Value)
Soma de `total_amount` de pedidos não cancelados/reembolsados.

### 6.6 Frete Grátis
```
if subtotal >= FREE_SHIPPING_THRESHOLD (R$ 150):
    shipping_cost = 0
```

---

## 7. Flags de Qualidade de Dados

Para uso em validação, testes dbt e dashboards de data quality:

| Flag | Tabela | Condição |
|------|--------|----------|
| `flag_delivered_no_date` | orders/fact_sales | `status = delivered AND delivered_at IS NULL` |
| `flag_delivered_no_tracking` | orders/fact_sales | `status = delivered AND tracking_code IS NULL` |
| `flag_payment_approved_no_date` | payments/fact_sales | `payment.status = approved AND paid_at IS NULL` |
| `has_third_party_data_issue` | products/dim_products | `third_party_id IS NOT NULL AND third_party_name IS NULL` |
| `margin_tier = NEGATIVA` | products/dim_products | `cost_price > price` |
| `cancellation_reason IS NULL` | orders | Pedido cancelado sem motivo |
| Email inválido | customers | Emails com formato incorreto |
| CPF NULL | customers | Clientes sem CPF (estrangeiros) |

---

## 8. Padrões para Regex (Prática)

| Dado | Padrão | Uso |
|------|--------|-----|
| CPF | `[^0-9]` → remover | Padronizar para 11 dígitos |
| CNPJ | `[^0-9]` → remover | Padronizar para 14 dígitos |
| Telefone | Extrair DDD + número | Padronizar para `+55XXXXXXXXXXX` |
| SKU | `split_part(sku, '-', N)` | Extrair componentes CAT/SUB/SEQ |
| Endereço | Regex para extrair CEP, estado, bairro | Parsing de endereços |
| Gateway JSON | `gateway_raw_response` | Extrair gateway, tid, status via regex ou `::json` |
