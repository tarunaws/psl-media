#!/usr/bin/env python3
"""
HTML to PDF Converter using macOS Safari/Chrome
"""

import os
import subprocess
import glob

def convert_html_to_pdf_safari(html_file):
    """Convert HTML to PDF using macOS tools"""
    
    pdf_file = html_file.replace('.html', '.pdf')
    abs_html_path = os.path.abspath(html_file)
    
    # Method 1: Try using Safari's print-to-pdf (via AppleScript)
    applescript = f'''
    tell application "Safari"
        activate
        open location "file://{abs_html_path}"
        delay 2
        tell application "System Events"
            keystroke "p" using {{command down}}
            delay 1
            click button "PDF" of window 1
            delay 1
            keystroke "s" using {{command down}}
            delay 1
            keystroke "{pdf_file}"
            delay 1
            keystroke return
        end tell
        delay 2
        close front window
    end tell
    '''
    
    try:
        subprocess.run(['osascript', '-e', applescript], timeout=30)
        if os.path.exists(pdf_file):
            return pdf_file
    except:
        pass
    
    return None

def main():
    print("🔄 Converting HTML files to PDF using macOS tools...")
    
    html_files = glob.glob("pdfs/*.html")
    
    if not html_files:
        print("❌ No HTML files found in pdfs/ directory")
        return
    
    success_count = 0
    
    for html_file in html_files:
        print(f"📄 Converting: {html_file}")
        pdf_file = convert_html_to_pdf_safari(html_file)
        
        if pdf_file:
            success_count += 1
            print(f"✅ Created: {pdf_file}")
        else:
            print(f"❌ Failed: {html_file}")
    
    print(f"\n📊 Summary: {success_count}/{len(html_files)} files converted to PDF")

if __name__ == "__main__":
    main()