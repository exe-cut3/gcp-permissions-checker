#!/usr/bin/env python3

import os
import sys
from google.oauth2 import service_account
from googleapiclient import discovery
from tqdm import tqdm

def get_caller_identity(credentials):

    try:
        project_id = credentials.project_id
        client_email = credentials.service_account_email

        service = discovery.build('cloudresourcemanager', 'v1', credentials=credentials)
        project_info = service.projects().get(projectId=project_id).execute()
        print(f"Service Account Email: {client_email}")
        print(f"Project ID: {project_info['projectId']}")
        print(f"Project Name: {project_info['name']}")
    except Exception as e:
        print(f"Failed to get caller identity: {e}")

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
    if len(sys.argv) != 2:
        print("Usage: ./gcp_perm_checker.py path/to/key.json")
        exit(1)

    key_path = sys.argv[1]

    try:
        credentials = service_account.Credentials.from_service_account_file(
            filename=key_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        print("Service account credentials loaded successfully.")
        get_caller_identity(credentials)
        project_id = credentials.project_id
    except Exception as e:
        print(f"Failed to load service account credentials: {e}")
        exit(1)

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
