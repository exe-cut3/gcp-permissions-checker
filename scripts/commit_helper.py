
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

def main():
    filepath = 'permissions.txt'
    
    # Get current (staged/working) and previous content
    current_perms = get_file_content(filepath)
    prev_perms = get_head_content(filepath)
    
    # Calculate diff
    added = current_perms - prev_perms
    removed = prev_perms - current_perms
    
    if not added and not removed:
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
        
    print(msg)

if __name__ == "__main__":
    main()
