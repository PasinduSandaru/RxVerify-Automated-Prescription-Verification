import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.database import db
from app.models import Prescription, PrescriptionItem, User
from app.utils.crypto import encrypt_data, decrypt_data, calculate_prescription_hash, verify_prescription_integrity

def run_tests():
    app = create_app()
    
    print("=" * 60)
    print("RxVerify: Cybersecurity Mechanisms Demonstration Runner")
    print("=" * 60)

    # Test Case 1: AES-256 GCM File Encryption & Decryption
    print("\n[PART 1] Testing AES-256 GCM File Encryption...")
    original_text = b"Confidential Prescription Image Data - Visual Elements & Handwriting OCR raw bytes"
    
    # Encrypt
    encrypted_data = encrypt_data(original_text)
    print(f"[OK] File Encrypted successfully. Original size: {len(original_text)} bytes | Encrypted size: {len(encrypted_data)} bytes")
    assert original_text != encrypted_data, "Plaintext and ciphertext must not match"
    
    # Decrypt
    decrypted_text = decrypt_data(encrypted_data)
    print(f"[OK] File Decrypted successfully. Decrypted content: '{decrypted_text.decode()}'")
    assert original_text == decrypted_text, "Decrypted data must match original text"

    # Test Case 2: SHA-256 Prescription Record Hashing and Tamper Auditing
    print("\n[PART 2] Testing SHA-256 Record Hashing & Database Tampering Detection...")
    
    with app.app_context():
        # Clear database and initialize
        db.create_all()
        
        # Add test user (Pharmacist)
        user = User(username="dr_auditor", email="auditor@rxverify.org", role="Pharmacist")
        user.set_password("AuditPassword")
        db.session.add(user)
        db.session.commit()

        # Create Prescription record
        rx = Prescription(
            patient_name="Bob Miller",
            doctor_name="Dr. Watson",
            status="Pending",
            pharmacist_id=user.id
        )
        db.session.add(rx)
        db.session.flush()

        # Add item
        item = PrescriptionItem(
            prescription_id=rx.id,
            drug_name="Metformin",
            dosage="500",
            dosage_unit="mg",
            quantity=30
        )
        db.session.add(item)
        db.session.flush()

        # Calculate cryptographical hash signature and store it
        record_hash = calculate_prescription_hash(rx)
        rx.image_hash_sha256 = record_hash
        db.session.commit()
        
        print(f"[OK] Stored prescription record hash signature: {record_hash}")
        
        # Verify integrity initially
        is_intact = verify_prescription_integrity(rx)
        print(f"[OK] Database integrity check: {'INTACT' if is_intact else 'TAMPERED'}")
        assert is_intact is True, "Database must be intact at start"

        # Simulate Direct Database Tampering (e.g. SQL Injection update or malicious admin change)
        print("\nSIMULATING DIRECT DATABASE TAMPERING: Modifying Patient Name directly in DB...")
        
        # We modify the database patient name directly without recalculating or updating the signature
        db.session.execute(
            db.text("UPDATE prescriptions SET patient_name = 'Malicious Hack' WHERE id = :id"),
            {"id": rx.id}
        )
        db.session.commit()
        
        # Refresh session
        db.session.expire_all()
        tampered_rx = Prescription.query.get(rx.id)
        
        print(f"Tampered Record patient_name in database: '{tampered_rx.patient_name}'")
        print(f"Stored integrity signature remains: {tampered_rx.image_hash_sha256}")

        # Recalculate and audit
        is_still_intact = verify_prescription_integrity(tampered_rx)
        print(f"[OK] Recalculating audit check: {'INTACT' if is_still_intact else 'SECURITY ALERT: DATABASE RECORD TAMPERED OR ALTERED OUTSIDE THE APP!'}")
        assert is_still_intact is False, "Database tampering must be caught"

    print("\n" + "=" * 60)
    print("All cybersecurity mechanism checks passed successfully!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
