import os
import re
import html as html_module

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
    # Optionally, decode HTML entities (uncomment if needed)
    html = html_module.unescape(html)
    return html

def html_generator():
    # base_dir = os.path.dirname("samples")
    input_path = os.path.join("samples", "medical_form.html")
    output_path = os.path.join("samples", "medical_form_standard.html")

    if not os.path.exists(input_path):
        print(f"Input file not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        weird_html = f.read()

    standard_html = clean_html_content(weird_html)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(standard_html)
    print(f"Standard HTML written to: {output_path}")

if __name__ == "__main__":
    html_generator()