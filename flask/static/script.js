// PDF Redactor - Interactive UI Script

document.addEventListener('DOMContentLoaded', function() {
    // File upload handling
    const fileInput = document.getElementById('pdf_file');
    const fileLabel = document.querySelector('.file-label');
    const fileUpload = document.querySelector('.file-upload');
    
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                fileLabel.textContent = fileName;
                fileUpload.classList.add('has-file');
            } else {
                fileLabel.textContent = 'Choose PDF file';
                fileUpload.classList.remove('has-file');
            }
        });
    }
    
    // Advanced options toggle
    const advancedToggle = document.querySelector('.advanced-toggle');
    const advancedContent = document.querySelector('.advanced-content');
    
    if (advancedToggle && advancedContent) {
        advancedToggle.addEventListener('click', function() {
            advancedContent.classList.toggle('active');
            advancedToggle.classList.toggle('active');
        });
    }
    
    // Color preview update
    const colorSelect = document.getElementById('color');
    const colorPreview = document.querySelector('.color-preview');
    
    if (colorSelect && colorPreview) {
        colorSelect.addEventListener('change', function() {
            colorPreview.style.backgroundColor = this.value;
        });
    }
    
    // Form submission loading indicator
    const form = document.getElementById('redaction-form');
    const loadingIndicator = document.querySelector('.loading');
    
    if (form && loadingIndicator) {
        form.addEventListener('submit', function() {
            // Validate form
            const redactionOptions = [
                'redact_phone', 'redact_email', 'redact_iban', 'redact_cc',
                'redact_cvv', 'redact_cc_expiration', 'redact_bic',
                'redact_aadhaar', 'redact_pan'
            ];
            
            let optionSelected = false;
            for (const option of redactionOptions) {
                if (document.getElementById(option).checked) {
                    optionSelected = true;
                    break;
                }
            }
            
            if (!optionSelected) {
                alert('Please select at least one type of information to redact');
                return false;
            }
            
            // Show loading indicator
            loadingIndicator.classList.add('active');
            
            // Allow form submission
            return true;
        });
    }
    
    // Flash message auto-dismiss
    const flashMessages = document.querySelectorAll('.flash');
    if (flashMessages.length > 0) {
        setTimeout(function() {
            flashMessages.forEach(message => {
                message.style.opacity = '0';
                setTimeout(() => {
                    message.style.display = 'none';
                }, 500);
            });
        }, 5000);
    }
    
    // Tooltips for mobile - convert to click instead of hover
    if (window.innerWidth <= 768) {
        const tooltipLabels = document.querySelectorAll('label[data-tooltip]');
        tooltipLabels.forEach(label => {
            label.addEventListener('click', function(e) {
                // Don't trigger if clicking the checkbox
                if (e.target.tagName !== 'INPUT') {
                    e.preventDefault();
                    // Create tooltip element
                    const tooltip = document.createElement('div');
                    tooltip.className = 'mobile-tooltip';
                    tooltip.textContent = this.getAttribute('data-tooltip');
                    tooltip.style.position = 'fixed';
                    tooltip.style.top = '50%';
                    tooltip.style.left = '50%';
                    tooltip.style.transform = 'translate(-50%, -50%)';
                    tooltip.style.backgroundColor = 'rgba(0,0,0,0.8)';
                    tooltip.style.color = 'white';
                    tooltip.style.padding = '1rem';
                    tooltip.style.borderRadius = '8px';
                    tooltip.style.maxWidth = '80%';
                    tooltip.style.zIndex = '1000';
                    tooltip.style.textAlign = 'center';
                    
                    document.body.appendChild(tooltip);
                    
                    // Remove after tap elsewhere
                    setTimeout(() => {
                        document.addEventListener('click', function removeTooltip() {
                            document.body.removeChild(tooltip);
                            document.removeEventListener('click', removeTooltip);
                        });
                    }, 100);
                }
            });
        });
    }
    
    // Enhance checkbox styling
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const parentOption = this.closest('.option-item');
            if (this.checked) {
                parentOption.style.backgroundColor = 'rgba(67, 97, 238, 0.1)';
                parentOption.style.borderLeft = '3px solid var(--primary-color)';
            } else {
                parentOption.style.backgroundColor = '';
                parentOption.style.borderLeft = '';
            }
        });
        
        // Initialize state
        if (checkbox.checked) {
            const parentOption = checkbox.closest('.option-item');
            parentOption.style.backgroundColor = 'rgba(67, 97, 238, 0.1)';
            parentOption.style.borderLeft = '3px solid var(--primary-color)';
        }
    });
});
