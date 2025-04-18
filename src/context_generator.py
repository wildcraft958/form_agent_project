# summarize.py
import os
import json
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
# from langchain_core.runnables import RunnableLambda
from rich.console import Console
from rich.panel import Panel

console = Console()

def get_samples_dir():
    # Always resolve path relative to project root
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    samples_dir = os.path.join(base_dir, "samples")
    return samples_dir

def get_summaries_dir():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    summaries_dir = os.path.join(base_dir, "summaries")
    os.makedirs(summaries_dir, exist_ok=True)
    return summaries_dir

def find_most_recent_json(samples_dir):
    """Find the most recent template_*.json file in samples_dir."""
    json_files = [os.path.join(samples_dir, f) for f in os.listdir(samples_dir) if f.startswith("template_") and f.endswith(".json")]
    if not json_files:
        return None
    def extract_timestamp(f):
        base = os.path.basename(f)
        parts = base.split("_")
        if len(parts) < 3:
            return 0
        try:
            dt_str = parts[-2] + "_" + parts[-1].split(".")[0]
            return int(dt_str.replace("_", ""))
        except Exception:
            return 0
    return max(json_files, key=extract_timestamp)

def extract_metadata(json_data):
    """Extracts and formats metadata for summarization."""
    info = json_data.get('details', {}).get('DATA', {})
    def safe_first(lst, key):
        return lst[0][key] if lst and key in lst[0] else None
    meta = {
        "Title": info.get("title"),
        "Author": info.get("author"),
        "Created": info.get("created"),
        "Views": info.get("views"),
        "Downloads": info.get("downloads"),
        "Language": info.get("englishName"),
        "Template Type": info.get("dataType"),
        "Organization": safe_first(info.get("organizations", []), "name"),
        "Specialty": safe_first(info.get("specialty", []), "name"),
        "Description": info.get("description"),
        "Original Author": info.get("originalAuthor"),
        "Published At": info.get("published_at"),
        "Template ID": info.get("template_id"),
        "Status": info.get("template_status"),
    }
    # Remove None values for cleaner context
    return {k: v for k, v in meta.items() if v}

def summarize_metadata(metadata, llm, chain):
    """Summarizes metadata using LLM."""
    prompt_input = json.dumps(metadata, indent=2)
    summary = chain.invoke({"meta": prompt_input})
    return summary.strip()

def generate_context_for_chatbot():
    samples_dir = get_samples_dir()
    summaries_dir = get_summaries_dir()
    most_recent = find_most_recent_json(samples_dir)
    if not most_recent:
        console.print("[bold red]No template JSON files found in samples directory.[/bold red]")
        return None

    console.print(Panel(f"Processing JSON file:\n[cyan]{most_recent}[/cyan]", title="Selected Template", border_style="blue"))

    # Load JSON
    with open(most_recent, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract metadata
    metadata = extract_metadata(data)
    console.print(Panel(f"[bold]Extracted Metadata:[/bold]\n{json.dumps(metadata, indent=2)}", title="Metadata", border_style="magenta"))

    # Setup LangChain prompt + Ollama
    llm = OllamaLLM(model="llama3")
    template = PromptTemplate.from_template("""
                                            Summarize this medical template metadata in 4-5 lines, making it easy to understand and human-friendly.
                                            Highlight the clinical context, intended use, and any unique aspects:

                                            {meta}
                                            """)
    chain = template | llm

    # Summarize
    summary = summarize_metadata(metadata, llm, chain)
    console.print(Panel(f"[italic]{summary}[/italic]", title="Summary", border_style="green"))

    # Save summary for context use
    summary_filename = os.path.basename(most_recent).replace('.json', '_summary.txt')
    output_path = os.path.join(summaries_dir, summary_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    console.print(Panel(f"Summary saved to:\n[cyan]{output_path}[/cyan]", title="Saved", border_style="green"))

    # Return summary as context for chatbot
    return summary

if __name__ == "__main__":
    context = generate_context_for_chatbot()
    # if context:
    #     print("\n[Context for chatbot]:\n")
    #     # print(context)
