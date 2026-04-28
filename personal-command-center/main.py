from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from database import initialize_database
import os

# Create a Console object - this is how we print nice-looking stuff
console = Console()

def show_menu():
    """
    Displays the main menu with all available options.
    Uses rich's Panel to create a nice box around the menu.
    """
    # Clear the terminal screen (works on Windows/Mac/Linux)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Create a nice-looking menu panel
    menu_text = """
[bold cyan]1.[/] 📚 Assignments
[bold cyan]2.[/] ✅ Daily Habits  
[bold cyan]3.[/] 💪 Workouts
[bold cyan]4.[/] 📊 Dashboard
[bold cyan]5.[/] 🚪 Exit
    """
    
    # Panel creates a box around text with a title
    console.print(Panel(menu_text, title="[bold magenta]Personal Productivity Center[/]", border_style="cyan"))

def main():
    """
    Main function that runs the app.
    This is an infinite loop that keeps showing the menu until you exit.
    """
    # Make sure database exists before starting
    if not os.path.exists('data/data.db'):
        console.print("[yellow]First time setup...[/]")
        os.makedirs('data', exist_ok=True)
        initialize_database()
    
    while True:  # Loop forever until user exits
        show_menu()
        
        # Prompt.ask() shows a nice prompt and waits for user input
        choice = Prompt.ask("[bold green]Choose an option[/]", choices=["1", "2", "3", "4", "5"])
        
        if choice == "1":
            console.print("[yellow]Assignments feature coming soon...[/]")
            input("\nPress Enter to continue...")
        elif choice == "2":
            console.print("[yellow]Habits feature coming soon...[/]")
            input("\nPress Enter to continue...")
        elif choice == "3":
            console.print("[yellow]Workouts feature coming soon...[/]")
            input("\nPress Enter to continue...")
        elif choice == "4":
            console.print("[yellow]Dashboard feature coming soon...[/]")
            input("\nPress Enter to continue...")
        elif choice == "5":
            console.print("[bold green]👋 See you later![/]")
            break  # Exit the loop and end the program

# This runs when you execute the file
if __name__ == "__main__":
    main()