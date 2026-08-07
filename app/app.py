"""
NovaMart - Flask Application
==============================
Main web application with:
- Home: Overview dashboard
- Dashboard: Blank page for Metabase iframe embed
- Reports: Month/year filter to generate PDF reports
"""




import io
import os
from datetime import datetime

from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, flash

from database import query, query_one, execute
from pdf_generator import generate_monthly_report

app = Flask(__name__)
app.secret_key = "novamart-dev-secret-key"


@app.route("/")
def index():
    """Home page with summary metrics."""
    metrics = {}

    row = query_one("SELECT COUNT(*) AS total FROM app.orders")
    metrics["total_orders"] = row["total"] if row else 0

    row = query_one("SELECT COALESCE(SUM(valor_total), 0) AS total FROM app.orders WHERE id_status NOT IN (6,7)")
    metrics["total_revenue"] = float(row["total"]) if row else 0

    row = query_one("SELECT COUNT(*) AS total FROM app.customers")
    metrics["total_customers"] = row["total"] if row else 0

    row = query_one("SELECT COUNT(*) AS total FROM app.sellers WHERE status = 'active'")
    metrics["active_sellers"] = row["total"] if row else 0

    row = query_one("SELECT COUNT(*) AS total FROM app.products WHERE status = 'active'")
    metrics["active_products"] = row["total"] if row else 0

    row = query_one("SELECT ROUND(AVG(avaliacao), 2) AS avg FROM app.reviews")
    metrics["avg_rating"] = float(row["avg"]) if row and row["avg"] else 0

    recent_orders = query("""
        SELECT o.id, c.nome_completo AS customer, o.valor_total,
               os.nome AS status, o.data_pedido
        FROM app.orders o
        JOIN app.customers c ON c.id = o.id_cliente
        JOIN app.order_statuses os ON os.id = o.id_status
        ORDER BY o.data_pedido DESC
        LIMIT 10
    """)

    return render_template("index.html", metrics=metrics, recent_orders=recent_orders)


@app.route("/dashboard")
def dashboard():
    """Blank page for embedding Metabase dashboard via iframe."""
    return render_template("dashboard.html")


@app.route("/reports")
def reports():
    """Reports page with month/year selector."""
    # Get available months from orders
    months = query("""
        SELECT DISTINCT
            EXTRACT(YEAR FROM data_pedido)::int AS year,
            EXTRACT(MONTH FROM data_pedido)::int AS month
        FROM app.orders
        ORDER BY year DESC, month DESC
    """)
    return render_template("reports.html", months=months)


@app.route("/reports/generate", methods=["POST"])
def generate_report():
    """Generate PDF report for selected month/year."""
    month = int(request.form.get("month", datetime.now().month))
    year = int(request.form.get("year", datetime.now().year))

    pdf_buffer = generate_monthly_report(month, year)

    return send_file(
        io.BytesIO(pdf_buffer),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"novamart_report_{year}_{month:02d}.pdf",
    )


