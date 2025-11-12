import os
import uuid
import datetime
import boto3
import json
from decimal import Decimal

from validate import hash_password

REGION = os.environ.get("AWS_REGION", "us-east-1")
TENANT_ID = os.environ.get("TENANT_ID", "default")
SUCURSAL_ID = os.environ.get("SEED_SUCURSAL_ID", "sucursal-1")

ORDERS_TABLE = os.environ.get("ORDERS_TABLE", "Orders")
MENU_TABLE = os.environ.get("MENU_TABLE", "MenuItems")
PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "Products")
STAFF_TABLE = os.environ.get("STAFF_TABLE", "Staff")
USERS_TABLE = os.environ.get("USERS_TABLE", "papasqueens-users")


dynamo = boto3.resource("dynamodb", region_name=REGION)

def now_iso():
    return datetime.datetime.utcnow().isoformat()


def as_decimal(n):
    if isinstance(n, (int, float)):
        return Decimal(str(n))
    return n


def products_seed():
    alitas = [
        {
            "nombre": "Alitas X 6 und",
            "precio": 24.90,
            "precio_regular": 33.50,
            "descuento": 26,
            "descripcion": "6 alitas jugosas con 3 cremas a elección, 1 papa pequeña gratis y 1 salsa gratis.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 8 und",
            "precio": 31.90,
            "precio_regular": 43.90,
            "descuento": 27,
            "descripcion": "8 alitas jugosas con 3 cremas a elección, 1 papa pequeña gratis y 2 salsas gratis.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 10 und",
            "precio": 36.90,
            "precio_regular": 49.90,
            "descuento": 26,
            "descripcion": "10 alitas jugosas con 3 cremas a elección, 1 papa pequeña gratis y 2 salsas gratis.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 16 und",
            "precio": 59.90,
            "precio_regular": 81.90,
            "descuento": 27,
            "descripcion": "16 alitas con 5 cremas, 2 papas pequeñas y 3 salsas.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 20 und",
            "precio": 62.90,
            "precio_regular": 94.90,
            "descuento": 34,
            "descripcion": "20 alitas con 5 cremas, 2 papas pequeñas y 4 salsas.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 24 und",
            "precio": 75.90,
            "precio_regular": 102.90,
            "descuento": 26,
            "descripcion": "24 alitas con 6 cremas, 3 papas pequeñas y 4 salsas.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 30 und",
            "precio": 99.90,
            "precio_regular": 134.90,
            "descuento": 26,
            "descripcion": "30 alitas con 7 cremas, 4 papas pequeñas y 6 salsas.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 40 und",
            "precio": 124.90,
            "precio_regular": 168.90,
            "descuento": 26,
            "descripcion": "40 alitas con 10 cremas, 1 papa familiar y 6 salsas.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 50 und",
            "precio": 155.90,
            "precio_regular": 210.90,
            "descuento": 26,
            "descripcion": "50 alitas con 14 cremas, 1 papa familiar y 7 salsas.",
            "categoria": "ALITAS",
        },
        {
            "nombre": "Alitas X 100 und",
            "precio": 299.90,
            "precio_regular": 404.90,
            "descuento": 26,
            "descripcion": "100 alitas con 30 cremas, 2 papas familiares y 7 salsas.",
            "categoria": "ALITAS",
        },
    ]

    combos = [
        {
            "nombre": "Combo Express para 1 persona",
            "precio": 34.40,
            "precio_regular": 46.90,
            "descuento": 27,
            "descripcion": "8 alitas, 2 salsas, papas artesanales y gaseosa 500 ml.",
            "categoria": "COMBOS",
        },
        {
            "nombre": "Combo causitas para 4 personas",
            "precio": 109.90,
            "precio_regular": 149.90,
            "descuento": 27,
            "descripcion": "30 alitas, 6 salsas, papas familiares, 10 cremas y 4 Inca Kola 500 ml.",
            "categoria": "COMBOS",
        },
        {
            "nombre": "Dúo perfecto para 2 personas",
            "precio": 64.90,
            "precio_regular": 88.90,
            "descuento": 27,
            "descripcion": "16 alitas, 3 salsas, papas artesanales y 2 gaseosas 500 ml.",
            "categoria": "COMBOS",
        },
    ]

    hamburguesas = [
        {
            "nombre": "Burger Bacon",
            "precio": 23.90,
            "descripcion": "Res 120g, tocino, cheddar, lechuga, tomate y mayonesa.",
            "categoria": "HAMBURGUESAS",
        },
        {
            "nombre": "Burger Chesse",
            "precio": 21.90,
            "descripcion": "Res 120g, cheddar, lechuga, tomate y mayonesa.",
            "categoria": "HAMBURGUESAS",
        },
        {
            "nombre": "Burger Clasica",
            "precio": 16.90,
            "descripcion": "Res 120g, lechuga, tomate y mayonesa.",
            "categoria": "HAMBURGUESAS",
        },
        {
            "nombre": "Burger Royal",
            "precio": 24.90,
            "descripcion": "Res 120g, jamón, cheddar, huevo, lechuga, tomate y mayonesa.",
            "categoria": "HAMBURGUESAS",
        },
        {
            "nombre": "Pq-broster Clasica",
            "precio": 14.90,
            "descripcion": "Pollo broaster 90g, lechuga, tomate y mayonesa.",
            "categoria": "HAMBURGUESAS",
        },
        {
            "nombre": "Pq-broster Queso Tocino",
            "precio": 18.90,
            "descripcion": "Pollo broaster 90g, queso Edam, tocino, lechuga, tomate y mayonesa.",
            "categoria": "HAMBURGUESAS",
        },
    ]

    salchipapas = [
        {
            "nombre": "SalchiQueen's Especial Premium",
            "precio": 27.90,
            "descripcion": "Papas artesanales con hot dog y chorizo, cremas y bebida 500 ml.",
            "categoria": "SALCHIPAPAS",
        },
        {
            "nombre": "SalchiQueen's Premium",
            "precio": 24.90,
            "descripcion": "Papas artesanales con hot dog, cremas y bebida 500 ml.",
            "categoria": "SALCHIPAPAS",
        },
        {
            "nombre": "Salchipollo Premium",
            "precio": 26.90,
            "descripcion": "Pollo Broaster, cremas y bebida 500 ml.",
            "categoria": "SALCHIPAPAS",
        },
    ]

    all_products = alitas + combos + hamburguesas + salchipapas

    items = []
    for p in all_products:
        pid = str(uuid.uuid4())
        items.append({
            "id_producto": pid,
            "tenant_id": TENANT_ID,
            "nombre": p["nombre"],
            "categoria": p["categoria"],
            "precio": as_decimal(p.get("precio", 0)),
            "precio_regular": as_decimal(p.get("precio_regular", p.get("precio", 0))),
            "descuento": int(p.get("descuento", 0)),
            "descripcion": p.get("descripcion", ""),
            "available": True,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })
    return items


