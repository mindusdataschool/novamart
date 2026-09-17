"""
NovaMart - Continuous Data Ingestion Simulator
================================================
Simulates real-time data ingestion for the marketplace.
Designed to be scheduled via cron/task scheduler to generate
new orders, update statuses, and add reviews periodically.

Usage:
    python continuous_ingestion.py              # Run once (default batch)
    python continuous_ingestion.py --orders 10  # Generate 10 new orders
    python continuous_ingestion.py --loop 60    # Run every 60 seconds
"""

import argparse
import random
import time
import uuid
from datetime import datetime, timedelta

import psycopg2
from faker import Faker
from generate_seed_data import (
    DB_CONFIG,
    generate_address_raw,
    generate_cpf,
    generate_phone,
    generate_product_name,
    generate_tracking_code,
    BR_STATES,
)

fake = Faker("pt_BR")


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def generate_new_orders(conn, count=5):
    """Generate new orders simulating real customer activity."""
    cur = conn.cursor()

    # Get active products
    cur.execute("SELECT id, id_vendedor, preco FROM app.products WHERE status = 'active'")
    products = cur.fetchall()
    if not products:
        print("[WARN] No active products found.")
        return 0

    # Get active customers
    cur.execute("SELECT id FROM app.customers WHERE status = 'active'")
    customers = [r[0] for r in cur.fetchall()]
    if not customers:
        print("[WARN] No active customers found.")
        return 0

    # Get active coupons
    cur.execute("""
        SELECT id, tipo_desconto, valor_desconto, valor_max_desconto, valor_minimo_pedido
        FROM app.coupons WHERE status = 'active' AND valido_ate > NOW()
    """)
    coupons = cur.fetchall()

    orders_created = 0
    now = datetime.now()

    for _ in range(count):
        id_cliente = random.choice(customers)

        # 1-4 items
        num_items = random.choices([1, 2, 3, 4], weights=[40, 30, 20, 10], k=1)[0]
        selected = random.sample(products, min(num_items, len(products)))

        subtotal = 0
        items = []
        for prod_id, id_vendedor, preco in selected:
            qty = random.choices([1, 2, 3], weights=[65, 25, 10], k=1)[0]
            preco_unitario = float(preco)
            preco_total = round(preco_unitario * qty, 2)
            discount = round(preco_total * random.uniform(0, 0.08), 2) if random.random() < 0.15 else 0
            subtotal += preco_total - discount
            items.append((prod_id, id_vendedor, qty, preco_unitario, preco_total, discount))

        subtotal = round(subtotal, 2)

        # Coupon
        id_cupom = None
        coupon_discount = 0
        if random.random() < 0.15 and coupons:
            c = random.choice(coupons)
            id_cupom, c_type, c_val, c_max, c_min = c
            if c_min is None or subtotal >= float(c_min):
                if c_type == "percentage":
                    coupon_discount = round(subtotal * (float(c_val) / 100), 2)
                    if c_max:
                        coupon_discount = min(coupon_discount, float(c_max))
                else:
                    coupon_discount = float(c_val)
            else:
                id_cupom = None

        shipping = 0 if subtotal >= 150 else round(random.uniform(8, 35), 2)
        total = round(max(0, subtotal - coupon_discount + shipping), 2)

        # New orders always start as pending
        id_metodo_pagamento = random.choices([1, 2, 3, 4, 5], weights=[30, 10, 40, 12, 8], k=1)[0]
        data_pedido = now - timedelta(minutes=random.randint(0, 30))

        cur.execute("""
            INSERT INTO app.orders
            (id_cliente, data_pedido, id_status, id_metodo_pagamento, id_cupom,
             valor_desconto, custo_frete, subtotal, valor_total,
             endereco_entrega_raw, criado_em, atualizado_em)
            VALUES (%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (id_cliente, data_pedido, id_metodo_pagamento, id_cupom,
              coupon_discount, shipping, subtotal, total,
              generate_address_raw(), now, now))

        id_pedido = cur.fetchone()[0]

        for prod_id, id_vendedor, qty, unit_p, total_p, disc in items:
            cur.execute("""
                INSERT INTO app.order_items
                (id_pedido, id_produto, id_vendedor, quantidade, preco_unitario, preco_total, valor_desconto)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (id_pedido, prod_id, id_vendedor, qty, unit_p, total_p, disc))

        # Payment: pending for new orders
        gateway_tx = None
        if id_metodo_pagamento == 3:  # PIX - auto approve
            gateway_tx = f"txn_{uuid.uuid4().hex[:20]}"
            cur.execute("""
                INSERT INTO app.payments
                (id_pedido, id_metodo_pagamento, id_transacao_gateway, status, valor,
                 parcelas, pago_em, criado_em)
                VALUES (%s,%s,%s,'approved',%s,1,%s,%s)
            """, (id_pedido, id_metodo_pagamento, gateway_tx, total, now, now))
            # Also update order to payment_confirmed
            cur.execute("UPDATE app.orders SET id_status = 2, atualizado_em = %s WHERE id = %s", (now, id_pedido))
        else:
            parcelas = random.choices([1, 2, 3, 6, 10, 12], weights=[30, 15, 20, 15, 10, 10], k=1)[0] if id_metodo_pagamento == 1 else 1
            installment_val = round(total / parcelas, 2) if parcelas > 1 else None
            cur.execute("""
                INSERT INTO app.payments
                (id_pedido, id_metodo_pagamento, status, valor, parcelas,
                 valor_parcela, criado_em)
                VALUES (%s,%s,'pending',%s,%s,%s,%s)
            """, (id_pedido, id_metodo_pagamento, total, parcelas, installment_val, now))

        orders_created += 1

    conn.commit()
    cur.close()
    print(f"  [+] {orders_created} new orders created")
    return orders_created


