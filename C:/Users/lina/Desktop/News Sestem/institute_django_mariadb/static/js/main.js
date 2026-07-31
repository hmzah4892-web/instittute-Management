document.addEventListener('DOMContentLoaded', function() {
    // Modal toggle logic
    var modalTriggers = document.querySelectorAll('[data-modal-target]');
    var modalCloses = document.querySelectorAll('[data-modal-close]');

    modalTriggers.forEach(function(trigger) {
        trigger.addEventListener('click', function() {
            var target = document.getElementById(trigger.getAttribute('data-modal-target'));
            if (target) target.classList.add('active');
        });
    });

    modalCloses.forEach(function(close) {
        close.addEventListener('click', function() {
            close.closest('.modal-overlay').classList.remove('active');
        });
    });
});
