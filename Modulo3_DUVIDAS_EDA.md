# Módulo 3 — Minhas Anotações de EDA
**Mindus Data School · NovaMart · PostgreSQL**

> **Como usar este arquivo:**
> 1. Rode cada bloco do `Modulo3_EDA_Script.sql` no DBeaver
> 2. Preencha as células `→` com o que você observou
> 3. Marque cada pergunta com: **[PERGUNTAR]** (pro stakeholder) | **[BUG]** (problema técnico) | **[OK]** (esperado)
> 4. No final, leve as questões marcadas como [PERGUNTAR] pra reunião com a Marina
>
> **Não deixe nenhuma célula em branco.** Se não sabe, escreva "não sei — perguntar".

---

## NÍVEL 1 — Volumetria

### 1.1 Contagem de registros
| Tabela | Registros observados | Esperado? |
|---|---|---|
| customers | | |
| sellers | | |
| products | | |
| orders | | |
| order_items | | |
| payments | | |
| reviews | | |

→ **Observação geral:**

→ **Alguma tabela surpreendeu? Por quê?**

---

### 1.2 Período dos dados
→ **Primeiro pedido:**
→ **Último pedido:**
→ **Período total coberto:**
→ **O volume é consistente ao longo dos meses?** (sim / não / observação)

---

### 1.3 Volume mensal
→ **Mês com mais pedidos:**
→ **Mês com menos pedidos:**
→ **Observei alguma sazonalidade?**

---

### 1.4 Status e métodos de pagamento disponíveis
→ **Status existentes no banco (lista completa):**

→ **Qual ID = "entregue"?**
→ **Qual ID = "cancelado"?**
→ **Métodos de pagamento ativos:**

---

## NÍVEL 2 — Auditoria de NULLs

### 2.1 NULLs em customers

| Campo | Total NULL | % | Esperado ou Bug? |
|---|---|---|---|
| cpf | | | |
| email | | | |
| telefone | | | |
| data_nascimento | | | |
| cep | | | |

→ **Campos que me preocuparam:**

→ **Pergunta(s) pro stakeholder:**

---

### 2.2 NULLs em products

→ **% de produtos com preco_custo NULL:**
→ **O que acho que significa um preco_custo NULL:** [PERGUNTAR] / [BUG] / [OK]

→ **Pergunta:**

---

### 2.3 NULLs em orders (datas)

→ **Pedidos sem delivered_at:**
→ **Pedidos sem tracking_code:**
→ **Faz sentido um pedido ter status "entregue" sem entregue_em?** [PERGUNTAR] / [BUG]

→ **Pergunta:**

---

### 2.4 NULLs em payments (por status)

| Status | Total | Sem paid_at | % sem data |
|---|---|---|---|
| approved | | | |
| pending | | | |
| outros | | | |

→ **Pagamento 'approved' sem paid_at é:** [PERGUNTAR] / [BUG] / [OK]
→ **Pergunta:**

---

### 2.5 NULLs em sellers

→ **Sellers sem taxa_comissao:**
→ **O que usar quando taxa é NULL?** [PERGUNTAR] / [OK]
→ **Pergunta:**

---

## NÍVEL 3 — Distribuições

### 3.1 Pedidos por status

→ **Distribuição que observei (top 3 status):**

→ **Parece saudável? Algum status com % inesperado?**

---

### 3.2 Receita por estado (top 5)

| Estado | Receita | Ticket Médio |
|---|---|---|
| 1. | | |
| 2. | | |
| 3. | | |
| 4. | | |
| 5. | | |

→ **O estado líder faz sentido para o perfil do marketplace?**

---

### 3.3 Distribuição de preços
→ **Faixa com mais produtos:**
→ **Produto mais caro encontrado (aprox):**
→ **Há outliers de preço que parecem erro de cadastro?**

---

### 3.4 Top 3 produtos mais vendidos

| Produto | SKU | Unidades vendidas |
|---|---|---|
| 1. | | |
| 2. | | |
| 3. | | |

→ **Esses produtos têm boa margem ou são volume sem lucro?**

---

### 3.5 Sellers por volume
→ **Há sellers com avaliação alta (≥ 4.5) e volume baixo de pedidos?** (sim / não)
→ **Lista de sellers nessa situação (se houver):**

→ **Possível causa:** [PERGUNTAR] / [Seller novo] / [Produto de nicho]

---

### 3.6 Distribuição de avaliações
→ **Nota mais frequente:**
→ **% de notas 5:**
→ **% de notas 1:**
→ **Distribuição parece real ou fabricada?**

---

## NÍVEL 4 — Consistência de FKs

| Verificação | Resultado | Problema? |
|---|---|---|
| Pedidos sem cliente | | |
| Itens sem produto | | |
| Pedidos sem pagamento | | |
| Pedidos com 2+ pagamentos | | |
| Reviews sem pedido | | |
| Produtos sem categoria | | |

→ **Alguma inconsistência de FK encontrada?**
→ **O que fazer com registros órfãos?** [PERGUNTAR] / [Descartar] / [Manter com flag]

---

## NÍVEL 5 — Anomalias Investigadas

### 5.1 Pedidos "entregues" sem data de entrega
→ **Quantidade:**
→ **% do total de pedidos entregues:**
→ **Classifico como:** [BUG] / [Regra de negócio — PERGUNTAR]
→ **Pergunta exata pro stakeholder:**

---

### 5.2 Pagamentos aprovados sem data
→ **Quantidade:**
→ **% dos pagamentos aprovados:**
→ **Classifico como:** [BUG de pipeline] / [Regra — PERGUNTAR]
→ **Pergunta exata pro stakeholder:**

---

### 5.3 Produtos com margem negativa
→ **Quantidade:**
→ **Categoria mais afetada:**
→ **São promoções intencionais ou erro de cadastro?** [PERGUNTAR] / [BUG]
→ **Pergunta exata pro stakeholder:**

---

### 5.4 CPF em múltiplos formatos

| Formato | Quantidade | % |
|---|---|---|
| Com máscara (XXX.XXX.XXX-XX) | | |
| Só números (11 dígitos) | | |
| Formato inválido | | |
| NULL | | |

→ **De onde vieram os formatos diferentes?** [PERGUNTAR]
→ **Devemos normalizar no dbt?** [PERGUNTAR] / sim / não
→ **Pergunta exata pro stakeholder:**

---

### 5.5 Emails inválidos
→ **Sem arroba:**
→ **Sem domínio:**
→ **Total inválidos:**
→ **O que fazer com esses emails no modelo?** [PERGUNTAR] / [Flag is_email_valid] / [NULL]
→ **Pergunta exata pro stakeholder:**

---

## CONSOLIDADO — Perguntas para o Stakeholder

> Copie aqui todas as perguntas marcadas como [PERGUNTAR] nos níveis anteriores.
> Esta lista é o que você vai levar pra reunião com a Marina.

1.
2.
3.
4.
5.
6.
7.
8.
9.
10.

---

## CONSOLIDADO — Bugs para Reportar à Engenharia

> Itens marcados como [BUG] que não precisam de decisão de negócio — apenas correção técnica.

1.
2.
3.

---

## CONSOLIDADO — Decisões já claras (não precisa perguntar)

> Coisas que você entendeu pelo contexto e não precisam de validação com stakeholder.

1.
2.
3.

---

*Próximo passo: leve as perguntas do consolidado pra sessão com a Marina (STAKEHOLDER_SKILL.md).*
