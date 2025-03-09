import cv2
import numpy as np
from PIL import Image
import io
import fitz

def test_face_detection(pdf_path):
    print(f"Testing face detection on: {pdf_path}")
    
    # Load the face detection cascade
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        print("Error: Could not load face cascade classifier")
        return
    
    # Open the PDF
    pdf = fitz.open(pdf_path)
    print(f"PDF has {len(pdf)} pages")
    
    for page_num in range(len(pdf)):
        page = pdf[page_num]
        print(f"\nProcessing page {page_num + 1}")
        
        # Get images from the page
        images = page.get_images(full=True)
        print(f"Found {len(images)} images on page")
        
        for img_index, img in enumerate(images):
            try:
                # Get the image
                xref = img[0]
                base_image = pdf.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Convert to PIL Image
                pil_image = Image.open(io.BytesIO(image_bytes))
                print(f"Image {img_index + 1} size: {pil_image.size}")
                
                # Save the original image for inspection
                pil_image.save(f"test_image_{page_num + 1}_{img_index + 1}.png")
                
                # Convert to OpenCV format
                cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                
                # Convert to grayscale
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                
                # Detect faces with different scale factors
                scale_factors = [1.1, 1.2, 1.3]
                min_neighbors_values = [3, 4, 5]
                
                for scale_factor in scale_factors:
                    for min_neighbors in min_neighbors_values:
                        faces = face_cascade.detectMultiScale(
                            gray,
                            scaleFactor=scale_factor,
                            minNeighbors=min_neighbors,
                            minSize=(20, 20)
                        )
                        
                        if len(faces) > 0:
                            print(f"Found {len(faces)} faces with scale={scale_factor}, minNeighbors={min_neighbors}")
                            
                            # Draw rectangles around faces
                            for (x, y, w, h) in faces:
                                cv2.rectangle(cv_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                            
                            # Save the image with detected faces
                            output_filename = f"detected_faces_{page_num + 1}_{img_index + 1}_s{scale_factor}_n{min_neighbors}.png"
                            cv2.imwrite(output_filename, cv_image)
                            print(f"Saved detected faces to: {output_filename}")
                
                # Try to get image location in PDF
                print("\nTesting image location methods:")
                
                # Method 1: get_image_bbox
                try:
                    rect = page.get_image_bbox(xref)
                    print(f"get_image_bbox successful: {rect}")
                except Exception as e:
                    print(f"get_image_bbox failed: {e}")
                
                # Method 2: get_image_rects
                try:
                    rects = page.get_image_rects()
                    if rects and img_index < len(rects):
                        rect = rects[img_index]
                        print(f"get_image_rects successful: {rect}")
                    else:
                        print("get_image_rects: No rectangle found")
                except Exception as e:
                    print(f"get_image_rects failed: {e}")
                
                # Method 3: image matrix
                if len(img) > 7:
                    try:
                        matrix = fitz.Matrix(img[6])
                        rect = matrix.rect
                        print(f"Matrix rect successful: {rect}")
                    except Exception as e:
                        print(f"Matrix rect failed: {e}")
                
            except Exception as e:
                print(f"Error processing image {img_index + 1}: {e}")
    
    pdf.close()

if __name__ == "__main__":
    test_face_detection("941w-UHRf_NCyJ7c.pdf") 