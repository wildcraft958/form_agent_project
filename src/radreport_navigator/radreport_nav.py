import logging
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from database.manager import load_templates_data
from interface.cli import parameter_navigation_menu, handle_direct_id_search

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RadReportNavigator")
console = Console()

# Main function
def main():
    logger.info("Starting RadReport Navigator CLI")
    
    with console.status("Loading templates data..."):
        templates_data = load_templates_data()
    
    if not templates_data:
        logger.error("Failed to load templates data. Exiting.")
        console.print("[bold red]Failed to load templates data. Exiting.[/bold red]")
        return
    
    while True:
        console.print(Panel.fit("RadReport Navigator", style="bold green"))
        menu_items = [
            "Navigate templates by parameters",
            "Search template by ID",
            "Exit"
        ]
        
        for i, item in enumerate(menu_items, 1):
            console.print(f"[bold cyan]{i}[/bold cyan]. {item}")
        
        choice = Prompt.ask("Enter your choice", choices=["1", "2", "3"])
        
        if choice == "1":
            parameter_navigation_menu()
        elif choice == "2":
            handle_direct_id_search(templates_data)
        elif choice == "3":
            logger.info("Exiting. Goodbye!")
            console.print("[bold green]Exiting. Goodbye![/bold green]")
            break

if __name__ == "__main__":
    main()
