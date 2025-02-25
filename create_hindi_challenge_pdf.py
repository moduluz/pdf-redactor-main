#!/usr/bin/env python3
import fitz  # PyMuPDF
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from io import BytesIO
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import random
import string

# We'll use the default Helvetica font, noting that some Hindi characters may not display correctly
hindi_font = 'Helvetica'
print("Using Helvetica font. Some Hindi characters may not display correctly.")

def create_hindi_challenge_pdf(output_path="hindi_redaction_challenge.pdf"):
    """
    Creates a PDF with challenging Hindi/Indian content for redaction tools.
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    # Create a special style for Hindi text
    hindi_style = styles["Normal"].clone('hindi')
    hindi_style.fontName = hindi_font
    
    elements = []
    
    # Title - both in English and Hindi
    title = Paragraph("<font size='16'><b>भारतीय गोपनीय जानकारी रिडैक्शन परीक्षण</b></font><br/><font size='12'>(Indian Sensitive Information Redaction Test)</font>", styles["Normal"])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Introduction
    intro = Paragraph(
        """यह दस्तावेज़ विभिन्न प्रकार की संवेदनशील जानकारी दिखाता है जिसे रिडैक्शन टूल द्वारा पहचाना जाना चाहिए।
        इसमें भारतीय फोन नंबर, आधार नंबर, पैन नंबर, ईमेल पते और बैंकिंग जानकारी शामिल है। <br/><br/>
        (This document demonstrates various types of sensitive information that should be detected by redaction tools.
        It includes Indian phone numbers, Aadhaar numbers, PAN numbers, email addresses, and banking information.)""", 
        styles["Normal"]
    )
    elements.append(intro)
    elements.append(Spacer(1, 12))
    
    # 1. Phone numbers in Indian format
    phone_section = Paragraph("<b>1. भारतीय फोन नंबर (Indian Phone Numbers)</b>", styles["Normal"])
    elements.append(phone_section)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("मानक मोबाइल (Standard Mobile): +91 98765 43210", styles["Normal"]))
    elements.append(Paragraph("मोबाइल बिना +91 के (Mobile without +91): 98765 43210", styles["Normal"]))
    elements.append(Paragraph("मोबाइल बिना स्पेस के (Mobile without spaces): 9876543210", styles["Normal"]))
    elements.append(Paragraph("लैंडलाइन (Landline): 011-23456789", styles["Normal"]))
    elements.append(Paragraph("एसटीडी कोड के साथ (With STD code): (0124) 4567890", styles["Normal"]))
    elements.append(Paragraph("विदेशी प्रारूप (International format): +91-98765-43210", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 2. Aadhaar Numbers (India's Unique ID)
    aadhaar_section = Paragraph("<b>2. आधार नंबर (Aadhaar Numbers)</b>", styles["Normal"])
    elements.append(aadhaar_section)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("मानक आधार (Standard Aadhaar): 1234 5678 9012", styles["Normal"]))
    elements.append(Paragraph("बिना स्पेस के (Without spaces): 123456789012", styles["Normal"]))
    elements.append(Paragraph("हाइफन के साथ (With hyphens): 1234-5678-9012", styles["Normal"]))
    elements.append(Paragraph("प्रारूपण के साथ (With formatting): आधार संख्या: 9876 5432 1098", styles["Normal"]))
    elements.append(Paragraph("खंडित (Split format): 8765 4321", styles["Normal"]))
    elements.append(Paragraph("0987", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 3. PAN Numbers (Permanent Account Number for taxes)
    pan_section = Paragraph("<b>3. पैन नंबर (PAN Numbers)</b>", styles["Normal"])
    elements.append(pan_section)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("मानक पैन (Standard PAN): ABCDE1234F", styles["Normal"]))
    elements.append(Paragraph("प्रारूपण के साथ (With formatting): PAN: BNZAA2318J", styles["Normal"]))
    elements.append(Paragraph("वाक्य में (In a sentence): मेरा पैन नंबर है CQBPK8349L है।", styles["Normal"]))
    elements.append(Paragraph("हाइफन के साथ (With hyphens): DTXPS-7291-Q", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 4. Email Addresses
    email_section = Paragraph("<b>4. ईमेल पते (Email Addresses)</b>", styles["Normal"])
    elements.append(email_section)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("सामान्य (Normal): राहुल.शर्मा@example.com", styles["Normal"]))
    elements.append(Paragraph("हिंदी यूजरनेम (Hindi username): प्रिया123@gmail.com", styles["Normal"]))
    elements.append(Paragraph("अंग्रेजी में (In English): sunil.kumar@company.co.in", styles["Normal"]))
    elements.append(Paragraph("भारतीय डोमेन (Indian domain): contact@निक्षय.भारत", styles["Normal"]))
    elements.append(Paragraph("मिश्रित (Mixed): amit.patel@भारत.org", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 5. Banking Information
    bank_section = Paragraph("<b>5. बैंकिंग जानकारी (Banking Information)</b>", styles["Normal"])
    elements.append(bank_section)
    elements.append(Spacer(1, 6))
    
    # Indian Account Numbers
    elements.append(Paragraph("बैंक खाता संख्या (Bank Account Number): 1234567890", styles["Normal"]))
    elements.append(Paragraph("एसबीआई खाता (SBI Account): 35241268933", styles["Normal"]))
    elements.append(Paragraph("आईसीआईसीआई खाता (ICICI Account): ICICI000047291826453", styles["Normal"]))
    
    # IFSC Codes (Indian Financial System Code)
    elements.append(Paragraph("आईएफएससी कोड (IFSC Codes):", styles["Normal"]))
    elements.append(Paragraph("SBIN0001234 - स्टेट बैंक ऑफ इंडिया", styles["Normal"]))
    elements.append(Paragraph("HDFC0004321 - एचडीएफसी बैंक", styles["Normal"]))
    elements.append(Paragraph("ICIC0006789 - आईसीआईसीआई बैंक", styles["Normal"]))
    
    # UPI IDs
    elements.append(Paragraph("यूपीआई आईडी (UPI IDs):", styles["Normal"]))
    elements.append(Paragraph("rahul@upi", styles["Normal"]))
    elements.append(Paragraph("9876543210@ybl", styles["Normal"]))
    elements.append(Paragraph("sunil.kumar@okicici", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 6. Credit Card Information
    cc_section = Paragraph("<b>6. क्रेडिट कार्ड जानकारी (Credit Card Information)</b>", styles["Normal"])
    elements.append(cc_section)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("विसा (Visa): 4111 1111 1111 1111", styles["Normal"]))
    elements.append(Paragraph("मास्टरकार्ड (Mastercard): 5500 0000 0000 0004", styles["Normal"]))
    elements.append(Paragraph("बिना स्पेस के (Without spaces): 378282246310005", styles["Normal"]))
    elements.append(Paragraph("CVV कोड: 123", styles["Normal"]))
    elements.append(Paragraph("समाप्ति तिथि (Expiry date): 10/25", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 7. Names and Addresses
    address_section = Paragraph("<b>7. नाम और पते (Names and Addresses)</b>", styles["Normal"])
    elements.append(address_section)
    elements.append(Spacer(1, 6))
    
    elements.append(Paragraph("पूरा नाम (Full name): राजेश कुमार शर्मा", styles["Normal"]))
    elements.append(Paragraph("पता (Address): फ्लैट नंबर 203, सूर्या अपार्टमेंट्स, सेक्टर 21", styles["Normal"]))
    elements.append(Paragraph("गुड़गांव, हरियाणा - 122001", styles["Normal"]))
    elements.append(Paragraph("अन्य पता (Another address): 42, महात्मा गांधी रोड, कोलकाता - 700001", styles["Normal"]))
    
    elements.append(Spacer(1, 12))
    
    # 8. Mixed data in a table format
    table_section = Paragraph("<b>8. तालिका में मिश्रित जानकारी (Mixed Information in Table)</b>", styles["Normal"])
    elements.append(table_section)
    elements.append(Spacer(1, 6))
    
    data = [
        ['नाम (Name)', 'फोन (Phone)', 'ईमेल (Email)', 'आधार (Aadhaar)'],
        ['सुनील वर्मा', '+91 98765 12345', 'sunil@example.com', '1234 5678 9012'],
        ['प्रिया शर्मा', '99887 76655', 'priya.sharma@gmail.com', '8765 4321 0987'],
        ['अमित पटेल', '011-23456789', 'amit1980@yahoo.co.in', '5432 1098 7654'],
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
    
    # 9. Contextual paragraph with mixed sensitive information
    context_section = Paragraph("<b>9. प्रासंगिक अनुच्छेद (Contextual Paragraph)</b>", styles["Normal"])
    elements.append(context_section)
    elements.append(Spacer(1, 6))
    
    paragraph = """
    श्री राजीव मेहता (rajiv.mehta@company.co.in, +91 99887 65432) ने 15 मई, 2023 को 
    अपने एचडीएफसी बैंक खाते (खाता संख्या: 50362010901547, IFSC: HDFC0000236) से 
    ₹50,000 का भुगतान किया। उनका आधार नंबर 7654 3210 9876 है और पैन नंबर ABNTY1234D है। 
    कृपया अधिक जानकारी के लिए हमारी सहायता टीम से 1800-267-1234 पर संपर्क करें।
    
    (Mr. Rajiv Mehta (rajiv.mehta@company.co.in, +91 99887 65432) made a payment of 
    ₹50,000 on May 15, 2023 from his HDFC Bank account (Account Number: 50362010901547, 
    IFSC: HDFC0000236). His Aadhaar number is 7654 3210 9876 and PAN number is ABNTY1234D. 
    Please contact our support team at 1800-267-1234 for more information.)
    """
    
    elements.append(Paragraph(paragraph, styles["Normal"]))
    
    # Build the PDF
    doc.build(elements)
    
    # Add an image with embedded Hindi sensitive information
    modify_pdf_with_image(output_path)
    
    print(f"Created Hindi challenging PDF: {output_path}")

def modify_pdf_with_image(pdf_path):
    """
    Modify the PDF to add an image with embedded sensitive information in Hindi
    """
    # Create a temporary PDF with an image containing text
    img_pdf = BytesIO()
    c = canvas.Canvas(img_pdf, pagesize=letter)
    
    # Draw some sensitive information as text in the image
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "आधार कार्ड संख्या (Aadhaar number): 8765 1234 5678")
    c.drawString(100, 680, "ईमेल (Email): विकास.शर्मा@example.com")
    c.drawString(100, 660, "मोबाइल (Mobile): +91-88776-55443")
    c.drawString(100, 640, "क्रेडिट कार्ड (Credit card): 4012 8888 8888 1881")
    
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
    create_hindi_challenge_pdf() 