def advance_order_statuses(conn, max_updates=20):
    """Progress existing orders through their lifecycle."""
    cur = conn.cursor()
    now = datetime.now()
    updates = 0

    # Pending → Payment Confirmed (for non-PIX after some time)
    cur.execute("""
        SELECT o.id, o.valor_total, o.id_metodo_pagamento
        FROM app.orders o
        WHERE o.id_status = 1
          AND o.data_pedido < NOW() - INTERVAL '30 minutes'
        ORDER BY RANDOM() LIMIT %s
    """, (max_updates // 4,))

    for id_pedido, total, pay_method in cur.fetchall():
        if random.random() < 0.85:  # 85% get approved
            gateway_tx = f"txn_{uuid.uuid4().hex[:20]}"
            cur.execute("""
                UPDATE app.payments SET status = 'approved', pago_em = %s,
                    id_transacao_gateway = %s
                WHERE id_pedido = %s AND status = 'pending'
            """, (now, gateway_tx, id_pedido))
            cur.execute("UPDATE app.orders SET id_status = 2, atualizado_em = %s WHERE id = %s", (now, id_pedido))
        else:  # 15% get cancelled
            cur.execute("UPDATE app.orders SET id_status = 6, cancelado_em = %s, motivo_cancelamento = 'Pagamento não aprovado', atualizado_em = %s WHERE id = %s", (now, now, id_pedido))
            cur.execute("UPDATE app.payments SET status = 'cancelled' WHERE id_pedido = %s", (id_pedido,))
        updates += 1

    # Payment Confirmed → Processing
    cur.execute("""
        SELECT id FROM app.orders
        WHERE id_status = 2
          AND atualizado_em < NOW() - INTERVAL '1 hour'
        ORDER BY RANDOM() LIMIT %s
    """, (max_updates // 3,))
    for (id_pedido,) in cur.fetchall():
        cur.execute("UPDATE app.orders SET id_status = 3, atualizado_em = %s WHERE id = %s", (now, id_pedido))
        updates += 1

    # Processing → Shipped
    cur.execute("""
        SELECT id FROM app.orders
        WHERE id_status = 3
          AND atualizado_em < NOW() - INTERVAL '4 hours'
        ORDER BY RANDOM() LIMIT %s
    """, (max_updates // 3,))
    for (id_pedido,) in cur.fetchall():
        company_id = random.randint(1, 5)
        tracking = generate_tracking_code(company_id)
        est_delivery = (now + timedelta(days=random.randint(2, 10))).date()
        cur.execute("""
            UPDATE app.orders SET id_status = 4, id_transportadora = %s,
                codigo_rastreamento = %s, previsao_entrega = %s, atualizado_em = %s
            WHERE id = %s
        """, (company_id, tracking, est_delivery, now, id_pedido))
        updates += 1

    # Shipped → Delivered
    cur.execute("""
        SELECT id FROM app.orders
        WHERE id_status = 4
          AND atualizado_em < NOW() - INTERVAL '2 days'
        ORDER BY RANDOM() LIMIT %s
    """, (max_updates // 3,))
    for (id_pedido,) in cur.fetchall():
        cur.execute("""
            UPDATE app.orders SET id_status = 5, entregue_em = %s, atualizado_em = %s
            WHERE id = %s
        """, (now, now, id_pedido))
        updates += 1

    conn.commit()
    cur.close()
    print(f"  [~] {updates} order statuses advanced")
    return updates


def generate_new_reviews(conn, max_reviews=5):
    """Generate reviews for recently delivered orders without reviews."""
    cur = conn.cursor()

    cur.execute("""
        SELECT oi.id, o.id_cliente, oi.id_produto, oi.id_vendedor
        FROM app.order_items oi
        JOIN app.orders o ON o.id = oi.id_pedido
        LEFT JOIN app.reviews r ON r.id_item_pedido = oi.id
        WHERE o.id_status = 5 AND r.id IS NULL
        ORDER BY RANDOM()
        LIMIT %s
    """, (max_reviews,))

    items = cur.fetchall()
    count = 0

    for oi_id, cust_id, prod_id, id_vendedor in items:
        if random.random() < 0.5:  # 50% chance of reviewing
            rating = random.choices([1, 2, 3, 4, 5], weights=[5, 8, 15, 30, 42], k=1)[0]
            titles = {
                5: ["Excelente!", "Amei!", "Super recomendo!", "Perfeito!"],
                4: ["Muito bom!", "Gostei!", "Bom produto"],
                3: ["OK", "Regular", "Razoável"],
                2: ["Abaixo do esperado", "Poderia ser melhor"],
                1: ["Péssimo", "Não recomendo", "Horrível"],
            }
            title = random.choice(titles.get(rating, [""])) if random.random() < 0.6 else None
            comentario = fake.paragraph(nb_sentences=random.randint(1, 3)) if random.random() < 0.7 else None

            cur.execute("""
                INSERT INTO app.reviews
                (id_item_pedido, id_cliente, id_produto, id_vendedor, avaliacao, titulo, comentario,
                 compra_verificada, votos_uteis, criado_em)
                VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE,0,%s)
            """, (oi_id, cust_id, prod_id, id_vendedor, rating, title, comentario, datetime.now()))
            count += 1

    conn.commit()
    cur.close()
    print(f"  [★] {count} new reviews generated")
    return count


def register_new_customers(conn, count=2):
    """Occasionally register new customers."""
    cur = conn.cursor()
    now = datetime.now()

    for _ in range(count):
        state = random.choices(list(BR_STATES.keys()), weights=list(BR_STATES.values()), k=1)[0]
        cpf_fmt = random.random() < 0.7

        cur.execute("""
            INSERT INTO app.customers
            (nome_completo, email, telefone, cpf, data_nascimento, endereco_raw, cidade, estado,
             cep, status, criado_em, atualizado_em)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s)
        """, (
            fake.name(), fake.email(), generate_phone(),
            generate_cpf(formatted=cpf_fmt),
            fake.date_of_birth(minimum_age=18, maximum_age=65),
            generate_address_raw(), fake.city(), state,
            f"{random.randint(10000,99999)}-{random.randint(100,999)}",
            now, now
        ))

    conn.commit()
    cur.close()
    print(f"  [👤] {count} new customers registered")


def update_stock(conn):
    """Update stock quantities for products that were ordered."""
    cur = conn.cursor()

    cur.execute("""
        UPDATE app.products p SET
            quantidade_estoque = GREATEST(0, p.quantidade_estoque - sub.qty),
            atualizado_em = NOW()
        FROM (
            SELECT oi.id_produto, SUM(oi.quantidade) AS qty
            FROM app.order_items oi
            JOIN app.orders o ON o.id = oi.id_pedido
            WHERE o.id_status IN (2, 3, 4, 5)
              AND o.atualizado_em > NOW() - INTERVAL '1 hour'
            GROUP BY oi.id_produto
        ) sub
        WHERE p.id = sub.id_produto
    """)

    updated = cur.rowcount
    conn.commit()
    cur.close()
    print(f"  [📦] {updated} product stocks updated")


def run_ingestion_cycle(new_orders=5):
    """Run a single ingestion cycle."""
    conn = get_conn()
    try:
        print(f"\n{'='*50}")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ingestion cycle started")
        print(f"{'='*50}")

        generate_new_orders(conn, count=new_orders)
        advance_order_statuses(conn, max_updates=15)
        generate_new_reviews(conn, max_reviews=5)

        if random.random() < 0.3:
            register_new_customers(conn, count=random.randint(1, 3))

        update_stock(conn)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Cycle complete ✓")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Ingestion cycle failed: {e}")
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="NovaMart Continuous Data Ingestion")
    parser.add_argument("--orders", type=int, default=5, help="New orders per cycle (default: 5)")
    parser.add_argument("--loop", type=int, default=0, help="Loop interval in seconds (0 = run once)")
    args = parser.parse_args()

    if args.loop > 0:
        print(f"Starting continuous ingestion (every {args.loop}s, {args.orders} orders/cycle)")
        print("Press Ctrl+C to stop")
        while True:
            try:
                run_ingestion_cycle(new_orders=args.orders)
                time.sleep(args.loop)
            except KeyboardInterrupt:
                print("\nIngestion stopped.")
                break
    else:
        run_ingestion_cycle(new_orders=args.orders)


if __name__ == "__main__":
    main()