@app.route("/api/metrics/<int:year>/<int:month>")
def api_metrics(year, month):
    """API endpoint for report metrics (used by PDF generator)."""
    data = {}

    # Revenue
    row = query_one("""
        SELECT COALESCE(SUM(valor_total), 0) AS revenue,
               COUNT(*) AS orders,
               COALESCE(AVG(valor_total), 0) AS avg_ticket
        FROM app.orders
        WHERE EXTRACT(YEAR FROM data_pedido) = %s
          AND EXTRACT(MONTH FROM data_pedido) = %s
          AND id_status NOT IN (6, 7)
    """, (year, month))
    data["revenue"] = float(row["revenue"])
    data["total_orders"] = row["orders"]
    data["avg_ticket"] = float(row["avg_ticket"])

    # Previous month comparison
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev = query_one("""
        SELECT COALESCE(SUM(valor_total), 0) AS revenue, COUNT(*) AS orders
        FROM app.orders
        WHERE EXTRACT(YEAR FROM data_pedido) = %s
          AND EXTRACT(MONTH FROM data_pedido) = %s
          AND id_status NOT IN (6, 7)
    """, (prev_year, prev_month))
    data["prev_revenue"] = float(prev["revenue"])
    data["prev_orders"] = prev["orders"]

    # Top categories
    data["top_categories"] = [dict(r) for r in query("""
        SELECT pc.nome AS category, SUM(oi.preco_total) AS total
        FROM app.order_items oi
        JOIN app.products p ON p.id = oi.id_produto
        JOIN app.product_categories pc ON pc.id = p.id_categoria
        JOIN app.orders o ON o.id = oi.id_pedido
        WHERE EXTRACT(YEAR FROM o.data_pedido) = %s
          AND EXTRACT(MONTH FROM o.data_pedido) = %s
          AND o.id_status NOT IN (6, 7)
        GROUP BY pc.nome
        ORDER BY total DESC
        LIMIT 8
    """, (year, month))]

    # Top sellers
    data["top_sellers"] = [dict(r) for r in query("""
        SELECT s.nome_empresa, SUM(oi.preco_total) AS total,
               COUNT(DISTINCT oi.id_pedido) AS orders
        FROM app.order_items oi
        JOIN app.sellers s ON s.id = oi.id_vendedor
        JOIN app.orders o ON o.id = oi.id_pedido
        WHERE EXTRACT(YEAR FROM o.data_pedido) = %s
          AND EXTRACT(MONTH FROM o.data_pedido) = %s
          AND o.id_status NOT IN (6, 7)
        GROUP BY s.nome_empresa
        ORDER BY total DESC
        LIMIT 10
    """, (year, month))]

    # Payment method distribution
    data["payment_methods"] = [dict(r) for r in query("""
        SELECT pm.nome AS method, COUNT(*) AS count, SUM(p.valor) AS total
        FROM app.payments p
        JOIN app.payment_methods pm ON pm.id = p.id_metodo_pagamento
        JOIN app.orders o ON o.id = p.id_pedido
        WHERE EXTRACT(YEAR FROM o.data_pedido) = %s
          AND EXTRACT(MONTH FROM o.data_pedido) = %s
          AND p.status = 'approved'
        GROUP BY pm.nome
        ORDER BY total DESC
    """, (year, month))]

    # Daily revenue for trend chart
    data["daily_revenue"] = [dict(r) for r in query("""
        SELECT data_pedido::date AS day, SUM(valor_total) AS revenue, COUNT(*) AS orders
        FROM app.orders
        WHERE EXTRACT(YEAR FROM data_pedido) = %s
          AND EXTRACT(MONTH FROM data_pedido) = %s
          AND id_status NOT IN (6, 7)
        GROUP BY data_pedido::date
        ORDER BY day
    """, (year, month))]

    # Order status distribution
    data["status_distribution"] = [dict(r) for r in query("""
        SELECT os.nome AS status, COUNT(*) AS count
        FROM app.orders o
        JOIN app.order_statuses os ON os.id = o.id_status
        WHERE EXTRACT(YEAR FROM o.data_pedido) = %s
          AND EXTRACT(MONTH FROM o.data_pedido) = %s
        GROUP BY os.nome, os.ordem_exibicao
        ORDER BY os.ordem_exibicao
    """, (year, month))]

    # New customers this month
    row = query_one("""
        SELECT COUNT(*) AS total FROM app.customers
        WHERE EXTRACT(YEAR FROM criado_em) = %s
          AND EXTRACT(MONTH FROM criado_em) = %s
    """, (year, month))
    data["new_customers"] = row["total"]

    # Average rating this month
    row = query_one("""
        SELECT ROUND(AVG(avaliacao), 2) AS avg, COUNT(*) AS total
        FROM app.reviews
        WHERE EXTRACT(YEAR FROM criado_em) = %s
          AND EXTRACT(MONTH FROM criado_em) = %s
    """, (year, month))
    data["avg_rating"] = float(row["avg"]) if row and row["avg"] else 0
    data["total_reviews"] = row["total"] if row else 0

    # Serialize dates
    for d in data["daily_revenue"]:
        d["day"] = d["day"].isoformat()
    for d in data["top_categories"]:
        d["total"] = float(d["total"])
    for d in data["top_sellers"]:
        d["total"] = float(d["total"])
    for d in data["payment_methods"]:
        d["total"] = float(d["total"])

    return jsonify(data)


