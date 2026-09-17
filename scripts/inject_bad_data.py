"""
NovaMart - Bad Data Injector (ferramenta didática)
=====================================================
Insere, de propósito, linhas inválidas nas tabelas "app.*" (dados brutos
da aplicação) para que o pipeline agendado (ingestão + dbt build) capture
o problema via teste do dbt, dispare o alerta de falha no Discord, e você
possa demonstrar em aula o ciclo completo: erro -> alerta -> debug -> fix.

Casos disponíveis:
  1 - Genérico (accepted_values): status de pagamento fora da lista válida
  2 - Genérico (relationships): item de pedido referenciando produto inexistente
  3 - Customizado (teste singular): preco_total não bate com quantidade * preco_unitario

Uso:
    python inject_bad_data.py --case 1
    python inject_bad_data.py --case 2
    python inject_bad_data.py --case 3
"""

import argparse
from datetime import datetime

import psycopg2
from generate_seed_data import DB_CONFIG


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def case_1_invalid_payment_status(conn):
    """Dispara o teste genérico accepted_values em stg_payments.status."""
    cur = conn.cursor()
    cur.execute("SELECT id, valor_total FROM app.orders ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("[WARN] Nenhum pedido encontrado para anexar o pagamento inválido.")
        return
    id_pedido, total = row
    cur.execute(
        """
        INSERT INTO app.payments (id_pedido, id_metodo_pagamento, status, valor, parcelas, criado_em)
        VALUES (%s, 3, 'chargeback_iniciado', %s, 1, %s)
        """,
        (id_pedido, total, datetime.now()),
    )
    conn.commit()
    cur.close()
    print(f"[INJECT] Pagamento com status inválido 'chargeback_iniciado' inserido no pedido {id_pedido}.")
    print("         -> Teste esperado: accepted_values em stg_payments.status")


def case_2_orphan_order_item(conn):
    """Dispara o teste genérico relationships entre stg_order_items.id_produto e stg_products."""
    cur = conn.cursor()
    cur.execute("SELECT id, id_vendedor FROM app.products ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("[WARN] Nenhum produto encontrado.")
        return
    _, id_vendedor = row
    cur.execute("SELECT id FROM app.orders ORDER BY RANDOM() LIMIT 1")
    id_pedido = cur.fetchone()[0]
    fake_product_id = 999999999
    cur.execute(
        """
        INSERT INTO app.order_items
        (id_pedido, id_produto, id_vendedor, quantidade, preco_unitario, preco_total, valor_desconto)
        VALUES (%s, %s, %s, 1, 99.90, 99.90, 0)
        """,
        (id_pedido, fake_product_id, id_vendedor),
    )
    conn.commit()
    cur.close()
    print(f"[INJECT] Item de pedido apontando para produto inexistente ({fake_product_id}) no pedido {id_pedido}.")
    print("         -> Teste esperado: relationships em stg_order_items.id_produto -> stg_products")
    print("         -> Nota: se sua tabela app.order_items tiver FK real para app.products,")
    print("            esse insert vai falhar direto no Postgres (o que também é um ótimo exemplo em aula:")
    print("            camada de proteção do banco vs. camada de teste do dbt).")


def case_3_price_mismatch(conn):
    """Dispara um teste customizado (singular): preco_total != quantidade * preco_unitario."""
    cur = conn.cursor()
    cur.execute("SELECT id, id_vendedor, preco FROM app.products ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if not row:
        print("[WARN] Nenhum produto encontrado.")
        return
    id_produto, id_vendedor, preco = row
    cur.execute("SELECT id FROM app.orders ORDER BY RANDOM() LIMIT 1")
    id_pedido = cur.fetchone()[0]
    quantidade = 3
    preco_unitario = float(preco)
    preco_total_errado = 0.01  # deveria ser quantidade * preco_unitario
    cur.execute(
        """
        INSERT INTO app.order_items
        (id_pedido, id_produto, id_vendedor, quantidade, preco_unitario, preco_total, valor_desconto)
        VALUES (%s, %s, %s, %s, %s, %s, 0)
        """,
        (id_pedido, id_produto, id_vendedor, quantidade, preco_unitario, preco_total_errado),
    )
    conn.commit()
    cur.close()
    print(f"[INJECT] Item de pedido com preco_total inconsistente ({preco_total_errado}) no pedido {id_pedido}.")
    print("         -> Teste esperado: teste singular assert_order_item_price_matches_quantity")


CASES = {
    1: case_1_invalid_payment_status,
    2: case_2_orphan_order_item,
    3: case_3_price_mismatch,
}


def main():
    parser = argparse.ArgumentParser(description="NovaMart Bad Data Injector")
    parser.add_argument("--case", type=int, choices=sorted(CASES.keys()), required=True)
    args = parser.parse_args()

    conn = get_conn()
    try:
        CASES[args.case](conn)
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Falha ao injetar dado problemático: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
