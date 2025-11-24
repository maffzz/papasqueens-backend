#!/usr/bin/env python3
"""
Script para eliminar los datos de seed de la tabla Staff en DynamoDB
"""
import boto3
from boto3.dynamodb.conditions import Key, Attr

DYNAMO_REGION = "us-east-1"
TABLE_NAME = "Staff"

TENANTS = [
    "tenant_pq_barranco",
    "tenant_pq_puruchuco",
    "tenant_pq_villamaria",
    "tenant_pq_jiron",
]


def delete_all_staff_by_tenant(table, tenant_id):
    """Elimina todos los registros de staff de un tenant específico"""
    try:
        # Query por tenant_id (partition key)
        response = table.query(
            KeyConditionExpression=Key("tenant_id").eq(tenant_id)
        )
        
        items = response.get("Items", [])
        deleted_count = 0
        
        for item in items:
            print(f"   🗑️  Eliminando: {item['id_staff']} ({item.get('name', 'N/A')}) - {item.get('role', 'N/A')}")
            table.delete_item(
                Key={
                    "tenant_id": item["tenant_id"],
                    "id_staff": item["id_staff"]
                }
            )
            deleted_count += 1
        
        return deleted_count
    except Exception as e:
        print(f"   ❌ Error al eliminar staff de {tenant_id}: {e}")
        return 0


def delete_specific_staff(table, tenant_id, id_staff):
    """Elimina un staff específico"""
    try:
        print(f"   🗑️  Eliminando: {tenant_id} / {id_staff}")
        table.delete_item(
            Key={
                "tenant_id": tenant_id,
                "id_staff": id_staff
            }
        )
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def list_all_staff(table):
    """Lista todos los registros de staff"""
    print("\n📋 Listando todos los registros de Staff:")
    print("=" * 80)
    
    total = 0
    for tenant in TENANTS:
        try:
            response = table.query(
                KeyConditionExpression=Key("tenant_id").eq(tenant)
            )
            items = response.get("Items", [])
            
            if items:
                print(f"\n🏪 {tenant} ({len(items)} registros):")
                for item in items:
                    role_emoji = {
                        "admin": "👔",
                        "cocinero": "👨‍🍳",
                        "empaquetador": "📦",
                        "delivery": "🚚",
                        "staff": "👤"
                    }.get(item.get("role", ""), "❓")
                    
                    print(f"   {role_emoji} {item['id_staff']:40} | {item.get('name', 'N/A'):20} | {item.get('role', 'N/A')}")
                    total += 1
        except Exception as e:
            print(f"   ❌ Error al listar {tenant}: {e}")
    
    print(f"\n📊 Total de registros: {total}")
    print("=" * 80)
    return total


def main():
    session = boto3.Session(region_name=DYNAMO_REGION)
    dynamo = session.resource("dynamodb")
    table = dynamo.Table(TABLE_NAME)

    print("=" * 80)
    print("🗑️  DELETE SEED STAFF - PAPAS QUEEN'S")
    print("=" * 80)
    print(f"📋 Tabla: {TABLE_NAME}")
    print(f"🌎 Región: {DYNAMO_REGION}")
    print("=" * 80)
    
    # Listar primero
    total_before = list_all_staff(table)
    
    if total_before == 0:
        print("\n✅ No hay registros para eliminar")
        return
    
    print("\n⚠️  OPCIONES:")
    print("   1. Eliminar TODO el seed (todos los tenants)")
    print("   2. Eliminar un tenant específico")
    print("   3. Eliminar un staff específico")
    print("   4. Cancelar")
    
    choice = input("\n👉 Selecciona una opción (1-4): ").strip()
    
    if choice == "1":
        confirm = input(f"\n⚠️  ¿Estás seguro de eliminar {total_before} registros? (escribe 'SI' para confirmar): ").strip()
        if confirm == "SI":
            print("\n🗑️  Eliminando todos los registros...")
            total_deleted = 0
            for tenant in TENANTS:
                print(f"\n🏪 Procesando {tenant}:")
                deleted = delete_all_staff_by_tenant(table, tenant)
                total_deleted += deleted
            
            print("\n" + "=" * 80)
            print(f"✅ Eliminación completada: {total_deleted} registros eliminados")
            print("=" * 80)
        else:
            print("\n❌ Operación cancelada")
    
    elif choice == "2":
        print("\n🏪 Tenants disponibles:")
        for i, tenant in enumerate(TENANTS, 1):
            print(f"   {i}. {tenant}")
        
        tenant_choice = input("\n👉 Selecciona el número del tenant: ").strip()
        try:
            tenant_idx = int(tenant_choice) - 1
            if 0 <= tenant_idx < len(TENANTS):
                tenant = TENANTS[tenant_idx]
                confirm = input(f"\n⚠️  ¿Eliminar todos los registros de {tenant}? (escribe 'SI'): ").strip()
                if confirm == "SI":
                    print(f"\n🗑️  Eliminando registros de {tenant}...")
                    deleted = delete_all_staff_by_tenant(table, tenant)
                    print(f"\n✅ {deleted} registros eliminados de {tenant}")
                else:
                    print("\n❌ Operación cancelada")
            else:
                print("\n❌ Opción inválida")
        except ValueError:
            print("\n❌ Entrada inválida")
    
    elif choice == "3":
        tenant_id = input("\n👉 Tenant ID (ej: tenant_pq_barranco): ").strip()
        id_staff = input("👉 ID Staff (ej: tenant_pq_barranco_admin1): ").strip()
        
        confirm = input(f"\n⚠️  ¿Eliminar {tenant_id} / {id_staff}? (escribe 'SI'): ").strip()
        if confirm == "SI":
            if delete_specific_staff(table, tenant_id, id_staff):
                print("\n✅ Registro eliminado")
            else:
                print("\n❌ No se pudo eliminar el registro")
        else:
            print("\n❌ Operación cancelada")
    
    else:
        print("\n❌ Operación cancelada")


if __name__ == "__main__":
    main()
