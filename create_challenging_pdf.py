#!/usr/bin/env python3
import fitz  # PyMuPDF
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from io import BytesIO
import random
import string

def create_challenging_pdf(output_path="advanced_redaction_challenge.pdf"):
    """
    Creates a PDF with challenging content for redaction tools.
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title = Paragraph("<font size='16'><b>Advanced Redaction Challenge Document</b></font>", styles["Normal"])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Introduction
    intro = Paragraph(
        """This document contains various forms of sensitive information that are 
        designed to challenge redaction tools. Some information is obvious, while 
        other data is obfuscated, split across lines, embedded in images, or formatted 
        in ways to evade detection.""", 
        styles["Normal"]
    )
    elements.append(intro)
    elements.append(Spacer(1, 12))
    
    # 1. Standard format but with invisible characters
    email_section = Paragraph("<b>1. Emails with Special Formatting</b>", styles["Normal"])
    elements.append(email_section)
    elements.append(Spacer(1, 6))
    
    # Normal email
    elements.append(Paragraph("Normal email: john.doe@example.com", styles["Normal"]))
    
    # Email with zero-width spaces
    elements.append(Paragraph("Email with zero-width spaces: alice\u200B.\u200Bsmith@\u200Bcompany\u200B.org", styles["Normal"]))
    
    # Email split across multiple lines
    elements.append(Paragraph("Email split across lines: robert", styles["Normal"]))
    elements.append(Paragraph(".williams@enterprise", styles["Normal"]))
    elements.append(Paragraph(".net", styles["Normal"]))
    
    # Email with unusual TLD
    elements.append(Paragraph("Email with unusual TLD: contact@business.solutions", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 2. Phone numbers in various formats
    phone_section = Paragraph("<b>2. Phone Numbers in Various Formats</b>", styles["Normal"])
    elements.append(phone_section)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("Standard US: (555) 123-4567", styles["Normal"]))
    elements.append(Paragraph("International: +44 20 7946 0958", styles["Normal"]))
    elements.append(Paragraph("No separators: 5551234567", styles["Normal"]))
    elements.append(Paragraph("With letters: 1-800-CALL-NOW", styles["Normal"]))
    elements.append(Paragraph("Split format: 555 123", styles["Normal"]))
    elements.append(Paragraph("4567", styles["Normal"]))
    elements.append(Paragraph("Unusual format: 555/123.4567", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 3. Credit card information
    cc_section = Paragraph("<b>3. Credit Card Information</b>", styles["Normal"])
    elements.append(cc_section)
    elements.append(Spacer(1, 6))
    
    # Standard format
    elements.append(Paragraph("Visa: 4111 1111 1111 1111", styles["Normal"]))
    
    # Without spaces
    elements.append(Paragraph("MasterCard without spaces: 5500000000000004", styles["Normal"]))
    
    # With other separators
    elements.append(Paragraph("Amex with dashes: 3782-8224-6310-005", styles["Normal"]))
    
    # Split across lines
    elements.append(Paragraph("Split card number: 6011 0009", styles["Normal"]))
    elements.append(Paragraph("9013 9424", styles["Normal"]))
    
    # With text around it
    elements.append(Paragraph("Card embedded in text: Your card 3566002020360505 has been confirmed", styles["Normal"]))
    
    # With confusing strings nearby
    elements.append(Paragraph("With similar numbers nearby: Order #4111222233334444 - Customer ID: 4111-1111-1111-1111", styles["Normal"]))
    
    # CVV codes
    elements.append(Paragraph("CVV code variations:", styles["Normal"]))
    elements.append(Paragraph("CVV: 123", styles["Normal"]))
    elements.append(Paragraph("Security Code: 456", styles["Normal"]))
    elements.append(Paragraph("CVC2: 789", styles["Normal"]))
    elements.append(Paragraph("The code is: 321", styles["Normal"]))
    
    # Expiration dates
    elements.append(Paragraph("Expiration dates:", styles["Normal"]))
    elements.append(Paragraph("Exp: 05/25", styles["Normal"]))
    elements.append(Paragraph("Valid thru: 08-2028", styles["Normal"]))
    elements.append(Paragraph("Expiry: 12/24", styles["Normal"]))
    elements.append(Paragraph("Card expires on: 01 / 2026", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 4. Banking information
    bank_section = Paragraph("<b>4. Banking Information</b>", styles["Normal"])
    elements.append(bank_section)
    elements.append(Spacer(1, 6))
    
    # IBAN examples
    elements.append(Paragraph("Standard IBAN: DE89 3704 0044 0532 0130 00", styles["Normal"]))
    elements.append(Paragraph("IBAN without spaces: GB29NWBK60161331926819", styles["Normal"]))
    elements.append(Paragraph("Split IBAN: FR14 2004", styles["Normal"]))
    elements.append(Paragraph("1010 0505 0001 3M02 606", styles["Normal"]))
    
    # BIC/SWIFT examples
    elements.append(Paragraph("BIC: DEUTDEFF", styles["Normal"]))
    elements.append(Paragraph("SWIFT Code: CHASUS33XXX", styles["Normal"]))
    elements.append(Paragraph("Bank code is MIDLGB22 for transfers", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 5. Obfuscated information
    obfs_section = Paragraph("<b>5. Obfuscated Information</b>", styles["Normal"])
    elements.append(obfs_section)
    elements.append(Spacer(1, 6))
    
    # Encoded or obfuscated information
    elements.append(Paragraph("Base64 email: am9obi5kb2VAZXhhbXBsZS5jb20=", styles["Normal"]))
    elements.append(Paragraph("Reversed credit card: 1111 1111 1111 1144", styles["Normal"]))
    elements.append(Paragraph("Credit card with letters: 4111-AAAA-1111-BBBB", styles["Normal"]))
    elements.append(Paragraph("Phone with letters: 5-A-5-B-1-C-2-D-3-E-4-F-5-G-6-H-7", styles["Normal"]))
    
    # Mixed with Unicode
    elements.append(Paragraph("Unicode confusables: 𝟒𝟏𝟏𝟏 𝟏𝟏𝟏𝟏 𝟏𝟏𝟏𝟏 𝟏𝟏𝟏𝟏", styles["Normal"]))
    elements.append(Paragraph("IBAN with homoglyphs: DЕ89 3704 0044 0532 0130 00", styles["Normal"]))  # DE uses Cyrillic Е
    
    elements.append(Spacer(1, 12))
    
    # 6. Data in tables
    table_section = Paragraph("<b>6. Information in Tables</b>", styles["Normal"])
    elements.append(table_section)
    elements.append(Spacer(1, 6))
    
    # Simple table with sensitive data
    data = [
        ['Name', 'Email', 'Phone', 'Card Number'],
        ['John Smith', 'john@example.com', '(555) 123-4567', '4111 1111 1111 1111'],
        ['Jane Doe', 'jane@company.org', '+1 555-987-6543', '5500 0000 0000 0004'],
        ['Robert Brown', 'robert@business.net', '555.123.4567', '3782 8224 6310 005'],
    ]
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # 7. Information in context
    context_section = Paragraph("<b>7. Information in Context</b>", styles["Normal"])
    elements.append(context_section)
    elements.append(Spacer(1, 6))
    
    paragraph = """
    During our meeting on June 15, 2023, Mr. Smith (email: ceo@megacorp.com, phone: 555-123-9876)
    approved the purchase using his corporate card (Amex 3714 496353 98431, exp: 07/26, CVV: 1234).
    For international transfers, please use our bank account (IBAN: ES91 2100 0418 4502 0005 1332,
    BIC: CAIXESBBXXX). Contact our support team at help@megacorp.com or call 1-800-555-HELP if you
    have any questions about this transaction.
    """
    
    elements.append(Paragraph(paragraph, styles["Normal"]))
    elements.append(Spacer(1, 12))
    
    # Build the PDF
    doc.build(elements)
    
    # Add an image with embedded text using PyMuPDF
    modify_pdf_with_image(output_path)
    
    print(f"Created challenging PDF: {output_path}")

def modify_pdf_with_image(pdf_path):
    """
    Modify the PDF to add an image with embedded sensitive information
    """
    # Create a temporary PDF with an image containing text
    img_pdf = BytesIO()
    c = canvas.Canvas(img_pdf, pagesize=letter)
    
    # Draw some sensitive information as text in the image
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "Image containing card number: 6011 0009 9013 9424")
    c.drawString(100, 680, "Email in image: security@bank-example.com")
    c.drawString(100, 660, "Phone in image: +1-888-555-0123")
    c.drawString(100, 640, "IBAN in image: CH93 0076 2011 6238 5295 7")
    
    c.save()
    
    # Open the original PDF and add the image PDF as an image
    doc = fitz.open(pdf_path)
    img_pdf.seek(0)
    img_doc = fitz.open("pdf", img_pdf.read())
    
    # Get the first page of each
    page = doc[-1]  # Get the last page of the original document
    img_page = img_doc[0]
    
    # Convert the image page to an image and insert it
    pix = img_page.get_pixmap()
    img_bytes = pix.pil_tobytes(format="png")
    
    # Insert the image
    page.insert_image(
        fitz.Rect(100, 100, 500, 250),  # rectangle where to place the image
        stream=img_bytes,
    )
    
    # Save the modified PDF with incremental update
    doc.save(pdf_path, incremental=True, encryption=False)
    doc.close()
    img_doc.close()

if __name__ == "__main__":
    create_challenging_pdf() 