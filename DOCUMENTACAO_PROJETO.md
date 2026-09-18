# NovaMart - Documentacao do Projeto

## 1. Visao geral

O NovaMart e um laboratorio de marketplace brasileiro que combina:

- uma aplicacao operacional em Flask;
- PostgreSQL como banco transacional, no schema `app`;
- scripts para criar o schema, gerar dados sinteticos e simular operacao continua;
- um projeto dbt para transformar os dados em camadas analiticas;
- relatorios PDF, endpoint de metricas e ponto de integracao com Metabase.

O fluxo de negocio cobre clientes, sellers, produtos, pedidos, itens, pagamentos, entregas, avaliacoes, cupons e repasses.

## 2. Arquitetura e diagrama

```text
PostgreSQL (app) -> dbt stg -> dbt int -> dbt marts -> BI/analises
       ^                 ^
       |                 |
   Flask CRUD       pipeline agendado
       ^                 ^
       +---------- scripts de seed e ingestao
```

### Diagrama do projeto

![Diagrama da arquitetura do NovaMart](novamart_diagram.svg)

Fonte editavel: [novamart_diagram.drawio](novamart_diagram.drawio).

## 3. Aplicacao e scripts

### Aplicacao (`app/`)

- `app/app.py`: rotas Flask para dashboard, CRUD, relatorios e API de metricas.
- `app/database.py`: conexoes PostgreSQL usando `DATABASE_URL` ou `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASS`.
- `app/pdf_generator.py`: relatorios mensais em PDF com ReportLab e Matplotlib.
- `app/templates/`: interface Jinja2 para clientes, sellers, produtos, pedidos e relatorios.
- `/dashboard`: pagina preparada para embed do Metabase, usando `METABASE_SITE_URL` e `METABASE_DASHBOARD_TOKEN`.

As metricas operacionais excluem pedidos cancelados e devolvidos da receita. O relatorio mensal calcula receita, pedidos, ticket medio, categorias, sellers, pagamentos, tendencia diaria, status e novos clientes.

### Scripts (`scripts/`)

- `create_tables.py` / `create_tables.sql`: cria o schema `app`, tabelas, chaves estrangeiras e tabelas de apoio.
- `generate_seed_data.py`: gera aproximadamente 100 clientes, 15 sellers, 150 produtos, 800 pedidos e 10 cupons, com historico sintetico de um ano.
- `continuous_ingestion.py`: cria novos pedidos e avanca status, pagamentos, entregas e avaliacoes; pode rodar uma vez ou em loop.
- `run_pipeline.py`: executa ingestao, `dbt build` por camada, `dbt docs generate`, grava logs e envia alerta ao Discord em caso de falha.
- `inject_bad_data.py`: injeta cenarios didaticos de falha para demonstrar os testes de qualidade.
- `BUSINESS_RULES.md`: regras detalhadas e distribuicoes dos dados sinteticos.

### Execucao local

