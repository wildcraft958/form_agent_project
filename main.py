import os
import json
import re
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.traceback import install

from src.html_converter import convert_html_to_json
from src.JSON_converter import convert_json_to_html
from src.llm_handler import LLMHandler
from src.chat_history import ChatHistoryManager
from src.form_processor import FormProcessor
from src.context_generator import generate_context_for_chatbot

# Enable rich tracebacks for better error visibility
install()
console = Console()

# Load environment variables
load_dotenv()

def read_latest_summary(summaries_dir):
    """Read the most recent summary file from the summaries directory."""
    try:
        summary_files = [f for f in os.listdir(summaries_dir) if f.endswith('_summary.txt')]
        if not summary_files:
            return None
        
        # Get the most recent summary file
        latest_summary = max(summary_files, key=lambda f: os.path.getmtime(os.path.join(summaries_dir, f)))
        summary_path = os.path.join(summaries_dir, latest_summary)
        
        with open(summary_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        console.print(Panel(f"[red]Error reading summary file: {str(e)}[/red]", title="Summary Error", border_style="red"))
        return None

def get_project_paths():
    """Get standardized project paths."""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    samples_dir = os.path.join(base_dir, "samples")
    summaries_dir = os.path.join(base_dir, "summaries")
    os.makedirs(summaries_dir, exist_ok=True)
    return {
        "base": base_dir,
        "samples": samples_dir,
        "summaries": summaries_dir,
        "history": os.path.join(base_dir, "chat_history.json")
    }

def read_html_file(file_path):
    """Read HTML file content with improved error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        console.print(Panel(f"[red]Error: File not found at {file_path}[/red]", title="File Error", border_style="red"))
        return None
    except Exception as e:
        console.print(Panel(f"[red]Unexpected error reading file: {str(e)}[/red]", title="File Error", border_style="red"))
        return None

def save_json_to_file(json_data, file_path):
    """Save JSON data to file with directory creation."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
        console.print(Panel(f"[green]Successfully saved JSON to {file_path}[/green]", title="Success", border_style="green"))
    except Exception as e:
        console.print(Panel(f"[red]Error saving JSON file: {str(e)}[/red]", title="File Error", border_style="red"))

def enhance_form_schema(form_json):
    """Enhance the form schema with additional metadata for better interaction."""
    enhanced_form = dict(form_json)
    critical_terms = ["diagnosis", "impression", "findings", "assessment"]
    for field_name in enhanced_form:
        if any(term in field_name.lower() for term in critical_terms):
            enhanced_form[field_name]["required"] = True
    return enhanced_form

def main():
    """Main execution flow with enhanced error handling and user experience."""
    paths = get_project_paths()
    try:
        # File paths
        json_output_path = os.path.join(paths["samples"], "form_structure.json")
        filled_form_path = os.path.join(paths["samples"], "filled_form.json")

        # Step 1: Display welcome message
        console.print(Panel("[bold cyan]Medical Form Assistant[/bold cyan]\nThis bot will help you complete a medical form.\nI'll guide you through each field with explanations.\nLet's get started!", title="Welcome", border_style="cyan"))

        # Step 2: Use local HTML form
        console.print(Panel("[bold]Using Local HTML Form[/bold]", border_style="blue"))
        sample_form_path = os.path.join(paths["samples"], "medical_form_standard.html")

        # Read HTML form
        console.print("[bold]Reading HTML Form...[/bold]")
        html_content = read_html_file(sample_form_path)
        if not html_content:
            return

        # Convert HTML to JSON
        console.print("[bold]Converting HTML to JSON...[/bold]")
        form_json = convert_html_to_json(html_content)
        if not form_json:
            console.print(Panel("[red]Conversion failed: Empty JSON output[/red]", border_style="red"))
            return

        # Enhance form with metadata
        form_json = enhance_form_schema(form_json)
        save_json_to_file(form_json, json_output_path)

        # Step 3: Generate or load form context
        console.print(Panel("[bold]Loading Form Context[/bold]", border_style="blue"))
        form_context = read_latest_summary(paths["summaries"])
        if not form_context:
            console.print("[yellow]No existing summary found. Generating new context...[/yellow]")
            form_context = generate_context_for_chatbot()
        if form_context:
            console.print("[green]Form context loaded successfully.[/green]")
        else:
            console.print("[yellow]Warning: No form context available. Proceeding without context.[/yellow]")

        # Step 4: Initialize components
        console.print(Panel("[bold]Initializing Components[/bold]", border_style="blue"))
        history_manager = ChatHistoryManager(history_file=paths["history"])
        model_type = os.getenv("MODEL_TYPE", "ollama").lower()
        if model_type not in ["ollama", "huggingface"]:
            raise ValueError(f"Invalid MODEL_TYPE: {model_type}. Choose 'ollama' or 'huggingface'")

        llm_handler = LLMHandler(
            model_type=model_type,
            history_manager=history_manager,
            model_name=os.getenv("MODEL_NAME")
        )

        # Step 5: Initialize the form processor with context
        form_processor = FormProcessor(llm_handler, form_context)
        form_processor.load_form(form_json)

        # Step 6: Process form with iterative user interaction
        console.print(Panel("[bold]Processing Form with Interactive Communication[/bold]", border_style="blue"))
        filled_form = form_processor.process_form()

        # Step 7: Summarize collected information
        console.print(Panel("[bold green]Form Completion Summary[/bold green]\nThank you for completing the medical form. Here's a summary of the information provided:", border_style="green"))
        for field_name, field_data in filled_form.items():
            if not field_name.startswith('_') and not field_data.get('hidden', False):
                display_name = field_data.get('label', " ".join(word.capitalize() for word in field_name.split('_')))
                value = field_data.get('value', 'Not provided')
                needs_review = field_data.get('needs_review', False)
                review_status = " [NEEDS REVIEW]" if needs_review else ""
                console.print(f"- [bold]{display_name}[/bold]: {value}{review_status}")

        # Step 8: Save results
        console.print(Panel("[bold]Saving Results...[/bold]", border_style="blue"))
        save_json_to_file(filled_form, filled_form_path)

        # Step 9: Convert JSON to HTML
        console.print(Panel("[bold]Converting JSON to HTML...[/bold]", border_style="blue"))
        html_output_path = os.path.join(paths["samples"], "filled_form.html")
        html_content = convert_json_to_html(filled_form)
        if not html_content:
            console.print(Panel("[red]Conversion failed: Empty HTML output[/red]", border_style="red"))
            return

        with open(html_output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        console.print(Panel(f"[bold green]Operation completed successfully![/bold green]\nFilled form saved to: [cyan]{filled_form_path}[/cyan]\nHTML version saved to: [cyan]{html_output_path}[/cyan]", border_style="green"))

        # Report any fields that need review
        review_fields = [k for k, v in filled_form.items() if v.get('needs_review', False)]
        if review_fields:
            console.print(Panel("[yellow]Fields Needing Human Review:[/yellow]", border_style="yellow"))
            for field in review_fields:
                display_name = filled_form[field].get('label', field)
                review_reason = filled_form[field].get('review_reason', 'Validation failed')
                console.print(f"- [bold]{display_name}[/bold]: {review_reason}")

    except Exception as e:
        console.print(Panel(f"[red]!!! Critical Error: {str(e)}[/red]", title="Critical Error", border_style="red"))
        if isinstance(e, ImportError):
            console.print("[yellow]Please check your package installations[/yellow]")
        elif "API token" in str(e):
            console.print("[yellow]Verify your .env file contains correct API credentials[/yellow]")

if __name__ == "__main__":
    main()