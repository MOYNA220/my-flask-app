// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
  // Flash message auto-dismiss
  const flashMessages = document.querySelectorAll('.alert');
  if (flashMessages.length > 0) {
    flashMessages.forEach(message => {
      setTimeout(() => {
        message.style.opacity = '0';
        setTimeout(() => message.remove(), 500);
      }, 5000);
    });
  }

  // Mobile menu toggle
  const menuToggle = document.querySelector('.menu-toggle');
  const navMenu = document.querySelector('.nav-menu');
  
  if (menuToggle && navMenu) {
    menuToggle.addEventListener('click', () => {
      navMenu.classList.toggle('active');
    });
  }

  // Confirm before delete actions
  const deleteButtons = document.querySelectorAll('.btn-delete');
  deleteButtons.forEach(button => {
    button.addEventListener('click', (e) => {
      if (!confirm('Are you sure you want to delete this item?')) {
        e.preventDefault();
      }
    });
  });

  // Form validation
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', (e) => {
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;
      
      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          field.classList.add('error');
          isValid = false;
        } else {
          field.classList.remove('error');
        }
      });
      
      if (!isValid) {
        e.preventDefault();
        alert('Please fill in all required fields.');
      }
    });
  });
});

// Helper function for AJAX requests
function makeRequest(method, url, data, callback) {
  const xhr = new XMLHttpRequest();
  xhr.open(method, url, true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onload = function() {
    if (xhr.status >= 200 && xhr.status < 300) {
      callback(null, JSON.parse(xhr.responseText));
    } else {
      callback(xhr.statusText, null);
    }
  };
  xhr.onerror = function() {
    callback(xhr.statusText, null);
  };
  xhr.send(JSON.stringify(data));
}