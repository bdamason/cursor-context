"""
Sync Onboarding Documentation to Confluence
Target: IA space > semantic > Onboarding folder
Uses environment variables for credentials (from Key Vault or .env)
"""

import os
import sys
from pathlib import Path
from atlassian import Confluence
from md2cf.confluence_renderer import ConfluenceRenderer
import mistune
import datetime

# ========================================
# CONFIGURATION FROM ENVIRONMENT
# ========================================

# Get credentials from environment variables (loaded from Key Vault or .env)
CONFLUENCE_URL = os.getenv("CONFLUENCE_URL", "https://esosolutions.atlassian.net/wiki")
CONFLUENCE_USERNAME = os.getenv("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
CONFLUENCE_SPACE_KEY = "IA"  # Infrastructure & Analytics space
PARENT_PAGE_TITLE = "semantic"  # Main folder
ONBOARDING_PAGE_TITLE = "Onboarding"  # Onboarding subfolder

# ========================================
# ONBOARDING FILE MAPPINGS
# ========================================

# Map Git files to Confluence page titles under "Onboarding" folder
ONBOARDING_MAPPINGS = {
    "CURSOR_ONBOARDING_CHECKLIST.md": {
        "title": "Cursor Onboarding Checklist",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Complete 90-minute onboarding guide for new team members using Cursor IDE"
    },
    "GETTING_STARTED.md": {
        "title": "Getting Started with AI-Enhanced Development",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Framework overview and AI collaboration basics"
    },
    "TEAM_README.md": {
        "title": "Team Collaboration Guide",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Git workflow, branch strategy, and team assignments"
    },
    "QUICK_START_GUIDE.md": {
        "title": "Quick Start Guide",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Hands-on exercises and first-hour examples"
    },
    "QUICK_START_MCP.md": {
        "title": "MCP Quick Start",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Model Context Protocol setup and configuration"
    },
    "GIT_SETUP_GUIDE.md": {
        "title": "Git Setup Guide",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Initialize repository and connect to Bitbucket"
    },
    "AZURE_KEYVAULT_SETUP.md": {
        "title": "Azure Key Vault Setup",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Secure secrets management with Azure Key Vault"
    },
    "MCP_SECURITY_GUIDE.md": {
        "title": "MCP Security Guide",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Security best practices for MCP configuration"
    },
    "MSSQL_KEYVAULT_SETUP.md": {
        "title": "MS SQL Key Vault Setup",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Configure SQL Server credentials in Key Vault"
    },
    ".cursorrules": {
        "title": "Repository Standards (cursorrules)",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "All coding standards and AI collaboration rules"
    },
    "DOCUMENTATION_INDEX.md": {
        "title": "Documentation Index",
        "parent": ONBOARDING_PAGE_TITLE,
        "description": "Complete navigation guide to all documentation"
    }
}

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_or_create_page(confluence, space_key: str, parent_title: str, page_title: str) -> str:
    """
    Get existing page ID or create new page under parent
    Returns page_id
    """
    # Try to find existing page
    try:
        page = confluence.get_page_by_title(space=space_key, title=page_title)
        if page:
            print(f"[OK] Found existing page: {page_title}")
            return page['id']
    except Exception:
        print(f"[INFO] Page not found, will create: {page_title}")
    
    # Get parent page ID
    try:
        parent_page = confluence.get_page_by_title(space=space_key, title=parent_title)
        if not parent_page:
            print(f"[ERROR] Parent page '{parent_title}' not found!")
            return None
        parent_id = parent_page['id']
    except Exception as e:
        print(f"[ERROR] Error getting parent page '{parent_title}': {e}")
        return None
    
    # Create new page
    try:
        new_page = confluence.create_page(
            space=space_key,
            title=page_title,
            body="<p>Content will be updated...</p>",
            parent_id=parent_id
        )
        print(f"[OK] Created new page: {page_title}")
        return new_page['id']
    except Exception as e:
        print(f"[ERROR] Error creating page '{page_title}': {e}")
        return None


def update_page_content(confluence, page_id: str, page_title: str, content: str):
    """
    Update page content
    """
    try:
        # Get current page to get version number
        page = confluence.get_page_by_id(page_id, expand='version')
        
        # Update page
        confluence.update_page(
            page_id=page_id,
            title=page_title,
            body=content,
            parent_id=None,
            type='page',
            representation='storage',
            minor_edit=False
        )
        print(f"[OK] Updated page: {page_title}")
        return True
    except Exception as e:
        print(f"[ERROR] Error updating page '{page_title}': {e}")
        return False


def convert_markdown_to_confluence(markdown_content: str) -> str:
    """
    Convert markdown to Confluence storage format (XHTML)
    Uses md2cf library for proper conversion
    """
    renderer = ConfluenceRenderer(use_xhtml=True)
    confluence_mistune = mistune.Markdown(renderer=renderer)
    return confluence_mistune(markdown_content)


def create_onboarding_index_page(confluence, space_key: str, parent_title: str, onboarding_title: str):
    """
    Create the main Onboarding index page with navigation
    """
    page_id = get_or_create_page(
        confluence=confluence,
        space_key=space_key,
        parent_title=parent_title,
        page_title=onboarding_title
    )
    
    if not page_id:
        return False
    
    # Create comprehensive index page
    index_content = """
    <h1>🚀 Onboarding Documentation</h1>
    
    <ac:structured-macro ac:name="info">
      <ac:rich-text-body>
        <p><strong>New to the ESO BI Team?</strong> Start here! This section contains everything you need to get up and running with our development environment and tools.</p>
        <p><strong>Estimated Time:</strong> 90-120 minutes for complete onboarding</p>
      </ac:rich-text-body>
    </ac:structured-macro>
    
    <h2>📋 Quick Start (30 minutes)</h2>
    <p>Essential setup to start working:</p>
    <ol>
      <li><strong><ac:link><ri:page ri:content-title="Cursor Onboarding Checklist" /></ac:link></strong> - Complete step-by-step guide (START HERE!)</li>
      <li><strong><ac:link><ri:page ri:content-title="Azure Key Vault Setup" /></ac:link></strong> - Secure credentials management</li>
      <li><strong><ac:link><ri:page ri:content-title="MCP Security Guide" /></ac:link></strong> - MCP configuration security</li>
      <li><strong><ac:link><ri:page ri:content-title="Repository Standards (cursorrules)" /></ac:link></strong> - Coding standards and rules</li>
    </ol>
    
    <h2>📖 Foundation (60 minutes)</h2>
    <p>Core concepts and workflows:</p>
    <ul>
      <li><strong><ac:link><ri:page ri:content-title="Getting Started with AI-Enhanced Development" /></ac:link></strong> - AI collaboration framework</li>
      <li><strong><ac:link><ri:page ri:content-title="Team Collaboration Guide" /></ac:link></strong> - Git workflow and team processes</li>
      <li><strong><ac:link><ri:page ri:content-title="Git Setup Guide" /></ac:link></strong> - Initialize and connect to Bitbucket</li>
      <li><strong><ac:link><ri:page ri:content-title="Documentation Index" /></ac:link></strong> - Navigate all repository documentation</li>
    </ul>
    
    <h2>🔧 Technical Setup (30 minutes)</h2>
    <p>Deep dive into specific tools:</p>
    <ul>
      <li><strong><ac:link><ri:page ri:content-title="Quick Start Guide" /></ac:link></strong> - Hands-on exercises</li>
      <li><strong><ac:link><ri:page ri:content-title="MCP Quick Start" /></ac:link></strong> - Model Context Protocol</li>
      <li><strong><ac:link><ri:page ri:content-title="MS SQL Key Vault Setup" /></ac:link></strong> - SQL Server credentials</li>
    </ul>
    
    <h2>💡 Key Concepts</h2>
    
    <ac:structured-macro ac:name="panel" ac:schema-version="1">
      <ac:parameter ac:name="bgColor">#E3FCEF</ac:parameter>
      <ac:parameter ac:name="titleBGColor">#00875A</ac:parameter>
      <ac:parameter ac:name="titleColor">#FFFFFF</ac:parameter>
      <ac:parameter ac:name="title">Security First</ac:parameter>
      <ac:rich-text-body>
        <p><strong>Never commit secrets to Git!</strong></p>
        <ul>
          <li>✅ Store credentials in Azure Key Vault</li>
          <li>✅ Use environment variables for local development</li>
          <li>✅ Reference variables with <code>${VARIABLE_NAME}</code> syntax</li>
          <li>❌ Never hardcode passwords or API tokens</li>
        </ul>
      </ac:rich-text-body>
    </ac:structured-macro>
    
    <ac:structured-macro ac:name="panel" ac:schema-version="1">
      <ac:parameter ac:name="bgColor">#FFF0B3</ac:parameter>
      <ac:parameter ac:name="titleBGColor">#FF991F</ac:parameter>
      <ac:parameter ac:name="titleColor">#FFFFFF</ac:parameter>
      <ac:parameter ac:name="title">Cost Control</ac:parameter>
      <ac:rich-text-body>
        <p><strong>Control Cursor AI costs by selecting the right model:</strong></p>
        <ul>
          <li>💰 <strong>Regular Mode</strong> (<code>claude-4.5-sonnet</code>): $200-500/month - Use as default</li>
          <li>💸 <strong>Thinking Mode</strong> (<code>claude-4.5-sonnet-thinking</code>): $500-1000/month - Use sparingly</li>
          <li>🎯 <strong>Target</strong>: Keep under $300/month</li>
        </ul>
        <p>Switch to regular mode in Settings to save 50-70% on costs!</p>
      </ac:rich-text-body>
    </ac:structured-macro>
    
    <ac:structured-macro ac:name="panel" ac:schema-version="1">
      <ac:parameter ac:name="bgColor">#DEEBFF</ac:parameter>
      <ac:parameter ac:name="titleBGColor">#0747A6</ac:parameter>
      <ac:parameter ac:name="titleColor">#FFFFFF</ac:parameter>
      <ac:parameter ac:name="title">Repository Standards</ac:parameter>
      <ac:rich-text-body>
        <p><strong>Critical Rules (memorize these!):</strong></p>
        <ol>
          <li>❌ <strong>NEVER</strong> use <code>[stage]</code> schema → ✅ Use <code>[bi]</code> schema</li>
          <li>⏰ Convert <code>[bi]</code> UTC timestamps to Central Time (future dept schemas store in Central)</li>
          <li>🧹 <strong>ALWAYS</strong> clean up temp tables (before & after use)</li>
          <li>🔒 <strong>NEVER</strong> commit secrets to git</li>
          <li>📋 <strong>USE</strong> Plan Mode for complex multi-step tasks</li>
        </ol>
      </ac:rich-text-body>
    </ac:structured-macro>
    
    <h2>✅ Success Checklist</h2>
    <p>You're fully onboarded when you can check all these:</p>
    <ul>
      <li>✅ Cursor installed with secure configuration (Key Vault or .env)</li>
      <li>✅ MS SQL MCP server working (can query database via AI)</li>
      <li>✅ Using cost-effective model (regular, not thinking)</li>
      <li>✅ Understand repository standards (.cursorrules)</li>
      <li>✅ Read essential documentation</li>
      <li>✅ Completed first successful AI interaction</li>
      <li>✅ Understand git workflow</li>
      <li>✅ Know where to get help</li>
    </ul>
    
    <h2>🆘 Need Help?</h2>
    <ul>
      <li><strong>Access Issues:</strong> Contact your team lead</li>
      <li><strong>Technical Questions:</strong> Check documentation first, then ask in team channel</li>
      <li><strong>Domain Questions:</strong> Contact your domain expert</li>
    </ul>
    
    <hr/>
    
    <p style="text-align: center; color: #6B778C; font-size: 0.9em;">
      <strong>Maintained By:</strong> ESO Business Intelligence Team<br/>
      <strong>Last Updated:</strong> {last_updated}<br/>
      <strong>Source:</strong> <a href="https://bitbucket.org/eso-bi-semantic/semantic">Git Repository</a>
    </p>
    """.format(last_updated=datetime.datetime.now().strftime('%Y-%m-%d'))
    
    return update_page_content(
        confluence=confluence,
        page_id=page_id,
        page_title=onboarding_title,
        content=index_content
    )


def sync_file_to_confluence(confluence, space_key: str, file_path: str, mapping: dict, repo_root: Path):
    """
    Sync a single file to Confluence
    """
    full_path = repo_root / file_path
    
    if not full_path.exists():
        print(f"[WARN] File not found: {file_path}")
        return False
    
    # Read file content
    with open(full_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Convert markdown to Confluence format
    converted_content = convert_markdown_to_confluence(markdown_content)
    
    # Add metadata header
    header = f"""
    <ac:structured-macro ac:name="info">
      <ac:rich-text-body>
        <p><strong>Source:</strong> <a href="https://bitbucket.org/eso-bi-semantic/semantic/src/main/{file_path}">{file_path}</a></p>
        <p><strong>Last Synced:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Description:</strong> {mapping.get('description', 'No description available')}</p>
      </ac:rich-text-body>
    </ac:structured-macro>
    <hr/>
    """
    
    # Add professional footer
    footer = """
    <hr/>
    <ac:structured-macro ac:name="tip">
      <ac:rich-text-body>
        <p><strong>💡 Found an issue or want to improve this documentation?</strong></p>
        <p>This content is auto-synced from our Git repository. To make changes:</p>
        <ol>
          <li>Edit the source file in Git</li>
          <li>Submit a pull request</li>
          <li>Changes will sync to Confluence automatically</li>
        </ol>
      </ac:rich-text-body>
    </ac:structured-macro>
    <p style="text-align: center; color: #6B778C; font-size: 0.9em;">
      <strong>Maintained By:</strong> ESO Business Intelligence Team<br/>
      <strong>Questions?</strong> Contact your team lead or ask in team channel
    </p>
    """
    
    # Combine header, content, and footer
    confluence_content = header + converted_content + footer
    
    # Get or create page
    page_id = get_or_create_page(
        confluence=confluence,
        space_key=space_key,
        parent_title=mapping['parent'],
        page_title=mapping['title']
    )
    
    if not page_id:
        return False
    
    # Update page content
    return update_page_content(
        confluence=confluence,
        page_id=page_id,
        page_title=mapping['title'],
        content=confluence_content
    )


# ========================================
# MAIN SCRIPT
# ========================================

def main():
    """
    Main sync function for onboarding documentation
    """
    print("=" * 60)
    print("Confluence Onboarding Sync Script")
    print("=" * 60)
    
    # Check for required environment variables
    if not CONFLUENCE_USERNAME or not CONFLUENCE_API_TOKEN:
        print("\n[ERROR] Missing required environment variables!")
        print("\nPlease set:")
        print("   - CONFLUENCE_USERNAME (your email)")
        print("   - CONFLUENCE_API_TOKEN (create at: https://id.atlassian.com/manage-profile/security/api-tokens)")
        print("\nYou can load these from Azure Key Vault:")
        print("   .\\load-secrets-from-keyvault.ps1 -KeyVaultName '[vault-name]'")
        print("\nOr add to your .env file:")
        print("   CONFLUENCE_USERNAME=your.email@eso.com")
        print("   CONFLUENCE_API_TOKEN=your-api-token-here")
        sys.exit(1)
    
    # Initialize Confluence connection
    print("\nConnecting to Confluence...")
    print(f"   URL: {CONFLUENCE_URL}")
    print(f"   User: {CONFLUENCE_USERNAME}")
    print(f"   Space: {CONFLUENCE_SPACE_KEY}")
    
    try:
        confluence = Confluence(
            url=CONFLUENCE_URL,
            username=CONFLUENCE_USERNAME,
            password=CONFLUENCE_API_TOKEN,
            cloud=True
        )
        # Test connection
        confluence.get_space(CONFLUENCE_SPACE_KEY)
        print("[OK] Connected successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Confluence: {e}")
        sys.exit(1)
    
    # Get repository root
    repo_root = Path(__file__).parent
    print(f"\nRepository root: {repo_root}")
    
    # Ensure semantic page exists
    print(f"\nVerifying '{PARENT_PAGE_TITLE}' page exists...")
    try:
        semantic_page = confluence.get_page_by_title(space=CONFLUENCE_SPACE_KEY, title=PARENT_PAGE_TITLE)
        if semantic_page:
            print(f"[OK] Found '{PARENT_PAGE_TITLE}' page")
        else:
            print(f"[ERROR] '{PARENT_PAGE_TITLE}' page not found! Please create it first.")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error finding '{PARENT_PAGE_TITLE}' page: {e}")
        sys.exit(1)
    
    # Create Onboarding index page
    print(f"\nCreating '{ONBOARDING_PAGE_TITLE}' index page...")
    if not create_onboarding_index_page(confluence, CONFLUENCE_SPACE_KEY, PARENT_PAGE_TITLE, ONBOARDING_PAGE_TITLE):
        print(f"[ERROR] Failed to create '{ONBOARDING_PAGE_TITLE}' page")
        sys.exit(1)
    
    # Sync all onboarding files
    print("\nSyncing onboarding files to Confluence...")
    success_count = 0
    fail_count = 0
    
    for file_path, mapping in ONBOARDING_MAPPINGS.items():
        print(f"\n{'='*60}")
        print(f"Processing: {file_path}")
        print(f"→ {mapping['title']}")
        print(f"{'='*60}")
        
        if sync_file_to_confluence(confluence, CONFLUENCE_SPACE_KEY, file_path, mapping, repo_root):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SYNC SUMMARY")
    print("=" * 60)
    print(f"Successfully synced: {success_count} files")
    print(f"Failed: {fail_count} files")
    print(f"\n✅ Onboarding section created!")
    print(f"\n📍 View in Confluence:")
    print(f"   {CONFLUENCE_URL}/spaces/{CONFLUENCE_SPACE_KEY}/pages")
    print(f"   Navigate to: {PARENT_PAGE_TITLE} → {ONBOARDING_PAGE_TITLE}")
    print("=" * 60)


if __name__ == "__main__":
    main()

















































