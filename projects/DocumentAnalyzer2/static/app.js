// Contract Analysis Tool JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const progressContainer = document.getElementById('progressContainer');
    const submitBtn = document.getElementById('submitBtn');
    const submitText = document.getElementById('submitText');
    const fileInput = document.getElementById('file');
    const contractTextInput = document.getElementById('contractText');
    
    const fileMethodRadio = document.getElementById('fileMethod');
    const textMethodRadio = document.getElementById('textMethod');
    const fileSection = document.getElementById('fileSection');
    const textSection = document.getElementById('textSection');

    // Toggle between file upload and text paste
    function toggleInputMethod() {
        if (fileMethodRadio && fileMethodRadio.checked) {
            fileSection.style.display = 'block';
            textSection.style.display = 'none';
            submitText.textContent = 'Upload and Analyze';
            fileInput.setAttribute('required', '');
            contractTextInput.removeAttribute('required');
        } else if (textMethodRadio && textMethodRadio.checked) {
            fileSection.style.display = 'none';
            textSection.style.display = 'block';
            submitText.textContent = 'Analyze Text';
            contractTextInput.setAttribute('required', '');
            fileInput.removeAttribute('required');
        }
    }

    if (fileMethodRadio) fileMethodRadio.addEventListener('change', toggleInputMethod);
    if (textMethodRadio) textMethodRadio.addEventListener('change', toggleInputMethod);

    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            if (fileMethodRadio && fileMethodRadio.checked) {
                const file = fileInput.files[0];
                if (!file) {
                    e.preventDefault();
                    showAlert('Please select a file to upload.', 'error');
                    return;
                }

                // Check file size (16MB limit)
                const maxSize = 16 * 1024 * 1024; // 16MB in bytes
                if (file.size > maxSize) {
                    e.preventDefault();
                    showAlert('File size exceeds 16MB limit. Please choose a smaller file.', 'error');
                    return;
                }
            } else if (textMethodRadio && textMethodRadio.checked) {
                const text = contractTextInput.value.trim();
                if (!text) {
                    e.preventDefault();
                    showAlert('Please paste contract text to analyze.', 'error');
                    return;
                }
                if (text.length < 50) {
                    e.preventDefault();
                    showAlert('Please paste more contract text for analysis (minimum 50 characters)', 'error');
                    return;
                }
            }

            // Show progress indicator
            showProgress();
        });
    }

    // File input change handler for validation feedback
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                validateFile(file);
            }
            resetFormState();
        });
    }

    // Text input change handler
    if (contractTextInput) {
        contractTextInput.addEventListener('input', function() {
            resetFormState();
        });
    }

    function resetFormState() {
        if (submitBtn && submitBtn.disabled) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = submitText ? submitText.textContent : 'Analyze';
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
        }
    }

    function validateFile(file) {
        const allowedTypes = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'text/markdown',
            'image/png',
            'image/jpeg',
            'image/jpg',
            'image/tiff',
            'image/bmp',
            'image/webp'
        ];

        const allowedExtensions = ['pdf', 'docx', 'txt', 'md', 'png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp', 'webp'];
        const fileExtension = file.name.split('.').pop().toLowerCase();

        if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
            showAlert('File type not supported. Please upload a PDF, DOCX, TXT, MD, or image file.', 'error');
            fileInput.value = '';
            return false;
        }

        const maxSize = 16 * 1024 * 1024; // 16MB
        if (file.size > maxSize) {
            showAlert('File size exceeds 16MB limit. Please choose a smaller file.', 'error');
            fileInput.value = '';
            return false;
        }

        return true;
    }

    function showProgress() {
        if (progressContainer && submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Processing...';
            progressContainer.style.display = 'block';
            
            // Scroll to progress indicator
            progressContainer.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
        }
    }

    function showAlert(message, type) {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insert at the top of the main container
        const mainContainer = document.querySelector('main');
        if (mainContainer) {
            mainContainer.insertBefore(alertDiv, mainContainer.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (alertDiv && alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }

    // Handle drag and drop for file upload
    if (fileInput && fileSection) {
        const dropZone = fileSection;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            dropZone.classList.add('bg-secondary');
        }

        function unhighlight(e) {
            dropZone.classList.remove('bg-secondary');
        }

        dropZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;

            if (files.length > 0) {
                fileInput.files = files;
                validateFile(files[0]);
            }
        }
    }

    // Initialize the correct input method on page load
    toggleInputMethod();

    // Auto-dismiss alerts after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            if (alert.querySelector('.btn-close')) {
                alert.remove();
            }
        });
    }, 5000);
});

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy to clipboard:', err);
    });
}