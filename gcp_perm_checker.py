#!/usr/bin/env python3

import os
import sys
import argparse
from google.oauth2 import service_account, credentials
from googleapiclient import discovery
from tqdm import tqdm

def get_project_info(credentials, project_id):
    try:
        service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
        

        project_info = service.projects().get(projectId=project_id).execute()
        

        permissions_test = service.projects().testIamPermissions(
            resource=project_id,
            body={"permissions": ["resourcemanager.projects.get"]}
        ).execute()

        print("Authenticated successfully.")
        print(f"Project ID: {project_info.get('projectId')}")
        print(f"Project Name: {project_info.get('name')}")
        print(f"Project Number: {project_info.get('projectNumber')}")
        print(f"Accessible permissions: {permissions_test.get('permissions', [])}")
    except Exception as e:
        print(f"Failed to get project info: {e}")
        exit(1)

def test_permissions(credentials, project_id, permissions_list):
    try:
        service = discovery.build("cloudresourcemanager", "v1", credentials=credentials)
        body = {"permissions": permissions_list}
        request = service.projects().testIamPermissions(resource=project_id, body=body)
        returned_permissions = request.execute()
        return returned_permissions.get('permissions', [])
    except Exception:
        return []

def read_permissions(file_path):
    with open(file_path, "r") as file:
        return [line.strip() for line in file]

def batch_permissions(permissions_list, batch_size=25):
    for i in range(0, len(permissions_list), batch_size):
        yield permissions_list[i:i + batch_size]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GCP Permissions Checker")
    parser.add_argument("key_path", nargs='?', default=None, help="Path to service account key file (ignored if -Token is used)")
    parser.add_argument("-Token", dest="access_token", help="Access token for authentication")
    parser.add_argument("-ProjectID", dest="project_id", help="Project ID (required when using -Token)")
    args = parser.parse_args()

    if args.access_token:
        if not args.project_id:
            print("Error: -ProjectID is required when using -Token")
            exit(1)
        credentials = credentials.Credentials(token=args.access_token)
        project_id = args.project_id
        print("Using provided access token for authentication.")
    elif args.key_path:
        try:
            credentials = service_account.Credentials.from_service_account_file(
                filename=args.key_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            project_id = credentials.project_id
            print("Service account credentials loaded successfully.")
        except Exception as e:
            print(f"Failed to load service account credentials: {e}")
            exit(1)
    else:
        print("Usage: ./gcp_perm_checker.py path/to/key.json or ./gcp_perm_checker.py -Token ACCESS_TOKEN -ProjectID PROJECT_ID")
        exit(1)

    get_project_info(credentials, project_id)

    try:
        consolidated_file = "permissions.txt"
        permissions_list = read_permissions(consolidated_file)
        total_batches = len(permissions_list) // 25 + (1 if len(permissions_list) % 25 > 0 else 0)
        progress_bar_format = "{desc}: {percentage:3.0f}%|{bar}| Elapsed Time: {elapsed}"
        for permissions_batch in tqdm(batch_permissions(permissions_list), total=total_batches, desc="Scanning", bar_format=progress_bar_format, ncols=80):
            found_permissions = test_permissions(credentials, project_id, permissions_batch)
            if found_permissions:
                tqdm.write(f"Found permissions: {found_permissions}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting gracefully.")
        exit(0)