# ======================== CUSTOMERS CRUD ========================

@app.route("/customers")
def customers_list():
    """List all customers with search."""
    search = request.args.get("q", "")
    if search:
        customers = query("""
            SELECT id, nome_completo, email, cpf, cidade, estado, status, criado_em
            FROM app.customers
            WHERE nome_completo ILIKE %s OR email ILIKE %s OR cpf ILIKE %s
            ORDER BY criado_em DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        customers = query("""
            SELECT id, nome_completo, email, cpf, cidade, estado, status, criado_em
            FROM app.customers ORDER BY criado_em DESC LIMIT 100
        """)
    return render_template("customers/list.html", customers=customers, search=search)


@app.route("/customers/new", methods=["GET", "POST"])
def customers_new():
    """Form to create a new customer."""
    if request.method == "POST":
        execute("""
            INSERT INTO app.customers (nome_completo, email, telefone, cpf, data_nascimento,
                endereco_raw, cidade, estado, cep, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            request.form["nome_completo"],
            request.form.get("email") or None,
            request.form.get("telefone") or None,
            request.form.get("cpf") or None,
            request.form.get("data_nascimento") or None,
            request.form.get("endereco_raw") or None,
            request.form.get("city") or None,
            request.form.get("state") or None,
            request.form.get("cep") or None,
            request.form.get("status", "active"),
        ))
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("customers_list"))
    return render_template("customers/form.html", customer=None)


@app.route("/customers/<int:id>/edit", methods=["GET", "POST"])
def customers_edit(id):
    """Edit an existing customer."""
    if request.method == "POST":
        execute("""
            UPDATE app.customers
            SET nome_completo=%s, email=%s, telefone=%s, cpf=%s, data_nascimento=%s,
                endereco_raw=%s, cidade=%s, estado=%s, cep=%s, status=%s, atualizado_em=NOW()
            WHERE id=%s
        """, (
            request.form["nome_completo"],
            request.form.get("email") or None,
            request.form.get("telefone") or None,
            request.form.get("cpf") or None,
            request.form.get("data_nascimento") or None,
            request.form.get("endereco_raw") or None,
            request.form.get("city") or None,
            request.form.get("state") or None,
            request.form.get("cep") or None,
            request.form.get("status", "active"),
            id,
        ))
        flash("Cliente atualizado com sucesso!", "success")
        return redirect(url_for("customers_list"))
    customer = query_one("SELECT * FROM app.customers WHERE id = %s", (id,))
    return render_template("customers/form.html", customer=customer)


# ======================== SELLERS CRUD ========================

@app.route("/sellers")
def sellers_list():
    """List all sellers."""
    search = request.args.get("q", "")
    if search:
        sellers = query("""
            SELECT s.id, s.nome_empresa, s.nome_fantasia, s.cnpj, s.cidade, s.estado,
                   s.status, s.avaliacao, sc.nome AS category
            FROM app.sellers s
            LEFT JOIN app.seller_categories sc ON sc.id = s.id_categoria
            WHERE s.nome_empresa ILIKE %s OR s.cnpj ILIKE %s
            ORDER BY s.criado_em DESC
        """, (f"%{search}%", f"%{search}%"))
    else:
        sellers = query("""
            SELECT s.id, s.nome_empresa, s.nome_fantasia, s.cnpj, s.cidade, s.estado,
                   s.status, s.avaliacao, sc.nome AS category
            FROM app.sellers s
            LEFT JOIN app.seller_categories sc ON sc.id = s.id_categoria
            ORDER BY s.criado_em DESC LIMIT 100
        """)
    return render_template("sellers/list.html", sellers=sellers, search=search)


