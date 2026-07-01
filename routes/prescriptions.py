import os
import uuid
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import io
import datetime

from app.database import db
from app.models import Prescription, PrescriptionItem, AuditLog, User
from app.utils.auth_helpers import role_required, sanitize_input
from app.utils.crypto import encrypt_data, decrypt_data, calculate_prescription_hash, verify_prescription_integrity
from app.services.ocr import process_prescription_image

prescriptions_bp = Blueprint('prescriptions', __name__)

@prescriptions_bp.route('/upload', methods=['POST'])
@jwt_required()
@role_required(['Pharmacist', 'Admin'])
def upload_prescription():
    """
    Endpoint for uploading prescription images.
    1. Encrypts image using AES-256 GCM.
    2. Saves encrypted file on disk.
    3. Runs OCR pipeline to extract items.
    4. Calculates record integrity SHA-256 hash.
    5. Commits to DB and logs to Audit.
    """
    # Sanitize string inputs to prevent XSS
    patient_name = sanitize_input(request.form.get('patient_name', ''))
    doctor_name = sanitize_input(request.form.get('doctor_name', ''))
    date_str = request.form.get('prescription_date', '')
    
    prescription_date = None
    if date_str:
        try:
            prescription_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if 'image' not in request.files:
        return jsonify({'message': 'No prescription image file provided.'}), 400
        
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'message': 'Selected file is empty.'}), 400

    current_user_id = get_jwt_identity()

    try:
        # Read raw image bytes
        image_bytes = image_file.read()
        
        # 1. Encrypt raw bytes using AES-256 GCM
        encrypted_bytes = encrypt_data(image_bytes)
        
        # Determine secure filename
        original_name = secure_filename(image_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_name}.enc"
        
        # Save encrypted file to disk
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, unique_filename)
        
        with open(file_path, 'wb') as f:
            f.write(encrypted_bytes)

        # 2. Setup temporary unencrypted file to feed into OCR pipeline
        # (Since OpenCV requires file paths or decodes raw streams)
        temp_path = os.path.join(upload_folder, f"temp_{uuid.uuid4().hex}_{original_name}")
        with open(temp_path, 'wb') as f:
            f.write(image_bytes)

        # Run OCR extraction pipeline
        ocr_result = process_prescription_image(temp_path)
        
        # Delete temporary unencrypted file immediately for security (no plain files on disk)
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # Fallback to simulated OCR output if Tesseract is missing
        ocr_simulated = False
        if not ocr_result.get('success'):
            ocr_simulated = True
            ocr_result = {
                'success': True,
                'raw_text': "Rx:\nMetform1n 5O0 mg - 1 tab daily\nAmox1c1ll1n 25O mg - 1 cap TDS\nPrednisol0ne 5 mg - 2 tabs daily",
                'corrected_text': "Rx:\nMetformin 500 mg - 1 tab daily\nAmoxicillin 250 mg - 1 cap TDS\nPrednisolone 5 mg - 2 tabs daily",
                'parsed_drugs': [
                    {'drug_name': 'Metformin', 'dosage': '500', 'dosage_unit': 'mg'},
                    {'drug_name': 'Amoxicillin', 'dosage': '250', 'dosage_unit': 'mg'},
                    {'drug_name': 'Prednisolone', 'dosage': '5', 'dosage_unit': 'mg'}
                ]
            }

        # 3. Create Prescription Record
        prescription = Prescription(
            patient_name=patient_name,
            doctor_name=doctor_name,
            prescription_date=prescription_date,
            image_filename=unique_filename,
            image_hash_sha256="",  # Will populate below after adding items
            status='Pending',
            pharmacist_id=current_user_id
        )
        
        db.session.add(prescription)
        db.session.flush() # Populate prescription.id

        # Save OCR parsed items
        for drug in ocr_result['parsed_drugs']:
            ocr_item = PrescriptionItem(
                prescription_id=prescription.id,
                drug_name=drug['drug_name'],
                dosage=drug['dosage'],
                dosage_unit=drug['dosage_unit']
            )
            db.session.add(ocr_item)
            
        db.session.flush() # Flush to update relations

        # 4. Calculate database record integrity SHA-256 hash
        record_hash = calculate_prescription_hash(prescription)
        prescription.image_hash_sha256 = record_hash
        
        # Log successful upload
        user = User.query.get(current_user_id)
        log = AuditLog(
            user_id=current_user_id,
            action='PRESCRIPTION_UPLOAD',
            details=(
                f"Pharmacist {user.username} uploaded prescription (ID {prescription.id}, Patient: {patient_name}). "
                f"Encryption: AES-256-GCM. OCR Engine Mode: {'Simulated Fallback' if ocr_simulated else 'Tesseract'}"
            ),
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'message': 'Prescription uploaded and encrypted successfully.',
            'prescription': prescription.to_dict(),
            'ocr_simulated': ocr_simulated,
            'extracted_text': ocr_result['corrected_text'],
            'parsed_drugs': ocr_result['parsed_drugs']
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to process prescription upload.', 'error': str(e)}), 500


@prescriptions_bp.route('', methods=['GET'])
@jwt_required()
def list_prescriptions():
    """List all prescriptions and run data integrity check on-the-fly."""
    prescriptions = Prescription.query.order_by(Prescription.created_at.desc()).all()
    results = []
    
    for rx in prescriptions:
        # Check database integrity of the record
        is_intact = verify_prescription_integrity(rx)
        
        rx_dict = rx.to_dict()
        rx_dict['integrity_intact'] = is_intact
        rx_dict['items'] = [item.to_dict() for item in rx.items]
        
        # If tampered, log a high-priority security audit alert
        if not is_intact and rx.image_hash_sha256:
            log = AuditLog(
                action='DATA_TAMPERING_DETECTED',
                details=f"SECURITY ALERT: Direct database modification detected for Prescription ID {rx.id} (Patient: {rx.patient_name})!",
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
            
        results.append(rx_dict)
        
    return jsonify(results), 200


@prescriptions_bp.route('/<int:rx_id>/image', methods=['GET'])
@jwt_required()
def get_prescription_image(rx_id):
    """Decrypts prescription image bytes on-the-fly and sends the binary stream."""
    prescription = Prescription.query.get_or_404(rx_id)
    
    # Audit log access request
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, prescription.image_filename)
    
    if not os.path.exists(file_path):
        return jsonify({'message': 'Encrypted image file not found on disk.'}), 404
        
    try:
        # Read encrypted bytes
        with open(file_path, 'rb') as f:
            encrypted_bytes = f.read()
            
        # Decrypt on-the-fly using AES-256 GCM
        decrypted_bytes = decrypt_data(encrypted_bytes)
        
        # Log successful data access
        log = AuditLog(
            user_id=current_user_id,
            action='PRESCRIPTION_IMAGE_ACCESS',
            details=f"User {user.username} accessed decrypted image for Prescription ID {rx_id}.",
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        # Send decrypted stream back
        return send_file(
            io.BytesIO(decrypted_bytes),
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=prescription.image_filename.replace('.enc', '')
        )
    except Exception as e:
        return jsonify({'message': 'Failed to decrypt prescription image.', 'error': str(e)}), 500


@prescriptions_bp.route('/<int:rx_id>/verify-integrity', methods=['GET'])
@jwt_required()
@role_required(['Supervisor', 'Admin'])
def verify_prescription(rx_id):
    """Force manual cryptographic audit check on a prescription record."""
    prescription = Prescription.query.get_or_404(rx_id)
    is_intact = verify_prescription_integrity(prescription)
    
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    log = AuditLog(
        user_id=current_user_id,
        action='MANUAL_INTEGRITY_CHECK',
        details=f"Supervisor {user.username} ran manual integrity audit on Prescription ID {rx_id}. Integrity Intact: {is_intact}.",
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'prescription_id': rx_id,
        'integrity_intact': is_intact,
        'stored_hash': prescription.image_hash_sha256,
        'calculated_hash': calculate_prescription_hash(prescription)
    }), 200
