#!/usr/bin/env python3
"""
Script rápido para eliminar TODOS los registros de Staff
⚠️  CUIDADO: Esto borra TODO sin preguntar
"""
import boto3
from boto3.dynamodb.conditions import Key

DYNAMO_REGION = "us-east-1"
TABLE_NAME = "Staff"

TENANTS = [
    "tenant_pq_barranco",
    "tenant_pq_puruchuco",
    "tenant_pq_villamaria",
    "tenant_pq_jiron",
]


def main():
    session = boto3.Session(region_name=DYNAMO_REGION)
    dynamo = session.resource("dynamodb")
    table = dynamo.Table(TABLE_NAME)

    print("=" * 80)
    print("🗑️  LIMPIEZA TOTAL DE STAFF")
    print("=" * 80)
    
    total_deleted = 0
    
    for tenant in TENANTS:
        print(f"\n🏪 Limpiando {tenant}...")
        
        try:
            response = table.query(
                KeyConditionExpression=Key("tenant_id").eq(tenant)
            )
            
            items = response.get("Items", [])
            
            for item in items:
                role_emoji = {
                    "admin": "👔",
                    "cocinero": "👨‍🍳",
                    "empaquetador": "📦",
                    "delivery": "🚚",
                    "staff": "👤"
                }.get(item.get("role", ""), "❓")
                
                print(f"   🗑️  {role_emoji} {item['id_staff']:40} | {item.get('name', 'N/A')}")
                
                table.delete_item(
                    Key={
                        "tenant_id": item["tenant_id"],
                        "id_staff": item["id_staff"]
                    }
                )
                total_deleted += 1
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print(f"✅ Limpieza completada: {total_deleted} registros eliminados")
    print("=" * 80)


if __name__ == "__main__":
    main()
