"""
NovaMart - Seed Data Generator
===============================
Generates realistic seed data for all backend tables.

Business Rules & Data Quality Patterns:
- See BUSINESS_RULES.md for full documentation
- Intentional data quality issues for dbt treatment:
  * CPFs with mixed formatting (with/without dots/dashes)
  * Phones with varied formats (+55, (XX), raw digits)
  * Addresses as raw strings to parse with regex
  * SKUs with parseable pattern: CAT-SUB-XXXXX
  * Some products with preco_custo > preco (margin issue)
  * Tracking codes NULL before shipping
  * entregue_em NULL on some 'delivered' orders (data issue)
  * Payments approved but pago_em NULL (inconsistency)
  * id_externo NULL for own-inventory products
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import psycopg2
from faker import Faker

fake = Faker("pt_BR")
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# ======================== CONFIGURATION ========================

import os

# Try to load .env for local development if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# DB configuration: prefer DATABASE_URL, otherwise use DB_* environment variables.
_DATABASE_URL = os.getenv("DATABASE_URL")
if _DATABASE_URL:
    DB_CONFIG = {"dsn": _DATABASE_URL}
else:
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "dbname": os.getenv("DB_NAME", "nova_market"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASS", ""),
    }

# Volume settings
NUM_CUSTOMERS = 100
NUM_SELLERS = 15
NUM_PRODUCTS = 150
NUM_ORDERS = 800
NUM_COUPONS = 10

# Date range for historical data
START_DATE = datetime(2024, 7, 1)
END_DATE = datetime(2025, 12, 31)

# Brazilian states with population weight
BR_STATES = {
    "SP": 0.22, "RJ": 0.10, "MG": 0.10, "BA": 0.07, "PR": 0.06,
    "RS": 0.06, "PE": 0.05, "CE": 0.04, "PA": 0.04, "SC": 0.04,
    "MA": 0.03, "GO": 0.03, "AM": 0.02, "PB": 0.02, "ES": 0.02,
    "RN": 0.02, "AL": 0.02, "MT": 0.01, "PI": 0.01, "DF": 0.01,
    "MS": 0.01, "SE": 0.01, "RO": 0.01, "TO": 0.005, "AC": 0.005,
    "AP": 0.003, "RR": 0.002,
}

# ======================== LOOKUP DATA ========================

SELLER_CATEGORIES = [
    (1, "Eletrônicos", "Equipamentos eletrônicos e informática"),
    (2, "Moda e Vestuário", "Roupas, calçados e acessórios"),
    (3, "Casa e Decoração", "Móveis, decoração e utensílios"),
    (4, "Esportes e Lazer", "Artigos esportivos e de lazer"),
    (5, "Saúde e Beleza", "Cosméticos, perfumaria e cuidados pessoais"),
    (6, "Alimentos e Bebidas", "Produtos alimentícios em geral"),
    (7, "Livros e Papelaria", "Livros, materiais escolares e escritório"),
    (8, "Brinquedos", "Brinquedos e jogos infantis"),
    (9, "Automotivo", "Peças, acessórios e ferramentas veiculares"),
    (10, "Pet Shop", "Produtos para animais de estimação"),
]

PRODUCT_CATEGORIES = [
    (1, "Smartphones e Telefonia", "smartphones-telefonia"),
    (2, "Informática", "informatica"),
    (3, "Eletrodomésticos", "eletrodomesticos"),
    (4, "Moda Feminina", "moda-feminina"),
    (5, "Moda Masculina", "moda-masculina"),
    (6, "Calçados", "calcados"),
    (7, "Móveis", "moveis"),
    (8, "Decoração", "decoracao"),
    (9, "Esportes", "esportes"),
    (10, "Beleza", "beleza"),
    (11, "Livros", "livros"),
    (12, "Brinquedos e Games", "brinquedos-games"),
    (13, "Automotivo", "automotivo"),
    (14, "Pet", "pet"),
    (15, "Alimentos", "alimentos"),
]

PRODUCT_SUBCATEGORIES = [
    # Smartphones
    (1, 1, "Celulares", "celulares"),
    (2, 1, "Capas e Películas", "capas-peliculas"),
    (3, 1, "Carregadores", "carregadores"),
    # Informática
    (4, 2, "Notebooks", "notebooks"),
    (5, 2, "Periféricos", "perifericos"),
    (6, 2, "Componentes", "componentes"),
    (7, 2, "Monitores", "monitores"),
    # Eletrodomésticos
    (8, 3, "Geladeiras", "geladeiras"),
    (9, 3, "Máquinas de Lavar", "maquinas-lavar"),
    (10, 3, "Micro-ondas", "micro-ondas"),
    (11, 3, "Aspiradores", "aspiradores"),
    # Moda Feminina
    (12, 4, "Vestidos", "vestidos"),
    (13, 4, "Blusas", "blusas"),
    (14, 4, "Calças", "calcas-femininas"),
    # Moda Masculina
    (15, 5, "Camisetas", "camisetas"),
    (16, 5, "Calças", "calcas-masculinas"),
    (17, 5, "Jaquetas", "jaquetas"),
    # Calçados
    (18, 6, "Tênis", "tenis"),
    (19, 6, "Sandálias", "sandalias"),
    (20, 6, "Botas", "botas"),
    # Móveis
    (21, 7, "Sofás", "sofas"),
    (22, 7, "Mesas", "mesas"),
    (23, 7, "Cadeiras", "cadeiras"),
    # Decoração
    (24, 8, "Quadros", "quadros"),
    (25, 8, "Almofadas", "almofadas"),
    (26, 8, "Iluminação", "iluminacao"),
    # Esportes
    (27, 9, "Fitness", "fitness"),
    (28, 9, "Camping", "camping"),
    (29, 9, "Ciclismo", "ciclismo"),
    # Beleza
    (30, 10, "Maquiagem", "maquiagem"),
    (31, 10, "Skincare", "skincare"),
    (32, 10, "Perfumes", "perfumes"),
    # Livros
    (33, 11, "Ficção", "ficcao"),
    (34, 11, "Técnicos", "tecnicos"),
    (35, 11, "Infantis", "infantis"),
    # Brinquedos
    (36, 12, "Educativos", "educativos"),
    (37, 12, "Games", "games"),
    (38, 12, "Bonecas e Bonecos", "bonecas-bonecos"),
    # Automotivo
    (39, 13, "Pneus", "pneus"),
    (40, 13, "Acessórios", "acessorios-auto"),
    (41, 13, "Ferramentas", "ferramentas"),
    # Pet
    (42, 14, "Ração", "racao"),
    (43, 14, "Brinquedos Pet", "brinquedos-pet"),
    (44, 14, "Higiene Pet", "higiene-pet"),
    # Alimentos
    (45, 15, "Orgânicos", "organicos"),
    (46, 15, "Bebidas", "bebidas"),
    (47, 15, "Snacks", "snacks"),
]

SHIPPING_COMPANIES = [
    (1, "Correios - PAC", "https://rastreamento.correios.com.br/?objetos={code}", 8),
    (2, "Correios - SEDEX", "https://rastreamento.correios.com.br/?objetos={code}", 3),
    (3, "Jadlog", "https://www.jadlog.com.br/tracking?code={code}", 5),
    (4, "Loggi", "https://www.loggi.com/rastreio/{code}", 4),
    (5, "Azul Cargo", "https://www.azulcargo.com.br/rastreio/{code}", 6),
]

PAYMENT_METHODS = [
    (1, "Cartão de Crédito", "credit_card", 12),
    (2, "Cartão de Débito", "debit_card", 1),
    (3, "PIX", "pix", 1),
    (4, "Boleto Bancário", "boleto", 1),
    (5, "Carteira Digital", "wallet", 1),
]

ORDER_STATUSES = [
    (1, "Pendente", "pending", "Pedido criado, aguardando pagamento", 1),
    (2, "Pagamento Confirmado", "payment_confirmed", "Pagamento aprovado", 2),
    (3, "Em Processamento", "processing", "Pedido sendo preparado", 3),
    (4, "Enviado", "shipped", "Pedido despachado para entrega", 4),
    (5, "Entregue", "delivered", "Pedido entregue ao cliente", 5),
    (6, "Cancelado", "cancelled", "Pedido cancelado", 6),
    (7, "Reembolsado", "refunded", "Valor devolvido ao cliente", 7),
    (8, "Devolvido", "returned", "Produto retornado pelo cliente", 8),
]

PLATFORM_CONFIGS = [
    ("MARKETPLACE_COMMISSION_RATE", "0.15", "Taxa de comissão padrão do marketplace (15%)"),
    ("SELLER_TAX_RATE", "0.0825", "Alíquota de imposto sobre vendas do seller (8.25%)"),
    ("FREE_SHIPPING_THRESHOLD", "150.00", "Valor mínimo para frete grátis"),
    ("MAX_INSTALLMENTS_NO_INTEREST", "3", "Máximo de parcelas sem juros"),
    ("INTEREST_RATE_PER_INSTALLMENT", "0.0199", "Taxa de juros por parcela (1.99%)"),
    ("REVIEW_BONUS_RATING_THRESHOLD", "4.5", "Rating mínimo para bonus do seller"),
    ("SELLER_BONUS_PERCENTAGE", "0.02", "Percentual de bonus para sellers bem avaliados"),
    ("REFUND_WINDOW_DAYS", "30", "Prazo em dias para solicitar reembolso"),
    ("MAX_COUPON_DISCOUNT_PERCENTAGE", "0.30", "Desconto máximo permitido por cupom (30%)"),
    ("PAYOUT_PROCESSING_DAYS", "15", "Dias para processar pagamento ao seller"),
]

# ======================== PRODUCT NAME TEMPLATES ========================

PRODUCT_TEMPLATES = {
    1: [  # Smartphones
        ("Samsung Galaxy A{n}", 800, 2500), ("iPhone {n} Pro", 4000, 9000),
        ("Motorola Moto G{n}", 600, 1800), ("Xiaomi Redmi Note {n}", 800, 2200),
    ],
    2: [  # Capas
        ("Capa Silicone {brand}", 15, 60), ("Película Vidro {brand}", 10, 40),
    ],
    3: [  # Carregadores
        ("Carregador USB-C {w}W", 30, 150), ("Cabo USB-C 2m", 15, 50),
    ],
    4: [  # Notebooks
        ("Notebook {brand} i5 8GB", 2500, 5000), ("Notebook {brand} i7 16GB", 4000, 8000),
        ("Notebook {brand} Ryzen 5", 2200, 4500),
    ],
    5: [  # Periféricos
        ("Mouse Gamer {brand}", 50, 300), ("Teclado Mecânico {brand}", 100, 500),
        ("Headset {brand}", 60, 400), ("Webcam {brand} HD", 80, 250),
    ],
    6: [  # Componentes
        ("SSD {brand} {gb}GB", 150, 800), ("Memória RAM DDR4 {gb}GB", 100, 500),
        ("Placa de Vídeo {brand}", 800, 5000),
    ],
    7: [  # Monitores
        ("Monitor {brand} {pol}\"", 500, 3000),
    ],
    8: [("Geladeira {brand} {l}L", 1500, 5000)],
    9: [("Lava e Seca {brand} {kg}kg", 1800, 4500)],
    10: [("Micro-ondas {brand} {l}L", 300, 900)],
    11: [("Aspirador {brand} {w}W", 200, 1200)],
    12: [("Vestido {style}", 50, 300)],
    13: [("Blusa {style}", 30, 180)],
    14: [("Calça Jeans Feminina", 60, 250)],
    15: [("Camiseta {style}", 25, 120)],
    16: [("Calça Masculina {style}", 60, 200)],
    17: [("Jaqueta {style}", 100, 400)],
    18: [("Tênis {brand} {model}", 100, 800)],
    19: [("Sandália {brand}", 40, 200)],
    20: [("Bota {style}", 120, 500)],
    21: [("Sofá {n} Lugares {style}", 800, 4000)],
    22: [("Mesa {style}", 200, 2000)],
    23: [("Cadeira {style}", 150, 1500)],
    24: [("Quadro Decorativo {style}", 30, 200)],
    25: [("Kit Almofadas {style}", 40, 180)],
    26: [("Luminária {style}", 50, 400)],
    27: [("Esteira Elétrica {brand}", 800, 3000), ("Halteres {kg}kg Par", 30, 200)],
    28: [("Barraca Camping {n} Pessoas", 100, 600), ("Saco de Dormir {brand}", 80, 350)],
    29: [("Bicicleta {brand} Aro {n}", 500, 3000), ("Capacete Ciclismo {brand}", 50, 300)],
    30: [("Kit Maquiagem {brand}", 50, 400), ("Base Líquida {brand}", 25, 120)],
    31: [("Sérum Facial {brand}", 40, 250), ("Protetor Solar FPS{n}", 20, 80)],
    32: [("Perfume {brand} {ml}ml", 80, 500)],
    33: [("Livro: {title}", 20, 80)],
    34: [("Livro Técnico: {title}", 40, 200)],
    35: [("Livro Infantil: {title}", 15, 60)],
    36: [("Brinquedo Educativo {type}", 30, 150)],
    37: [("Game {title} - {platform}", 100, 350)],
    38: [("Boneco {character}", 30, 200)],
    39: [("Pneu {brand} {size}", 200, 800)],
    40: [("Acessório Auto {type}", 20, 300)],
    41: [("Kit Ferramentas {n} Peças", 50, 500)],
    42: [("Ração {brand} {kg}kg", 40, 250)],
    43: [("Brinquedo Pet {type}", 10, 80)],
    44: [("Shampoo Pet {brand} {ml}ml", 15, 60)],
    45: [("Kit Orgânicos {type}", 30, 150)],
    46: [("Vinho {origin} {type}", 30, 300), ("Cerveja Artesanal {type}", 15, 60)],
    47: [("Snack {type} {g}g", 5, 30)],
}

BRANDS = ["Samsung", "LG", "Dell", "Lenovo", "Asus", "Logitech", "Razer", "HyperX",
           "Kingston", "Corsair", "AOC", "Philips", "Brastemp", "Electrolux", "Consul",
           "Nike", "Adidas", "Puma", "Olympikus", "Havaianas", "Caloi", "Tramontina",
           "Royal Canin", "PremieR", "Natura", "O Boticário", "MAC", "Lancôme"]

STYLES = ["Casual", "Clássico", "Moderno", "Vintage", "Premium", "Básico", "Slim Fit",
          "Oversized", "Retrô", "Industrial", "Minimalista", "Rústico"]

BOOK_TITLES = ["O Algoritmo da Vida", "Dados do Amanhã", "SQL para Todos",
               "Python na Prática", "Engenharia de Dados", "O Poder dos Dados",
               "Machine Learning 101", "Cloud Computing", "Big Data Brasil"]

GAME_TITLES = ["Aventura Épica", "Corrida Máxima", "Mundo Aberto", "Batalha Final"]
PLATFORMS = ["PS5", "Xbox", "Switch", "PC"]
CHARACTERS = ["Super-herói", "Dinossauro", "Astronauta", "Princesa", "Robô"]


# ======================== HELPER FUNCTIONS ========================

def random_date(start, end):
    """Generate random datetime between start and end."""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def generate_cpf(formatted=True):
    """Generate a random CPF (not validated, for simulation purposes)."""
    nums = [random.randint(0, 9) for _ in range(9)]
    # Calculate check digits
    s = sum((10 - i) * nums[i] for i in range(9))
    d1 = 11 - (s % 11)
    d1 = 0 if d1 >= 10 else d1
    nums.append(d1)
    s = sum((11 - i) * nums[i] for i in range(10))
    d2 = 11 - (s % 11)
    d2 = 0 if d2 >= 10 else d2
    nums.append(d2)
    raw = "".join(str(n) for n in nums)
    if formatted:
        return f"{raw[:3]}.{raw[3:6]}.{raw[6:9]}-{raw[9:]}"
    return raw


def generate_cnpj(formatted=True):
    """Generate a random CNPJ."""
    nums = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, random.randint(1, 9)]
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(w * n for w, n in zip(weights1, nums))
    d1 = 11 - (s % 11)
    d1 = 0 if d1 >= 10 else d1
    nums.append(d1)
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    s = sum(w * n for w, n in zip(weights2, nums))
    d2 = 11 - (s % 11)
    d2 = 0 if d2 >= 10 else d2
    nums.append(d2)
    raw = "".join(str(n) for n in nums)
    if formatted:
        return f"{raw[:2]}.{raw[2:5]}.{raw[5:8]}/{raw[8:12]}-{raw[12:]}"
    return raw


def generate_phone():
    """Generate telefone in various formats (intentional inconsistency for regex practice)."""
    ddd = random.choice(["11", "21", "31", "41", "51", "61", "71", "81", "85", "92", "27", "48"])
    num = f"9{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
    fmt = random.choice(["formatted", "raw", "international", "partial", "with_spaces"])
    if fmt == "formatted":
        return f"({ddd}) {num[:5]}-{num[5:]}"
    elif fmt == "raw":
        return f"{ddd}{num}"
    elif fmt == "international":
        return f"+55{ddd}{num}"
    elif fmt == "partial":
        return f"{ddd} {num}"
    else:
        return f"+55 {ddd} {num[:5]} {num[5:]}"


def generate_address_raw():
    """Generate address as raw string with varied formatting (for regex parsing)."""
    street_types = ["Rua", "Av.", "Avenida", "R.", "Travessa", "Alameda", "Praça"]
    street = f"{random.choice(street_types)} {fake.street_name()}"
    number = random.randint(1, 5000)
    complement = random.choice([
        f"Apt {random.randint(1, 500)}",
        f"Apto. {random.randint(1, 500)}",
        f"Bloco {random.choice('ABCDEF')} Apt {random.randint(1, 200)}",
        f"Casa {random.randint(1, 30)}",
        f"Sala {random.randint(100, 1500)}",
        "",  # no complement
        None,  # will be excluded
    ])
    bairro = fake.bairro()
    city = fake.city()
    state = random.choices(list(BR_STATES.keys()), weights=list(BR_STATES.values()), k=1)[0]
    cep = f"{random.randint(10000, 99999)}-{random.randint(100, 999)}"

    # Vary the format intentionally
    fmt = random.choice(["full", "no_cep", "compact", "messy"])
    if fmt == "full" and complement:
        return f"{street}, {number}, {complement}, {bairro}, {city} - {state}, CEP: {cep}"
    elif fmt == "no_cep":
        parts = [f"{street}, {number}"]
        if complement:
            parts.append(complement)
        parts.extend([bairro, f"{city}/{state}"])
        return ", ".join(parts)
    elif fmt == "compact":
        return f"{street} {number} - {bairro} - {city} {state} {cep}"
    else:
        parts = [street, str(number)]
        if complement:
            parts.append(complement)
        parts.extend([bairro, city, state])
        return " | ".join(parts)


def generate_sku(category_slug, subcategory_slug, seq):
    """Generate SKU with parseable pattern: CAT-SUB-XXXXX."""
    cat = category_slug[:3].upper()
    sub = subcategory_slug[:3].upper()
    return f"{cat}-{sub}-{seq:05d}"


def generate_product_name(id_subcategoria):
    """Generate a realistic product name based on subcategory."""
    templates = PRODUCT_TEMPLATES.get(id_subcategoria, [("Produto Genérico", 10, 100)])
    template, min_p, max_p = random.choice(templates)
    name = template.format(
        n=random.randint(5, 15), brand=random.choice(BRANDS),
        w=random.choice([15, 20, 25, 30, 45, 65]), gb=random.choice([128, 256, 512, 1000]),
        pol=random.choice([21, 24, 27, 29, 32, 34]),
        l=random.choice([260, 340, 400, 460, 500]),
        kg=random.choice([8, 10, 11, 12, 15]),
        style=random.choice(STYLES), model=f"V{random.randint(1,5)}",
        size=f"{random.choice([175, 185, 195, 205, 215])}/{random.choice([55, 60, 65, 70])}R{random.choice([14, 15, 16, 17])}",
        ml=random.choice([50, 75, 100, 150, 200]),
        g=random.choice([50, 100, 150, 200, 300]),
        title=random.choice(BOOK_TITLES + GAME_TITLES),
        platform=random.choice(PLATFORMS),
        character=random.choice(CHARACTERS),
        type=random.choice(["Premium", "Standard", "Deluxe", "Compact"]),
        origin=random.choice(["Chileno", "Argentino", "Italiano", "Português"]),
    )
    preco = round(random.uniform(min_p, max_p), 2)
    return name, preco


def generate_tracking_code(company_id):
    """Generate tracking code based on shipping company."""
    prefix_map = {1: "BR", 2: "BR", 3: "JD", 4: "LOG", 5: "AZL"}
    prefix = prefix_map.get(company_id, "TK")
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
    return f"{prefix}{code}"


# ======================== DATA GENERATORS ========================

def seed_lookup_tables(conn):
    """Insert all lookup/dimension data."""
    cur = conn.cursor()

    # Seller categories
    cur.executemany(
        "INSERT INTO app.seller_categories (id, nome, descricao) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        SELLER_CATEGORIES,
    )

    # Product categories
    cur.executemany(
        "INSERT INTO app.product_categories (id, nome, slug) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        PRODUCT_CATEGORIES,
    )

    # Product subcategories
    cur.executemany(
        "INSERT INTO app.product_subcategories (id, id_categoria, nome, slug) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        PRODUCT_SUBCATEGORIES,
    )

    # Shipping companies
    cur.executemany(
        "INSERT INTO app.shipping_companies (id, nome, padrao_url_rastreamento, media_dias_entrega) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        SHIPPING_COMPANIES,
    )

    # Payment methods
    cur.executemany(
        "INSERT INTO app.payment_methods (id, nome, codigo, max_parcelas) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        PAYMENT_METHODS,
    )

    # Order statuses
    cur.executemany(
        "INSERT INTO app.order_statuses (id, nome, codigo, descricao, ordem_exibicao) VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
        ORDER_STATUSES,
    )

    # Platform config
    cur.executemany(
        "INSERT INTO app.platform_config (chave, valor, descricao) VALUES (%s, %s, %s) ON CONFLICT (chave) DO NOTHING",
        PLATFORM_CONFIGS,
    )

    # Reset sequences
    for table in ["seller_categories", "product_categories", "product_subcategories",
                  "shipping_companies", "payment_methods", "order_statuses"]:
        cur.execute(f"SELECT setval(pg_get_serial_sequence('app.{table}', 'id'), (SELECT COALESCE(MAX(id),0) FROM app.{table}));")

    conn.commit()
    cur.close()
    print("[OK] Lookup tables seeded.")


def seed_customers(conn):
    """Generate customer records with intentional format variations."""
    cur = conn.cursor()
    customers = []

    referral_codes_pool = [f"REF{random.randint(1000,9999)}" for _ in range(50)]

    for i in range(1, NUM_CUSTOMERS + 1):
        nome_completo = fake.name()

        # Email: 95% valid, 5% with typos/issues
        if random.random() < 0.95:
            email = fake.email()
        else:
            # Intentional data issues
            email = random.choice([
                nome_completo.replace(" ", "") + "@gmailcom",  # missing dot
                f"{fake.user_name()}@",  # incomplete
                f"  {fake.email()}  ",  # extra spaces
                "",  # empty
                None,  # null
            ])

        # Phone in varied formats
        telefone = generate_phone()

        # CPF: 70% formatted, 20% raw, 10% issues
        r = random.random()
        if r < 0.70:
            cpf = generate_cpf(formatted=True)
        elif r < 0.90:
            cpf = generate_cpf(formatted=False)
        else:
            cpf = random.choice([
                generate_cpf(formatted=True).replace("-", ""),  # partial format
                f" {generate_cpf()} ",  # extra spaces
                None,  # null (foreigner, for example)
            ])

        data_nascimento = fake.date_of_birth(minimum_age=18, maximum_age=75)
        endereco_raw = generate_address_raw()
        state = random.choices(list(BR_STATES.keys()), weights=list(BR_STATES.values()), k=1)[0]
        city = fake.city()
        cep = f"{random.randint(10000, 99999)}-{random.randint(100, 999)}"

        # Status distribution: 85% active, 10% inactive, 5% blocked
        status = random.choices(["active", "inactive", "blocked"], weights=[85, 10, 5], k=1)[0]

        codigo_indicacao = random.choice(referral_codes_pool) if random.random() < 0.3 else None
        referred_by = random.randint(1, max(1, i - 1)) if random.random() < 0.15 and i > 10 else None

        criado_em = random_date(START_DATE, END_DATE)

        customers.append((
            nome_completo, email, telefone, cpf, data_nascimento, endereco_raw, city, state,
            cep, status, codigo_indicacao, referred_by, criado_em, criado_em
        ))

    cur.executemany("""
        INSERT INTO app.customers
        (nome_completo, email, telefone, cpf, data_nascimento, endereco_raw, cidade, estado,
         cep, status, codigo_indicacao, indicado_por_id_cliente, criado_em, atualizado_em)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, customers)

    conn.commit()
    cur.close()
    print(f"[OK] {NUM_CUSTOMERS} customers seeded.")


