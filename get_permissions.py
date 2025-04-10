import requests
import re

def download_gcp_permissions():
    """Get list of all GCP permissions"""
    base_ref_page = requests.get("https://cloud.google.com/iam/docs/permissions-reference").text
    results = re.findall(r'<td id="([^"]+)"', base_ref_page)
    return results

if __name__ == "__main__":
    permissions = download_gcp_permissions()
    with open("permissions.txt", "w") as f:
        for perm in permissions:
            f.write(perm + "\n")
