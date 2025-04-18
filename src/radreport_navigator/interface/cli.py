import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
from rich import box

from api.api_manager import (
    fetch_subspecialties, fetch_organizations, fetch_languages, 
    fetch_api_data, fetch_template_details, format_date_for_api, 
    TEMPLATES_ENDPOINT
)
from utils.helpers import save_response_to_file, extract_template_id
from database.manager import find_template_by_id

logger = logging.getLogger("RadReportNavigator.ui")
console = Console()

# Display sample template IDs from JSON data
def display_sample_templates(templates_data, count=5):
    if not templates_data:
        logger.warning("No template data available to display samples")
        return
    
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Template ID", style="bold")
    table.add_column("Title")
    
    for i, template in enumerate(templates_data[:count], 1):
        table.add_row(
            str(i),
            str(template.get('template_id', 'N/A')),
            template.get('title', 'No title')
        )
    
    console.print(Panel.fit(table, title="Sample Templates"))

# Parameter-based navigation menu
def parameter_navigation_menu():
    while True:
        console.print(Panel.fit("Parameter-based Navigation", style="bold green"))
        menu_items = [
            "Search by specialty",
            "Search by organization",
            "Search by language",
            "Search by keyword",
            "Go back to main menu"
        ]
        
        for i, item in enumerate(menu_items, 1):
            console.print(f"[bold cyan]{i}[/bold cyan]. {item}")
        
        choice = Prompt.ask("Enter your choice", choices=[str(i) for i in range(1, 6)])
        
        if choice == "1":
            handle_specialty_search()
        elif choice == "2":
            handle_organization_search()
        elif choice == "3":
            handle_language_search()
        elif choice == "4":
            handle_keyword_search()
        elif choice == "5":
            return

def handle_specialty_search():
    subspecialties = fetch_subspecialties()
    if not subspecialties:
        console.print("[bold red]Failed to fetch specialties[/bold red]")
        return
    
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Name")
    table.add_column("Code", style="bold")
    
    for i, specialty in enumerate(subspecialties, 1):
        table.add_row(
            str(i),
            specialty.get('name', 'N/A'),
            specialty.get('code', 'N/A')
        )
    
    console.print(Panel.fit(table, title="Available Specialties"))
    
    selected_specs = Prompt.ask("Enter specialty codes separated by commas (e.g., CH,CT)")
    results = fetch_api_data(TEMPLATES_ENDPOINT, {"specialty": selected_specs})
    display_search_results(results)

def handle_organization_search():
    organizations = fetch_organizations()
    if not organizations:
        console.print("[bold red]Failed to fetch organizations[/bold red]")
        return
    
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Name")
    table.add_column("Code", style="bold")
    
    for i, org in enumerate(organizations, 1):
        table.add_row(
            str(i),
            org.get('name', 'N/A'),
            org.get('code', 'N/A')
        )
    
    console.print(Panel.fit(table, title="Available Organizations"))
    
    selected_orgs = Prompt.ask("Enter organization codes separated by commas (e.g., rsna,acr)")
    results = fetch_api_data(TEMPLATES_ENDPOINT, {"organization": selected_orgs})
    display_search_results(results)

def handle_language_search():
    languages = fetch_languages()
    if not languages:
        console.print("[bold red]Failed to fetch languages[/bold red]")
        return
    
    table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("#", style="dim", width=4)
    table.add_column("Language")
    table.add_column("Code", style="bold")
    
    for i, lang in enumerate(languages, 1):
        table.add_row(
            str(i),
            lang.get('lang', 'N/A'),
            lang.get('code', 'N/A')
        )
    
    console.print(Panel.fit(table, title="Available Languages"))
    
    selected_langs = Prompt.ask("Enter language codes separated by commas (e.g., en,fr)")
    results = fetch_api_data(TEMPLATES_ENDPOINT, {"language": selected_langs})
    display_search_results(results)

def handle_keyword_search():
    keyword = Prompt.ask("Enter search keyword")
    results = fetch_api_data(TEMPLATES_ENDPOINT, {"search": keyword})
    display_search_results(results)

# Display search results with pagination
def display_search_results(results):
    if not results:
        console.print("[bold red]No results found.[/bold red]")
        return
    
    page_size = 10
    total_pages = (len(results) + page_size - 1) // page_size
    current_page = 1
    
    while True:
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(results))
        
        table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table.add_column("#", style="dim", width=4)
        table.add_column("Template ID", style="bold")
        table.add_column("Title")
        
        for i, template in enumerate(results[start_idx:end_idx], start_idx + 1):
            table.add_row(
                str(i),
                str(template.get('template_id')),
                template.get('title')
            )
        
        console.print(Panel.fit(
            table, 
            title=f"Search Results (Page {current_page}/{total_pages})"
        ))
        
        if total_pages > 1:
            navigation_help = "[bold]N[/bold]: Next page | [bold]P[/bold]: Previous page | [bold]S[/bold]: Select template | [bold]B[/bold]: Back"
            console.print(navigation_help)
            nav = Prompt.ask("Enter navigation choice", choices=["N", "P", "S", "B"], default="S").upper()
            
            if nav == 'N' and current_page < total_pages:
                current_page += 1
            elif nav == 'P' and current_page > 1:
                current_page -= 1
            elif nav == 'S':
                select_template(results)
                return
            elif nav == 'B':
                return
        else:
            select_template(results)
            return

def select_template(templates):
    try:
        selection = int(Prompt.ask("Enter template number (0 to cancel)", default="0"))
        if 1 <= selection <= len(templates):
            template = templates[selection - 1]
            process_template_selection(template)
    except ValueError:
        console.print("[bold red]Invalid selection.[/bold red]")

def process_template_selection(template):
    template_id = template.get("template_id")
    version_date = template.get("created")
    formatted_date = format_date_for_api(version_date)
    
    with console.status(f"Fetching details for template {template_id}..."):
        details = fetch_template_details(template_id, formatted_date)
    
    if details:
        result = {
            "currentVersion": {
                "created": version_date,
                "template_version": template.get("template_version")
            },
            "details": details
        }
        save_response_to_file(result, template_id)
        console.print(f"[bold green]Template details saved successfully![/bold green]")
    else:
        console.print(f"[bold red]Failed to fetch details for template {template_id}[/bold red]")

def handle_direct_id_search(templates_data):
    display_sample_templates(templates_data)
    user_input = Prompt.ask("Enter template ID (e.g., RPT144)")
    template_id = extract_template_id(user_input)
    
    if not template_id:
        console.print("[bold red]Invalid template ID format.[/bold red]")
        return
    
    template = find_template_by_id(templates_data, template_id)
    if template:
        process_template_selection(template)
    else:
        logger.warning(f"Template {template_id} not found")
        console.print(f"[bold red]Template {template_id} not found[/bold red]")
