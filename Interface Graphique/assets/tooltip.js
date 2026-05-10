function initTooltips() {
    var cards = document.querySelectorAll('.home-pred-card, .suivi-pred-card');
    cards.forEach(function (card) {
        if (card._tipReady) return;
        var tip = card.querySelector('.home-pred-tooltip, .suivi-pred-tooltip');
        if (!tip) return;
        card._tipReady = true;

        function place(e) {
            var rect = card.getBoundingClientRect();
            var x = e.clientX - rect.left;
            var y = e.clientY - rect.top;

            // bascule à gauche si ça dépasse l'écran à droite
            if (e.clientX + 310 > window.innerWidth)  x -= 310;
            // bascule en haut si ça dépasse l'écran en bas
            if (e.clientY + 250 > window.innerHeight) y -= 250;

            tip.style.left = x + 'px';
            tip.style.top  = y + 'px';
        }

        card.addEventListener('mouseenter', function (e) {
            place(e);
            tip.style.opacity = '1';
            card.style.zIndex = '100';
        });
        card.addEventListener('mousemove', place);
        card.addEventListener('mouseleave', function () {
            tip.style.opacity = '0';
            card.style.zIndex = '';
        });

        // Cache la tooltip quand le curseur passe sur un bouton
        var btns = card.querySelectorAll('button, a');
        btns.forEach(function (btn) {
            btn.addEventListener('mouseenter', function () {
                tip.style.opacity = '0';
            });
            btn.addEventListener('mouseleave', function () {
                tip.style.opacity = '1';
            });
        });
    });
}

document.addEventListener('DOMContentLoaded', initTooltips);
new MutationObserver(initTooltips).observe(document.body, { childList: true, subtree: true });
