#!/usr/bin/env python3
"""Create a test PDF with various sensitive data for testing the redactor."""

import fitz  # PyMuPDF

def create_test_pdf(output_path="test_sensitive.pdf"):
    doc = fitz.open()
    
    # Page 1: Personal Information
    page = doc.new_page()
    y = 72
    
    # Title
    page.insert_text((72, y), "CONFIDENTIAL - Employee Record", fontsize=18, fontname="helv")
    y += 40
    
    page.insert_text((72, y), "Personal Information", fontsize=14, fontname="helv")
    y += 30
    
    # Phone numbers (various formats)
    page.insert_text((72, y), "Phone Numbers:", fontsize=11, fontname="helv")
    y += 20
    page.insert_text((90, y), "Mobile: +1-555-123-4567", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "Home: (555) 987-6543", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "Work: 555.246.8135", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "India Mobile: +91 9876543210", fontsize=10, fontname="helv")
    y += 30
    
    # Email addresses
    page.insert_text((72, y), "Email Addresses:", fontsize=11, fontname="helv")
    y += 20
    page.insert_text((90, y), "Personal: john.doe@gmail.com", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "Work: jdoe@company.org", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "Alternate: jane_smith+work@example.co.uk", fontsize=10, fontname="helv")
    y += 30
    
    # Credit card numbers
    page.insert_text((72, y), "Payment Information:", fontsize=11, fontname="helv")
    y += 20
    page.insert_text((90, y), "Visa: 4532 0151 2345 6789", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "Mastercard: 5425-2334-3456-7890", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "Amex: 371449635398431", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "CVV: 123", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "Expiry: 05/26", fontsize=10, fontname="helv")
    y += 30
    
    # Indian IDs
    page.insert_text((72, y), "Indian Government IDs:", fontsize=11, fontname="helv")
    y += 20
    page.insert_text((90, y), "Aadhaar: 2234 5678 9012", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "PAN: ABCPD1234E", fontsize=10, fontname="helv")
    y += 30
    
    # IBAN / BIC
    page.insert_text((72, y), "Banking Details:", fontsize=11, fontname="helv")
    y += 20
    page.insert_text((90, y), "IBAN: DE89370400440532013000", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((90, y), "BIC: COBADEFFXXX", fontsize=10, fontname="helv")
    y += 40
    
    # Footer note
    page.insert_text((72, y), "This document contains fictional data for testing purposes only.",
                     fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))
    
    doc.save(output_path)
    doc.close()
    print(f"[+] Test PDF created: {output_path}")
    print(f"    Contains: phone numbers, emails, credit cards, CVV, expiry dates,")
    print(f"    Aadhaar, PAN, IBAN, and BIC/SWIFT codes")

if __name__ == "__main__":
    create_test_pdf()
