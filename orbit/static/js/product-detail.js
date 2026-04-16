document.addEventListener('DOMContentLoaded', function () {

    var thumbList  = document.getElementById('thumbList');
    var scrollBox  = document.getElementById('thumbScrollBox');
    var btnUp      = document.getElementById('thumbUp');
    var btnDown    = document.getElementById('thumbDown');
    var mainImage  = document.getElementById('mainImage');

    if (!thumbList || !mainImage) return;

    var STEP          = 84;
    var currentOffset = 0;

    var thumbItems = thumbList.querySelectorAll('.thumb-item');

    thumbItems.forEach(function (thumb) {
        thumb.addEventListener('click', function () {
            var src = thumb.dataset.src;
            var alt = thumb.dataset.alt;

            thumbItems.forEach(function (t) { t.classList.remove('active'); });
            thumb.classList.add('active');

            mainImage.style.opacity = '0';
            setTimeout(function () {
                mainImage.src = src;
                mainImage.alt = alt;
                mainImage.style.opacity = '1';
            }, 220);
        });
    });

    function getMaxOffset() {
        var totalHeight = thumbItems.length * STEP;
        var boxHeight   = scrollBox.clientHeight || 400;
        return Math.max(0, totalHeight - boxHeight);
    }

    function applyOffset() {
        thumbList.style.transform  = 'translateY(-' + currentOffset + 'px)';
        updateArrows();
    }

    function updateArrows() {
        var max = getMaxOffset();
        btnUp.style.visibility   = currentOffset > 0   ? 'visible' : 'hidden';
        btnDown.style.visibility = currentOffset < max ? 'visible' : 'hidden';
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

    var container = document.querySelector(".main-image-area");

    if (container && mainImage) {

        container.addEventListener("mousemove", function(e) {
            const rect = container.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width) * 100;
            const y = ((e.clientY - rect.top) / rect.height) * 100;

            mainImage.style.transformOrigin = `${x}% ${y}%`;
            mainImage.style.transform = "scale(2)";
        });

        container.addEventListener("mouseleave", function() {
            mainImage.style.transform = "scale(1)";
        });

    }
});