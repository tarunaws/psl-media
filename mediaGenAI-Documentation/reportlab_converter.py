#!/usr/bin/env python3
"""
Advanced Markdown to PDF Converter using ReportLab
"""

import os
import glob
import markdown
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from pathlib import Path
import re

def clean_html_for_reportlab(html_text):
    """Clean HTML for ReportLab compatibility"""
    # Remove unsupported tags and convert to ReportLab-compatible format
    html_text = re.sub(r'<pre><code[^>]*>', '<pre>', html_text)
    html_text = re.sub(r'</code></pre>', '</pre>', html_text)
    html_text = re.sub(r'<code[^>]*>', '<font name="Courier">', html_text)
    html_text = re.sub(r'</code>', '</font>', html_text)
    html_text = re.sub(r'<table[^>]*>.*?</table>', '', html_text, flags=re.DOTALL)  # Remove tables for now
    html_text = re.sub(r'<img[^>]*>', '', html_text)  # Remove images
    return html_text

def convert_md_to_pdf_reportlab(md_file_path, output_dir="pdfs"):
    """Convert markdown to PDF using ReportLab"""
    
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
    html = markdown.markdown(md_content, extensions=['fenced_code'])
    
    # Generate PDF filename
    pdf_filename = os.path.join(output_dir, Path(md_file_path).stem + '.pdf')
    
    try:
        # Create PDF document
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=HexColor('#2c3e50'),
            alignment=1  # Center alignment
        )
        
        heading1_style = ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            spaceBefore=20,
            textColor=HexColor('#2c3e50')
        )
        
        heading2_style = ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=HexColor('#34495e')
        )
        
        # Story to hold document content
        story = []
        
        # Add title
        title = Path(md_file_path).stem.replace('_', ' ').title()
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 20))
        
        # Split content by lines and process
        lines = md_content.split('\n')
        current_paragraph = ""
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if current_paragraph:
                    story.append(Paragraph(current_paragraph, styles['Normal']))
                    story.append(Spacer(1, 6))
                    current_paragraph = ""
                continue
            
            if line.startswith('# '):
                if current_paragraph:
                    story.append(Paragraph(current_paragraph, styles['Normal']))
                    current_paragraph = ""
                story.append(Spacer(1, 12))
                story.append(Paragraph(line[2:], heading1_style))
                
            elif line.startswith('## '):
                if current_paragraph:
                    story.append(Paragraph(current_paragraph, styles['Normal']))
                    current_paragraph = ""
                story.append(Spacer(1, 10))
                story.append(Paragraph(line[3:], heading2_style))
                
            elif line.startswith('### '):
                if current_paragraph:
                    story.append(Paragraph(current_paragraph, styles['Normal']))
                    current_paragraph = ""
                story.append(Spacer(1, 8))
                story.append(Paragraph(line[4:], styles['Heading3']))
                
            elif line.startswith('```'):
                # Skip code blocks for now (ReportLab has limited code support)
                continue
                
            elif line.startswith('- ') or line.startswith('* '):
                if current_paragraph:
                    story.append(Paragraph(current_paragraph, styles['Normal']))
                    current_paragraph = ""
                bullet_text = f"• {line[2:]}"
                story.append(Paragraph(bullet_text, styles['Normal']))
                
            elif line.startswith('1. ') or re.match(r'^\d+\. ', line):
                if current_paragraph:
                    story.append(Paragraph(current_paragraph, styles['Normal']))
                    current_paragraph = ""
                story.append(Paragraph(line, styles['Normal']))
                
            else:
                if current_paragraph:
                    current_paragraph += " " + line
                else:
                    current_paragraph = line
        
        # Add any remaining paragraph
        if current_paragraph:
            story.append(Paragraph(current_paragraph, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        print(f"✅ Converted: {md_file_path} → {pdf_filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error converting {md_file_path}: {e}")
        return False

def main():
    """Main function to convert all markdown files to PDF"""
    
    print("🔍 Searching for .md files...")
    
    # Find all markdown files recursively
    md_files = glob.glob("**/*.md", recursive=True)
    
    if not md_files:
        print("❌ No .md files found")
        return
    
    print(f"📄 Found {len(md_files)} markdown files")
    print("\n🔄 Converting to PDF using ReportLab...")
    
    success_count = 0
    
    for md_file in md_files:
        if convert_md_to_pdf_reportlab(md_file):
            success_count += 1
    
    print(f"\n📊 Conversion Summary:")
    print(f"   ✅ Successfully converted: {success_count}/{len(md_files)} files to PDF")
    print(f"   📁 PDF files saved in: ./pdfs/ directory")
    
    if success_count == len(md_files):
        print("🎉 All files converted successfully!")
    else:
        print(f"⚠️  {len(md_files) - success_count} files failed to convert")

if __name__ == "__main__":
    main()