#!/usr/bin/env python3
"""
Challenging PDF Generator for PDFRedactor Testing
This script creates a PDF file with various sensitive information patterns
to test the capabilities of the PDFRedactor tool.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    PageBreak, Image, Flowable, Frame, FrameBreak, NextPageTemplate, 
    PageTemplate, BaseDocTemplate
)
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.units import inch, mm
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.barcode import qr
from reportlab.graphics import renderPDF
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import random

# Register some fonts
try:
    pdfmetrics.registerFont(TTFont('Vera', 'Vera.ttf'))
    pdfmetrics.registerFont(TTFont('VeraBd', 'VeraBd.ttf'))
    pdfmetrics.registerFont(TTFont('VeraIt', 'VeraIt.ttf'))
    CUSTOM_FONT = 'Vera'
except:
    print("Warning: Vera fonts not found, using default fonts")
    CUSTOM_FONT = 'Helvetica'

# Define some sample data
NAMES = [
    "John Smith", 
    "Jane  Q.  Doe", 
    "Mary-Anne Johnson-Williams", 
    "Garcia, Roberto", 
    "Sarah McDowell",
    "James O'Connor",
    "Dr. Elizabeth Chen",
    "Mr. William Jones Jr.",
    "李明 (Li Ming)"
]

PHONE_NUMBERS = [
    "+44 20 7946 0958",
    "555-123-4567 x890",
    "8005551234",
    "(212) 555-9876",
    "800-555\n1234",  # Split across lines
    "Phone Number: 415-555-9090",
    "+1.800.555.1234",
    "+61 4 1234 5678",
    "📞 202-555-0123"
]

EMAIL_ADDRESSES = [
    "user@example.com",
    "john.doe+newsletter@company.org",
    "support@sub.domain.example.co.uk",
    "contact me at user@example.com for details",
    "Email Address: jane.smith@corporation.net",
    "📧 contact@business.com",
    "firstname.lastname@university.edu",
    "user_name@provider-service.com",
    "info@компания.рф"  # IDN email
]

CREDIT_CARDS = [
    "4111111111111111",  # Visa without spaces
    "4111 1111 1111 1111",  # Visa with spaces
    "4111-1111-1111-1111",  # Visa with hyphens
    "5500 0000 0000 0004",  # Mastercard
    "3782 822463 10005",  # Amex (15 digits)
    "Card ending in 1111",
    "Payment method: Visa 4111 1111 1111 1111",
    "Card Number:\n4111 1111 1111 1111",  # Split across lines
    "XXXX-XXXX-XXXX-4321"  # Partially masked
]

CVV_CODES = [
    "123",
    "CVV: 123",
    "(CVV: 123)",
    "Security Code: 456",
    "CVC: 789",
    "Card Verification Value: 321",
    "CV2: 987",
    "CSC: 654"  # Card Security Code
]

EXPIRATION_DATES = [
    "05/25",
    "05/2025",
    "Expires: 05/25",
    "Valid Thru: 01/26",
    "Expiration Date: 12/2024",
    "Exp. Date: 10/27",
    "Good Thru: 11/28",
    "MM/YY: 06/29"
]

BANK_ACCOUNTS = [
    "DE89 3704 0044 0532 0130 00",  # German IBAN with spaces
    "DE89370400440532013000",  # German IBAN without spaces
    "IBAN: DE89 3704 0044 0532 0130 00",
    "GB29NWBK60161331926819",  # UK IBAN
    "FR1420041010050500013M02606",  # French IBAN
    "IT60X0542811101000000123456",  # Italian IBAN
    "DEUTDEFF",  # BIC/SWIFT
    "BIC: SOGEFRPP",  # French BIC with label
    "Bank details: IBAN DE89370400440532013000"
]

CHALLENGING_HEADINGS = [
    "John Smith's Account Details:",
    "Credit Card: 4111 1111 1111 1111",
    "Contact: +1 (555) 123-4567",
    "Section Title: Sensitive Info",
    "SECTION: PERSONAL DETAILS",
    "1. Bank Account Information",
    "I. Contact Information",
    "CONFIDENTIAL: Customer Data",
    "User Profile for jane.doe@example.com",
    "Credit Card Information (4111-1111-1111-1111)"
]

class RotatedText(Flowable):
    """A flowable for rotated text"""
    def __init__(self, text, angle, font="Helvetica", size=10, textColor=colors.black):
        Flowable.__init__(self)
        self.text = text
        self.angle = angle
        self.font = font
        self.size = size
        self.textColor = textColor

    def draw(self):
        canvas = self.canv
        canvas.saveState()
        canvas.translate(0, 0)
        canvas.rotate(self.angle)
        canvas.setFont(self.font, self.size)
        canvas.setFillColor(self.textColor)
        canvas.drawString(0, 0, self.text)
        canvas.restoreState()

    def wrap(self, availWidth, availHeight):
        return (len(self.text) * self.size * 0.6, self.size * 1.2)

class QRCodeFlowable(Flowable):
    """A flowable for QR codes"""
    def __init__(self, data, size=1*inch):
        Flowable.__init__(self)
        self.data = data
        self.size = size
        
    def draw(self):
        qr_code = qr.QrCodeWidget(self.data)
        bounds = qr_code.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        d = Drawing(self.size, self.size, transform=[self.size/width, 0, 0, self.size/height, 0, 0])
        d.add(qr_code)
        renderPDF.draw(d, self.canv, 0, 0)
        
    def wrap(self, availWidth, availHeight):
        return (self.size, self.size)

def create_watermark(canvas, doc):
    """Add a watermark to the page"""
    canvas.saveState()
    canvas.setFont(CUSTOM_FONT, 60)
    canvas.setFillColor(colors.lightgrey)
    canvas.setStrokeColor(colors.lightgrey)
    canvas.translate(A4[0]/2, A4[1]/2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "CONFIDENTIAL")
    canvas.restoreState()

def create_header_footer(canvas, doc):
    """Add header and footer to the page"""
    canvas.saveState()
    
    # Header
    canvas.setFont(CUSTOM_FONT, 8)
    canvas.drawString(inch, A4[1] - 0.5*inch, "CONFIDENTIAL DOCUMENT")
    canvas.drawRightString(A4[0] - inch, A4[1] - 0.5*inch, f"Page {doc.page}")
    
    # Footer with sensitive info
    canvas.setFont(CUSTOM_FONT, 6)
    canvas.drawString(inch, 0.5*inch, f"Document owner: {random.choice(NAMES)}")
    canvas.drawRightString(A4[0] - inch, 0.5*inch, f"Contact: {random.choice(PHONE_NUMBERS)}")
    
    canvas.restoreState()

def create_two_column_template():
    """Create a two-column page template"""
    frame_left = Frame(
        inch, 
        inch, 
        A4[0]/2 - 1.5*inch, 
        A4[1] - 2*inch,
        leftPadding=0,
        rightPadding=0,
        id='left'
    )
    
    frame_right = Frame(
        A4[0]/2 - 0.25*inch, 
        inch, 
        A4[0]/2 - 1.5*inch, 
        A4[1] - 2*inch,
        leftPadding=0,
        rightPadding=0,
        id='right'
    )
    
    return PageTemplate(
        id='TwoColumn',
        frames=[frame_left, frame_right],
        onPage=create_header_footer,
        onPageEnd=create_watermark
    )

def generate_challenging_pdf(output_file="challenging_redaction_test.pdf"):
    """Generate a challenging PDF file for testing the PDFRedactor tool"""
    
    # Create document with multiple templates
    doc = BaseDocTemplate(
        output_file,
        pagesize=A4,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch
    )
    
    # Add page templates
    standard_template = PageTemplate(
        id='Standard',
        frames=[Frame(doc.leftMargin, doc.bottomMargin, 
                      doc.width, doc.height, id='normal')],
        onPage=create_header_footer,
        onPageEnd=create_watermark
    )
    
    two_column_template = create_two_column_template()
    
    doc.addPageTemplates([standard_template, two_column_template])
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Add custom styles
    styles.add(ParagraphStyle(
        name='Heading_with_sensitive',
        parent=styles['Heading1'],
        textColor=colors.darkblue,
        fontName=CUSTOM_FONT
    ))
    
    styles.add(ParagraphStyle(
        name='Normal_small',
        parent=styles['Normal'],
        fontSize=8,
        fontName=CUSTOM_FONT
    ))
    
    styles.add(ParagraphStyle(
        name='Sensitive_info',
        parent=styles['Normal'],
        textColor=colors.darkred,
        fontName=CUSTOM_FONT
    ))
    
    # Build story elements
    story = []
    
    # Title page
    story.append(Paragraph("Challenging PDF for Redaction Testing", styles['Title']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("This document contains various formats of sensitive information designed to test PDF redaction tools.", styles['Normal']))
    story.append(Spacer(1, 0.25*inch))
    story.append(Paragraph(f"Document Owner: {random.choice(NAMES)}", styles['Normal']))
    story.append(Paragraph(f"Contact: {random.choice(EMAIL_ADDRESSES)}", styles['Normal']))
    story.append(Paragraph(f"Phone: {random.choice(PHONE_NUMBERS)}", styles['Normal']))
    story.append(Spacer(1, 0.5*inch))
    
    story.append(Paragraph("Document Overview:", styles['Heading2']))
    story.append(Paragraph("1. Personal Information Section", styles['Normal']))
    story.append(Paragraph("2. Financial Information Section", styles['Normal']))
    story.append(Paragraph("3. Two-Column Layout with Mixed Content", styles['Normal']))
    story.append(Paragraph("4. Complex Tables and Formatted Text", styles['Normal']))
    story.append(Paragraph("5. Visual Elements and Special Formatting", styles['Normal']))
    
    story.append(PageBreak())
    
    # Section 1: Personal Information
    story.append(Paragraph("1. Personal Information", styles['Heading1']))
    story.append(Spacer(1, 0.1*inch))
    
    # Names with various formats
    story.append(Paragraph("1.1 Customer Names", styles['Heading2']))
    for i, name in enumerate(NAMES):
        story.append(Paragraph(f"Customer {i+1}: {name}", styles['Normal']))
    
    story.append(Spacer(1, 0.2*inch))
    
    # Phone numbers in various formats
    story.append(Paragraph("1.2 Contact Numbers", styles['Heading2']))
    for i, phone in enumerate(PHONE_NUMBERS):
        style = styles['Normal'] if i % 2 == 0 else styles['Normal_small']
        story.append(Paragraph(f"Contact {i+1}: {phone}", style))
    
    story.append(Spacer(1, 0.2*inch))
    
    # Email addresses with variations
    story.append(Paragraph("1.3 Email Addresses", styles['Heading2']))
    for i, email in enumerate(EMAIL_ADDRESSES):
        style = styles['Normal'] if i % 2 == 0 else styles['Sensitive_info']
        story.append(Paragraph(f"Email {i+1}: {email}", style))
    
    story.append(PageBreak())
    
    # Section 2: Financial Information
    story.append(Paragraph("2. Financial Information", styles['Heading1']))
    story.append(Spacer(1, 0.1*inch))
    
    # Credit card information
    story.append(Paragraph("2.1 Payment Methods", styles['Heading2']))
    
    # Create a table for credit card info
    credit_card_data = []
    credit_card_data.append(["Card Type", "Card Number", "Expiration", "Security Code"])
    
    for i in range(5):
        card = random.choice(CREDIT_CARDS)
        exp = random.choice(EXPIRATION_DATES)
        cvv = random.choice(CVV_CODES)
        card_type = "Visa" if card.startswith("4") else "Mastercard" if card.startswith("5") else "Amex"
        credit_card_data.append([card_type, card, exp, cvv])
    
    cc_table = Table(credit_card_data, colWidths=[1*inch, 2.5*inch, 1.5*inch, 1.5*inch])
    cc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), CUSTOM_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(cc_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Bank account details
    story.append(Paragraph("2.2 Bank Account Information", styles['Heading2']))
    for i, account in enumerate(BANK_ACCOUNTS):
        story.append(Paragraph(f"Account {i+1}: {account}", styles['Normal']))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Challenging headings
    story.append(Paragraph("2.3 Additional Financial Details", styles['Heading2']))
    for heading in CHALLENGING_HEADINGS[:5]:
        story.append(Paragraph(heading, styles['Heading_with_sensitive']))
        story.append(Paragraph("This section contains additional details related to the account.", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(PageBreak())
    
    # Section 3: Two-column layout
    story.append(NextPageTemplate('TwoColumn'))
    story.append(Paragraph("3. Two-Column Layout with Mixed Content", styles['Heading1']))
    story.append(Spacer(1, 0.1*inch))
    
    # Left column
    story.append(Paragraph("3.1 Customer Details", styles['Heading2']))
    story.append(Paragraph(f"Name: {random.choice(NAMES)}", styles['Normal']))
    story.append(Paragraph(f"Email: {random.choice(EMAIL_ADDRESSES)}", styles['Normal']))
    story.append(Paragraph(f"Phone: {random.choice(PHONE_NUMBERS)}", styles['Normal']))
    story.append(Paragraph(f"Account: {random.choice(BANK_ACCOUNTS)}", styles['Normal']))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Notes:", styles['Heading3']))
    story.append(Paragraph("Customer requested account statements to be sent to their email address. Verified identity through security questions.", styles['Normal_small']))
    
    # Add a QR code with email
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Scan to contact:", styles['Normal_small']))
    random_email = random.choice(EMAIL_ADDRESSES)
    if '<' in random_email:
        random_email = random_email.split('<')[1].split('>')[0]  # Extract email from formats like "Contact <email@example.com>"
    story.append(QRCodeFlowable(f"mailto:{random_email}", size=1.5*inch))
    
    # Move to right column
    story.append(FrameBreak())
    
    # Right column
    story.append(Paragraph("3.2 Transaction History", styles['Heading2']))
    
    # Create a table for transactions
    transaction_data = [
        ["Date", "Amount", "Description"],
        ["2023-01-15", "$156.78", "Online Purchase"],
        ["2023-01-28", "$1,234.56", "Wire Transfer"],
        ["2023-02-03", "$89.99", "Subscription"],
        ["2023-02-17", "$500.00", "ATM Withdrawal"],
        ["2023-03-01", "$2,345.67", "Payroll Deposit"]
    ]
    
    transaction_table = Table(transaction_data, colWidths=[1*inch, 1*inch, 1.5*inch])
    transaction_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), CUSTOM_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(transaction_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Add some payment info
    story.append(Paragraph("Payment Methods:", styles['Heading3']))
    story.append(Paragraph(f"Primary Card: {random.choice(CREDIT_CARDS)}", styles['Normal']))
    story.append(Paragraph(f"Expiration: {random.choice(EXPIRATION_DATES)}", styles['Normal']))
    story.append(Paragraph(f"CVV: {random.choice(CVV_CODES)}", styles['Normal']))
    
    story.append(PageBreak())
    story.append(NextPageTemplate('Standard'))  # Back to standard template
    
    # Section 4: Complex tables and formatted text
    story.append(Paragraph("4. Complex Tables and Formatted Text", styles['Heading1']))
    story.append(Spacer(1, 0.1*inch))
    
    # Create a complex table with merged cells
    story.append(Paragraph("4.1 Customer Database Extract", styles['Heading2']))
    
    complex_data = [
        ["ID", "Customer Information", "", "", "Financial Data", ""],
        ["", "Name", "Email", "Phone", "Account #", "Card"],
    ]
    
    # Add some rows with merged cells
    for i in range(1, 6):
        complex_data.append([
            f"CUST-{1000+i}",
            random.choice(NAMES),
            random.choice(EMAIL_ADDRESSES),
            random.choice(PHONE_NUMBERS),
            random.choice(BANK_ACCOUNTS).split()[-1] if ' ' in random.choice(BANK_ACCOUNTS) else random.choice(BANK_ACCOUNTS)[-8:],
            random.choice(CREDIT_CARDS)
        ])
    
    complex_table = Table(complex_data, colWidths=[0.7*inch, 1.5*inch, 1.5*inch, 1.3*inch, 1.5*inch, 1.5*inch])
    complex_table.setStyle(TableStyle([
        # Header formatting
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.black),
        ('SPAN', (1, 0), (3, 0)),  # Merge Customer Information cells
        ('SPAN', (4, 0), (5, 0)),  # Merge Financial Data cells
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 1), CUSTOM_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        # Alternate row colors
        ('BACKGROUND', (0, 2), (-1, 2), colors.lightblue),
        ('BACKGROUND', (0, 4), (-1, 4), colors.lightblue),
        ('BACKGROUND', (0, 6), (-1, 6), colors.lightblue),
    ]))
    
    story.append(complex_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Add some specially formatted text
    story.append(Paragraph("4.2 Special Formatting Cases", styles['Heading2']))
    
    # Text with unusual spacing
    story.append(Paragraph("Text with unusual spacing:", styles['Normal']))
    story.append(Paragraph("Credit   Card:   " + random.choice(CREDIT_CARDS).replace(" ", "   "), styles['Normal']))
    
    # Text with mixed case
    story.append(Paragraph("Text with mixed case:", styles['Normal']))
    story.append(Paragraph("EmAiL: " + random.choice(EMAIL_ADDRESSES).upper(), styles['Normal']))
    
    # Rotated text
    story.append(Paragraph("Rotated text:", styles['Normal']))
    story.append(RotatedText("Phone: " + random.choice(PHONE_NUMBERS), 45, CUSTOM_FONT, 12, colors.blue))
    story.append(Spacer(1, 0.5*inch))  # Space for the rotated text
    
    # Split sensitive info across lines
    split_cc = random.choice(CREDIT_CARDS).replace(" ", "")
    story.append(Paragraph("Split card number:", styles['Normal']))
    story.append(Paragraph(f"{split_cc[:4]}", styles['Normal']))
    story.append(Paragraph(f"{split_cc[4:8]}", styles['Normal']))
    story.append(Paragraph(f"{split_cc[8:12]}", styles['Normal']))
    story.append(Paragraph(f"{split_cc[12:16]}", styles['Normal']))
    
    story.append(PageBreak())
    
    # Section 5: Visual elements and special formatting
    story.append(Paragraph("5. Visual Elements and Special Formatting", styles['Heading1']))
    story.append(Spacer(1, 0.1*inch))
    
    # Add some QR codes
    story.append(Paragraph("5.1 QR Codes with Embedded Information", styles['Heading2']))
    
    # Create a table with QR codes
    qr_data = [["Contact QR", "Payment QR", "Account QR"]]
    qr_row = [
        QRCodeFlowable(f"CONTACT:{random.choice(NAMES)}\nTEL:{random.choice(PHONE_NUMBERS)}\nEMAIL:{random.choice(EMAIL_ADDRESSES)}", size=1.5*inch),
        QRCodeFlowable(f"PAYMENT:{random.choice(CREDIT_CARDS)}\nEXP:{random.choice(EXPIRATION_DATES)}\nCVV:{random.choice(CVV_CODES)}", size=1.5*inch),
        QRCodeFlowable(f"ACCOUNT:{random.choice(BANK_ACCOUNTS)}", size=1.5*inch)
    ]
    qr_data.append(qr_row)
    
    qr_table = Table(qr_data, colWidths=[2*inch, 2*inch, 2*inch])
    qr_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), CUSTOM_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(qr_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Challenging headings with more complex formats
    story.append(Paragraph("5.2 Complex Document Headings", styles['Heading2']))
    for heading in CHALLENGING_HEADINGS[5:]:
        story.append(Paragraph(heading, styles['Heading_with_sensitive']))
        story.append(Paragraph("This section contains information that may be challenging to redact correctly when preserving headings.", styles['Normal']))
        story.append(Spacer(1, 0.1*inch))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Low contrast text
    story.append(Paragraph("5.3 Low Contrast Text", styles['Heading2']))
    
    low_contrast_style = ParagraphStyle(
        name='LowContrast',
        parent=styles['Normal'],
        textColor=colors.lightgrey,
        fontSize=8
    )
    
    story.append(Paragraph("The following text has very low contrast:", styles['Normal']))
    story.append(Paragraph(f"Credit Card: {random.choice(CREDIT_CARDS)}", low_contrast_style))
    story.append(Paragraph(f"Phone Number: {random.choice(PHONE_NUMBERS)}", low_contrast_style))
    story.append(Paragraph(f"Bank Account: {random.choice(BANK_ACCOUNTS)}", low_contrast_style))
    
    # Build the document
    doc.build(story)
    print(f"Generated challenging PDF: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_challenging_pdf()