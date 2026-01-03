"""
Delete old Cursor-related pages that were moved to "Cursor AI Setup" subfolder
"""

import os
import sys
from atlassian import Confluence

# Configuration
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "https://esosolutions.atlassian.net/wiki")
CONFLUENCE_USERNAME = os.environ.get("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN")
CONFLUENCE_SPACE_KEY = "IA"

# Check for required credentials
if not CONFLUENCE_USERNAME or not CONFLUENCE_API_TOKEN:
    print("[ERROR] Missing required environment variables!")
    print("Please set CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN")
    print("Run: .\\load-secrets-from-keyvault.ps1 -KeyVaultName ea-dev-keyvault-shared")
    sys.exit(1)

# Old Cursor pages to delete (these are now under "Cursor AI Setup" subfolder)
OLD_CURSOR_PAGES_TO_DELETE = [
    "Cursor Onboarding Checklist",
    "Azure Key Vault Integration Guide",
    "MCP Configuration Security Guide",
    "Quick Start: Model Context Protocol (MCP)"
]

def main():
    print("=" * 60)
    print("Confluence Cleanup Script - Old Cursor Pages")
    print("Deleting old Cursor pages now under 'Cursor AI Setup'")
    print("=" * 60)
    
    # Connect to Confluence
    print("\nConnecting to Confluence...")
    try:
        confluence = Confluence(
            url=CONFLUENCE_URL,
            username=CONFLUENCE_USERNAME,
            password=CONFLUENCE_API_TOKEN,
            cloud=True
        )
        confluence.get_space(CONFLUENCE_SPACE_KEY)
        print("Connected successfully!")
    except Exception as e:
        print(f"Failed to connect to Confluence: {e}")
        sys.exit(1)
    
    # Delete old pages
    deleted_count = 0
    not_found_count = 0
    safe_count = 0
    
    for page_title in OLD_CURSOR_PAGES_TO_DELETE:
        print(f"\n{'='*60}")
        print(f"Processing: {page_title}")
        print(f"{'='*60}")
        
        try:
            # Find the page
            page = confluence.get_page_by_title(space=CONFLUENCE_SPACE_KEY, title=page_title)
            
            if page:
                page_id = page['id']
                print(f"[FOUND] Page ID: {page_id}")
                
                # Get parent hierarchy to verify it's the OLD page
                ancestors = confluence.get_page_ancestors(page_id)
                parent_titles = [a['title'] for a in ancestors]
                
                print(f"[INFO] Parent hierarchy: {' > '.join(parent_titles)}")
                
                # Check if it's under "Cursor AI Setup" (the NEW location - don't delete)
                if 'Cursor AI Setup' in parent_titles:
                    print(f"[SAFE] '{page_title}' is under 'Cursor AI Setup' - will NOT delete (this is the new one!)")
                    safe_count += 1
                # Check if it's directly under "Onboarding" (the OLD location - delete it)
                elif 'Onboarding' in parent_titles and 'Cursor AI Setup' not in parent_titles:
                    # Delete the old page
                    confluence.remove_page(page_id)
                    print(f"[DELETED] '{page_title}' - Old copy removed (was directly under Onboarding)")
                    deleted_count += 1
                else:
                    print(f"[INFO] '{page_title}' has unexpected hierarchy - skipping for safety")
            else:
                print(f"[NOT FOUND] '{page_title}' - may already be deleted")
                not_found_count += 1
                
        except Exception as e:
            print(f"[ERROR] Error processing '{page_title}': {e}")
            not_found_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)
    print(f"Deleted (old duplicates): {deleted_count} pages")
    print(f"Protected (new versions): {safe_count} pages")
    print(f"Not found/errors: {not_found_count} pages")
    print("=" * 60)

if __name__ == "__main__":
    main()

















