def seed_sellers(conn):
    """Generate seller records."""
    cur = conn.cursor()
    sellers = []

    for i in range(NUM_SELLERS):
        company = fake.company()
        nome_fantasia = company.split()[0] + random.choice([" Store", " Shop", " Brasil", " Online", " Digital"])

        # CNPJ format variations
        if random.random() < 0.75:
            cnpj = generate_cnpj(formatted=True)
        else:
            cnpj = generate_cnpj(formatted=False)

        id_categoria = random.randint(1, len(SELLER_CATEGORIES))

        # Commission rate: base 15% +/- variation, some sellers have negotiated rates
        base_commission = 0.15
        if random.random() < 0.2:
            commission = round(random.uniform(0.08, 0.12), 4)  # negotiated lower
        elif random.random() < 0.1:
            commission = round(random.uniform(0.18, 0.25), 4)  # premium tier
        else:
            commission = round(base_commission + random.uniform(-0.03, 0.03), 4)

        state = random.choices(list(BR_STATES.keys()), weights=list(BR_STATES.values()), k=1)[0]
        city = fake.city()
        endereco_raw = generate_address_raw()

        # Rating: weighted toward good ratings
        rating = round(min(5.0, max(1.0, np.random.normal(4.0, 0.7))), 2)

        status = random.choices(["active", "inactive", "suspended"], weights=[80, 12, 8], k=1)[0]
        onboarding = fake.date_between(start_date=START_DATE, end_date=END_DATE)
        criado_em = datetime.combine(onboarding, datetime.min.time())

        sellers.append((
            company, nome_fantasia, cnpj, fake.company_email(), generate_phone(),
            id_categoria, commission, endereco_raw, city, state, rating,
            status, onboarding, criado_em, criado_em
        ))

    cur.executemany("""
        INSERT INTO app.sellers
        (nome_empresa, nome_fantasia, cnpj, email_contato, telefone_contato,
         id_categoria, taxa_comissao, endereco_raw, cidade, estado, avaliacao,
         status, data_cadastro, criado_em, atualizado_em)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, sellers)

    conn.commit()
    cur.close()
    print(f"[OK] {NUM_SELLERS} sellers seeded.")


def seed_products(conn):
    """Generate product records with varied data quality."""
    cur = conn.cursor()
    products = []
    sku_counter = {}

    for i in range(NUM_PRODUCTS):
        subcat = random.choice(PRODUCT_SUBCATEGORIES)
        subcat_id = subcat[0]
        cat_id = subcat[1]
        cat_slug = next(c[2] for c in PRODUCT_CATEGORIES if c[0] == cat_id)
        sub_slug = subcat[3]

        id_vendedor = random.randint(1, NUM_SELLERS)
        name, preco = generate_product_name(subcat_id)

        # SKU generation
        sku_key = f"{cat_slug}-{sub_slug}"
        sku_counter[sku_key] = sku_counter.get(sku_key, 0) + 1
        sku = generate_sku(cat_slug, sub_slug, sku_counter[sku_key])

        descricao = fake.paragraph(nb_sentences=3)

        # Cost preco: normally lower than preco, but ~5% have cost > preco (data quality issue)
        if random.random() < 0.05:
            preco_custo = round(preco * random.uniform(1.05, 1.3), 2)  # INTENTIONAL: cost > preco
        elif random.random() < 0.10:
            preco_custo = None  # Some products don't have cost registered
        else:
            preco_custo = round(preco * random.uniform(0.3, 0.75), 2)

        stock = int(np.random.exponential(50))
        if random.random() < 0.08:
            stock = 0  # out of stock

        weight = round(random.uniform(0.1, 30.0), 3) if random.random() > 0.1 else None

        # Third party: ~30% of products are from third parties
        if random.random() < 0.30:
            id_externo = f"TP-{random.randint(1000, 9999)}"
            nome_externo = random.choice([
                "Distribuidora Central", "Mega Atacado", "Sul Importados",
                "Norte Distribuidora", "Prime Supply", "Global Goods",
                None,  # INTENTIONAL: has ID but no name (data issue)
            ])
        else:
            id_externo = None
            nome_externo = None

        status = random.choices(
            ["active", "inactive", "discontinued", "pending_review"],
            weights=[75, 10, 10, 5], k=1
        )[0]

        e_digital = subcat_id in [33, 34, 35, 37]  # books and games might be digital

        criado_em = random_date(START_DATE, END_DATE)

        products.append((
            id_vendedor, name, sku, descricao, preco, preco_custo,
            cat_id, subcat_id, stock, weight, id_externo, nome_externo,
            status, e_digital, criado_em, criado_em
        ))

    cur.executemany("""
        INSERT INTO app.products
        (id_vendedor, nome, sku, descricao, preco, preco_custo,
         id_categoria, id_subcategoria, quantidade_estoque, weight_kg,
         id_externo, nome_externo, status, e_digital,
         criado_em, atualizado_em)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, products)

    conn.commit()
    cur.close()
    print(f"[OK] {NUM_PRODUCTS} products seeded.")


