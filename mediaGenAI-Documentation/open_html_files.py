#!/usr/bin/env python3
"""
HTML File Opener - Opens all HTML files in browser for manual PDF conversion
"""

import os
import webbrowser
import glob
import time

def main():
    print("🌐 Opening HTML files in your default browser...")
    print("💡 For each file that opens:")
    print("   1. Press Cmd+P (or Ctrl+P)")  
    print("   2. Choose 'Save as PDF' or 'Print to PDF'")
    print("   3. Save the PDF to your desired location")
    print()
    
    html_files = glob.glob("pdfs/*.html")
    
    if not html_files:
        print("❌ No HTML files found in pdfs/ directory")
        return
    
    print(f"📄 Found {len(html_files)} HTML files to convert:")
    for i, html_file in enumerate(html_files, 1):
        filename = os.path.basename(html_file)
        print(f"   {i}. {filename}")
    
    print()
    input("Press Enter to start opening files in browser...")
    
    for i, html_file in enumerate(html_files, 1):
        abs_path = os.path.abspath(html_file)
        file_url = f"file://{abs_path}"
        
        print(f"🌐 Opening {i}/{len(html_files)}: {os.path.basename(html_file)}")
        
        try:
            webbrowser.open(file_url)
            print("   ✅ Opened in browser")
            
            if i < len(html_files):
                print("   ⏳ Waiting 3 seconds before opening next file...")
                time.sleep(3)
        except Exception as e:
            print(f"   ❌ Error opening: {e}")
    
    print()
    print("🎉 All HTML files opened!")
    print("💾 Remember to save each one as PDF using Cmd+P → Save as PDF")

if __name__ == "__main__":
    main()