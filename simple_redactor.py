#!/usr/bin/env python3

import fitz
import re
import os
from PIL import Image
import pytesseract
import io

def redact_pdf(input_path, output_path):
    print(f"Processing {input_path}")
    
    # Open the PDF
    pdf = fitz.open(input_path)
    print(f"PDF has {len(pdf)} pages")
    
    # Process each page
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        print(f"\nProcessing page {page_num + 1}")
        
        # Get all images on the page
        images = page.get_images(full=True)
        print(f"Found {len(images)} images on page")
        
        for img_index, img in enumerate(images):
            try:
                xref = img[0]
                print(f"Processing image {img_index + 1} (xref: {xref})")
                
                # Extract image
                base_image = pdf.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Convert to PIL Image
                pil_image = Image.open(io.BytesIO(image_bytes))
                print(f"Image size: {pil_image.width}x{pil_image.height}")
                
                # Perform OCR
                text = pytesseract.image_to_string(pil_image)
                print(f"OCR text: {text}")
                
                # Check for sensitive information
                has_sensitive = False
                
                # Check for phone numbers
                phone_pattern = r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
                if re.search(phone_pattern, text):
                    print("Found phone number")
                    has_sensitive = True
                
                # Check for email addresses
                email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                if re.search(email_pattern, text):
                    print("Found email address")
                    has_sensitive = True
                
                if has_sensitive:
                    print("Attempting to redact image...")
                    
                    # Try to get image location
                    rect = None
                    
                    # Method 1: Try get_image_bbox
                    try:
                        rect = page.get_image_bbox(xref)
                        print(f"Got rect from get_image_bbox: {rect}")
                    except Exception as e:
                        print(f"get_image_bbox failed: {e}")
                    
                    # Method 2: Try get_image_rects
                    if not rect:
                        try:
                            rects = page.get_image_rects()
                            if rects and img_index < len(rects):
                                rect = rects[img_index]
                                print(f"Got rect from get_image_rects: {rect}")
                        except Exception as e:
                            print(f"get_image_rects failed: {e}")
                    
                    # Method 3: Try to get rect from image info
                    if not rect and len(img) > 7:
                        try:
                            matrix = fitz.Matrix(img[6])
                            rect = matrix.rect
                            print(f"Got rect from image matrix: {rect}")
                        except Exception as e:
                            print(f"Matrix rect failed: {e}")
                    
                    # If we found a rectangle, apply redaction
                    if rect:
                        try:
                            # Create redaction annotation
                            annot = page.add_redact_annot(rect)
                            
                            # Set redaction appearance
                            annot.set_colors(stroke=(0, 0, 0), fill=(0, 0, 0))
                            annot.update()
                            
                            # Apply the redaction
                            page.apply_redactions()
                            print("Successfully applied redaction")
                        except Exception as e:
                            print(f"Failed to apply redaction: {e}")
                    else:
                        print("Could not determine image location")
            
            except Exception as e:
                print(f"Error processing image: {e}")
    
    # Save the redacted PDF
    print(f"\nSaving redacted PDF to {output_path}")
    pdf.save(output_path)
    pdf.close()
    print("Done!")

if __name__ == "__main__":
    input_file = "941w-UHRf_NCyJ7c.pdf"
    output_file = "941w-UHRf_NCyJ7c_redacted.pdf"
    redact_pdf(input_file, output_file) 