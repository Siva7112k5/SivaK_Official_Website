// Auto-fill plan from pricing buttons
document.querySelectorAll('.choose-plan').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const plan = btn.getAttribute('data-plan');
        if (plan) {
            const planSelect = document.getElementById('plan');
            if (planSelect) {
                planSelect.value = plan;
                // Scroll to request section
                document.getElementById('request').scrollIntoView({ behavior: 'smooth' });
            }
        }
    });
});

// Form submission
const form = document.getElementById('projectForm');
const messageDiv = document.getElementById('formMessage');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        project_type: document.getElementById('project_type').value,
        plan: document.getElementById('plan').value,
        description: document.getElementById('description').value,
        transaction_id: document.getElementById('transaction_id').value
    };
    
    // Basic validation
    if (!formData.transaction_id) {
        showMessage('Please enter the payment transaction ID after making payment.', 'error');
        return;
    }
    
    // Disable button
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.innerText = 'Submitting...';
    
    try {
        const response = await fetch('/submit-request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        const result = await response.json();
        if (result.success) {
            showMessage('Request submitted! Admin will verify your payment and contact you soon.', 'success');
            form.reset();
        } else {
            showMessage('Error: ' + result.message, 'error');
        }
    } catch (err) {
        showMessage('Network error. Please try again.', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Submit Request & Pay';
    }
});

function showMessage(msg, type) {
    messageDiv.innerText = msg;
    messageDiv.classList.remove('hidden', 'text-green-400', 'text-red-400');
    messageDiv.classList.add(type === 'success' ? 'text-green-400' : 'text-red-400');
    setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}