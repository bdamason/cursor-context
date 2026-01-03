"""
Delete old Confluence pages that were moved to Onboarding section
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

# Pages to delete (old copies that were moved to Onboarding)
OLD_PAGES_TO_DELETE = [
    "Getting Started",
    "Quick Start Guide", 
    "Team Collaboration",
    "Git Setup",
    "Confluence Integration"
]

def main():
    print("=" * 60)
    print("Confluence Cleanup Script")
    print("Deleting old pages that were moved to Onboarding")
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
    
    for page_title in OLD_PAGES_TO_DELETE:
        print(f"\n{'='*60}")
        print(f"Processing: {page_title}")
        print(f"{'='*60}")
        
        try:
            # Find the page
            page = confluence.get_page_by_title(space=CONFLUENCE_SPACE_KEY, title=page_title)
            
            if page:
                page_id = page['id']
                print(f"[FOUND] Page ID: {page_id}")
                
                # Confirm it's under 'semantic' parent (not Onboarding)
                # This is a safety check to make sure we don't delete the new ones
                ancestors = confluence.get_page_ancestors(page_id)
                parent_titles = [a['title'] for a in ancestors]
                
                print(f"[INFO] Parent hierarchy: {' > '.join(parent_titles)}")
                
                # Check if it's the OLD page (under semantic root, not under Onboarding)
                if 'Onboarding' not in parent_titles:
                    # Delete the page (it's a duplicate)
                    confluence.remove_page(page_id)
                    print(f"[DELETED] '{page_title}' - Old duplicate removed")
                    deleted_count += 1
                else:
                    print(f"[SAFE] '{page_title}' is under Onboarding - will NOT delete")
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
    print(f"Deleted: {deleted_count} pages")
    print(f"Not found/skipped: {not_found_count} pages")
    print("=" * 60)

if __name__ == "__main__":
    main()

