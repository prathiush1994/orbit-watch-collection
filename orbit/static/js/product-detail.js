// product-detail.js
// Thumbnails are rendered directly in HTML by Django template.
// This file handles: click to swap main image, arrow scroll.

document.addEventListener('DOMContentLoaded', function () {

    var thumbList  = document.getElementById('thumbList');
    var scrollBox  = document.getElementById('thumbScrollBox');
    var btnUp      = document.getElementById('thumbUp');
    var btnDown    = document.getElementById('thumbDown');
    var mainImage  = document.getElementById('mainImage');

    if (!thumbList || !mainImage) return;

    var STEP          = 84;   // 76px thumb + 8px gap
    var currentOffset = 0;


    // ── Attach click handlers to every thumbnail ───────────────────────
    // Thumbnails already exist in DOM — just wire up the clicks.
    var thumbItems = thumbList.querySelectorAll('.thumb-item');

    thumbItems.forEach(function (thumb) {
        thumb.addEventListener('click', function () {
            var src = thumb.dataset.src;
            var alt = thumb.dataset.alt;

            // Remove active from all, set on clicked
            thumbItems.forEach(function (t) { t.classList.remove('active'); });
            thumb.classList.add('active');

            // Fade main image to new src
            mainImage.style.transition = 'opacity 0.22s ease';
            mainImage.style.opacity    = '0';
            setTimeout(function () {
                mainImage.src           = src;
                mainImage.alt           = alt;
                mainImage.style.opacity = '1';
            }, 220);
        });
    });


    // ── Arrow scroll ───────────────────────────────────────────────────
    function getMaxOffset() {
        var totalHeight = thumbItems.length * STEP;
        var boxHeight   = scrollBox.clientHeight || 400;
        return Math.max(0, totalHeight - boxHeight);
    }

    function applyOffset() {
        thumbList.style.transition = 'transform 0.3s ease';
        thumbList.style.transform  = 'translateY(-' + currentOffset + 'px)';
        updateArrows();
    }

    function updateArrows() {
        var max = getMaxOffset();
        if (max <= 0) {
            // Everything fits — hide both arrows
            btnUp.style.visibility   = 'hidden';
            btnDown.style.visibility = 'hidden';
        } else {
            btnUp.style.visibility   = currentOffset > 0   ? 'visible' : 'hidden';
            btnDown.style.visibility = currentOffset < max ? 'visible' : 'hidden';
        }
    }

    if (btnUp) {
        btnUp.addEventListener('click', function () {
            currentOffset = Math.max(0, currentOffset - STEP);
            applyOffset();
        });
    }

    if (btnDown) {
        btnDown.addEventListener('click', function () {
            currentOffset = Math.min(getMaxOffset(), currentOffset + STEP);
            applyOffset();
        });
    }


    // ── Init ───────────────────────────────────────────────────────────
    requestAnimationFrame(function () {
        updateArrows();
    });

});