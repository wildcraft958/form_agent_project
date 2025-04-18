import os
import re
import json
import html as html_module
from rich.panel import Panel
from rich.console import Console
import glob
from datetime import datetime

def clean_html_content(raw_html: str) -> str:
    """
    Cleans weird/escaped HTML content and returns standard HTML.
    Handles:
      - Escaped newlines (\n, \r\n)
      - Escaped quotes (\")
      - Double-escaped backslashes (\\)
      - Redundant whitespace
      - Encoded HTML entities (optional)
    """
    # Decode unicode escapes
    try:
        html = raw_html.encode('utf-8').decode('unicode_escape')
    except Exception:
        html = raw_html  # fallback if decode fails

    # Replace escaped double quotes
    html = html.replace('\\"', '"')
    # Replace escaped single quotes
    html = html.replace("\\'", "'")
    # Replace double backslashes with single
    html = html.replace('\\\\', '\\')
    # Remove redundant escaped newlines
    html = html.replace('\\n', '\n').replace('\\r', '\r')
    # Remove redundant whitespace
    html = re.sub(r'[ \t]+(\n)', r'\1', html)
    # Optionally, decode HTML entities
    html = html_module.unescape(html)
    return html

def json_to_html(json_path):
    """
    Extracts HTML from a JSON file, cleans it, and saves to 'medical_form_standard.html'.
    
    Args:
        json_path: Path to the JSON file containing HTML
    """
    console = Console()
    
    # Always save as 'medical_form_standard.html' in the same directory as the JSON file
    html_path = os.path.join(os.path.dirname(json_path), "medical_form_standard.html")
    
    if not os.path.exists(json_path):
        console.print(f"[bold red]Error:[/bold red] Input file not found: {json_path}")
        return
    
    try:
        # Load JSON file
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract HTML content from the JSON
        template_data = data["details"]["DATA"]["templateData"]
        
        # Clean the HTML content
        cleaned_html = clean_html_content(template_data)
        
        # Write cleaned HTML to output file
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(cleaned_html)
        
        # Show success message
        panel = Panel(
            f"[bold green]✓ Extracted and cleaned HTML written to:[/bold green]\n[cyan]{html_path}[/cyan]",
            title="[bold green]Success[/bold green]",
            border_style="green",
        )
        console.print(panel)
        
    except KeyError as e:
        console.print(f"[bold red]Error:[/bold red] Could not find expected HTML data in JSON. Missing key: {e}")
    except json.JSONDecodeError:
        console.print(f"[bold red]Error:[/bold red] Invalid JSON format in file: {json_path}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "samples")
    samples_dir = os.path.abspath(samples_dir)
    json_files = glob.glob(os.path.join(samples_dir, "template_*.json"))

    if not json_files:
        Console().print("[bold red]Error:[/bold red] No JSON files found in samples directory.")
    else:
        # Extract timestamp from filename and sort by most recent
        def extract_timestamp(f):
            # filename: template_{template_id}_YYYYMMDD_HHMMSS.json
            base = os.path.basename(f)
            parts = base.split("_")
            if len(parts) < 3:
                return datetime.min
            try:
                dt_str = parts[-2] + "_" + parts[-1].split(".")[0]
                return datetime.strptime(dt_str, "%Y%m%d_%H%M%S")
            except Exception:
                return datetime.min

        most_recent_json = max(json_files, key=extract_timestamp)
        json_to_html(most_recent_json)