// change_password.js
// Place this file in: orbit/static/js/change_password.js

document.addEventListener('DOMContentLoaded', function () {

    const otpData = document.getElementById('otp-data');
    if (!otpData) return;

    const mode = otpData.dataset.mode;

    // ── TIMER MODE (OTP verification step) ──────────────────
    if (mode === 'timer') {
        let timeLeft         = parseInt(otpData.dataset.remaining);
        const timerEl        = document.getElementById('timer');
        const timerContainer = document.getElementById('timer-container');
        const resendLabel    = document.getElementById('resend-label');
        const resendBtn      = document.getElementById('resend-btn');
        const otpForm        = document.getElementById('otp-form-container');
        const expiredMsg     = document.getElementById('otp-expired-msg');
        const otpInput       = document.getElementById('otpInput');

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

                // Update resend button to red
                resendLabel.textContent  = 'OTP expired. Get a new code:';
                resendLabel.style.color  = '#fa3434';
                resendBtn.textContent    = 'Send New OTP';
                resendBtn.className      = 'btn btn-sm btn-danger';
                return;
            }

            const m = Math.floor(timeLeft / 60);
            const s = timeLeft % 60;
            timerEl.textContent = m + ':' + String(s).padStart(2, '0');
            timeLeft--;
        }

        const timerInterval = setInterval(updateTimer, 1000);
        updateTimer();
    }

    // ── PASSWORD MODE (set new password step) ───────────────
    if (mode === 'password') {
        const pwd        = document.getElementById('pwd');
        const cpwd       = document.getElementById('cpwd');
        const strengthBar = document.getElementById('strength-bar');
        const matchMsg   = document.getElementById('match-msg');

        if (pwd) {
            pwd.addEventListener('input', function () {
                const val = this.value;
                let score = 0;
                if (val.length >= 8)          score++;
                if (/[A-Z]/.test(val))        score++;
                if (/[0-9]/.test(val))        score++;
                if (/[^A-Za-z0-9]/.test(val)) score++;

                const colors = ['#ef4444', '#f97316', '#eab308', '#22c55e'];
                strengthBar.style.width      = (score * 25) + '%';
                strengthBar.style.background = colors[score - 1] || '#eee';
            });
        }

        if (cpwd) {
            cpwd.addEventListener('input', function () {
                if (this.value === pwd.value) {
                    matchMsg.textContent = '✓ Passwords match';
                    matchMsg.style.color = '#22c55e';
                } else {
                    matchMsg.textContent = '✗ Do not match';
                    matchMsg.style.color = '#ef4444';
                }
            });
        }
    }

});