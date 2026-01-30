# GCP Permissions Checker

<img src="/static/clouds.jpg" width="400" height="400">

A native Python tool to enumerate and validate Google Cloud IAM permissions via `iam.permissions.queryTestablePermissions` and `projects.testIamPermissions`.

## Installation

```bash
pip3 install -r requirements.txt
```

## Usage

**Service Account Key**
```bash
python3 gcp_perm_checker.py --service-account key.json
```
*Note: `--project` is optional if defined in the key file.*

**Access Token**
```bash
python3 gcp_perm_checker.py --token <ACCESS_TOKEN> --project <PROJECT_ID>
```

**Arguments**
*   `--project`: Target Project ID (Required for tokens).
*   `--out`: Output file path (e.g., `results.json`).
*   `--format`: `txt` or `json`.

## CI/CD & Maintenance

The repository uses GitHub Actions (`.github/workflows/update-permissions.yml`) to schedule weekly updates of the `permissions.txt` master list.

**Manual Update**
```bash
python3 get_permissions.py --out permissions.txt
```
*Requires `roles/iam.roleViewer`.*
