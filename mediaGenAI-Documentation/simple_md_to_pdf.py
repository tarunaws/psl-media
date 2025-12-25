#!/usr/bin/env python3
"""
Simple Markdown to PDF Converter
Uses markdown and built-in html2text capabilities
"""

import os
import glob
import markdown
import subprocess
import sys
from pathlib import Path

def convert_md_to_html(md_file_path, output_dir="pdfs"):
    """Convert markdown to HTML first"""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read markdown file
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except Exception as e:
        print(f"Error reading {md_file_path}: {e}")
        return None
    
    # Convert markdown to HTML
    html = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'toc'])
    
    # Add CSS styling for better appearance
    css_styles = """
    <style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
        line-height: 1.6;
        margin: 40px;
        color: #333;
        max-width: 800px;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50;
        margin-top: 30px;
        margin-bottom: 15px;
    }
    h1 {
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
        font-size: 2.2em;
    }
    h2 {
        border-bottom: 2px solid #e74c3c;
        padding-bottom: 5px;
        font-size: 1.8em;
    }
    h3 {
        font-size: 1.4em;
        color: #34495e;
    }
    code {
        background-color: #f8f9fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: 'SF Mono', 'Monaco', 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
        font-size: 0.9em;
    }
    pre {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 15px;
        overflow-x: auto;
        font-family: 'SF Mono', 'Monaco', 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
    }
    pre code {
        background: none;
        padding: 0;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 20px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    table, th, td {
        border: 1px solid #ddd;
    }
    th, td {
        padding: 12px 15px;
        text-align: left;
    }
    th {
        background-color: #3498db;
        color: white;
        font-weight: bold;
    }
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    blockquote {
        border-left: 4px solid #3498db;
        margin: 20px 0;
        padding: 10px 20px;
        background-color: #f8f9fa;
        font-style: italic;
    }
    ul, ol {
        margin: 15px 0;
        padding-left: 30px;
    }
    li {
        margin: 8px 0;
    }
    a {
        color: #3498db;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    @media print {
        body {
            margin: 20px;
        }
        h1, h2 {
            page-break-after: avoid;
        }
        pre, table {
            page-break-inside: avoid;
        }
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
        <h1 style="text-align: center; color: #2c3e50; margin-bottom: 30px;">{Path(md_file_path).stem.replace('_', ' ').title()}</h1>
        {html}
    </body>
    </html>
    """
    
    # Save HTML file
    html_filename = os.path.join(output_dir, Path(md_file_path).stem + '.html')
    
    try:
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return html_filename
    except Exception as e:
        print(f"❌ Error creating HTML for {md_file_path}: {e}")
        return None

def convert_html_to_pdf_via_browser(html_file):
    """Convert HTML to PDF using system's print-to-PDF capability"""
    
    pdf_file = html_file.replace('.html', '.pdf')
    
    # Try different methods to convert HTML to PDF
    methods = [
        # Method 1: Try using wkhtmltopdf if available
        f"wkhtmltopdf --page-size A4 --margin-top 20mm --margin-bottom 20mm --margin-left 15mm --margin-right 15mm '{html_file}' '{pdf_file}'",
        
        # Method 2: Try using Chrome/Chromium headless
        f"google-chrome --headless --disable-gpu --print-to-pdf='{pdf_file}' --print-to-pdf-no-header 'file://{os.path.abspath(html_file)}'",
        
        # Method 3: Try using Chromium
        f"chromium --headless --disable-gpu --print-to-pdf='{pdf_file}' --print-to-pdf-no-header 'file://{os.path.abspath(html_file)}'",
        
        # Method 4: Try using Safari (macOS)
        f"Safari --headless --print-to-pdf '{pdf_file}' '{html_file}'" # Note: This might not work
    ]
    
    for method in methods:
        try:
            result = subprocess.run(method, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and os.path.exists(pdf_file):
                return pdf_file
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            continue
    
    return None

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
    print("📝 Step 1: Converting Markdown to HTML...")
    
    html_files = []
    success_count = 0
    
    # Convert each file to HTML first
    for md_file in md_files:
        print(f"   Processing: {md_file}")
        html_file = convert_md_to_html(md_file)
        if html_file:
            html_files.append(html_file)
            success_count += 1
            print(f"   ✅ HTML created: {html_file}")
        else:
            print(f"   ❌ Failed to convert: {md_file}")
    
    print(f"\n📊 HTML Conversion Summary:")
    print(f"   ✅ Successfully converted: {success_count}/{len(md_files)} files to HTML")
    print(f"   📁 HTML files saved in: ./pdfs/ directory")
    
    # Try to convert HTML to PDF
    print(f"\n🔄 Step 2: Attempting to convert HTML to PDF...")
    print(f"📋 Checking for PDF conversion tools...")
    
    # Check what tools are available
    tools_available = []
    tools_to_check = ['wkhtmltopdf', 'google-chrome', 'chromium']
    
    for tool in tools_to_check:
        try:
            result = subprocess.run(f"which {tool}", shell=True, capture_output=True)
            if result.returncode == 0:
                tools_available.append(tool)
                print(f"   ✅ Found: {tool}")
        except:
            pass
    
    if not tools_available:
        print(f"\n⚠️  No PDF conversion tools found.")
        print(f"📄 HTML files have been created successfully in ./pdfs/ directory")
        print(f"💡 To convert to PDF manually:")
        print(f"   1. Open each HTML file in your browser")
        print(f"   2. Use File → Print → Save as PDF")
        print(f"   3. Or install wkhtmltopdf: brew install wkhtmltopdf")
        return
    
    # Try to convert HTML files to PDF
    pdf_success_count = 0
    for html_file in html_files:
        pdf_file = convert_html_to_pdf_via_browser(html_file)
        if pdf_file:
            pdf_success_count += 1
            print(f"   ✅ PDF created: {pdf_file}")
        else:
            print(f"   ⚠️  Could not create PDF for: {html_file}")
    
    print(f"\n📊 Final Summary:")
    print(f"   📄 HTML files: {success_count}/{len(md_files)} created successfully")
    print(f"   📄 PDF files: {pdf_success_count}/{len(html_files)} created successfully") 
    print(f"   📁 Files saved in: ./pdfs/ directory")
    
    if pdf_success_count > 0:
        print("🎉 PDF conversion completed!")
    else:
        print("💡 HTML files created - you can manually print them to PDF from your browser")

if __name__ == "__main__":
    main()