def seed_coupons(conn):
    """Generate coupon records."""
    cur = conn.cursor()
    coupons = []

    coupon_prefixes = ["NOVA", "PROMO", "DESC", "BLACK", "WELCOME", "VIP", "SUMMER", "WINTER"]

    for i in range(NUM_COUPONS):
        prefix = random.choice(coupon_prefixes)
        code = f"{prefix}{random.randint(10, 99)}"
        tipo_desconto = random.choice(["percentage", "fixed"])

        if tipo_desconto == "percentage":
            valor_desconto = random.choice([5, 10, 15, 20, 25, 30])
            max_discount = round(random.uniform(30, 150), 2)
        else:
            valor_desconto = round(random.uniform(10, 100), 2)
            max_discount = None

        min_order = round(random.uniform(50, 300), 2) if random.random() > 0.3 else None
        max_usos = random.choice([50, 100, 200, 500, 1000, None])
        usos_atuais = random.randint(0, (max_usos or 500) // 2)

        valido_de = random_date(START_DATE, END_DATE)
        valido_ate = valido_de + timedelta(days=random.randint(7, 90))

        id_vendedor = random.randint(1, NUM_SELLERS) if random.random() < 0.3 else None

        status = "active" if valido_ate > datetime.now() else "expired"
        if random.random() < 0.1:
            status = "inactive"

        coupons.append((
            code, tipo_desconto, valor_desconto, min_order, max_discount,
            max_usos, usos_atuais, valido_de, valido_ate, id_vendedor,
            status, valido_de
        ))

    cur.executemany("""
        INSERT INTO app.coupons
        (codigo, tipo_desconto, valor_desconto, valor_minimo_pedido, valor_max_desconto,
         max_usos, usos_atuais, valido_de, valido_ate, id_vendedor,
         status, criado_em)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, coupons)

    conn.commit()
    cur.close()
    print(f"[OK] {NUM_COUPONS} coupons seeded.")


def seed_orders_and_items(conn):
    """Generate orders, order items, and payments with realistic patterns."""
    cur = conn.cursor()

    # Fetch product info for preco references
    cur.execute("SELECT id, id_vendedor, preco, id_categoria FROM app.products WHERE status = 'active'")
    products = cur.fetchall()
    if not products:
        print("[ERROR] No products found. Seed products first.")
        return

    product_ids = [p[0] for p in products]
    product_map = {p[0]: {"id_vendedor": p[1], "preco": float(p[2]), "id_categoria": p[3]} for p in products}

    # Fetch coupons
    cur.execute("SELECT id, tipo_desconto, valor_desconto, valor_max_desconto, valor_minimo_pedido FROM app.coupons WHERE status = 'active'")
    coupons = cur.fetchall()

    orders_data = []
    items_data = []
    payments_data = []

    for order_num in range(1, NUM_ORDERS + 1):
        id_cliente = random.randint(1, NUM_CUSTOMERS)
        data_pedido = random_date(START_DATE, END_DATE)

        # 1-6 items per order (weighted toward fewer)
        num_items = random.choices([1, 2, 3, 4, 5, 6], weights=[35, 30, 18, 10, 5, 2], k=1)[0]

        # Pick products for this order
        order_products = random.sample(product_ids, min(num_items, len(product_ids)))

        subtotal = 0
        order_items = []

        for prod_id in order_products:
            info = product_map[prod_id]
            qty = random.choices([1, 2, 3, 4, 5], weights=[60, 25, 10, 3, 2], k=1)[0]
            preco_unitario = info["preco"]

            # Small random preco variation (simulates preco at time of purchase)
            if random.random() < 0.15:
                preco_unitario = round(preco_unitario * random.uniform(0.85, 1.10), 2)

            preco_total = round(preco_unitario * qty, 2)
            item_discount = round(preco_total * random.uniform(0, 0.1), 2) if random.random() < 0.2 else 0

            subtotal += preco_total - item_discount
            order_items.append((prod_id, info["id_vendedor"], qty, preco_unitario, preco_total, item_discount))

        subtotal = round(subtotal, 2)

        # Coupon: 20% of orders use a coupon
        id_cupom = None
        coupon_discount = 0
        if random.random() < 0.20 and coupons:
            coupon = random.choice(coupons)
            id_cupom = coupon[0]
            c_type, c_val, c_max, c_min = coupon[1], float(coupon[2]), coupon[3], coupon[4]

            if c_min and subtotal < float(c_min):
                id_cupom = None
            else:
                if c_type == "percentage":
                    coupon_discount = round(subtotal * (c_val / 100), 2)
                    if c_max:
                        coupon_discount = min(coupon_discount, float(c_max))
                else:
                    coupon_discount = float(c_val)

        # Shipping cost: free above threshold, otherwise based on weight
        if subtotal >= 150:
            shipping = 0
        else:
            shipping = round(random.uniform(8, 45), 2)

        total = round(max(0, subtotal - coupon_discount + shipping), 2)

        # Order status progression based on order age
        days_since_order = (END_DATE - data_pedido).days
        if days_since_order > 30:
            status_weights = [2, 2, 3, 10, 70, 8, 3, 2]
        elif days_since_order > 14:
            status_weights = [5, 5, 10, 30, 35, 10, 3, 2]
        elif days_since_order > 5:
            status_weights = [10, 15, 30, 25, 10, 7, 2, 1]
        else:
            status_weights = [40, 30, 20, 5, 0, 5, 0, 0]

        id_status = random.choices(range(1, 9), weights=status_weights, k=1)[0]

        id_metodo_pagamento = random.choices(
            [1, 2, 3, 4, 5], weights=[35, 10, 35, 12, 8], k=1
        )[0]

        id_transportadora = random.randint(1, len(SHIPPING_COMPANIES)) if id_status >= 4 else None
        codigo_rastreamento = generate_tracking_code(id_transportadora) if id_transportadora and id_status >= 4 else None

        # INTENTIONAL DATA ISSUE: ~3% of delivered orders have NULL tracking
        if id_status == 5 and random.random() < 0.03:
            codigo_rastreamento = None

        previsao_entrega = (data_pedido + timedelta(days=random.randint(3, 15))).date() if id_status >= 3 else None

        # entregue_em: should be set when status = delivered
        entregue_em = None
        if id_status == 5:
            entregue_em = data_pedido + timedelta(days=random.randint(3, 20))
            # INTENTIONAL DATA ISSUE: ~5% of delivered orders have NULL entregue_em
            if random.random() < 0.05:
                entregue_em = None

        cancelado_em = None
        motivo_cancelamento = None
        if id_status in (6, 7):
            cancelado_em = data_pedido + timedelta(hours=random.randint(1, 72))
            motivo_cancelamento = random.choice([
                "Cliente desistiu da compra",
                "Produto indisponível",
                "Erro no pedido",
                "Prazo de entrega insatisfatório",
                "Encontrou preço melhor",
                None,  # INTENTIONAL: cancelled without reason
            ])

        observacoes = fake.sentence() if random.random() < 0.1 else None
        shipping_address = generate_address_raw()

        orders_data.append((
            id_cliente, data_pedido, id_status, id_metodo_pagamento, id_cupom,
            coupon_discount, shipping, subtotal, total, shipping_address,
            id_transportadora, codigo_rastreamento, previsao_entrega, entregue_em,
            cancelado_em, motivo_cancelamento, observacoes, data_pedido, data_pedido
        ))

        # Store items for batch insert after orders
        items_data.append(order_items)

        # Payment data
        pay_status_map = {
            1: "pending", 2: "approved", 3: "approved", 4: "approved",
            5: "approved", 6: "cancelled", 7: "refunded", 8: "refunded"
        }
        pay_status = pay_status_map.get(id_status, "pending")

        parcelas = 1
        if id_metodo_pagamento == 1:  # credit card
            parcelas = random.choices([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                                          weights=[20, 15, 20, 10, 8, 8, 5, 4, 3, 3, 2, 2], k=1)[0]

        valor_parcela = round(total / parcelas, 2) if parcelas > 1 else None

        pago_em = None
        if pay_status in ("approved",):
            pago_em = data_pedido + timedelta(minutes=random.randint(1, 120))
            # INTENTIONAL: ~3% approved but pago_em is NULL
            if random.random() < 0.03:
                pago_em = None

        reembolsado_em = None
        valor_reembolso = None
        if pay_status == "refunded":
            reembolsado_em = data_pedido + timedelta(days=random.randint(1, 30))
            valor_reembolso = total if random.random() > 0.2 else round(total * random.uniform(0.5, 0.95), 2)

        gateway_tx = f"txn_{uuid.uuid4().hex[:20]}" if pay_status != "pending" else None

        # Gateway raw response with varied JSON-like strings (for regex practice)
        gateway_raw = None
        if gateway_tx:
            gw = random.choice(["pagarme", "mercadopago", "stripe", "asaas"])
            gateway_raw = f'{{"gateway":"{gw}","tid":"{gateway_tx}","status":"{pay_status}","amount":{total},"parcelas":{parcelas}}}'

        payments_data.append((
            id_metodo_pagamento, gateway_tx, pay_status, total, parcelas,
            valor_parcela, pago_em, reembolsado_em, valor_reembolso, gateway_raw, data_pedido
        ))

    # Insert orders
    cur.executemany("""
        INSERT INTO app.orders
        (id_cliente, data_pedido, id_status, id_metodo_pagamento, id_cupom,
         valor_desconto, custo_frete, subtotal, valor_total, endereco_entrega_raw,
         id_transportadora, codigo_rastreamento, previsao_entrega, entregue_em,
         cancelado_em, motivo_cancelamento, observacoes, criado_em, atualizado_em)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, orders_data)

    conn.commit()

    # Get order IDs
    cur.execute("SELECT id FROM app.orders ORDER BY id")
    order_ids = [r[0] for r in cur.fetchall()]

    # Insert order items
    all_items = []
    for id_pedido, items in zip(order_ids[-NUM_ORDERS:], items_data):
        for item in items:
            prod_id, id_vendedor, qty, unit_p, total_p, discount = item
            all_items.append((id_pedido, prod_id, id_vendedor, qty, unit_p, total_p, discount))

    cur.executemany("""
        INSERT INTO app.order_items
        (id_pedido, id_produto, id_vendedor, quantidade, preco_unitario, preco_total, valor_desconto)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, all_items)

    # Insert payments
    all_payments = []
    for id_pedido, pay in zip(order_ids[-NUM_ORDERS:], payments_data):
        all_payments.append((id_pedido,) + pay)

    cur.executemany("""
        INSERT INTO app.payments
        (id_pedido, id_metodo_pagamento, id_transacao_gateway, status, valor,
         parcelas, valor_parcela, pago_em, reembolsado_em, valor_reembolso,
         resposta_raw_gateway, criado_em)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, all_payments)

    conn.commit()
    cur.close()
    print(f"[OK] {NUM_ORDERS} orders, {len(all_items)} order items, {len(all_payments)} payments seeded.")


def seed_reviews(conn):
    """Generate reviews only for delivered orders."""
    cur = conn.cursor()

    # Get delivered order items (id_cliente is on orders, not order_items)
    cur.execute("""
        SELECT oi.id, o.id_cliente, oi.id_produto, oi.id_vendedor
        FROM app.order_items oi
        JOIN app.orders o ON o.id = oi.id_pedido
        WHERE o.id_status = 5
    """)
    delivered_items = cur.fetchall()

    reviews = []
    reviewed_items = set()

    # ~40% of delivered items get a review
    for item in delivered_items:
        if random.random() < 0.40 and item[0] not in reviewed_items:
            reviewed_items.add(item[0])

            # Rating distribution: weighted toward positive
            rating = random.choices([1, 2, 3, 4, 5], weights=[5, 8, 15, 30, 42], k=1)[0]

            title = None
            if random.random() < 0.6:
                if rating >= 4:
                    title = random.choice([
                        "Excelente produto!", "Recomendo muito!", "Ótima qualidade!",
                        "Superou expectativas", "Muito bom!", "Top demais!",
                        "Entrega rápida e produto perfeito", None
                    ])
                elif rating == 3:
                    title = random.choice([
                        "OK, razoável", "Nada demais", "Cumpre o básico",
                        "Regular", "Pode melhorar", None
                    ])
                else:
                    title = random.choice([
                        "Decepcionante", "Não recomendo", "Péssimo!",
                        "Produto veio com defeito", "Não comprem!", None
                    ])

            comentario = fake.paragraph(nb_sentences=random.randint(1, 4)) if random.random() < 0.7 else None

            is_verified = True if random.random() < 0.95 else False
            votos_uteis = int(np.random.exponential(3))

            criado_em = random_date(START_DATE, END_DATE)

            reviews.append((
                item[0], item[1], item[2], item[3],
                rating, title, comentario, is_verified, votos_uteis, criado_em
            ))

    cur.executemany("""
        INSERT INTO app.reviews
        (id_item_pedido, id_cliente, id_produto, id_vendedor,
         avaliacao, titulo, comentario, compra_verificada, votos_uteis, criado_em)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, reviews)

    conn.commit()
    cur.close()
    print(f"[OK] {len(reviews)} reviews seeded.")


def seed_seller_payouts(conn):
    """Generate monthly seller payout records."""
    cur = conn.cursor()

    # Get seller sales by month
    cur.execute("""
        SELECT
            oi.id_vendedor,
            DATE_TRUNC('month', o.data_pedido)::date AS ref_month,
            SUM(oi.preco_total) AS gross
        FROM app.order_items oi
        JOIN app.orders o ON o.id = oi.id_pedido
        WHERE o.id_status NOT IN (6, 7)
        GROUP BY oi.id_vendedor, DATE_TRUNC('month', o.data_pedido)
        HAVING SUM(oi.preco_total) > 0
    """)
    sales = cur.fetchall()

    # Get seller commission rates
    cur.execute("SELECT id, taxa_comissao FROM app.sellers")
    rates = {r[0]: float(r[1]) for r in cur.fetchall()}

    payouts = []
    for id_vendedor, ref_month, gross in sales:
        gross = float(gross)
        rate = rates.get(id_vendedor, 0.15)
        commission = round(gross * rate, 2)
        tax = round(gross * 0.0825, 2)
        net = round(gross - commission - tax, 2)

        status = "paid" if ref_month < datetime(2025, 11, 1).date() else "pending"
        pago_em = (datetime.combine(ref_month, datetime.min.time()) + timedelta(days=random.randint(15, 30))) if status == "paid" else None

        ref_str = ref_month.strftime("%Y-%m")
        payouts.append((id_vendedor, ref_str, gross, commission, tax, net, status, pago_em))

    cur.executemany("""
        INSERT INTO app.seller_payouts
        (id_vendedor, mes_referencia, valor_bruto, valor_comissao, valor_impostos,
         valor_liquido, status, pago_em)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, payouts)

    conn.commit()
    cur.close()
    print(f"[OK] {len(payouts)} seller payouts seeded.")


# ======================== MAIN ========================

def run_full_seed():
    """Execute complete seed in correct order."""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        print("=" * 60)
        print("NovaMart - Seed Data Generator")
        print("=" * 60)

        seed_lookup_tables(conn)
        seed_customers(conn)
        seed_sellers(conn)
        seed_products(conn)
        seed_coupons(conn)
        seed_orders_and_items(conn)
        seed_reviews(conn)
        seed_seller_payouts(conn)

        print("=" * 60)
        print("[DONE] All seed data generated successfully!")
        print("=" * 60)
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Seed failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_full_seed()
