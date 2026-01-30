import argparse
import logging
import os
import sys
from googleapiclient import discovery
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import google.auth

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_credentials(entry):
    """
    Get credentials from a file path or use default credentials.
    """
    if entry and os.path.exists(entry):
        logging.info(f"Using service account key: {entry}")
        return service_account.Credentials.from_service_account_file(entry)
    else:
        logging.info("Using Application Default Credentials")
        creds, project = google.auth.default()
        return creds

def get_project_id(credentials, project_arg=None):
    """
    Determine the project ID from arguments or credentials.
    """
    if project_arg:
        return project_arg
    
    if hasattr(credentials, 'project_id') and credentials.project_id:
        return credentials.project_id
        
    # If using default creds, we might need to look closer or ask user
    _, project = google.auth.default()
    if project:
        return project
        
    logging.error("Could not determine Project ID. Please provide --project.")
    sys.exit(1)

def fetch_permissions(credentials, project_id, output_file):
    """
    Fetch all testable permissions from the project using IAM API.
    """
    try:
        service = discovery.build('iam', 'v1', credentials=credentials)
        resource = f"//cloudresourcemanager.googleapis.com/projects/{project_id}"
        
        logging.info(f"Querying permissions for resource: {resource}")
        logging.info("This may take a moment as there are 12,000+ permissions...")
        
        # Include apiDisabled=True implicitly by querying everything
        body = {
            "fullResourceName": resource,
            "pageSize": 1000  # Max page size
        }
        
        request = service.permissions().queryTestablePermissions(body=body)
        
        all_permissions = set()
        page_count = 0
        
        while request is not None:
            response = request.execute()
            perms = response.get('permissions', [])
            
            for p in perms:
                all_permissions.add(p['name'])
            
            page_count += 1
            if page_count % 5 == 0:
                logging.info(f"Fetched {len(all_permissions)} permissions so far...")
                
            request = service.permissions().queryTestablePermissions_next(previous_request=request, previous_response=response)

        logging.info(f"Successfully retrieved {len(all_permissions)} unique permissions.")
        
        with open(output_file, 'w') as f:
            for p in sorted(all_permissions):
                f.write(p + "\n")
                
        logging.info(f"Saved permissions to {output_file}")
        
    except Exception as e:
        logging.error(f"Failed to fetch permissions: {e}")
        if "SERVICE_DISABLED" in str(e):
             logging.error("Hint: Enable the IAM API (iam.googleapis.com) on your project.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Fetch all GCP IAM permissions using Native API discovery.")
    parser.add_argument('--service-account', help="Path to service account JSON key file.")
    parser.add_argument('--project', help="GCP Project ID (optional if in key).")
    parser.add_argument('--out', default='permissions.txt', help="Output file path (default: permissions.txt).")
    
    args = parser.parse_args()
    
    creds = get_credentials(args.service_account)
    project_id = get_project_id(creds, args.project)
    
    logging.info(f"Target Project: {project_id}")
    fetch_permissions(creds, project_id, args.out)

if __name__ == "__main__":
    main()
