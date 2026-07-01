import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.database import db
from app.models import User, DrugReference, Prescription, PrescriptionItem, DispensedItem, ValidationResult, AuditLog

def verify_setup():
    app = create_app()
    
    print("=" * 60)
    print("RxVerify: Database Setup and Verification Utility")
    print("=" * 60)
    
    with app.app_context():
        # 1. Create tables
        print("\nStep 1: Dropping & Creating tables for verification...")
        db.drop_all()
        db.create_all()
        print("[OK] Database schema clean initialized.")

        # 2. Add Test User
        print("\nStep 2: Testing User Model, Password Hashing & Role...")
        test_user = User(
            username="dr_john",
            email="john@rxverify.org",
            role="Pharmacist"
        )
        test_user.set_password("SecurePassword123")
        db.session.add(test_user)
        db.session.commit()
        
        # Verify user queries and password hashing
        queried_user = User.query.filter_by(username="dr_john").first()
        assert queried_user is not None, "Failed to retrieve test user"
        assert queried_user.check_password("SecurePassword123"), "Password check failed"
        assert not queried_user.check_password("WrongPassword"), "Password check falsely passed"
        print(f"[OK] User created & verified: {queried_user.username} (Role: {queried_user.role})")

        # 3. Add Drug Reference
        print("\nStep 3: Seeding Drug Reference...")
        drug_ref = DrugReference(
            drug_name="Metformin",
            dosage="500",
            dosage_unit="mg",
            description="Reference Metformin for oral diabetes treatment."
        )
        db.session.add(drug_ref)
        db.session.commit()
        
        queried_drug = DrugReference.query.filter_by(drug_name="Metformin").first()
        assert queried_drug is not None, "Failed to retrieve drug reference"
        print(f"[OK] Drug reference inserted: {queried_drug.drug_name} {queried_drug.dosage}{queried_drug.dosage_unit}")

        # 4. Create Prescription Record
        print("\nStep 4: Creating Prescription and Items (OCR data)...")
        prescription = Prescription(
            patient_name="Alice Smith",
            doctor_name="Dr. House",
            image_filename="prescription_alice_001.jpg",
            image_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            status="Pending",
            pharmacist_id=queried_user.id
        )
        db.session.add(prescription)
        db.session.flush() # Flush to get prescription.id

        # Extracted OCR item
        ocr_item = PrescriptionItem(
            prescription_id=prescription.id,
            drug_name="Metformin",
            dosage="500",
            dosage_unit="mg",
            quantity=30
        )
        db.session.add(ocr_item)
        
        # Pharmacist dispensed item (with mismatch for testing)
        dispensed_item = DispensedItem(
            prescription_id=prescription.id,
            drug_name="Metronidazole", # Mismatched drug
            dosage="400",
            dosage_unit="mg",
            quantity=30
        )
        db.session.add(dispensed_item)
        db.session.commit()

        # Query prescription and check relationships
        queried_rx = Prescription.query.get(prescription.id)
        assert queried_rx is not None
        assert len(queried_rx.items) == 1
        assert len(queried_rx.dispensed_items) == 1
        print(f"[OK] Prescription & related items created successfully for: {queried_rx.patient_name}")
        print(f"  OCR Drug name: {queried_rx.items[0].drug_name}")
        print(f"  Dispensed Drug name: {queried_rx.dispensed_items[0].drug_name}")

        # 5. Add Validation Result
        print("\nStep 5: Logging validation results (PASS/FAIL checks)...")
        val_result = ValidationResult(
            prescription_id=prescription.id,
            status="FAIL",
            mismatch_details={
                "drug_match": False,
                "reason": "OCR extracted 'Metformin 500mg' but pharmacist dispensed 'Metronidazole 400mg'",
                "missing_drugs": ["Metformin"],
                "extra_drugs": ["Metronidazole"]
            },
            validated_by=queried_user.id
        )
        db.session.add(val_result)
        db.session.commit()

        queried_val = ValidationResult.query.filter_by(prescription_id=prescription.id).first()
        assert queried_val is not None
        print(f"[OK] Validation result logged: Status = {queried_val.status}")
        print(f"  Details: {queried_val.mismatch_details}")

        # 6. Add Audit Log
        print("\nStep 6: Recording Audit Log...")
        audit_log = AuditLog(
            user_id=queried_user.id,
            action="VALIDATION_RUN",
            details=f"Pharmacist dr_john executed validation on prescription ID {prescription.id}. Result: FAIL.",
            ip_address="127.0.0.1"
        )
        db.session.add(audit_log)
        db.session.commit()

        queried_log = AuditLog.query.filter_by(action="VALIDATION_RUN").first()
        assert queried_log is not None
        print(f"[OK] Audit log logged: User ID {queried_log.user_id} - Action: {queried_log.action}")
        print(f"  Details: {queried_log.details}")

        # 7. Verification of Cascading deletes
        print("\nStep 7: Testing cascading deletes...")
        db.session.delete(queried_rx)
        db.session.commit()
        
        # Verify related records are gone
        val_count = ValidationResult.query.filter_by(prescription_id=prescription.id).count()
        ocr_count = PrescriptionItem.query.filter_by(prescription_id=prescription.id).count()
        disp_count = DispensedItem.query.filter_by(prescription_id=prescription.id).count()
        
        assert val_count == 0, "ValidationResult was not cascadingly deleted"
        assert ocr_count == 0, "PrescriptionItem was not cascadingly deleted"
        assert disp_count == 0, "DispensedItem was not cascadingly deleted"
        print("[OK] Cascade verification complete. All dependent rows removed.")
        
        print("\n" + "=" * 60)
        print("RxVerify: Database setup and models verified successfully!")
        print("=" * 60)

if __name__ == '__main__':
    verify_setup()
