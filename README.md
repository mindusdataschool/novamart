# NovaMart

NovaMart é uma aplicação web em Flask para demonstrar um marketplace e-commerce brasileiro com operações de cadastro, gestão e análise de dados. O projeto reúne um backend relacional em PostgreSQL, uma interface web para CRUD operacional e recursos de relatórios em PDF com métricas mensais.

Documentação consolidada do projeto: [DOCUMENTACAO_PROJETO.md](DOCUMENTACAO_PROJETO.md).

A aplicação foi pensada como um laboratório de dados e analytics: além de servir como portal de negócio, ela possui dados sintéticos realistas, scripts de ingestão contínua e um modelo de dados preparado para dashboards e análises.

---

## 1) Panorama geral da aplicação

### Objetivo

O projeto simula um marketplace com:
- clientes
- sellers/vendedores
- produtos
- pedidos
- pagamentos
- avaliações
- cupons
- repasses aos sellers

A interface permite visualizar indicadores de negócio, navegar por cadastros e gerar relatórios executivos em PDF.

### Funcionalidades principais

- Dashboard principal com métricas resumidas:
  - total de pedidos
  - receita total
  - clientes cadastrados
  - sellers ativos
  - produtos ativos
  - avaliação média

- CRUD operacional para:
  - clientes
  - sellers
  - produtos
  - pedidos

- Página de relatórios com filtro por mês/ano para gerar PDF mensal

- Endpoint de API para métricas usadas na geração de relatórios

- Página preparada para embed de painel analítico (Metabase)

- Scripts para popular o banco com dados sintéticos e simular ingestão contínua

### Arquitetura geral

- Frontend: Flask + Jinja2 + templates HTML
- Backend: Flask routes e consultas SQL em PostgreSQL
- Relatórios: ReportLab + Matplotlib
- Dados: PostgreSQL com schema dedicado `app`
- Scripts auxiliares:
  - geração de seed data
  - criação de tabelas
  - ingestão contínua simulada

### Estrutura do repositório

- `app/` – aplicação Flask e templates
- `scripts/` – DDL, seed data, ingestão contínua e regras de negócio
- `requirements.txt` – dependências do projeto

![Arquitetura do pipeline](novamart_diagram.svg)

---

## 2) Documentação breve dos dados backend

### Modelo de dados

O backend utiliza PostgreSQL e organiza as tabelas no schema `app`.

### Principais entidades

- `app.customers` – clientes do marketplace
- `app.sellers` – vendedores/sellers
- `app.products` – produtos cadastrados pelos sellers
- `app.orders` – pedidos realizados
- `app.order_items` – itens de cada pedido
- `app.payments` – pagamentos associados aos pedidos
- `app.reviews` – avaliações de produtos e vendedores
- `app.coupons` – cupons de desconto
- `app.seller_payouts` – repasses financeiros aos sellers
- `app.platform_config` – parâmetros de negócio e configuração da plataforma

### Tabelas de apoio e lookup

- `app.seller_categories`
- `app.product_categories`
- `app.product_subcategories`
- `app.shipping_companies`
- `app.payment_methods`
- `app.order_statuses`

### Relações principais

- Um cliente pode ter vários pedidos
- Um pedido possui vários itens
- Cada item pertence a um produto e um seller
- Um pedido possui um pagamento associado
- Avaliações ligam-se a itens entregues
- Sellers podem ter pagamentos mensais (`seller_payouts`)

### Dados sintéticos e qualidade

Os dados gerados são intencionalmente realistas e incluem cenários de qualidade de dados que podem ser usados em análises e testes, por exemplo:
- CPF/CNPJ com formatos variados
- endereços em texto livre
- SKUs com padrão parseável
- pagamentos com status inconsistentes em alguns cenários
- pedidos com rastreamento ou datas ausentes em situações específicas

### Scripts backend relevantes

- `scripts/create_tables.py` ou `scripts/create_tables.sql` – cria o schema e as tabelas
- `scripts/generate_seed_data.py` – popula o banco com dados sintéticos
- `scripts/continuous_ingestion.py` – simula atividade contínua de pedidos, status, avaliações e estoque
- `scripts/BUSINESS_RULES.md` – documentação das regras de negócio e padrões de dados

---

## 3) Como rodar a aplicação em uma EC2

Abaixo está um fluxo simples para rodar a aplicação em uma instância EC2 Ubuntu (22.04/24.04) com PostgreSQL.

### 3.1 Pré-requisitos

- EC2 com Ubuntu
- porta 5000 liberada no security group (ou use um proxy/reverso se quiser expor em 80/443)
- acesso SSH à instância

### 3.2 Instalar dependências do sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv postgresql postgresql-contrib unzip curl
```

### 3.3 Configurar PostgreSQL

Entre como usuário `postgres` e crie o banco e o usuário da aplicação:

```bash
sudo -u postgres psql
```

Dentro do `psql`:

```sql
CREATE USER novamart_user WITH PASSWORD 'TroqueEssaSenha123!';
CREATE DATABASE nova_market OWNER novamart_user;
ALTER USER novamart_user WITH SUPERUSER;
\q
```

> Em ambientes de produção, prefira senhas fortes e restrinja permissões conforme necessário.

### 3.4 Clonar o projeto

```bash
cd /home/ubuntu
git clone <url-do-repositorio> novamart
cd novamart
```

### 3.5 Criar ambiente virtual e instalar dependências

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.6 Configurar variáveis de ambiente

O projeto aceita `DATABASE_URL` ou as variáveis `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASS`.

Exemplo com `DATABASE_URL`:

```bash
export DATABASE_URL="postgresql://novamart_user:TroqueEssaSenha123!@127.0.0.1:5432/nova_market"
```

Ou com variáveis separadas:

```bash
export DB_HOST=127.0.0.1
export DB_PORT=5432
export DB_NAME=nova_market
export DB_USER=novamart_user
export DB_PASS='TroqueEssaSenha123!'
```

### 3.7 Criar o schema e as tabelas

```bash
python scripts/create_tables.py
```

### 3.8 Popular o banco com dados iniciais

```bash
python scripts/generate_seed_data.py
```

### 3.9 Iniciar a aplicação

```bash
python app/app.py
```

A aplicação ficará disponível em:

```text
http://<IP-DA-EC2>:5000
```

### 3.10 Executar ingestão contínua (opcional)

Se você quiser simular atividade contínua do marketplace:

```bash
python scripts/continuous_ingestion.py --orders 5
```

Para rodar em loop:

```bash
python scripts/continuous_ingestion.py --orders 5 --loop 60
```

### 3.11 Recomendação para produção

Para uso real em produção, é melhor rodar a aplicação por trás de um proxy reverso como Nginx e um gerenciador de processo como `systemd` ou `gunicorn`.

Exemplo de execução com `gunicorn` (opcional):

```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 app.app:app
```

---

## 4) Pontos de atenção

- O projeto usa um `secret_key` fixo em desenvolvimento; em produção, substitua por um valor seguro via variável de ambiente.
- O banco precisa estar acessível da EC2.
- A aplicação foi construída como uma demonstração/ambiente de analytics e não substitui uma plataforma de e-commerce pronta para produção.

---

## 5) Resumo rápido

A NovaMart é uma aplicação Flask com backend PostgreSQL voltada para:
- gestão operacional de marketplace
- visualização de indicadores
- geração de relatórios PDF
- simulação de dados e ingestão contínua

Se você quiser evoluir o projeto, os próximos passos naturais são:
- adicionar autenticação de usuários
- integrar com um painel BI real
- publicar em produção com Nginx + HTTPS
- incluir testes automatizados e CI/CD
