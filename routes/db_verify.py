from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.database import db
from app.models import DrugReference, User, AuditLog
from app.utils.auth_helpers import role_required

db_bp = Blueprint('db', __name__)

@db_bp.route('/status', methods=['GET'])
def db_status():
    """Verify database connection status and fetch table counts."""
    try:
        # Check if database is accessible
        db.session.execute(db.text("SELECT 1"))
        
        # Gather counts
        user_count = User.query.count()
        drug_count = DrugReference.query.count()
        
        # Log successful connection check
        log = AuditLog(
            action='DB_STATUS_CHECK',
            details='Database status checked and verified successful connection.',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'status': 'connected',
            'database': db.engine.name,
            'summary': {
                'users': user_count,
                'drug_references': drug_count
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Failed to connect to the database.',
            'error': str(e)
        }), 500


@db_bp.route('/seed', methods=['POST'])
def seed_database():
    """Populates the DrugReference table with common research proposal test cases."""
    try:
        # Sample drugs referenced in RxVerify research proposal (e.g., Metformin, Metronidazole, Prednisolone, Prednisone, Amoxicillin)
        sample_drugs = [
            {'drug_name': 'Metformin', 'dosage': '500', 'dosage_unit': 'mg', 'description': 'Oral diabetes medicine'},
            {'drug_name': 'Metformin', 'dosage': '850', 'dosage_unit': 'mg', 'description': 'Oral diabetes medicine'},
            {'drug_name': 'Metformin', 'dosage': '1000', 'dosage_unit': 'mg', 'description': 'Oral diabetes medicine'},
            {'drug_name': 'Metronidazole', 'dosage': '400', 'dosage_unit': 'mg', 'description': 'Antibiotic for bacterial infections'},
            {'drug_name': 'Metronidazole', 'dosage': '500', 'dosage_unit': 'mg', 'description': 'Antibiotic for bacterial infections'},
            {'drug_name': 'Prednisolone', 'dosage': '5', 'dosage_unit': 'mg', 'description': 'Corticosteroid medication'},
            {'drug_name': 'Prednisolone', 'dosage': '10', 'dosage_unit': 'mg', 'description': 'Corticosteroid medication'},
            {'drug_name': 'Prednisone', 'dosage': '5', 'dosage_unit': 'mg', 'description': 'Corticosteroid medication'},
            {'drug_name': 'Prednisone', 'dosage': '10', 'dosage_unit': 'mg', 'description': 'Corticosteroid medication'},
            {'drug_name': 'Amoxicillin', 'dosage': '250', 'dosage_unit': 'mg', 'description': 'Penicillin antibiotic'},
            {'drug_name': 'Amoxicillin', 'dosage': '500', 'dosage_unit': 'mg', 'description': 'Penicillin antibiotic'},
            {'drug_name': 'Atorvastatin', 'dosage': '10', 'dosage_unit': 'mg', 'description': 'Cholesterol-lowering statin'},
            {'drug_name': 'Atorvastatin', 'dosage': '20', 'dosage_unit': 'mg', 'description': 'Cholesterol-lowering statin'},
            {'drug_name': 'Paracetamol', 'dosage': '500', 'dosage_unit': 'mg', 'description': 'Analgesic and antipyretic'},
            {'drug_name': 'Omeprazole', 'dosage': '20', 'dosage_unit': 'mg', 'description': 'Proton-pump inhibitor for acid reflux'}
        ]

        added_count = 0
        for drug_data in sample_drugs:
            # Check if this drug already exists to avoid duplication errors
            existing = DrugReference.query.filter_by(
                drug_name=drug_data['drug_name'],
                dosage=drug_data['dosage'],
                dosage_unit=drug_data['dosage_unit']
            ).first()
            
            if not existing:
                drug = DrugReference(**drug_data)
                db.session.add(drug)
                added_count += 1

        if added_count > 0:
            db.session.commit()
            
            # Log auditing
            log = AuditLog(
                action='DB_SEED_DRUGS',
                details=f'Seeded {added_count} new drug references into the database.',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

        return jsonify({
            'message': 'Database seeded successfully.',
            'added_count': added_count,
            'total_count': DrugReference.query.count()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'message': 'Database seeding failed.',
            'error': str(e)
        }), 500

@db_bp.route('/audits', methods=['GET'])
@jwt_required()
@role_required(['Supervisor', 'Admin'])
def get_audit_logs():
    """Fetches all system audit logs for security oversight."""
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return jsonify([log.to_dict() for log in logs]), 200

