document.addEventListener('DOMContentLoaded', function() {
    // Universal functions for login/register modals
    function openModal(modalId) {
        const modalOverlay = document.getElementById(modalId);
        if (modalOverlay) {
            modalOverlay.classList.add('visible');
            document.body.style.overflow = 'hidden'; // Prevent scrolling background
        }
    }

    function closeModal(modalId) {
        const modalOverlay = document.getElementById(modalId);
        if (modalOverlay) {
            modalOverlay.classList.remove('visible');
            document.body.style.overflow = ''; // Restore scrolling
        }
    }

    // Attach event listeners for login/register buttons if they exist
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn) {
        loginBtn.addEventListener('click', function() {
            openModal('loginRegisterModalOverlay');
            document.getElementById('loginForm').style.display = 'block';
            document.getElementById('registerForm').style.display = 'none';
        });
    }

    const registerBtn = document.getElementById('registerBtn');
    if (registerBtn) {
        registerBtn.addEventListener('click', function() {
            openModal('loginRegisterModalOverlay');
            document.getElementById('registerForm').style.display = 'block';
            document.getElementById('loginForm').style.display = 'none';
        });
    }

    const modalCloseBtn = document.querySelector('#loginRegisterModalOverlay .modal-close');
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', function() {
            closeModal('loginRegisterModalOverlay');
        });
    }

    // Handle showing specific modal based on URL query parameters (e.g., after failed login/register)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('showLoginModal') === 'true') {
        openModal('loginRegisterModalOverlay');
        document.getElementById('loginForm').style.display = 'block';
        document.getElementById('registerForm').style.display = 'none';
    } else if (urlParams.get('showRegisterModal') === 'true') {
        openModal('loginRegisterModalOverlay');
        document.getElementById('registerForm').style.display = 'block';
        document.getElementById('loginForm').style.display = 'none';
    }

    // Handle switching between login and register forms within the modal
    const showRegisterLink = document.getElementById('showRegisterLink');
    const showLoginLink = document.getElementById('showLoginLink');

    if (showRegisterLink) {
        showRegisterLink.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('loginForm').style.display = 'none';
            document.getElementById('registerForm').style.display = 'block';
        });
    }

    if (showLoginLink) {
        showLoginLink.addEventListener('click', function(e) {
            e.preventDefault();
            document.getElementById('registerForm').style.display = 'none';
            document.getElementById('loginForm').style.display = 'block';
        });
    }
});