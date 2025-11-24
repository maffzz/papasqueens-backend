#!/usr/bin/env python3
import os
import uuid
import datetime
import bcrypt
import boto3

DYNAMO_REGION = "us-east-1"
TABLE_NAME = "Staff"

TENANTS = [
    "tenant_pq_barranco",      # Sede Barranco (UTEC)
    "tenant_pq_puruchuco",     # Sede Puruchuco
    "tenant_pq_villamaria",    # Sede Villa María
    "tenant_pq_jiron",         # Sede Jirón
]

STAFF_PER_TENANT = [
    # 2 admins
    {
        "id_staff_suffix": "admin1",
        "name": "Administrador 1",
        "dni": "80000001",
        "role": "admin",
        "email_suffix": "admin1",
        "phone": "+51 900000001",
        "status": "activo",
    },
    {
        "id_staff_suffix": "admin2",
        "name": "Administrador 2",
        "dni": "80000002",
        "role": "admin",
        "email_suffix": "admin2",
        "phone": "+51 900000002",
        "status": "activo",
    },
    # 3 cocineros
    {
        "id_staff_suffix": "cocinero1",
        "name": "Cocinero 1",
        "dni": "70000001",
        "role": "cocinero",
        "email_suffix": "cocinero1",
        "phone": "+51 900000101",
        "status": "activo",
    },
    {
        "id_staff_suffix": "cocinero2",
        "name": "Cocinero 2",
        "dni": "70000002",
        "role": "cocinero",
        "email_suffix": "cocinero2",
        "phone": "+51 900000102",
        "status": "activo",
    },
    {
        "id_staff_suffix": "cocinero3",
        "name": "Cocinero 3",
        "dni": "70000003",
        "role": "cocinero",
        "email_suffix": "cocinero3",
        "phone": "+51 900000103",
        "status": "activo",
    },
    # 2 empaquetadores
    {
        "id_staff_suffix": "empaquetador1",
        "name": "Empaquetador 1",
        "dni": "65000001",
        "role": "empaquetador",
        "email_suffix": "empaquetador1",
        "phone": "+51 900000151",
        "status": "activo",
    },
    {
        "id_staff_suffix": "empaquetador2",
        "name": "Empaquetador 2",
        "dni": "65000002",
        "role": "empaquetador",
        "email_suffix": "empaquetador2",
        "phone": "+51 900000152",
        "status": "activo",
    },
    # 3 delivery
    {
        "id_staff_suffix": "delivery1",
        "name": "Repartidor 1",
        "dni": "60000001",
        "role": "delivery",
        "email_suffix": "delivery1",
        "phone": "+51 900000201",
        "status": "activo",
    },
    {
        "id_staff_suffix": "delivery2",
        "name": "Repartidor 2",
        "dni": "60000002",
        "role": "delivery",
        "email_suffix": "delivery2",
        "phone": "+51 900000202",
        "status": "activo",
    },
    {
        "id_staff_suffix": "delivery3",
        "name": "Repartidor 3",
        "dni": "60000003",
        "role": "delivery",
        "email_suffix": "delivery3",
        "phone": "+51 900000203",
        "status": "activo",
    },
]


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def main():
    session = boto3.Session(region_name=DYNAMO_REGION)
    dynamo = session.resource("dynamodb")
    table = dynamo.Table(TABLE_NAME)

    # Password fijo para todos los usuarios seed: 123456
    default_password = "123456"
    password_h = hash_password(default_password)
    now = datetime.datetime.utcnow().isoformat()

    print("=" * 80)
    print("🌱 SEED DE STAFF - PAPAS QUEEN'S")
    print("=" * 80)
    print(f"📋 Tabla: {TABLE_NAME}")
    print(f"🔐 Password por defecto: {default_password}")
    print(f"🏢 Tenants: {len(TENANTS)}")
    print(f"👥 Staff por tenant: {len(STAFF_PER_TENANT)}")
    print(f"📊 Total de registros a crear: {len(TENANTS) * len(STAFF_PER_TENANT)}")
    print("=" * 80)
    print()

    total_created = 0
    for tenant in TENANTS:
        # usar el sufijo del tenant como id_sucursal simple
        id_sucursal = tenant.replace("tenant_", "suc_")
        
        print(f"🏪 Procesando tenant: {tenant}")
        print(f"   ID Sucursal: {id_sucursal}")
        print()

        for spec in STAFF_PER_TENANT:
            id_staff = f"{tenant}_{spec['id_staff_suffix']}"
            email = f"{spec['email_suffix']}@{tenant}.papasqueens.test"

            item = {
                "tenant_id": tenant,
                "id_staff": id_staff,
                "name": spec["name"],
                "dni": spec["dni"],
                "role": spec["role"],
                "email": email,
                "password_hash": password_h,
                "status": spec["status"],
                "phone": spec["phone"],
                "hire_date": now,
                "id_sucursal": id_sucursal,
            }

            role_emoji = {
                "admin": "👔",
                "cocinero": "👨‍🍳",
                "empaquetador": "📦",
                "delivery": "🚚"
            }.get(spec["role"], "👤")

            print(f"   {role_emoji} {spec['role'].upper():15} | {item['name']:20} | {email}")

            try:
                table.put_item(Item=item)
                total_created += 1
            except Exception as e:
                print(f"      ❌ Error: {e}")

        print()

    print("=" * 80)
    print(f"✅ Seed completado: {total_created} registros creados")
    print(f"🔐 Password para todos: {default_password}")
    print("=" * 80)
    print()
    print("📝 Resumen por rol:")
    
    roles_count = {}
    for spec in STAFF_PER_TENANT:
        role = spec["role"]
        roles_count[role] = roles_count.get(role, 0) + 1
    
    for role, count in sorted(roles_count.items()):
        role_emoji = {
            "admin": "👔",
            "cocinero": "👨‍🍳",
            "empaquetador": "📦",
            "delivery": "🚚"
        }.get(role, "👤")
        total_per_role = count * len(TENANTS)
        print(f"   {role_emoji} {role.capitalize():15}: {count} por tenant × {len(TENANTS)} tenants = {total_per_role} total")
    
    print()
    print("🔗 Ejemplos de login:")
    print()
    for tenant in TENANTS[:1]:  # Solo mostrar ejemplos del primer tenant
        print(f"   Tenant: {tenant}")
        print(f"   Admin:        admin1@{tenant}.papasqueens.test / 123456")
        print(f"   Cocinero:     cocinero1@{tenant}.papasqueens.test / 123456")
        print(f"   Empaquetador: empaquetador1@{tenant}.papasqueens.test / 123456")
        print(f"   Delivery:     delivery1@{tenant}.papasqueens.test / 123456")
    print()


if __name__ == "__main__":
    main()
