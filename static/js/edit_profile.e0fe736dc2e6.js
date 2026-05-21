// edit_profile.js
// Place in: orbit/static/js/edit_profile.js

document.addEventListener('DOMContentLoaded', function () {

    const fileInput     = document.getElementById('profile_photo_input');
    const cropImage     = document.getElementById('crop-image');
    const cropBtn       = document.getElementById('crop-btn');
    const preview       = document.getElementById('photo-preview');
    const placeholder   = document.getElementById('photo-placeholder');
    const croppedInput  = document.getElementById('cropped_photo');
    const deleteInput   = document.getElementById('delete_photo');
    const deleteBtn     = document.getElementById('delete-photo-btn');
    const photoError    = document.getElementById('photo-error');
    const photoHint     = document.getElementById('photo-hint');

    const ALLOWED_TYPES = ['image/jpeg', 'image/png'];
    const MAX_BYTES     = 5 * 1024 * 1024;
    let cropper         = null;

    function showError(msg) {
        photoError.textContent = msg;
        photoError.classList.remove('d-none');
        photoHint.classList.add('d-none');
    }

    function clearError() {
        photoError.textContent = '';
        photoError.classList.add('d-none');
        photoHint.classList.remove('d-none');
    }

    function showPreview(src) {
        // Show photo, hide placeholder, show delete button
        if (preview)     { preview.src = src; preview.style.display = 'block'; }
        if (placeholder) { placeholder.style.display = 'none'; }
        if (deleteBtn)   { deleteBtn.style.display = 'inline-block'; }
    }

    function showPlaceholder() {
        // Show icon, hide photo, hide delete button
        if (preview)     { preview.style.display = 'none'; preview.src = ''; }
        if (placeholder) { placeholder.style.display = 'flex'; }
        if (deleteBtn)   { deleteBtn.style.display = 'none'; }
    }

    // ── 1. File selected ──────────────────────────────────────
    fileInput.addEventListener('change', function () {
        const file = this.files[0];
        clearError();
        if (!file) return;

        if (!ALLOWED_TYPES.includes(file.type)) {
            showError('Only JPG and PNG images are allowed.');
            fileInput.value = '';
            return;
        }
        if (file.size > MAX_BYTES) {
            showError('Image must be smaller than 5MB.');
            fileInput.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = function (e) {
            cropImage.src = e.target.result;
            if (cropper) { cropper.destroy(); cropper = null; }
            $('#cropperModal').modal('show');
            $('#cropperModal').one('shown.bs.modal', function () {
                cropper = new Cropper(cropImage, {
                    aspectRatio:      1,
                    viewMode:         1,
                    dragMode:         'move',
                    autoCropArea:     0.85,
                    guides:           true,
                    center:           true,
                    cropBoxMovable:   true,
                    cropBoxResizable: true,
                });
            });
        };
        reader.readAsDataURL(file);
        fileInput.value = '';
    });

    // ── 2. Crop confirmed ─────────────────────────────────────
    cropBtn.addEventListener('click', function () {
        if (!cropper) return;

        const canvas  = cropper.getCroppedCanvas({ width: 300, height: 300 });
        const dataURL = canvas.toDataURL('image/png');

        // Store base64 for submission, clear delete flag
        croppedInput.value = dataURL;
        deleteInput.value  = '0';

        showPreview(dataURL);
        $('#cropperModal').modal('hide');
    });

    // ── 3. Delete photo button ────────────────────────────────
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function () {
            // Tell Django to delete the photo
            deleteInput.value  = '1';
            croppedInput.value = '';

            showPlaceholder();
        });
    }

    // ── 4. Destroy cropper on modal close ─────────────────────
    $('#cropperModal').on('hidden.bs.modal', function () {
        if (cropper) { cropper.destroy(); cropper = null; }
    });

});