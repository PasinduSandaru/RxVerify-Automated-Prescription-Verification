from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.database import db
from app.models import Prescription, PrescriptionItem, DispensedItem, ValidationResult, AuditLog, User
from app.utils.auth_helpers import role_required, sanitize_input
from app.utils.crypto import calculate_prescription_hash
from app.services.validation import validate_prescription

validation_bp = Blueprint('validation', __name__)

@validation_bp.route('/<int:rx_id>/validate', methods=['POST'])
@jwt_required()
@role_required(['Pharmacist', 'Admin'])
def validate_dispensed_medications(rx_id):
    """
    Validates pharmacist-entered dispensed medicines against OCR-extracted ones.
    1. Saves dispensed items to DB.
    2. Runs RapidFuzz validation engine.
    3. Commits results and logs transactions.
    """
    prescription = Prescription.query.get_or_404(rx_id)
    
    # Check if request has body data
    data = request.get_json() or {}
    dispensed_raw = data.get('dispensed_items', [])
    
    if not dispensed_raw:
        return jsonify({'message': 'No dispensed medications provided for validation.'}), 400

    current_user_id = get_jwt_identity()

    try:
        # Clear existing dispensed items for this prescription if any (re-runs)
        DispensedItem.query.filter_by(prescription_id=rx_id).delete()

        # Save and sanitize new dispensed items
        dispensed_items_formatted = []
        for item in dispensed_raw:
            # Sanitize inputs to prevent XSS
            drug_name = sanitize_input(item.get('drug_name', ''))
            dosage = sanitize_input(item.get('dosage', ''))
            unit = sanitize_input(item.get('dosage_unit', ''))
            qty = item.get('quantity')
            
            if not drug_name:
                continue
                
            disp_model = DispensedItem(
                prescription_id=rx_id,
                drug_name=drug_name,
                dosage=dosage,
                dosage_unit=unit,
                quantity=int(qty) if qty else None
            )
            db.session.add(disp_model)
            
            dispensed_items_formatted.append({
                'drug_name': drug_name,
                'dosage': dosage,
                'dosage_unit': unit,
                'quantity': qty
            })
            
        db.session.flush() # Populate models

        # Get OCR items
        ocr_items = [{
            'drug_name': item.drug_name,
            'dosage': item.dosage,
            'dosage_unit': item.dosage_unit,
            'quantity': item.quantity
        } for item in prescription.items]

        # Run validation matching engine
        val_result = validate_prescription(ocr_items, dispensed_items_formatted)

        # Clear existing validation results for this prescription if any
        ValidationResult.query.filter_by(prescription_id=rx_id).delete()

        # Save new ValidationResult record
        db_val_result = ValidationResult(
            prescription_id=rx_id,
            status=val_result['status'],
            mismatch_details=val_result['mismatch_details'],
            validated_by=current_user_id
        )
        db.session.add(db_val_result)
        
        # Update Prescription Status
        prescription.status = 'Validated'
        db.session.flush()

        # Re-calculate prescription database record SHA-256 integrity hash
        # (since status changed and dispensed items were attached)
        new_record_hash = calculate_prescription_hash(prescription)
        prescription.image_hash_sha256 = new_record_hash

        # Audit log the validation run
        user = User.query.get(current_user_id)
        log = AuditLog(
            user_id=current_user_id,
            action='VALIDATION_RUN',
            details=f"Pharmacist {user.username} executed validation on Prescription ID {rx_id}. Status: {val_result['status']}.",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'message': 'Medications validated successfully.',
            'validation_id': db_val_result.id,
            'status': val_result['status'],
            'mismatch_details': val_result['mismatch_details']
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to execute validation rules.', 'error': str(e)}), 500


@validation_bp.route('/<int:rx_id>/result', methods=['GET'])
@jwt_required()
def get_validation_details(rx_id):
    """Retrieve detailed mismatch results for a specific prescription validation."""
    result = ValidationResult.query.filter_by(prescription_id=rx_id).first()
    if not result:
        return jsonify({'message': 'No validation validation history found for this prescription.'}), 404
        
    return jsonify(result.to_dict()), 200
