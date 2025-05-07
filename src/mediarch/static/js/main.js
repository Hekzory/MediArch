// Main JavaScript file for MediArch

document.addEventListener('DOMContentLoaded', function() {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      setTimeout(() => {
        alert.style.display = 'none';
      }, 500);
    }, 5000);
  });

  // Form validation
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', function(event) {
      const requiredFields = form.querySelectorAll('[required]');
      let isValid = true;
      
      requiredFields.forEach(field => {
        if (!field.value.trim()) {
          isValid = false;
          field.classList.add('invalid');
          
          const errorMessage = document.createElement('p');
          errorMessage.classList.add('text-red-500', 'text-sm', 'mt-1');
          errorMessage.textContent = 'This field is required';
          
          // Remove any existing error messages
          const existingError = field.parentNode.querySelector('.text-red-500');
          if (existingError) {
            field.parentNode.removeChild(existingError);
          }
          
          field.parentNode.appendChild(errorMessage);
        }
      });
      
      if (!isValid) {
        event.preventDefault();
      }
    });
  });
}); 