Pre-requisitos: Python, PostgreSQL, ambiente virtual, dependencias de `requirements.txt` e `dbt-core` com adaptador PostgreSQL disponiveis no ambiente. Configure um `.env` fora do versionamento.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python scripts/create_tables.py
python scripts/generate_seed_data.py
python app/app.py
```

Em outro processo, para simular atividade:

```bash
python scripts/continuous_ingestion.py --orders 5
python scripts/continuous_ingestion.py --orders 5 --loop 60
```

Para executar o fluxo completo:

```bash
python scripts/run_pipeline.py
python scripts/run_pipeline.py --full-refresh
```

O pipeline espera os binarios em `/home/ubuntu/novamart/venv/bin/` e o projeto dbt em `novamart_analytics/`; ajuste os caminhos em `scripts/run_pipeline.py` quando o ambiente for diferente.

## 4. Projeto dbt (`novamart_analytics/`)

### Fonte e camadas

- **Source `app`**: tabelas transacionais `orders`, `customers`, `products`, `order_items`, `payments`, `reviews`, `sellers`, status e categorias.
- **`models/stg`**: views de padronizacao, com nomes analiticos e conversao de tipos, por exemplo `data_pedido` para data.
- **`models/int`**: modelos incrementais com chave unica e reprocessamento aproximado dos ultimos tres dias:
  - `int_pedidos_enriquecido`: deduplicacao e `delivered_at_missing`;
  - `int_pagamentos_enriquecido`: `pago_em_ajustado` e `paid_at_missing`;
  - `int_itens_pedido_enriquecido`: receita, comissao, margem e `has_negative_margin`.
- **`models/marts`**: tabelas prontas para consumo:
  - `fct_itens_pedido`: fato de itens com receita, comissao, margem, status e categoria;
  - `rpt_pareto_produtos`: ranking de receita por produto e classificacao Pareto A/B (ate 80% acumulado = A).

Materializacao configurada em `dbt_project.yml`: `stg` como view, `int` como incremental e `marts` como table.

Comandos principais, executados dentro de `novamart_analytics/`:

```bash
dbt debug
dbt build --select path:models/stg
dbt build --select path:models/int
dbt build --select path:models/marts
dbt test
dbt docs generate
dbt docs serve
```

## 5. Regras de negocio e qualidade de dados

O dado sintetico representa problemas que existem em operacoes reais: documentos e telefones com formatos variados, enderecos livres, custos maiores que o preco, rastreio ou entrega ausentes, e pagamentos aprovados sem `pago_em`. A regra e preservar o registro, sinalizar a excecao e tornar a decisao analitica auditavel.

### Controles implementados

- PostgreSQL: chaves primarias e estrangeiras entre clientes, pedidos, itens, produtos, sellers, pagamentos e dimensoes.
- dbt: `not_null` e `unique` para `stg_orders.id_pedido`.
- dbt: valores permitidos para status de pedido e pagamento.
- dbt: teste de relacionamento de `stg_order_items.id_produto` com `stg_products`.
- dbt: teste singular para validar `preco_total = quantidade * preco_unitario`.
- Transformacoes: deduplicacao de pedidos, janela incremental de tres dias e `on_schema_change: sync_all_columns` em pedidos.
- Tratamento sem descarte: `delivered_at_missing`, `paid_at_missing` e `has_negative_margin` preservam a linha e identificam o problema.

### Decisoes analiticas

- Pedido entregue sem data: entra nas metricas de receita e recebe `delivered_at_missing`.
- Pagamento aprovado sem data: e considerado pago, usa `criado_em` como proxy em `pago_em_ajustado` e recebe `paid_at_missing`.
- Margem negativa: nao e corrigida automaticamente; deve ser investigada como promocao ou erro de cadastro.
- Receita, comissao e margem sao calculadas no nivel do item para permitir agregacao por produto, categoria e seller.

### Limites atuais e pontos de evolucao

- A cobertura de testes ainda esta concentrada em pedidos, pagamentos e relacionamento de itens; adicionar testes de unicidade, nulos, valores e freshness para todas as fontes.
- `int_pagamentos_enriquecido` e algumas flags intermediarias ainda nao alimentam um mart dedicado; publicar essas excecoes em uma tabela de qualidade facilitaria monitoramento.
- O teste de status de pagamento inclui `chargeback_iniciado`; revisar a lista quando esse status for usado apenas como dado invalido no exercicio didatico.
- O teste singular possui uma excecao explicita para o pedido `87`; substituir a excecao por correcao da origem ou regra documentada antes de uso produtivo.
- Os dados sao sinteticos. Resultados de negocio servem para demonstracao, validacao de pipeline e treinamento, nao para decisoes reais.

## 6. Operacao e observabilidade

O `run_pipeline.py` interrompe as camadas seguintes quando uma etapa falha, salva `logs/pipeline_<timestamp>.log` e envia um resumo ao Discord via `DISCORD_WEBHOOK_URL`. O fluxo recomendado e: corrigir a origem, executar novamente a camada afetada, validar `dbt test` e somente entao atualizar os marts e a documentacao.

Segredos devem permanecer em variaveis de ambiente. Antes de producao, trocar a chave fixa de desenvolvimento do Flask, restringir privilegios do usuario PostgreSQL, usar HTTPS e executar a aplicacao por Gunicorn atras de proxy reverso.