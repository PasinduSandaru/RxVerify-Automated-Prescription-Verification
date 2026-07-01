import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.validation import validate_prescription

def run_tests():
    print("=" * 60)
    print("RxVerify: Validation Engine (RapidFuzz Jaro-Winkler) Test Runner")
    print("=" * 60)

    # OCR Extracted Prescriptions (Baseline)
    ocr_items = [
        {'drug_name': 'Metformin', 'dosage': '500', 'dosage_unit': 'mg'},
        {'drug_name': 'Amoxicillin', 'dosage': '250', 'dosage_unit': 'mg'}
    ]

    # Test Case 1: Perfect Match (PASS)
    print("\nTest Case 1: Perfect Match")
    disp_1 = [
        {'drug_name': 'Metformin', 'dosage': '500', 'dosage_unit': 'mg'},
        {'drug_name': 'Amoxicillin', 'dosage': '250', 'dosage_unit': 'mg'}
    ]
    res_1 = validate_prescription(ocr_items, disp_1)
    print(f"Status: {res_1['status']}")
    assert res_1['status'] == 'PASS'
    print("[OK] Perfect match passed.")

    # Test Case 2: Minor spelling typos (WARNING)
    print("\nTest Case 2: Spelling Typo ('Amoxicilin' vs 'Amoxicillin')")
    disp_2 = [
        {'drug_name': 'Metformin', 'dosage': '500', 'dosage_unit': 'mg'},
        {'drug_name': 'Amoxicilin', 'dosage': '250', 'dosage_unit': 'mg'} # Jaro-Winkler matches
    ]
    res_2 = validate_prescription(ocr_items, disp_2)
    print(f"Status: {res_2['status']}")
    assert res_2['status'] == 'WARNING'
    assert res_2['mismatch_details']['has_spelling_warning'] is True
    print("[OK] Spelling typo warning logged.")

    # Test Case 3: Dosage mismatch (FAIL)
    print("\nTest Case 3: Dosage Strength Mismatch (500mg vs 850mg)")
    disp_3 = [
        {'drug_name': 'Metformin', 'dosage': '850', 'dosage_unit': 'mg'}, # Mismatch dosage
        {'drug_name': 'Amoxicillin', 'dosage': '250', 'dosage_unit': 'mg'}
    ]
    res_3 = validate_prescription(ocr_items, disp_3)
    print(f"Status: {res_3['status']}")
    assert res_3['status'] == 'FAIL'
    assert res_3['mismatch_details']['has_dosage_mismatch'] is True
    print("[OK] Dosage mismatch fail logged.")

    # Test Case 4: Missing medication (FAIL)
    print("\nTest Case 4: Missing Medication (Amoxicillin not dispensed)")
    disp_4 = [
        {'drug_name': 'Metformin', 'dosage': '500', 'dosage_unit': 'mg'}
    ]
    res_4 = validate_prescription(ocr_items, disp_4)
    print(f"Status: {res_4['status']}")
    assert res_4['status'] == 'FAIL'
    assert len(res_4['mismatch_details']['missing_drugs']) == 1
    assert res_4['mismatch_details']['missing_drugs'][0]['drug_name'] == 'Amoxicillin'
    print("[OK] Missing drug fail logged.")

    # Test Case 5: Extra unprescribed medication (FAIL)
    print("\nTest Case 5: Extra Medication (Metronidazole dispensed but not prescribed)")
    disp_5 = [
        {'drug_name': 'Metformin', 'dosage': '500', 'dosage_unit': 'mg'},
        {'drug_name': 'Amoxicillin', 'dosage': '250', 'dosage_unit': 'mg'},
        {'drug_name': 'Metronidazole', 'dosage': '400', 'dosage_unit': 'mg'} # Extra
    ]
    res_5 = validate_prescription(ocr_items, disp_5)
    print(f"Status: {res_5['status']}")
    assert res_5['status'] == 'FAIL'
    assert len(res_5['mismatch_details']['extra_drugs']) == 1
    assert res_5['mismatch_details']['extra_drugs'][0]['drug_name'] == 'Metronidazole'
    print("[OK] Extra drug fail logged.")

    print("\n" + "=" * 60)
    print("All validation rule engine test cases passed successfully!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
