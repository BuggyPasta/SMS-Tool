// Main application JavaScript 

// Template selection handler
document.addEventListener('DOMContentLoaded', function() {
    const templateSelect = document.getElementById('template');
    const messageTextarea = document.getElementById('message');

    if (templateSelect && messageTextarea) {
        templateSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption.value) {
                // In a real application, you would fetch the template content from the server
                // For now, we'll just set a placeholder
                messageTextarea.value = `Template ${selectedOption.text} selected`;
            } else {
                messageTextarea.value = '';
            }
        });
    }

    // Phone number validation
    const phoneInput = document.getElementById('phone');
    if (phoneInput) {
        phoneInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value.length > 11) {
                this.value = this.value.slice(0, 11);
            }
        });
    }

    // Theme toggle functionality
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');
            const isDark = document.body.classList.contains('dark-theme');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        });

        // Check for saved theme preference
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
        }
    }

    // Flash message auto-hide
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.classList.add('fade-out');
            setTimeout(function() {
                message.remove();
            }, 300);
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(function(field) {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('error');
                } else {
                    field.classList.remove('error');
                }
            });

            if (!isValid) {
                e.preventDefault();
                alert('Please fill in all required fields');
            }
        });
    });

    // Status badge colors
    const statusBadges = document.querySelectorAll('.status-badge');
    statusBadges.forEach(function(badge) {
        const status = badge.textContent.toLowerCase();
        badge.classList.add(`status-${status}`);
    });
}); 

// Enhanced character counter with message count
function updateCharacterCount() {
    const messageInput = document.getElementById('message');
    const counter = document.getElementById('char-counter');
    if (!messageInput || !counter) return;

    const text = messageInput.value;
    const length = text.length;
    const messageCount = Math.ceil(length / 160);
    const maxChars = messageCount * 160;

    counter.textContent = `Character counter: ${length}/${maxChars}. This SMS will be sent as ${messageCount} message${messageCount > 1 ? 's' : ''}.`;
}

// Template preview functionality
function setupTemplatePreview() {
    const templateSelect = document.getElementById('template-select');
    const previewDiv = document.createElement('div');
    previewDiv.id = 'template-preview';
    previewDiv.className = 'template-preview';
    document.body.appendChild(previewDiv);

    templateSelect.addEventListener('mouseover', (e) => {
        const option = e.target;
        if (option.tagName === 'OPTION') {
            const rect = option.getBoundingClientRect();
            previewDiv.textContent = option.getAttribute('data-content');
            previewDiv.style.top = `${rect.bottom + window.scrollY}px`;
            previewDiv.style.left = `${rect.left}px`;
            previewDiv.style.display = 'block';
        }
    });

    templateSelect.addEventListener('mouseout', (e) => {
        if (e.target.tagName === 'OPTION') {
            previewDiv.style.display = 'none';
        }
    });

    templateSelect.addEventListener('change', () => {
        previewDiv.style.display = 'none';
    });
}

// Enhanced input sanitization
function sanitizeMessage(message) {
    // Remove or replace potentially problematic characters
    let sanitized = message
        .replace(/[\u0000-\u001F\u007F-\u009F]/g, '') // Remove control characters
        .replace(/[^\x20-\x7E\u00A0-\u00FF\u0100-\u017F\u0180-\u024F\u1E00-\u1EFF]/g, ''); // Keep only printable characters and common Unicode ranges

    // Check for repeated characters
    const repeatedChars = sanitized.match(/(.)\1{3,}/g);
    if (repeatedChars) {
        throw new Error('Message contains too many repeated characters');
    }

    return sanitized;
}

// Enhanced phone number validation
function validatePhoneNumber(number) {
    // Remove all non-digit characters
    const cleanNumber = number.replace(/\D/g, '');
    
    // Check if it starts with 07 and is exactly 11 digits
    if (!/^07\d{9}$/.test(cleanNumber)) {
        throw new Error('Invalid phone number format. Must start with 07 and be 11 digits long.');
    }
    
    return cleanNumber;
}

// Dark mode toggle with localStorage persistence
function setupDarkModeToggle() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const body = document.body;
    
    // Check localStorage for saved preference
    const savedMode = localStorage.getItem('darkMode');
    if (savedMode === 'true') {
        body.classList.add('dark-mode');
        darkModeToggle.src = '/static/icons/mode_light.svg';
    }
    
    darkModeToggle.addEventListener('click', () => {
        body.classList.toggle('dark-mode');
        const isDarkMode = body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDarkMode);
        darkModeToggle.src = isDarkMode ? '/static/icons/mode_light.svg' : '/static/icons/mode_dark.svg';
    });
}

// Initialize all components
document.addEventListener('DOMContentLoaded', () => {
    setupTemplatePreview();
    setupCharacterCounter();
    setupDarkModeToggle();
});

function updateMessageFromTemplate(templateTitle) {
    const templateSelect = document.getElementById('template');
    const selectedOption = templateSelect.options[templateSelect.selectedIndex];
    const messageTextarea = document.getElementById('message');
    
    if (templateTitle && selectedOption.dataset.content) {
        messageTextarea.value = selectedOption.dataset.content;
        updateCharacterCount();
    } else {
        messageTextarea.value = '';
        updateCharacterCount();
    }
}

// Message preview functionality
function showMessagePreview(message) {
    const modal = document.getElementById('message-preview-modal');
    const content = document.getElementById('message-preview-content');
    const closeBtn = modal.querySelector('.close');
    
    // Set message content
    content.textContent = message;
    
    // Show modal
    modal.style.display = 'block';
    
    // Close button handler
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    }
    
    // Close on click outside
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    }
    
    // Close on escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            modal.style.display = 'none';
        }
    });
} 