#!/usr/bin/env python3
import boto3
import hashlib
import sys
from datetime import datetime

def hash_password(password):
    """Hash password usando SHA256 simple"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_admin(tenant_id, email, password, name="Administrador"):
    """Crea un usuario admin en la tabla Staff"""
    
    # Conectar a DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Staff')
    
    # Generar hash
    password_hash = hash_password(password)
    
    # Crear item
    item = {
        'tenant_id': tenant_id,
        'id_staff': f'admin-{email.split("@")[0]}',
        'name': name,
        'email': email,
        'role': 'admin',
        'status': 'activo',
        'password_hash': password_hash,
        'hire_date': datetime.utcnow().isoformat()
    }
    
    # Guardar en DynamoDB
    try:
        table.put_item(Item=item)
        print(f"\n✅ Admin creado exitosamente!")
        print(f"\n📋 Detalles:")
        print(f"   Tenant ID: {tenant_id}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   ID Staff: {item['id_staff']}")
        print(f"   Password Hash: {password_hash}")
        print(f"\n🔐 Usa estas credenciales para hacer login:")
        print(f"""
{{
  "username": "{email}",
  "password": "{password}",
  "tenant_id": "{tenant_id}"
}}
""")
        return True
    except Exception as e:
        print(f"\n❌ Error al crear admin: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Creador de Admin para Papas Queen's\n")
    
    # Obtener datos
    if len(sys.argv) >= 4:
        tenant_id = sys.argv[1]
        email = sys.argv[2]
        password = sys.argv[3]
        name = sys.argv[4] if len(sys.argv) > 4 else "Administrador"
    else:
        print("Uso: python create-admin.py <tenant_id> <email> <password> [nombre]")
        print("\nEjemplo:")
        print('  python create-admin.py tenant_pq_barranco admin@papasqueens.com admin123 "Admin Principal"')
        print("\nO ejecuta sin argumentos para modo interactivo:")
        
        tenant_id = input("\n1. Tenant ID (ej: tenant_pq_barranco): ").strip()
        email = input("2. Email: ").strip()
        password = input("3. Password: ").strip()
        name = input("4. Nombre (Enter para 'Administrador'): ").strip() or "Administrador"
    
    # Validar
    if not tenant_id or not email or not password:
        print("\n❌ Todos los campos son requeridos")
        sys.exit(1)
    
    # Crear admin
    create_admin(tenant_id, email, password, name)
