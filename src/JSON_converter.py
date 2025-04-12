import json
import sys

def convert_json_to_html(json_data):
    # Build the HTML form based on the JSON structure.
    # The expected JSON format is:
    # {
    #   "title": "Form Title",
    #   "fields": [
    #     {"label": "Field Label", "type": "text", "name": "field_name", "value": "default"},
    #     ...
    #   ]
    # }
    html_lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "  <meta charset='UTF-8'>",
        f"  <title>{json_data.get('title', 'Form')}</title>",
        "</head>",
        "<body>",
        "  <form>"
    ]

    for field in json_data.get("fields", []):
        label = field.get("label", "")
        field_type = field.get("type", "text")
        name = field.get("name", "")
        value = field.get("value", "")
        html_lines.append("    <div>")
        if label and name:
            html_lines.append(f"      <label for='{name}'>{label}</label>")
        if name:
            html_lines.append(f"      <input type='{field_type}' name='{name}' id='{name}' value='{value}'>")
        else:
            html_lines.append(f"      <input type='{field_type}' value='{value}'>")
        html_lines.append("    </div>")

    html_lines.append("    <input type='submit' value='Submit'>")
    html_lines.append("  </form>")
    html_lines.append("</body>")
    html_lines.append("</html>")

    return "\n".join(html_lines)

def main():
    if len(sys.argv) != 3:
        print("Usage: python JSON_converter.py <input.json> <output.html>")
        sys.exit(1)

    input_json_file = sys.argv[1]
    output_html_file = sys.argv[2]

    with open(input_json_file, "r", encoding="utf-8") as f:
        try:
            json_data = json.load(f)
        except json.JSONDecodeError as err:
            print(f"Error decoding JSON: {err}")
            sys.exit(1)

    # Convert JSON to HTML form
    html_content = convert_json_to_html(json_data)

    with open(output_html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()