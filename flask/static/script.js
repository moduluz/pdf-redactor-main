document.addEventListener('DOMContentLoaded', function() {
    // Toggle advanced options
    const advancedToggle = document.querySelector('.advanced-toggle');
    const advancedContent = document.querySelector('.advanced-content');
    
    if (advancedToggle && advancedContent) {
        advancedToggle.addEventListener('click', function() {
            this.classList.toggle('active');
            advancedContent.classList.toggle('active');
        });
    }
    
    // Form submission and loading indicator
    const redactionForm = document.getElementById('redaction-form');
    const loadingIndicator = document.querySelector('.loading');
    
    if (redactionForm && loadingIndicator) {
        redactionForm.addEventListener('submit', function() {
            // Validate that at least one redaction option is selected
            const checkboxes = document.querySelectorAll('input[type="checkbox"][name^="redact_"]');
            let atLeastOneChecked = false;
            
            checkboxes.forEach(function(checkbox) {
                if (checkbox.checked) {
                    atLeastOneChecked = true;
                }
            });
            
            // Validate file input
            const fileInput = document.getElementById('pdf_file');
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                alert('Please select a PDF file to redact.');
                return false;
            }
            
            // Check file type
            const fileName = fileInput.files[0].name;
            if (!fileName.toLowerCase().endsWith('.pdf')) {
                alert('Only PDF files are allowed.');
                return false;
            }
            
            if (!atLeastOneChecked) {
                alert('Please select at least one redaction option.');
                return false;
            }
            
            // Show loading indicator
            loadingIndicator.classList.add('active');
            
            // Submit form
            return true;
        });
    }
    
    // Auto-dismiss flash messages
    const flashMessages = document.querySelectorAll('.flash');
    if (flashMessages.length > 0) {
        setTimeout(function() {
            flashMessages.forEach(function(message) {
                message.style.opacity = '0';
                message.style.transition = 'opacity 0.5s ease';
                
                setTimeout(function() {
                    message.style.display = 'none';
                }, 500);
            });
        }, 5000);
    }
    
    // Color picker for redaction color
    const colorSelector = document.getElementById('color');
    if (colorSelector) {
        colorSelector.addEventListener('change', function() {
            const preview = document.querySelector('.color-preview');
            if (preview) {
                preview.style.backgroundColor = this.value;
            }
        });
    }
    
    // File input label update
    const fileInput = document.getElementById('pdf_file');
    const fileLabel = document.querySelector('.file-label');
    
    if (fileInput && fileLabel) {
        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                fileLabel.textContent = this.files[0].name;
            } else {
                fileLabel.textContent = 'Choose PDF file';
            }
        });
    }
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(function(tooltip) {
        tooltip.style.position = 'relative';
        tooltip.style.cursor = 'help';
        
        tooltip.addEventListener('mouseenter', function() {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltipElement = document.createElement('div');
            tooltipElement.className = 'tooltip';
            tooltipElement.textContent = tooltipText;
            tooltipElement.style.position = 'absolute';
            tooltipElement.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
            tooltipElement.style.color = 'white';
            tooltipElement.style.padding = '5px 10px';
            tooltipElement.style.borderRadius = '4px';
            tooltipElement.style.fontSize = '14px';
            tooltipElement.style.bottom = '100%';
            tooltipElement.style.left = '50%';
            tooltipElement.style.transform = 'translateX(-50%)';
            tooltipElement.style.marginBottom = '5px';
            tooltipElement.style.whiteSpace = 'nowrap';
            tooltipElement.style.zIndex = '10';
            
            this.appendChild(tooltipElement);
        });
        
        tooltip.addEventListener('mouseleave', function() {
            const tooltipElement = this.querySelector('.tooltip');
            if (tooltipElement) {
                tooltipElement.remove();
            }
        });
    });
}); 