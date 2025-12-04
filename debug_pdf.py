#!/usr/bin/env python3

import sys
import Quartz
from Foundation import NSURL

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using Vision framework"""
    try:
        # Load PDF
        pdf_url = NSURL.fileURLWithPath_(pdf_path)
        pdf_doc = Quartz.PDFDocument.alloc().initWithURL_(pdf_url)

        if pdf_doc is None:
            print(f"Warning: Could not load PDF: {pdf_path}")
            return ""

        all_text = []
        page_count = pdf_doc.pageCount()

        for page_num in range(page_count):
            page = pdf_doc.pageAtIndex_(page_num)
            if page:
                text = page.string()
                if text:
                    all_text.append(f"=== PAGE {page_num + 1} ===\n{text}")

        return "\n\n".join(all_text)

    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return ""

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: debug_pdf.py <pdf_file>")
        sys.exit(1)

    text = extract_text_from_pdf(sys.argv[1])
    print(text)