@app.route("/sellers/new", methods=["GET", "POST"])
def sellers_new():
    """Form to create a new seller."""
    categories = query("SELECT id, nome FROM app.seller_categories ORDER BY nome")
    if request.method == "POST":
        execute("""
            INSERT INTO app.sellers (nome_empresa, nome_fantasia, cnpj, email_contato,
                telefone_contato, id_categoria, taxa_comissao, endereco_raw, cidade, estado, status, data_cadastro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()::date)
            RETURNING id
        """, (
            request.form["nome_empresa"],
            request.form.get("nome_fantasia") or None,
            request.form.get("cnpj") or None,
            request.form.get("email_contato") or None,
            request.form.get("telefone_contato") or None,
            request.form.get("id_categoria") or None,
            request.form.get("taxa_comissao") or None,
            request.form.get("endereco_raw") or None,
            request.form.get("city") or None,
            request.form.get("state") or None,
            request.form.get("status", "active"),
        ))
        flash("Seller cadastrado com sucesso!", "success")
        return redirect(url_for("sellers_list"))
    return render_template("sellers/form.html", seller=None, categories=categories)


@app.route("/sellers/<int:id>/edit", methods=["GET", "POST"])
def sellers_edit(id):
    """Edit an existing seller."""
    categories = query("SELECT id, nome FROM app.seller_categories ORDER BY nome")
    if request.method == "POST":
        execute("""
            UPDATE app.sellers
            SET nome_empresa=%s, nome_fantasia=%s, cnpj=%s, email_contato=%s,
                telefone_contato=%s, id_categoria=%s, taxa_comissao=%s,
                endereco_raw=%s, cidade=%s, estado=%s, status=%s, atualizado_em=NOW()
            WHERE id=%s
        """, (
            request.form["nome_empresa"],
            request.form.get("nome_fantasia") or None,
            request.form.get("cnpj") or None,
            request.form.get("email_contato") or None,
            request.form.get("telefone_contato") or None,
            request.form.get("id_categoria") or None,
            request.form.get("taxa_comissao") or None,
            request.form.get("endereco_raw") or None,
            request.form.get("city") or None,
            request.form.get("state") or None,
            request.form.get("status", "active"),
            id,
        ))
        flash("Seller atualizado com sucesso!", "success")
        return redirect(url_for("sellers_list"))
    seller = query_one("SELECT * FROM app.sellers WHERE id = %s", (id,))
    return render_template("sellers/form.html", seller=seller, categories=categories)


# ======================== PRODUCTS CRUD ========================

@app.route("/products")
def products_list():
    """List all products."""
    search = request.args.get("q", "")
    if search:
        products = query("""
            SELECT p.id, p.nome, p.sku, p.preco, p.preco_custo, p.quantidade_estoque,
                   p.status, s.nome_empresa AS seller, pc.nome AS category
            FROM app.products p
            LEFT JOIN app.sellers s ON s.id = p.id_vendedor
            LEFT JOIN app.product_categories pc ON pc.id = p.id_categoria
            WHERE p.nome ILIKE %s OR p.sku ILIKE %s
            ORDER BY p.criado_em DESC
        """, (f"%{search}%", f"%{search}%"))
    else:
        products = query("""
            SELECT p.id, p.nome, p.sku, p.preco, p.preco_custo, p.quantidade_estoque,
                   p.status, s.nome_empresa AS seller, pc.nome AS category
            FROM app.products p
            LEFT JOIN app.sellers s ON s.id = p.id_vendedor
            LEFT JOIN app.product_categories pc ON pc.id = p.id_categoria
            ORDER BY p.criado_em DESC LIMIT 100
        """)
    return render_template("products/list.html", products=products, search=search)


