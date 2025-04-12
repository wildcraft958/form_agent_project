import os
import json
import re
import requests
from dotenv import load_dotenv
from src.html_converter import convert_html_to_json
from src.JSON_converter import convert_json_to_html
from src.llm_handler import LLMHandler
from src.chat_history import ChatHistoryManager
from src.form_processor import EnhancedFormProcessor
from src.mrrttemplate_parser import MRRTParser

# Load environment variables
load_dotenv()

def read_html_file(file_path):
    """Read HTML file content with improved error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None
    except Exception as e:
        print(f"Unexpected error reading file: {str(e)}")
        return None

def save_json_to_file(json_data, file_path):
    """Save JSON data to file with directory creation."""
    try:
        # Create directory if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        print(f"Successfully saved JSON to {file_path}")
    except Exception as e:
        print(f"Error saving JSON file: {str(e)}")

def fetch_radreport_template(template_id):
    """Fetch MRRT template from RadReport.org"""
    url = f"https://radreport.org/template/{template_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching template: {str(e)}")
        return None

def enhance_form_schema(form_json):
    """Enhance the form schema with additional metadata for better interaction."""
    enhanced_form = dict(form_json)
    
    # Add field descriptions and validation metadata
    field_metadata = {
        "patient_name": {
            "description": "Enter the patient's full legal name as it appears on their medical records.",
            "validation": r"^[A-Za-z\s\-'.]+$",
            "validation_message": "Name should contain only letters, spaces, hyphens, and apostrophes."
        },
        "patient_dob": {
            "description": "Enter the patient's date of birth in MM/DD/YYYY format.",
            "type": "date"
        },
        "patient_id": {
            "description": "Enter the patient's unique medical ID number or insurance identifier."
        },
        "diagnosis": {
            "description": "Enter the patient's diagnosis or reason for prescription.",
            "type": "textarea"
        },
        "medication": {
            "description": "Enter the prescribed medication name (generic or brand name)."
        },
        "dosage": {
            "description": "Enter the prescribed dosage amount (e.g., 500mg, 10ml).",
            "validation": r"^\d+(\.\d+)?\s*[a-zA-Z]+$",
            "validation_message": "Dosage should include a number followed by a unit (e.g., 10mg, 5ml)."
        },
        "frequency": {
            "description": "How often should the patient take this medication?",
            "type": "select"
        },
        "duration": {
            "description": "For how many days should the medication be taken?",
            "type": "number",
            "validation": r"^\d+$",
            "validation_message": "Duration should be a positive whole number of days."
        },
        "special_instructions": {
            "description": "Enter any special instructions for taking this medication (e.g., with food, before bedtime).",
            "type": "textarea",
            "required": False
        }
    }
    
    # Update form fields with enhanced metadata
    for field_name, metadata in field_metadata.items():
        if field_name in enhanced_form:
            enhanced_form[field_name].update(metadata)
    
    return enhanced_form

def get_project_paths():
    """Get standardized project paths."""
    return {
        "samples": "./samples",
        "filled_form": "./filled_form.json",
        "fhir_output": "./fhir_diagnosticreport.json"
    }

def main():
    """Main execution flow with enhanced error handling and user experience."""
    paths = get_project_paths()
    
    try:
        # File paths
        sample_form_path = os.path.join(paths["samples"], "medical_form.html")
        json_output_path = os.path.join(paths["samples"], "form_structure.json")
        filled_form_path = paths["filled_form"]

        # Step 1: Display welcome message
        print("\n=== Medical Prescription Form Assistant ===")
        print("This bot will help you complete a medical prescription form.")
        print("I'll guide you through each field with explanations.")
        print("For multiple choice questions, you can enter the number of your selection.")
        print("Let's get started!\n")

        # Step 2: Ask for RadReport template or use default
        print("\n=== Reading HTML Form ===")
        use_radreport = input("Would you like to use a RadReport.org template? (y/n): ").lower() == 'y'
        
        if use_radreport:
            template_id = input("Enter RadReport template ID: ")
            html_content = fetch_radreport_template(template_id)
            if not html_content:
                print("Using default medical form")
                html_content = read_html_file(sample_form_path)
        else:
            html_content = read_html_file(sample_form_path)
            
        if not html_content:
            return

        # Step 3: Convert HTML to JSON
        print("\n=== Converting HTML to JSON ===")
        if use_radreport:
            parser = MRRTParser()
            form_json = parser.parse_html(html_content)
        else:
            form_json = convert_html_to_json(html_content)
            
        if not form_json:
            print("Conversion failed: Empty JSON output")
            return
            
        # Step 4: Enhance form with metadata
        enhanced_form = enhance_form_schema(form_json)
        save_json_to_file(enhanced_form, json_output_path)

        # Step 5: Initialize components
        print("\n=== Initializing Components ===")
        history_file = os.path.join(os.path.dirname(paths["samples"]), "chat_history.json")
        history_manager = ChatHistoryManager(history_file=history_file)
        
        model_type = os.getenv("MODEL_TYPE", "ollama").lower()
        if model_type not in ["ollama", "huggingface"]:
            raise ValueError(f"Invalid MODEL_TYPE: {model_type}. Choose 'ollama' or 'huggingface'")

        llm_handler = LLMHandler(
            model_type=model_type,
            history_manager=history_manager,
            model_name=os.getenv("MODEL_NAME")  # Get specific model from env
        )

        # Step 6: Initialize the form processor
        form_processor = EnhancedFormProcessor(llm_handler)
        form_processor.load_form(enhanced_form)

        # Step 7: Process form with iterative user interaction
        print("\n=== Processing Form with Interactive Communication ===")
        filled_form = form_processor.process_form()

        # Step 8: Summarize collected information
        print("\n=== Form Completion Summary ===")
        print("Thank you for completing the medical prescription form. Here's a summary of the information provided:")
        
        for field_name, field_data in filled_form.items():
            if not field_data.get('hidden', False):
                display_name = " ".join(word.capitalize() for word in field_name.split('_'))
                value = field_data.get('value', 'Not provided')
                print(f"- {display_name}: {value}")
        
        # Step 9: Save results
        print("\n=== Saving Results ===")
        save_json_to_file(filled_form, filled_form_path)
        
        # Step 10: Convert JSON to HTML
        print("\n=== Converting JSON to HTML ===")
        html_output_path = os.path.join(paths["samples"], "filled_form.html")
        html_content = convert_json_to_html(filled_form)
        if not html_content:
            print("Conversion failed: Empty HTML output")
            return
        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Step 11: Convert to FHIR if needed
        if use_radreport:
            print("\n=== Converting to FHIR DiagnosticReport ===")
            fhir_report = convert_to_fhir(filled_form)
            save_json_to_file(fhir_report, paths["fhir_output"])
        
        print(f"\nOperation completed successfully!")
        print(f"Filled form saved to: {filled_form_path}")
        print(f"HTML version saved to: {html_output_path}")
        if use_radreport:
            print(f"FHIR report saved to: {paths['fhir_output']}")

    except Exception as e:
        print(f"\n!!! Critical Error: {str(e)}")
        if isinstance(e, ImportError):
            print("Please check your package installations")
        elif "API token" in str(e):
            print("Verify your .env file contains correct API credentials")

def convert_to_fhir(form_data):
    """Convert form data to FHIR DiagnosticReport"""
    return {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "18748-4",
                "display": "Diagnostic Imaging Report"
            }]
        },
        "subject": {
            "reference": "Patient/example",
            "display": form_data.get("patient_name", {}).get("value", "Unknown Patient")
        },
        "result": [{
            "reference": f"#obs{idx}",
            "display": field_name
        } for idx, (field_name, field) in enumerate(form_data.items())
           if not field.get('hidden', False)]
    }

if __name__ == "__main__":
    main()
