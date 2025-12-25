#!/usr/bin/env python3
"""
Markdown to PDF Converter
Converts all .md files in the workspace to PDF format
"""

import os
import glob
import markdown
from weasyprint import HTML, CSS
from pathlib import Path
import sys

def convert_md_to_pdf(md_file_path, output_dir="pdfs"):
    """Convert a single markdown file to PDF"""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read markdown file
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except Exception as e:
        print(f"Error reading {md_file_path}: {e}")
        return False
    
    # Convert markdown to HTML
    html = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'toc'])
    
    # Add CSS styling for better PDF appearance
    css_styles = """
    <style>
    body {
        font-family: Arial, sans-serif;
        line-height: 1.6;
        margin: 40px;
        color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50;
        margin-top: 30px;
        margin-bottom: 15px;
    }
    h1 {
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
    }
    h2 {
        border-bottom: 2px solid #e74c3c;
        padding-bottom: 5px;
    }
    code {
        background-color: #f8f9fa;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: 'Courier New', monospace;
    }
    pre {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 15px;
        overflow-x: auto;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
    }
    table, th, td {
        border: 1px solid #ddd;
    }
    th, td {
        padding: 12px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    blockquote {
        border-left: 4px solid #3498db;
        margin: 20px 0;
        padding: 10px 20px;
        background-color: #f8f9fa;
    }
    ul, ol {
        margin: 15px 0;
        padding-left: 30px;
    }
    li {
        margin: 5px 0;
    }
    </style>
    """
    
    # Create full HTML document
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{Path(md_file_path).stem}</title>
        {css_styles}
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    
    # Generate PDF filename
    pdf_filename = os.path.join(output_dir, Path(md_file_path).stem + '.pdf')
    
    try:
        # Convert HTML to PDF
        HTML(string=html_content).write_pdf(pdf_filename)
        print(f"✅ Converted: {md_file_path} → {pdf_filename}")
        return True
    except Exception as e:
        print(f"❌ Error converting {md_file_path}: {e}")
        return False

def main():
    """Main function to convert all markdown files"""
    
    # Get the current directory
    current_dir = os.getcwd()
    print(f"🔍 Searching for .md files in: {current_dir}")
    
    # Find all markdown files recursively
    md_files = glob.glob("**/*.md", recursive=True)
    
    if not md_files:
        print("❌ No .md files found in the current directory and subdirectories")
        return
    
    print(f"📄 Found {len(md_files)} markdown files:")
    for md_file in md_files:
        print(f"   - {md_file}")
    
    print("\n🔄 Starting conversion process...")
    
    success_count = 0
    total_files = len(md_files)
    
    # Convert each file
    for md_file in md_files:
        if convert_md_to_pdf(md_file):
            success_count += 1
    
    print(f"\n📊 Conversion Summary:")
    print(f"   ✅ Successfully converted: {success_count}/{total_files} files")
    print(f"   📁 PDF files saved in: ./pdfs/ directory")
    
    if success_count == total_files:
        print("🎉 All files converted successfully!")
    else:
        print(f"⚠️  {total_files - success_count} files failed to convert")

if __name__ == "__main__":
    main()