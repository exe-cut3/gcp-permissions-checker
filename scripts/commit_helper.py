
import json
import os
import sys
import subprocess

def get_file_content(filepath):
    """Read file content."""
    if not os.path.exists(filepath):
        return set()
    with open(filepath, 'r') as f:
        # Ignore empty lines and strip whitespace
        return {line.strip() for line in f if line.strip()}

def get_head_content(filepath):
    """Get content of the file from HEAD."""
    try:
        # git show HEAD:path/to/file
        result = subprocess.run(
            ['git', 'show', f'HEAD:{filepath}'],
            capture_output=True,
            text=True,
            check=True
        )
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except subprocess.CalledProcessError:
        # File might not exist in HEAD (first run)
        return set()

METADATA_FILE = 'permissions_metadata.jsonl'


def read_metadata_lines(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, encoding='utf-8') as f:
        return f.read().splitlines()


def read_head_metadata_lines(filepath):
    result = subprocess.run(
        ['git', 'show', f'HEAD:{filepath}'],
        capture_output=True, text=True, encoding='utf-8',
    )
    return result.stdout.splitlines() if result.returncode == 0 else []


def parse_metadata(lines):
    records = {}
    for line in lines:
        if line.strip():
            record = json.loads(line)
            records[record['name']] = record
    return records


def describe_metadata_changes(current, previous):
    """Summarise metadata edits to permissions present in both snapshots.

    Additions and removals are already reported from permissions.txt. This covers
    what that file cannot show, such as a permission moving from BETA to GA, which
    would otherwise never be committed because permissions.txt is unchanged.
    """
    if current and not previous:
        return f"metadata snapshot of {len(current)} permission{'s' if len(current) != 1 else ''}"
    changed = [name for name in current.keys() & previous.keys() if current[name] != previous[name]]
    if not changed:
        return ""
    stage = sum(1 for name in changed if current[name].get('stage') != previous[name].get('stage'))
    note = f"{len(changed)} metadata change{'s' if len(changed) != 1 else ''}"
    return f"{note} ({stage} stage)" if stage else note


def main():
    filepath = 'permissions.txt'
    
    # Get current (staged/working) and previous content
    current_perms = get_file_content(filepath)
    prev_perms = get_head_content(filepath)
    
    # Calculate diff
    added = current_perms - prev_perms
    removed = prev_perms - current_perms
    metadata_note = describe_metadata_changes(
        parse_metadata(read_metadata_lines(METADATA_FILE)),
        parse_metadata(read_head_metadata_lines(METADATA_FILE)),
    )
    
    if not added and not removed and not metadata_note:
        print("No changes detected.")
        sys.exit(0) # Exit with 0, logic in workflow will check output string or separate exit code
        # Actually, let's use a specific string for the workflow to trap, or just exit 0 with empty stdout if we want no commit?
        # Workflow expects a message. If message is empty, we skip.
    
    # Group by service
    service_stats = {}
    
    for p in added:
        service = p.split('.')[0]
        service_stats[service] = service_stats.get(service, 0) + 1
        
    for p in removed:
        service = p.split('.')[0]
        # We can track removed too, but maybe just showing added breakdown is enough for the title?
        # Let's count net impact or just added? User asked: "how many added permissions in which services"
        # "if they were not there, explicit in commit"
        pass

    # Sort services by count descending
    sorted_services = sorted(service_stats.items(), key=lambda x: x[1], reverse=True)
    top_services = sorted_services[:3] # Top 3
    remaining = len(sorted_services) - 3
    
    service_str_parts = []
    for svc, count in top_services:
        service_str_parts.append(f"{svc} (+{count})")
    
    if remaining > 0:
        service_str_parts.append(f"and {remaining} others")
        
    services_summary = ", ".join(service_str_parts) if service_str_parts else "various services"

    # Formulate message
    # "Auto-update: +5 permissions in compute, storage"
    # "Auto-update: +10, -2 permissions. Services: compute (+5), sql (+2)..."
    
    added_count = len(added)
    removed_count = len(removed)
    
    msg = f"Auto-update: +{added_count}, -{removed_count} permissions"
    if added_count > 0:
        msg += f". +{added_count} in {services_summary}"
        
    if metadata_note:
        msg += f"; {metadata_note}"
    print(msg)

if __name__ == "__main__":
    main()
