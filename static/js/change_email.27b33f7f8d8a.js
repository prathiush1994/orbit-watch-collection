// change_email.js
// Place in: orbit/static/js/change_email.js

document.addEventListener('DOMContentLoaded', function () {

    const otpData = document.getElementById('otp-data');
    if (!otpData || otpData.dataset.mode !== 'timer') return;

    let timeLeft          = parseInt(otpData.dataset.remaining);
    const timerEl         = document.getElementById('timer');
    const timerContainer  = document.getElementById('timer-container');
    const resendLabel     = document.getElementById('resend-label');
    const resendBtn       = document.getElementById('resend-btn');
    const otpForm         = document.getElementById('otp-form-container');
    const expiredMsg      = document.getElementById('otp-expired-msg');
    const otpInput        = document.getElementById('otpInput');

    // Numbers only
    if (otpInput) {
        otpInput.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }

    function updateTimer() {
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            timerContainer.style.display = 'none';
            otpForm.style.display        = 'none';
            expiredMsg.style.display     = 'block';
            resendLabel.textContent      = 'OTP expired. Get a new code:';
            resendLabel.style.color      = '#fa3434';
            resendBtn.textContent        = 'Send New OTP';
            resendBtn.className          = 'btn btn-sm btn-danger';
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