"""
    RISOLUZIONE DEL LAB: https://portswigger.net/web-security/nosql-injection/lab-nosql-injection-extract-unknown-fields
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
    
   
def main():
    if LAB_ID == "YOUR_LAB_ID_HERE":
        print_error("\nERRORE: Devi impostare il LAB_ID nello script!")
        print_info("Esempio: LAB_ID = '0a12003404bd3fe180f562b700ab0012'")
        sys.exit(1)
    
    exploit = NoSQLInjectionExploit(LAB_ID)
    
    if not exploit.check_lab_status():
        sys.exit(1)


if __name__ == "__main__":
    main()