@app.route("/products/new", methods=["GET", "POST"])
def products_new():
    """Form to create a new product."""
    sellers = query("SELECT id, nome_empresa FROM app.sellers WHERE status='active' ORDER BY nome_empresa")
    categories = query("SELECT id, nome FROM app.product_categories ORDER BY nome")
    subcategories = query("SELECT id, id_categoria, nome FROM app.product_subcategories ORDER BY nome")
    if request.method == "POST":
        execute("""
            INSERT INTO app.products (id_vendedor, nome, sku, descricao, preco, preco_custo,
                id_categoria, id_subcategoria, quantidade_estoque, weight_kg, status, e_digital)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            request.form["id_vendedor"],
            request.form["name"],
            request.form.get("sku") or None,
            request.form.get("descricao") or None,
            request.form["preco"],
            request.form.get("preco_custo") or None,
            request.form.get("id_categoria") or None,
            request.form.get("id_subcategoria") or None,
            request.form.get("quantidade_estoque", 0),
            request.form.get("weight_kg") or None,
            request.form.get("status", "active"),
            "e_digital" in request.form,
        ))
        flash("Produto cadastrado com sucesso!", "success")
        return redirect(url_for("products_list"))
    return render_template("products/form.html", product=None, sellers=sellers,
                           categories=categories, subcategories=subcategories)


@app.route("/products/<int:id>/edit", methods=["GET", "POST"])
def products_edit(id):
    """Edit an existing product."""
    sellers = query("SELECT id, nome_empresa FROM app.sellers WHERE status='active' ORDER BY nome_empresa")
    categories = query("SELECT id, nome FROM app.product_categories ORDER BY nome")
    subcategories = query("SELECT id, id_categoria, nome FROM app.product_subcategories ORDER BY nome")
    if request.method == "POST":
        execute("""
            UPDATE app.products
            SET id_vendedor=%s, nome=%s, sku=%s, descricao=%s, preco=%s, preco_custo=%s,
                id_categoria=%s, id_subcategoria=%s, quantidade_estoque=%s, weight_kg=%s,
                status=%s, e_digital=%s, atualizado_em=NOW()
            WHERE id=%s
        """, (
            request.form["id_vendedor"],
            request.form["name"],
            request.form.get("sku") or None,
            request.form.get("descricao") or None,
            request.form["preco"],
            request.form.get("preco_custo") or None,
            request.form.get("id_categoria") or None,
            request.form.get("id_subcategoria") or None,
            request.form.get("quantidade_estoque", 0),
            request.form.get("weight_kg") or None,
            request.form.get("status", "active"),
            "e_digital" in request.form,
            id,
        ))
        flash("Produto atualizado com sucesso!", "success")
        return redirect(url_for("products_list"))
    product = query_one("SELECT * FROM app.products WHERE id = %s", (id,))
    return render_template("products/form.html", product=product, sellers=sellers,
                           categories=categories, subcategories=subcategories)


# ======================== ORDERS CRUD ========================

@app.route("/orders")
def orders_list():
    """List all orders."""
    search = request.args.get("q", "")
    if search:
        orders = query("""
            SELECT o.id, c.nome_completo AS customer, o.valor_total, os.nome AS status,
                   o.data_pedido, pm.nome AS payment_method
            FROM app.orders o
            JOIN app.customers c ON c.id = o.id_cliente
            JOIN app.order_statuses os ON os.id = o.id_status
            LEFT JOIN app.payment_methods pm ON pm.id = o.id_metodo_pagamento
            WHERE c.nome_completo ILIKE %s OR o.id::text = %s
            ORDER BY o.data_pedido DESC
        """, (f"%{search}%", search))
    else:
        orders = query("""
            SELECT o.id, c.nome_completo AS customer, o.valor_total, os.nome AS status,
                   o.data_pedido, pm.nome AS payment_method
            FROM app.orders o
            JOIN app.customers c ON c.id = o.id_cliente
            JOIN app.order_statuses os ON os.id = o.id_status
            LEFT JOIN app.payment_methods pm ON pm.id = o.id_metodo_pagamento
            ORDER BY o.data_pedido DESC LIMIT 100
        """)
    return render_template("orders/list.html", orders=orders, search=search)


@app.route("/orders/<int:id>")
def orders_detail(id):
    """Order detail with items."""
    order = query_one("""
        SELECT o.*, c.nome_completo AS customer_name, os.nome AS status_name,
               pm.nome AS payment_method_name, sc.nome AS shipping_company_name
        FROM app.orders o
        JOIN app.customers c ON c.id = o.id_cliente
        JOIN app.order_statuses os ON os.id = o.id_status
        LEFT JOIN app.payment_methods pm ON pm.id = o.id_metodo_pagamento
        LEFT JOIN app.shipping_companies sc ON sc.id = o.id_transportadora
        WHERE o.id = %s
    """, (id,))
    items = query("""
        SELECT oi.*, p.nome AS product_name, s.nome_empresa AS seller_name
        FROM app.order_items oi
        JOIN app.products p ON p.id = oi.id_produto
        JOIN app.sellers s ON s.id = oi.id_vendedor
        WHERE oi.id_pedido = %s
    """, (id,))
    payment = query_one("SELECT * FROM app.payments WHERE id_pedido = %s", (id,))
    return render_template("orders/detail.html", order=order, items=items, payment=payment)


@app.route("/orders/new", methods=["GET", "POST"])
def orders_new():
    """Simplified order creation form."""
    customers = query("SELECT id, nome_completo FROM app.customers WHERE status='active' ORDER BY nome_completo")
    statuses = query("SELECT id, nome FROM app.order_statuses ORDER BY ordem_exibicao")
    payment_methods = query("SELECT id, nome FROM app.payment_methods WHERE ativo=TRUE ORDER BY nome")
    products = query("""
        SELECT p.id, p.nome, p.preco, p.id_vendedor, s.nome_empresa AS seller_name
        FROM app.products p
        JOIN app.sellers s ON s.id = p.id_vendedor
        WHERE p.status='active' AND p.quantidade_estoque > 0
        ORDER BY p.nome
    """)

    if request.method == "POST":
        id_cliente = request.form["id_cliente"]
        id_status = request.form.get("id_status", 1)
        id_metodo_pagamento = request.form.get("id_metodo_pagamento")
        custo_frete = float(request.form.get("custo_frete", 0) or 0)

        # Get selected products
        product_ids = request.form.getlist("product_ids[]")
        quantities = request.form.getlist("quantities[]")

        if not product_ids:
            flash("Selecione pelo menos um produto.", "danger")
            return render_template("orders/form.html", order=None, customers=customers,
                                   statuses=statuses, payment_methods=payment_methods, products=products)

        # Calculate totals
        subtotal = 0
        items_data = []
        for pid, qty in zip(product_ids, quantities):
            prod = query_one("SELECT id, preco, id_vendedor FROM app.products WHERE id = %s", (pid,))
            if prod:
                qty = int(qty) if qty else 1
                item_total = float(prod["preco"]) * qty
                subtotal += item_total
                items_data.append({
                    "id_produto": prod["id"],
                    "id_vendedor": prod["id_vendedor"],
                    "quantidade": qty,
                    "preco_unitario": float(prod["preco"]),
                    "preco_total": item_total,
                })

        valor_total = subtotal + custo_frete

        id_pedido = execute("""
            INSERT INTO app.orders (id_cliente, data_pedido, id_status, id_metodo_pagamento,
                custo_frete, subtotal, valor_total)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s)
            RETURNING id
        """, (id_cliente, id_status, id_metodo_pagamento, custo_frete, subtotal, valor_total))

        for item in items_data:
            execute("""
                INSERT INTO app.order_items (id_pedido, id_produto, id_vendedor, quantidade,
                    preco_unitario, preco_total)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_pedido, item["id_produto"], item["id_vendedor"],
                  item["quantidade"], item["preco_unitario"], item["preco_total"]))

        # Create payment record
        execute("""
            INSERT INTO app.payments (id_pedido, id_metodo_pagamento, status, valor, parcelas)
            VALUES (%s, %s, 'pending', %s, 1)
        """, (id_pedido, id_metodo_pagamento, valor_total))

        flash(f"Pedido #{id_pedido} criado com sucesso!", "success")
        return redirect(url_for("orders_detail", id=id_pedido))

    return render_template("orders/form.html", order=None, customers=customers,
                           statuses=statuses, payment_methods=payment_methods, products=products)


if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True, port=5000)
