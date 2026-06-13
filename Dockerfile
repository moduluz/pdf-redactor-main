FROM python:3.11-slim

# Install system dependencies, specifically Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spacy language model
RUN python -m spacy download en_core_web_sm

# Copy the rest of the application
COPY . .

# Expose the port Waitress will run on
EXPOSE 8080

# Command to run the application
CMD ["python", "wsgi.py"]
