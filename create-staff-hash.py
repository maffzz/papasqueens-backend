#!/usr/bin/env python3
import hashlib
import sys

def hash_password(password, salt="papasqueens_salt"):
    """Hash password usando SHA256 con salt"""
    return hashlib.sha256(f"{salt}{password}".encode('utf-8')).hexdigest()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python create-staff-hash.py <password>")
        print("\nEjemplo:")
        print("  python create-staff-hash.py miPassword123")
        sys.exit(1)
    
    password = sys.argv[1]
    
    # Hash sin salt (simple)
    hash_simple = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    # Hash con salt
    hash_salted = hash_password(password)
    
    print(f"\n🔐 Hashes para password: '{password}'")
    print(f"\n1. Sin salt (simple):")
    print(f"   {hash_simple}")
    print(f"\n2. Con salt 'papasqueens_salt':")
    print(f"   {hash_salted}")
    print(f"\n📋 Item para DynamoDB:")
    print(f"""
{{
  "tenant_id": "default",
  "id_staff": "admin-001",
  "name": "Admin Principal",
  "email": "admin@papasqueens.com",
  "role": "admin",
  "status": "activo",
  "password_hash": "{hash_simple}"
}}
""")
