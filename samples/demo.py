import json

# Path to your JSON file
json_path = "samples/template_144_20250418_145343.json"
# Path to save the extracted HTML
html_path = "samples/template_144_20250418_145343.html"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Navigate to the templateData field
template_data = data["details"]["DATA"]["templateData"]

# Save to HTML file
with open(html_path, "w", encoding="utf-8") as f:
    f.write(template_data)

print(f"Extracted HTML saved to {html_path}")