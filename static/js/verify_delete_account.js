// verify_delete_account.js
// Place this file in: orbit/static/js/verify_delete_account.js

document.addEventListener('DOMContentLoaded', function () {

    const otpData = document.getElementById('otp-data');
    if (!otpData) return;

    const mode = otpData.dataset.mode;
    if (mode !== 'timer') return;

    let timeLeft          = parseInt(otpData.dataset.remaining);
    const timerEl         = document.getElementById('timer');
    const timerContainer  = document.getElementById('timer-container');
    const resendLabel     = document.getElementById('resend-label');
    const resendBtn       = document.getElementById('resend-btn');
    const otpForm         = document.getElementById('otp-form-container');
    const expiredMsg      = document.getElementById('otp-expired-msg');
    const otpInput        = document.getElementById('otpInput');

    // Only allow numbers in OTP input
    if (otpInput) {
        otpInput.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }

    function updateTimer() {
        if (timeLeft <= 0) {
            clearInterval(timerInterval);

            // Hide timer and OTP form
            timerContainer.style.display = 'none';
            otpForm.style.display        = 'none';

            // Show expired message
            expiredMsg.style.display = 'block';

            // Update resend button to make it obvious
            resendLabel.textContent  = 'OTP expired. Get a new code:';
            resendLabel.style.color  = '#fa3434';
            resendBtn.textContent    = 'Send New OTP';
            resendBtn.className      = 'btn btn-danger mt-2';
            return;
        }

        const m = Math.floor(timeLeft / 60);
        const s = timeLeft % 60;
        timerEl.textContent = m + ':' + String(s).padStart(2, '0');
        timeLeft--;
    }

    const timerInterval = setInterval(updateTimer, 1000);
    updateTimer();

});