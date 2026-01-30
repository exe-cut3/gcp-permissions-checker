import argparse
import sys
import logging
import json
import os
from tqdm import tqdm
from googleapiclient import discovery
from google.oauth2 import service_account
import google.oauth2.credentials
import google.auth
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Configure logging to be cleaner
class CustomFormatter(logging.Formatter):
    format_str = "%(message)s"
    
    def format(self, record):
        if record.levelno == logging.INFO:
            return f"{Fore.BLUE}[*]{Style.RESET_ALL} {record.msg}"
        elif record.levelno == logging.WARNING:
            return f"{Fore.YELLOW}[!] {record.msg}{Style.RESET_ALL}"
        elif record.levelno == logging.ERROR:
            return f"{Fore.RED}[-] {record.msg}{Style.RESET_ALL}"
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(CustomFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])

# Silence the annoying "file_cache is only supported with oauth2client<4.0.0" warning
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

class GCPPermissionChecker:
    def __init__(self, service_account_path=None, project_id=None, access_token=None):
        self.credentials = self._get_credentials(service_account_path, access_token)
        self.project_id = self._get_project_id(self.credentials, project_id)
        self.service = discovery.build('cloudresourcemanager', 'v3', credentials=self.credentials)

    def _get_credentials(self, path, token):
        if token:
            logging.info("Using provided Access Token")
            return google.oauth2.credentials.Credentials(token)
        if path:
            logging.info(f"Loading credentials from {path}")
            return service_account.Credentials.from_service_account_file(path)
        else:
            logging.info("Using Application Default Credentials")
            creds, _ = google.auth.default()
            return creds

    def _get_project_id(self, creds, project_arg):
        if project_arg:
            return project_arg
        if hasattr(creds, 'project_id') and creds.project_id:
            return creds.project_id
        _, project = google.auth.default()
        if project:
            return project
        raise ValueError("Project ID could not be determined. Use --project.")

    def load_permissions_list(self, file_path='permissions.txt'):
        if not os.path.exists(file_path):
            logging.error(f"Permissions list file not found: {file_path}")
            logging.error("Run 'python3 get_permissions.py' first to generate it.")
            sys.exit(1)
        
        with open(file_path, 'r') as f:
            perms = [line.strip() for line in f if line.strip()]
        logging.info(f"Loaded {len(perms)} permissions from {file_path}")
        return perms

    def check_permissions(self, permissions_list):
        logging.info(f"Checking permissions against project: {self.project_id}")
        
        BATCH_SIZE = 100
        valid_permissions = []
        
        resource = self.project_id 
        if not resource.startswith('projects/'):
             resource = f'projects/{resource}'

        for i in tqdm(range(0, len(permissions_list), BATCH_SIZE), desc="Checking"):
            batch = permissions_list[i:i + BATCH_SIZE]
            try:
                request = self.service.projects().testIamPermissions(
                    resource=resource,
                    body={'permissions': batch}
                )
                response = request.execute()
                found_permissions = response.get('permissions', [])
                if found_permissions:
                    for p in found_permissions:
                        tqdm.write(f"{Fore.GREEN}[+] {p}{Style.RESET_ALL}", file=sys.stdout)
                valid_permissions.extend(found_permissions)
            except Exception as e:
                # Shorten error message for display
                err_msg = str(e).split('returned "')[1].split('"')[0] if 'returned "' in str(e) else str(e)
                logging.warning(f"Batch failed ({err_msg})")
                
        return sorted(list(set(valid_permissions)))

def main():
    parser = argparse.ArgumentParser(description="GCP Permissions Checker CLI")
    parser.add_argument('--service-account', help="Path to service account key file")
    parser.add_argument('--token', help="GCP Access Token (auth alternative)")
    parser.add_argument('--project', help="GCP Project ID (Required if using token)")
    parser.add_argument('--permissions-file', default='permissions.txt', help="File containing list of permissions to test")
    parser.add_argument('--out', help="Output file for results (JSON or TXT based on extension)")
    parser.add_argument('--format', choices=['json', 'txt'], default='txt', help="Output format")
    
    args = parser.parse_args()
    
    try:
        checker = GCPPermissionChecker(args.service_account, args.project, args.token)
        
        # Metadata display
        identity = getattr(checker.credentials, 'service_account_email', 'Unknown (Token/User)')
        logging.info(f"{Fore.CYAN}--- Configuration ---{Style.RESET_ALL}")
        logging.info(f"Target Project: {Style.BRIGHT}{checker.project_id}{Style.RESET_ALL}")
        logging.info(f"Identity      : {Style.BRIGHT}{identity}{Style.RESET_ALL}")
        logging.info(f"{Fore.CYAN}---------------------{Style.RESET_ALL}")

        perms_to_test = checker.load_permissions_list(args.permissions_file)
        
        logging.info("Starting permission check...")
        valid_perms = checker.check_permissions(perms_to_test)
        
        logging.info(f"Check complete. Found {len(valid_perms)} valid permissions.")
        
        if args.out:
            if args.out.endswith('.json') or args.format == 'json':
                with open(args.out, 'w') as f:
                    json.dump({"valid_permissions": valid_perms}, f, indent=2)
            else:
                with open(args.out, 'w') as f:
                    for p in valid_perms:
                        f.write(p + "\n")
            logging.info(f"Results saved to {args.out}")
        else:
            # Only print final dump if JSON format is explicitly requested
            if args.format == 'json':
               print(json.dumps({"valid_permissions": valid_perms}, indent=2))
            
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Operation canceled by user.{Style.RESET_ALL}")
        sys.exit(130)
