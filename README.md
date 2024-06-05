
# GCP permissions checker


<img src="/static/clouds.jpg" width="400" height="400">

GCP Permissions Checker is a simple Python script designed to enumerate (bruteforce) and test IAM permissions in Google Cloud Platform (GCP). This tool helps you to identify and validate the permissions associated with your GCP service accounts.

You just need to provide a service account key JSON file (key.json) to start enumerating.


## Installation

    pip3 install -r requirements.txt

## Usage

    ./gcp_perm_checker.py path/to/key.json
