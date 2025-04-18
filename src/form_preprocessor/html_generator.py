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
    Cleans and normalizes HTML content from various sources.
    Handles various encodings and escape sequences to produce clean HTML.
    
    Args:
        raw_html: Raw HTML content that may contain escape sequences
        
    Returns:
        Cleaned HTML content suitable for browser rendering
    """
    # Step 1: Handle basic escape sequences
    html = raw_html
    
    # Replace JSON string escape sequences
    html = html.replace('\\"', '"')
    html = html.replace("\\'", "'")
    html = html.replace('\\\\', '\\')
    html = html.replace('\\n', '\n')
    html = html.replace('\\r', '\r')
    html = html.replace('\\t', '\t')
    
    # Step 2: Try to decode Unicode escape sequences
    try:
        # This handles \uXXXX sequences
        html = bytes(html, 'utf-8').decode('unicode_escape')
    except (UnicodeError, AttributeError):
        # If decoding fails, keep the original string
        pass
    
    # Step 3: HTML entity decoding (like &auml; -> ä)
    html = html_module.unescape(html)
    
    # Step 4: Fix corrupted UTF-8 encodings (common in German characters)
    # Replace common incorrect encodings of German characters
    replacements = {
        'Ã¤': 'ä', 'Ã¶': 'ö', 'Ã¼': 'ü',
        'Ã„': 'Ä', 'Ã–': 'Ö', 'Ãœ': 'Ü',
        'ÃŸ': 'ß', 'Ã©': 'é', 'Ã¨': 'è',
        'Ã ': 'à', 'Ã¢': 'â', 'Ã´': 'ô',
        'Ã»': 'û', 'Ã®': 'î', 'Ã±': 'ñ',
        'Ã¡': 'á', 'Ã³': 'ó', 'Ãº': 'ú',
        'Ã­': 'í', 'Ã§': 'ç', 'Ã¿': 'ÿ',
        # Add more character mappings as needed
    }
    
    for incorrect, correct in replacements.items():
        html = html.replace(incorrect, correct)
    
    # Step 5: Clean up any redundant whitespace
    html = re.sub(r'\s+\n', '\n', html)  # Remove spaces before newlines
    html = re.sub(r'\n\s+', '\n', html)  # Remove spaces after newlines
    html = re.sub(r'\n{3,}', '\n\n', html)  # Replace 3+ newlines with 2
    
    return html

def extract_template_data(json_data):
    """
    Extracts template data from a JSON structure with error handling for different formats.
    
    Args:
        json_data: The loaded JSON data
        
    Returns:
        Template HTML data or None if not found
    """
    # Try different possible paths to the template data
    try:
        # Common path
        if "details" in json_data and "DATA" in json_data["details"]:
            return json_data["details"]["DATA"]["templateData"]
        # Alternative path
        elif "templateData" in json_data:
            return json_data["templateData"]
        # Look for any key that might contain "template" and has HTML content
        else:
            for key, value in json_data.items():
                if isinstance(value, str) and "<!DOCTYPE html>" in value:
                    return value
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, str) and "<!DOCTYPE html>" in subvalue:
                            return subvalue
        
        # If we got here, we couldn't find the template data
        return None
    except Exception as e:
        print(f"Error extracting template data: {e}")
        return None

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
            content = f.read()
            # Handle invalid JSON with control characters
            content = re.sub(r'[\x00-\x1F\x7F]', '', content)
            data = json.loads(content)
        
        # Extract HTML content from the JSON
        template_data = extract_template_data(data)
        
        if not template_data:
            console.print(f"[bold red]Error:[/bold red] Could not find HTML template data in JSON file.")
            return
        
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
        
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Error:[/bold red] Invalid JSON format in file: {json_path}")
        console.print(f"Details: {str(e)}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] An unexpected error occurred: {str(e)}")

def get_most_recent_json(directory):
    """
    Find the most recent template JSON file in the given directory.
    
    Args:
        directory: Directory to search for JSON files
        
    Returns:
        Path to the most recent JSON file or None if none found
    """
    json_files = glob.glob(os.path.join(directory, "template_*.json"))
    
    if not json_files:
        return None
    
    # Extract timestamp from filename and sort by most recent
    def extract_timestamp(f):
        # filename: template_{template_id}_YYYYMMDD_HHMMSS.json
        base = os.path.basename(f)
        parts = base.split("_")
        if len(parts) < 3:
            return datetime.min
        try:
            # Try to find date parts
            for i in range(1, len(parts)):
                part = parts[i].split(".")[0]
                if len(part) == 8 and part.isdigit():  # YYYYMMDD format
                    date_str = part
                    if i+1 < len(parts) and parts[i+1].split(".")[0].isdigit():
                        time_str = parts[i+1].split(".")[0]
                        return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                    return datetime.strptime(date_str, "%Y%m%d")
            
            # If we can't find a date, use file modification time
            return datetime.fromtimestamp(os.path.getmtime(f))
        except Exception:
            return datetime.min
    
    return max(json_files, key=extract_timestamp)

if __name__ == "__main__":
    # Get the current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Navigate to samples directory (two levels up + samples)
    samples_dir = os.path.join(script_dir, "..", "..", "samples")
    samples_dir = os.path.abspath(samples_dir)
    
    console = Console()
    
    # Check if samples directory exists
    if not os.path.exists(samples_dir):
        console.print(f"[bold yellow]Warning:[/bold yellow] Samples directory not found: {samples_dir}")
        console.print("Looking for JSON files in the current directory instead.")
        samples_dir = script_dir
    
    # Find the most recent JSON file
    most_recent_json = get_most_recent_json(samples_dir)
    
    if not most_recent_json:
        console.print("[bold red]Error:[/bold red] No template JSON files found.")
    else:
        console.print(f"[bold blue]Processing:[/bold blue] {most_recent_json}")
        json_to_html(most_recent_json)