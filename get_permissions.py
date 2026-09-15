import argparse
import json
import logging
import os
import sys
from collections import Counter
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
    if entry:
        if not os.path.exists(entry):
            # Falling back to ADC here would silently query a different identity,
            # yielding a short list that looks like a legitimate permission removal.
            logging.error(f"Service account key not found: {entry}")
            sys.exit(1)
        logging.info(f"Using service account key: {entry}")
        return service_account.Credentials.from_service_account_file(entry)

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

# apiDisabled is deliberately not kept: it reports whether the API is enabled in
# the collector's own project rather than anything about Google's catalog, so it
# would flip whenever that project changes and show up as spurious churn.
METADATA_FIELDS = ("title", "description", "stage", "customRolesSupportLevel", "primaryPermission")

# Proto3 JSON omits enum fields holding their zero value, which is the first value
# of each enum in the IAM discovery document. A missing stage therefore means ALPHA.
ENUM_DEFAULTS = {"stage": "ALPHA", "customRolesSupportLevel": "SUPPORTED"}


def to_record(permission):
    record = {"name": permission["name"]}
    for field in METADATA_FIELDS:
        value = permission.get(field, ENUM_DEFAULTS.get(field))
        if value not in (None, ""):
            record[field] = value
    return record


def _atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


def write_outputs(records, output_file, metadata_file):
    names = sorted(records)
    # One object per line keeps each daily diff down to the permissions whose
    # metadata actually changed, e.g. a single line for a BETA -> GA promotion.
    _atomic_write(metadata_file, "".join(
        json.dumps(records[name], ensure_ascii=False, separators=(",", ":")) + "\n" for name in names
    ))
    _atomic_write(output_file, "".join(name + "\n" for name in names))


def fetch_permissions(credentials, project_id, output_file, metadata_file):
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
        
        records = {}
        page_count = 0
        
        while request is not None:
            response = request.execute()
            perms = response.get('permissions', [])
            
            for p in perms:
                records[p['name']] = to_record(p)
            
            page_count += 1
            if page_count % 5 == 0:
                logging.info(f"Fetched {len(records)} permissions so far...")
                
            request = service.permissions().queryTestablePermissions_next(previous_request=request, previous_response=response)

        logging.info(f"Successfully retrieved {len(records)} unique permissions.")
        logging.info(f"Launch stages: {dict(Counter(r.get('stage') for r in records.values()))}")
        
        write_outputs(records, output_file, metadata_file)

        logging.info(f"Saved permissions to {output_file} and {metadata_file}")
        
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
    parser.add_argument('--metadata-out', default='permissions_metadata.jsonl',
                        help="Per-permission title, description and launch stage (default: permissions_metadata.jsonl).")
    
    args = parser.parse_args()
    
    creds = get_credentials(args.service_account)
    project_id = get_project_id(creds, args.project)
    
    logging.info(f"Target Project: {project_id}")
    fetch_permissions(creds, project_id, args.out, args.metadata_out)

if __name__ == "__main__":
    main()