def seed_table(table_name, items, key_field):
    table = dynamo.Table(table_name)
    with table.batch_writer() as batch:
        for it in items:
            batch.put_item(Item=it)
    print(f"Seeded {len(items)} items into {table_name}")


def seed_products_and_menu():
    items = products_seed()
    seed_table(PRODUCTS_TABLE, items, "id_producto")
    menu_items = [
        {**p} for p in items
    ]
    seed_table(MENU_TABLE, menu_items, "id_producto")
    return items


def seed_users_and_staff():
    now = now_iso()
    cliente_email = "cliente1@papasqueens.pe"
    staff_admin_email = "admin1@papasqueens.pe"
    staff_rider_email = "rider1@papasqueens.pe"

    users = [
        {
            "email": cliente_email,
            "id_user": str(uuid.uuid4()),
            "type_user": "cliente",
            "role": None,
            "password_hash": hash_password("Cliente123!"),
            "name": "Cliente Uno",
            "status": "activo",
            "id_sucursal": SUCURSAL_ID,
            "created_at": now,
            "updated_at": now,
        },
        {
            "email": staff_admin_email,
            "id_user": str(uuid.uuid4()),
            "type_user": "staff",
            "role": "admin",
            "password_hash": hash_password("Admin123!"),
            "name": "Admin Uno",
            "status": "activo",
            "id_sucursal": SUCURSAL_ID,
            "created_at": now,
            "updated_at": now,
        },
        {
            "email": staff_rider_email,
            "id_user": str(uuid.uuid4()),
            "type_user": "staff",
            "role": "repartidor",
            "password_hash": hash_password("Rider123!"),
            "name": "Rider Uno",
            "status": "activo",
            "id_sucursal": SUCURSAL_ID,
            "created_at": now,
            "updated_at": now,
        },
    ]

    seed_table(USERS_TABLE, users, "email")

    staff = [
        {
            "id_staff": str(uuid.uuid4()),
            "tenant_id": TENANT_ID,
            "name": "Cocinero Uno",
            "role": "cocinero",
            "email": "cocinero1@papasqueens.pe",
            "status": "activo",
            "hire_date": now,
            "updated_at": now,
        },
        {
            "id_staff": str(uuid.uuid4()),
            "tenant_id": TENANT_ID,
            "name": "Empacador Uno",
            "role": "empacador",
            "email": "empacador1@papasqueens.pe",
            "status": "activo",
            "hire_date": now,
            "updated_at": now,
        },
        {
            "id_staff": str(uuid.uuid4()),
            "tenant_id": TENANT_ID,
            "name": "Repartidor Uno",
            "role": "repartidor",
            "email": "repartidor1@papasqueens.pe",
            "status": "activo",
            "hire_date": now,
            "updated_at": now,
        },
    ]
    seed_table(STAFF_TABLE, staff, "id_staff")

    return {
        "users": users,
        "staff": staff,
    }


def seed_orders(product_items, users_info):
    now = now_iso()
    cliente = next(u for u in users_info["users"] if u["type_user"] == "cliente")
    customer_id = cliente["id_user"]

    p_by_cat = {}
    for p in product_items:
        p_by_cat.setdefault(p["categoria"], []).append(p)

    pick = []
    for cat in ["ALITAS", "HAMBURGUESAS"]:
        if p_by_cat.get(cat):
            pick.append(p_by_cat[cat][0]["id_producto"])

    order = {
        "id_order": str(uuid.uuid4()),
        "tenant_id": TENANT_ID,
        "id_customer": customer_id,
        "list_id_products": pick,
        "status": "recibido",
        "created_at": now,
        "updated_at": now,
    }

    seed_table(ORDERS_TABLE, [order], "id_order")
    return order


def main():
    print("Seeding PapasQueen's data...")
    products = seed_products_and_menu()
    refs = seed_users_and_staff()
    order = seed_orders(products, refs)

    summary = {
        "tenant_id": TENANT_ID,
        "sucursal": SUCURSAL_ID,
        "products": len(products),
        "users": len(refs["users"]),
        "staff": len(refs["staff"]),
        "orders": 1,
        "order_id": order["id_order"],
        "order_products": order["list_id_products"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()