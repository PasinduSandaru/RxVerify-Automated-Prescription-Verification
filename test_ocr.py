import os
import sys
import cv2

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.services.ocr import preprocess_image, correct_misreads, parse_drugs_and_dosages, process_prescription_image

def run_test():
    # Make sure app context is loaded (so config reads TESSERACT_CMD)
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("RxVerify: OCR Preprocessing & Extraction Test Utility")
        print("=" * 60)

        # Look for sample images in the project root
        workspace_dir = os.path.abspath(os.path.dirname(__file__))
        sample_images = [
            os.path.join(workspace_dir, "prescription 1.jpg"),
            os.path.join(workspace_dir, "prescription 2.jpg"),
            os.path.join(workspace_dir, "Prescription 3.jpg")
        ]

        found_image = None
        for img_path in sample_images:
            if os.path.exists(img_path):
                found_image = img_path
                break

        if not found_image:
            print("ERROR: No sample prescription images found in the workspace root.")
            print("Expected to find: 'prescription 1.jpg', 'prescription 2.jpg', or 'Prescription 3.jpg'")
            return

        print(f"\nProcessing Image: {os.path.basename(found_image)}")
        
        # 1. Test Preprocessing and save intermediate outputs for debugging
        debug_dir = os.path.join(workspace_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        print(f"Saving debug images to: {debug_dir}")

        try:
            # Grayscale & Deskewing & Thresholding
            img = cv2.imread(found_image)
            cv2.imwrite(os.path.join(debug_dir, "01_original.jpg"), img)
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(os.path.join(debug_dir, "02_grayscale.jpg"), gray)
            
            # Use ocr functions
            from app.services.ocr import deskew
            rotated = deskew(gray)
            cv2.imwrite(os.path.join(debug_dir, "03_deskewed.jpg"), rotated)
            
            preprocessed = preprocess_image(found_image)
            cv2.imwrite(os.path.join(debug_dir, "04_preprocessed_binary.jpg"), preprocessed)
            print("[OK] Preprocessing completed. Debug images saved successfully.")
        except Exception as e:
            print(f"Pre-processing save failed (non-blocking for OCR): {e}")

        # 2. Run core OCR orchestration
        print("\nRunning Tesseract OCR & Post-Processing...")
        result = process_prescription_image(found_image)

        if not result['success']:
            print(f"\n[NOTICE] OCR Pipeline failed to run Tesseract binary: {result.get('error')}")
            print("This is normal if Tesseract OCR is not installed on your system.")
            print("\n" + "-"*50)
            print("SIMULATING OCR CORRECTION AND PARSING LOGIC DEMO:")
            print("-"*50)
            
            # Mock OCR raw text with common misreads
            mock_raw_text = (
                "RxVerify Prescription\n"
                "Patient Name: Alice Smith\n"
                "Doctor: Dr. Mewan Jayathilake\n"
                "\n"
                "Rx:\n"
                "Metform1n 5O0 mg - 1 tab daily\n"
                "Metronidazole 4OOmg - 1 tab TDS\n"
                "Amox1c1ll1n 25O mg - 1 cap TDS\n"
                "0meprazole 2o mg - 1 cap daily before meals\n"
                "Prednisol0ne 5 mg - 2 tabs daily\n"
            )
            
            # Apply corrections and parse
            corrected = correct_misreads(mock_raw_text)
            parsed = parse_drugs_and_dosages(corrected)
            
            print("\n--- SIMULATED RAW TESSERACT TEXT (With typical character misreads) ---")
            print(mock_raw_text)
            print("-" * 60)

            print("\n--- SIMULATED CORRECTED TEXT (After post-processing rules) ---")
            print(corrected)
            print("-" * 60)

            print("\n--- PARSED DRUGS AND DOSAGES FROM CORRECTED TEXT ---")
            if parsed:
                for i, item in enumerate(parsed, 1):
                    print(f"{i}. Drug: {item['drug_name']} | Dosage: {item['dosage']} | Unit: {item['dosage_unit']}")
            else:
                print("[No drugs parsed]")
            print("=" * 60)
            print("To run this against the actual image text:")
            print("1. Install Tesseract OCR for Windows (UB Mannheim installer)")
            print("2. Set the correct installation path in the .env file (e.g. TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe)")
            return

        print("\n--- RAW TESSERACT TEXT ---")
        print(result['raw_text'] if result['raw_text'].strip() else "[No text extracted]")
        print("-" * 30)

        print("\n--- CORRECTED TEXT (Post-Processed) ---")
        print(result['corrected_text'] if result['corrected_text'].strip() else "[No text extracted]")
        print("-" * 30)

        print("\n--- PARSED DRUGS AND DOSAGES ---")
        parsed = result['parsed_drugs']
        if parsed:
            for i, item in enumerate(parsed, 1):
                print(f"{i}. Drug: {item['drug_name']} | Dosage: {item['dosage']} | Unit: {item['dosage_unit']}")
        else:
            print("[No drugs parsed. Make sure the text contains drug names and dosages]")
        print("=" * 60)

if __name__ == '__main__':
    run_test()
