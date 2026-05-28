/* ================================================================
   CHATBOT.JS — v6 — Extraction avec contexte historique
   ================================================================ */
console.log("[Chatbot] v6 chargé — extraction avec contexte historique");

(function () {
    "use strict";

    // ── État global ──────────────────────────────────────────────
    let _history      = [];      // messages de la conversation active
    let _activeId     = null;    // id de la conversation active
    let _isStreaming  = false;
    let _bound        = false;
    let _historyOpen  = false;
    let _initialized  = false;

    const POS_KEY       = "chatbot_btn_pos";
    const PANEL_POS_KEY = "chatbot_panel_pos";
    const MAX_MSG       = 60;    // messages max par conversation
    const MAX_CONVS     = 30;    // conversations max à conserver

    // ── Clés localStorage ────────────────────────────────────────

    function _getUserEmail() {
        try {
            const raw = sessionStorage.getItem("session-store");
            if (!raw) return null;
            const d = JSON.parse(raw);
            return d && d.email ? d.email : null;
        } catch (_) { return null; }
    }

    function _storeKey() {
        const email = _getUserEmail();
        const hash  = email ? btoa(email).replace(/[^a-zA-Z0-9]/g, "") : "guest";
        return "chatbot_convs_" + hash;
    }

    // ── Persistance conversations ────────────────────────────────

    function _loadStore() {
        try {
            const raw = localStorage.getItem(_storeKey());
            return raw ? JSON.parse(raw) : { activeId: null, list: [] };
        } catch (_) { return { activeId: null, list: [] }; }
    }

    function _saveStore(store) {
        try { localStorage.setItem(_storeKey(), JSON.stringify(store)); } catch (_) {}
    }

    // Génère un titre à partir du 1er message utilisateur
    function _autoTitle(text) {
        if (!text) return "Nouvelle conversation";
        const t = text.trim().replace(/\s+/g, " ");
        return t.length > 45 ? t.slice(0, 42) + "…" : t;
    }

    // Formate la date de façon relative
    function _relDate(isoStr) {
        try {
            const d    = new Date(isoStr);
            const now  = new Date();
            const diff = Math.floor((now - d) / 86400000);
            if (diff === 0)  return "Aujourd'hui";
            if (diff === 1)  return "Hier";
            if (diff < 7)    return "Il y a " + diff + " jours";
            if (diff < 30)   return "Il y a " + Math.floor(diff / 7) + " sem.";
            return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
        } catch (_) { return ""; }
    }

    // ── Gestion des conversations ─────────────────────────────────

    function _newConversation() {
        _history   = [];
        _activeId  = "conv_" + Date.now();

        // Réinitialiser la zone messages
        const container = $("#chatbot-messages");
        if (container) {
            container.innerHTML = "";
            const wrap   = document.createElement("div");
            wrap.id        = "chatbot-welcome";
            wrap.className = "chatbot-msg chatbot-msg-bot";
            wrap.innerHTML = `<div class="chatbot-bubble">
                <strong> Bonjour !</strong><br>
                Je suis votre assistant IA. Posez-moi vos questions sur la plateforme, les modèles de prédiction ou les actions disponibles.
            </div>`;
            container.appendChild(wrap);
        }

        // Passer à la vue chat
        if (_historyOpen) _toggleHistoryView(false);

        setTimeout(() => { const i = $("#chatbot-input"); if (i) { i.value = ""; i.focus(); } }, 100);
    }

    function _saveCurrentConversation() {
        if (!_activeId || _history.length === 0) return;
        const store = _loadStore();
        const idx   = store.list.findIndex(c => c.id === _activeId);
        const now   = new Date().toISOString();

        const title = _autoTitle(
            (_history.find(m => m.role === "user") || {}).content || ""
        );

        if (idx >= 0) {
            store.list[idx].messages = _history.slice(-MAX_MSG);
            store.list[idx].updated  = now;
            store.list[idx].title    = title;
        } else {
            store.list.unshift({
                id:       _activeId,
                title:    title,
                created:  now,
                updated:  now,
                messages: _history.slice(-MAX_MSG),
            });
            // Limiter le nombre de conversations
            if (store.list.length > MAX_CONVS) {
                store.list = store.list.slice(0, MAX_CONVS);
            }
        }
        store.activeId = _activeId;
        _saveStore(store);
    }

    function _loadConversation(id) {
        const store = _loadStore();
        const conv  = store.list.find(c => c.id === id);
        if (!conv) return;

        _activeId = id;
        _history  = conv.messages || [];

        // Rerendre les messages
        const container = $("#chatbot-messages");
        if (container) {
            container.innerHTML = "";
            _history.forEach(function (msg) {
                const role   = msg.role === "assistant" ? "bot" : msg.role;
                const wrap   = document.createElement("div");
                wrap.className = "chatbot-msg chatbot-msg-" + role;
                const bubble = document.createElement("div");
                bubble.className   = "chatbot-bubble";
                bubble.textContent = msg.content;
                wrap.appendChild(bubble);
                container.appendChild(wrap);
            });
        }
        scrollBottom();

        // Fermer l'historique, aller sur la vue chat
        _toggleHistoryView(false);
        setTimeout(() => { const i = $("#chatbot-input"); if (i) i.focus(); }, 200);
    }

    function _deleteConversation(id, e) {
        e.stopPropagation();
        const store = _loadStore();
        store.list  = store.list.filter(c => c.id !== id);
        if (store.activeId === id) store.activeId = null;
        _saveStore(store);

        // Si on vient de supprimer la conv active → nouvelle conv
        if (_activeId === id) _newConversation();

        // Rafraîchir la liste
        _renderHistoryList();
    }

    // ── Vue historique ────────────────────────────────────────────

    function _toggleHistoryView(forceState) {
        _historyOpen = (forceState !== undefined) ? forceState : !_historyOpen;

        const chatView = $("#chatbot-chat-view");
        const histView = $("#chatbot-history-view");
        const btn      = $("#chatbot-history-btn");
        if (!chatView || !histView) return;

        if (_historyOpen) {
            chatView.classList.add("cb-view-hidden");
            histView.classList.remove("cb-view-hidden");
            btn && btn.classList.add("cb-btn-active");
            _renderHistoryList();
        } else {
            histView.classList.add("cb-view-hidden");
            chatView.classList.remove("cb-view-hidden");
            btn && btn.classList.remove("cb-btn-active");
            scrollBottom();
        }
    }

    function _renderHistoryList() {
        const list = $("#chatbot-history-list");
        if (!list) return;

        const store = _loadStore();
        list.innerHTML = "";

        if (store.list.length === 0) {
            list.innerHTML = `<div class="cb-hist-empty">
                <i class="fa-solid fa-comments"></i>
                <p>Aucune conversation sauvegardée</p>
            </div>`;
            return;
        }

        // Grouper par date (Aujourd'hui / Hier / Cette semaine / Plus ancien)
        const groups = {};
        store.list.forEach(function (conv) {
            const label = _relDate(conv.updated);
            if (!groups[label]) groups[label] = [];
            groups[label].push(conv);
        });

        Object.keys(groups).forEach(function (label) {
            const section = document.createElement("div");
            section.className = "cb-hist-section";

            const heading = document.createElement("div");
            heading.className   = "cb-hist-section-label";
            heading.textContent = label;
            section.appendChild(heading);

            groups[label].forEach(function (conv) {
                const item = document.createElement("div");
                item.className = "cb-hist-item" + (conv.id === _activeId ? " cb-hist-item-active" : "");

                const preview = (conv.messages.slice().reverse().find(m => m.role === "assistant") || {}).content || "";
                const previewShort = preview.slice(0, 55) + (preview.length > 55 ? "…" : "");

                item.innerHTML = `
                    <div class="cb-hist-item-body">
                        <div class="cb-hist-item-title">${_esc(conv.title)}</div>
                        <div class="cb-hist-item-preview">${_esc(previewShort)}</div>
                    </div>
                    <button class="cb-hist-delete" title="Supprimer">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                `;

                item.querySelector(".cb-hist-item-body").addEventListener("click", function () {
                    _loadConversation(conv.id);
                });
                item.querySelector(".cb-hist-delete").addEventListener("click", function (e) {
                    _deleteConversation(conv.id, e);
                });

                section.appendChild(item);
            });

            list.appendChild(section);
        });
    }

    function _esc(str) {
        return (str || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
    }

    // ── Helpers DOM ──────────────────────────────────────────────

    function $(sel) { return document.querySelector(sel); }

    function scrollBottom() {
        const msgs = $("#chatbot-messages");
        if (msgs) msgs.scrollTop = msgs.scrollHeight;
    }

    function addMessage(role, text, id) {
        const msgs = $("#chatbot-messages");
        if (!msgs) return null;
        const wrap   = document.createElement("div");
        wrap.className = "chatbot-msg chatbot-msg-" + role;
        if (id) wrap.id = id;
        const bubble = document.createElement("div");
        bubble.className   = "chatbot-bubble";
        bubble.textContent = text;
        wrap.appendChild(bubble);
        msgs.appendChild(wrap);
        scrollBottom();
        return bubble;
    }

    function showTyping() {
        const msgs = $("#chatbot-messages");
        if (!msgs) return;
        const wrap = document.createElement("div");
        wrap.className = "chatbot-msg chatbot-msg-bot";
        wrap.id = "chatbot-typing";
        wrap.innerHTML = `<div class="chatbot-bubble chatbot-typing-bubble">
            <span class="chatbot-dot"></span><span class="chatbot-dot"></span><span class="chatbot-dot"></span>
        </div>`;
        msgs.appendChild(wrap);
        scrollBottom();
    }

    function removeTyping() {
        const t = $("#chatbot-typing");
        if (t) t.remove();
    }

    // ── Voix : MediaRecorder + Groq Whisper ─────────────────────
    // Fiable sur HTTP local — pas de dépendance Chrome Speech API

    let _isListening   = false;
    let _mediaRecorder = null;
    let _audioChunks   = [];

    function _setMicState(active) {
        _isListening = active;
        const btn = $("#chatbot-mic");
        if (!btn) return;
        if (active) {
            btn.classList.add("cb-mic-active");
            btn.title = "Arrêter";
        } else {
            btn.classList.remove("cb-mic-active");
            btn.title = "Parler";
        }
    }

    function toggleVoice() {
        const input = $("#chatbot-input");

        if (!_getUserEmail()) {
            if (input) input.placeholder = "Connectez-vous pour utiliser l'assistant…";
            return;
        }

        // Arrêter l'enregistrement
        if (_isListening && _mediaRecorder) {
            _mediaRecorder.stop();
            return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            addMessage("bot", "Accès au microphone non disponible sur ce navigateur.");
            return;
        }

        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(function (stream) {
                _audioChunks = [];

                const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
                    ? 'audio/webm;codecs=opus'
                    : MediaRecorder.isTypeSupported('audio/webm')
                    ? 'audio/webm'
                    : 'audio/ogg;codecs=opus';

                _mediaRecorder = new MediaRecorder(stream, { mimeType });

                _mediaRecorder.ondataavailable = function (e) {
                    if (e.data && e.data.size > 0) _audioChunks.push(e.data);
                };

                _mediaRecorder.onstop = async function () {
                    stream.getTracks().forEach(t => t.stop());
                    _setMicState(false);
                    if (_audioChunks.length === 0) return;

                    const blob = new Blob(_audioChunks, { type: mimeType });
                    _audioChunks = [];
                    if (input) input.placeholder = "Transcription en cours…";

                    try {
                        const formData = new FormData();
                        formData.append('audio', blob, 'audio.webm');
                        const resp = await fetch('/api/transcribe', { method: 'POST', body: formData });
                        const data = await resp.json();

                        if (data.text && data.text.trim()) {
                            if (input) {
                                input.value = data.text.trim();
                                input.placeholder = "Posez votre question ou parlez…";
                            }
                            setTimeout(sendMessage, 300);
                        } else {
                            if (input) input.placeholder = "Posez votre question ou parlez…";
                            addMessage("bot", data.error ? data.error : "Aucune parole détectée, réessayez.");
                        }
                    } catch (err) {
                        if (input) input.placeholder = "Posez votre question ou parlez…";
                        addMessage("bot", "Erreur transcription : " + err.message);
                    }
                };

                _setMicState(true);
                if (input) input.placeholder = "Parlez… re-cliquez pour arrêter";
                _mediaRecorder.start();
            })
            .catch(function (err) {
                _setMicState(false);
                if (err.name === 'NotAllowedError') {
                    addMessage("bot", "Permission micro refusée.\nAutorisez le micro dans les paramètres du navigateur.");
                } else {
                    addMessage("bot", "Micro inaccessible : " + err.message);
                }
            });
    }

    // ── Comparaison modèles ──────────────────────────────────────

    // Intention : "quel modèle pour Apple ?" / "compare les modèles sur TSLA" etc.
    // Regex sans caractères spéciaux pour éviter les problèmes d'encodage
    const _COMPARE_RE = /quel\s+mod.le|meilleur\s+mod.le|compare\s+.{0,15}mod.le|mod.le\s+.{0,20}conseill|recommand.{0,10}mod.le|quel\s+mod.l|si\s+j.avais\s+suivi|quel\s+algo|comparer\s+les\s+mod/i;

    function _extractCompareSymbol(text, history) {
        const lo = ' ' + text.toLowerCase() + ' ';
        const ctxLo = lo + ' ' + (history || []).slice(-8).map(m => (m.content || '').toLowerCase()).join(' ') + ' ';
        const sym = _findSymbol(lo) || _findSymbol(ctxLo);
        console.log("[Chatbot] _extractCompareSymbol:", sym, "| lo:", lo.slice(0,60));
        return sym;
    }

    function _makeSpark(series, bhSeries, W, H) {
        W = W || 380; H = H || 80;
        if (!series || series.length < 2) return '';
        const all = [...series, ...(bhSeries || [])];
        const mn = Math.min(...all), mx = Math.max(...all);
        const rng = mx - mn || 1;
        const PAD = { t: 6, b: 6, l: 4, r: 4 };
        const iW = W - PAD.l - PAD.r, iH = H - PAD.t - PAD.b;
        const vy = (v) => (PAD.t + (mx - v) / rng * iH).toFixed(1);
        const vx = (i, len) => (PAD.l + i / (len - 1) * iW).toFixed(1);
        const pts = (arr) => arr.map((v, i) => `${vx(i, arr.length)},${vy(v)}`).join(' ');
        const bhLine = bhSeries && bhSeries.length > 1
            ? `<polyline points="${pts(bhSeries)}" fill="none" stroke="rgba(255,255,255,0.22)" stroke-width="1.2" stroke-dasharray="4,3"/>`
            : '';
        // Coloring: green if final > start, red otherwise
        const finalV = series[series.length - 1];
        const startV = series[0];
        const lineCol = finalV >= startV ? '#3ef5a0' : '#ff6060';
        // Dashed line at start value (reference)
        const refY = vy(startV);
        const refLine = `<line x1="${PAD.l}" y1="${refY}" x2="${W - PAD.r}" y2="${refY}" stroke="rgba(255,255,255,0.1)" stroke-width="1" stroke-dasharray="2,4"/>`;
        return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:${H}px;display:block">
            ${refLine}
            ${bhLine}
            <polyline points="${pts(series)}" fill="none" stroke="${lineCol}" stroke-width="2"/>
        </svg>`;
    }

    function _makeDraggable(el, handle) {
        let sx = 0, sy = 0, sl = 0, st = 0, drag = false;
        handle.style.cursor = 'grab';
        const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
        const onDown = (cx, cy) => {
            drag = true;
            const r = el.getBoundingClientRect();
            sx = cx; sy = cy; sl = r.left; st = r.top;
            handle.style.cursor = 'grabbing';
            el.style.transition = 'none';
        };
        const onMove = (cx, cy) => {
            if (!drag) return;
            const nl = clamp(sl + cx - sx, 0, window.innerWidth  - el.offsetWidth);
            const nt = clamp(st + cy - sy, 0, window.innerHeight - el.offsetHeight);
            el.style.left = nl + 'px'; el.style.top = nt + 'px';
            el.style.right = 'auto';   el.style.bottom = 'auto';
        };
        const onUp = () => { drag = false; handle.style.cursor = 'grab'; };
        handle.addEventListener('mousedown', e => {
            if (e.target.closest('.cb-modal-close')) return;
            e.preventDefault(); onDown(e.clientX, e.clientY);
        });
        document.addEventListener('mousemove', e => onMove(e.clientX, e.clientY));
        document.addEventListener('mouseup', onUp);
        handle.addEventListener('touchstart', e => {
            const t = e.touches[0]; onDown(t.clientX, t.clientY);
        }, { passive: true });
        handle.addEventListener('touchmove', e => {
            const t = e.touches[0]; onMove(t.clientX, t.clientY);
        }, { passive: true });
        handle.addEventListener('touchend', onUp, { passive: true });
    }

    async function _loadAndShowCompare(symbol, bubble) {
        if (!symbol) return;

        console.log("[Chatbot] Ouverture modal comparaison pour:", symbol);
        const modal = _openCompareModal(symbol);
        if (!modal) { console.warn("[Chatbot] panel introuvable pour modal"); return; }

        try {
            const resp = await fetch(`/api/backtest-compare?symbol=${encodeURIComponent(symbol)}`);
            const data = await resp.json();
            const body = document.getElementById("cb-modal-body");
            if (!body) return;
            if (data.error) {
                body.innerHTML = `<div class="cb-modal-error">Donnees insuffisantes pour ${symbol}.<br><small>Ce ticker n'est peut-etre pas supporte par nos modeles.</small></div>`;
            } else {
                _populateCompareModal(body, symbol, data);
                // Ajouter un message chat avec les vrais résultats (corrige la reco générique du LLM)
                _addBacktestSummaryToChat(symbol, data);
            }
        } catch (e) {
            const body = document.getElementById("cb-modal-body");
            if (body) body.innerHTML = `<div class="cb-modal-error">Erreur de connexion au serveur.</div>`;
            console.warn("[Chatbot] backtest-compare fetch error:", e);
        }
    }

    function _addBacktestSummaryToChat(symbol, data) {
        const models = data.models || {};
        const best   = data.best_model;
        const start  = data.start || 500;
        const keys   = Object.keys(models);
        if (keys.length === 0) return;

        const lines = keys.map(k => {
            const m    = models[k];
            const gain = m.final - start;
            const sign = gain >= 0 ? '+' : '';
            const isBest = k === best;
            return `• ${m.label} : ${sign}${gain.toFixed(2)}€ (${sign}${m.return_pct}%) sur 500€${isBest ? ' ← meilleur' : ''}`;
        }).join('\n');

        const bestM     = models[best] || {};
        const bestGain  = (bestM.final || start) - start;
        const bestSign  = bestGain >= 0 ? '+' : '';
        const bestLabel = bestM.label || best;

        const msg = `Voici les resultats reels de la simulation sur les 180 derniers jours pour ${symbol} :\n${lines}\n\nSur la base des donnees historiques, le modele le plus performant pour ${symbol} est **${bestLabel}** (${bestSign}${bestGain.toFixed(2)}€ sur 500€ investis). C'est celui que je recommande pour ${symbol}.`;

        addMessage("bot", msg);
        _history.push({ role: "assistant", content: msg });
        _saveCurrentConversation();
        setTimeout(() => { const m = $("#chatbot-messages"); if (m) m.scrollTop = m.scrollHeight; }, 100);
    }

    function _openCompareModal(symbol) {
        const old = document.getElementById("cb-compare-modal");
        if (old) old.remove();

        const modal = document.createElement("div");
        modal.id = "cb-compare-modal";

        // Position initiale : à gauche du chatbot panel
        const panel = document.getElementById("chatbot-panel");
        if (panel) {
            const r = panel.getBoundingClientRect();
            const mw = 440;
            let left = r.left - mw - 14;
            if (left < 10) left = Math.min(r.right + 14, window.innerWidth - mw - 10);
            const top  = Math.max(10, r.top - 10);
            modal.style.cssText = `left:${left}px;top:${top}px;`;
        }

        modal.innerHTML = `
            <div class="cb-modal-header" id="cb-modal-drag-handle">
                <div class="cb-modal-title">
                    <i class="fas fa-chart-line"></i>
                    <span>Si j'avais suivi les conseils — ${symbol}</span>
                </div>
                <div style="display:flex;align-items:center;gap:6px">
                    <span class="cb-modal-drag-hint"><i class="fas fa-arrows-alt"></i></span>
                    <button class="cb-modal-close" id="cb-modal-close-btn"><i class="fas fa-times"></i></button>
                </div>
            </div>
            <div class="cb-modal-body" id="cb-modal-body">
                <div class="cb-modal-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    Simulation en cours...<br>
                    <small>Les 3 modeles sont calcules en parallele (~15s)</small>
                </div>
            </div>`;

        document.body.appendChild(modal);
        document.getElementById("cb-modal-close-btn").addEventListener("click", () => modal.remove());
        _makeDraggable(modal, document.getElementById("cb-modal-drag-handle"));
        return modal;
    }

    function _populateCompareModal(body, symbol, data) {
        const MODEL_ICON = { lstm: 'fas fa-brain', transformer: 'fas fa-atom', sentiment: 'fas fa-newspaper' };
        const models = data.models || {};
        const best   = data.best_model;
        const start  = data.start || 500;
        const keys   = Object.keys(models);
        if (keys.length === 0) {
            body.innerHTML = `<div class="cb-modal-error">Aucun modele n'a pu simuler ${symbol}.</div>`;
            return;
        }
        const rows = keys.map(k => {
            const m       = models[k];
            const isBest  = k === best;
            const gain    = m.final - start;
            const gainEur  = (gain >= 0 ? '+' : '') + gain.toFixed(2);
            const gainCls  = gain >= 0 ? 'cb-cmp-pos' : 'cb-cmp-neg';
            const retSign  = m.return_pct >= 0 ? '+' : '';
            const bhSign   = m.bh_return  >= 0 ? '+' : '';
            const vsPassif = m.final - m.bh_final;
            const vsEur    = (vsPassif >= 0 ? '+' : '') + vsPassif.toFixed(2);
            const vsCls    = vsPassif >= 0 ? 'cb-cmp-pos' : 'cb-cmp-neg';
            const vsText   = vsPassif >= 0
                ? `<span class="${vsCls}">${vsEur}€ de plus</span> qu'un simple achat sans IA`
                : `<span class="${vsCls}">${vsEur}€ de moins</span> qu'un simple achat sans IA`;
            const spark    = _makeSpark(m.series, m.bh_series, 400, 80);
            return `
            <div class="cb-modal-model${isBest ? ' cb-modal-model-best' : ''}">
                <div class="cb-modal-model-head">
                    <span class="cb-cmp-name"><i class="${MODEL_ICON[k] || 'fas fa-robot'}"></i> ${m.label}</span>
                    <div style="display:flex;align-items:center;gap:7px">
                        ${isBest ? '<span class="cb-cmp-badge">Recommande</span>' : ''}
                        <a href="/mon-suivi?mode=${k}&ticker=${symbol}" class="cb-modal-view-btn" title="Voir dans Mon Suivi">
                            <i class="fas fa-external-link-alt"></i> Mon Suivi
                        </a>
                    </div>
                </div>
                <div class="cb-modal-explain">
                    Si vous aviez investi <strong>${start}€</strong> sur <strong>${symbol}</strong>
                    depuis le <strong>${m.start_date}</strong> en suivant le modele <strong>${m.label}</strong>,
                    vous auriez maintenant
                    <strong class="${gainCls}">${m.final.toFixed(2)}€</strong> — soit
                    <strong class="${gainCls}">${gainEur}€ (${retSign}${m.return_pct}%)</strong>.
                    C'est ${vsText} (qui aurait donne <strong>${m.bh_final.toFixed(2)}€</strong>).
                </div>
                ${spark ? `<div class="cb-cmp-spark">${spark}<div class="cb-cmp-spark-legend"><span class="cb-cmp-spark-ai">— Modele IA</span><span class="cb-cmp-spark-bh">- - Sans IA (buy&amp;hold)</span></div></div>` : ''}
                <div class="cb-cmp-grid">
                    <div class="cb-cmp-cell">
                        <span class="cb-cmp-lbl">Valeur finale</span>
                        <span class="cb-cmp-val ${gainCls}">${m.final.toFixed(2)}€</span>
                    </div>
                    <div class="cb-cmp-cell">
                        <span class="cb-cmp-lbl">Taux reussite</span>
                        <span class="cb-cmp-val">${m.win_rate}%</span>
                    </div>
                    <div class="cb-cmp-cell">
                        <span class="cb-cmp-lbl">Sans IA (buy&amp;hold)</span>
                        <span class="cb-cmp-val">${m.bh_final.toFixed(2)}€ (${bhSign}${m.bh_return}%)</span>
                    </div>
                </div>
            </div>`;
        }).join('');
        const bestLabel = best ? (models[best]?.label || best) : '—';
        body.innerHTML = `
            <div class="cb-modal-subtitle">Simulation sur 180 jours · investissement de reference : ${start}€</div>
            ${rows}
            <div class="cb-modal-footer">Recommandation : <strong>${bestLabel}</strong> — meilleur rendement sur la periode</div>`;
    }

    // _showCompareCard gardé pour compat (ne fait rien, modal gere tout)
    function _showCompareCard() {}

    // ── Détection marqueur investissement ───────────────────────

    const INVEST_RE = /##INVEST##\s*(\{[\s\S]*?\})\s*##/;

    function _parseInvestMarker(text) {
        const m = text.match(INVEST_RE);
        if (!m) return null;
        try { return JSON.parse(m[1]); } catch(_) { return null; }
    }

    function _stripInvestMarker(text) {
        return text.replace(INVEST_RE, "").trim();
    }

    function _showInvestConfirm(bubble, data) {
        console.log("[Chatbot] _showInvestConfirm appelé:", data);
        const MODEL_LABELS = { sentiment: "Actualités", lstm: "LSTM", transformer: "Transformer" };
        const card = document.createElement("div");
        card.className = "cb-invest-card cb-invest-card-pulse";
        card.innerHTML = `
            <div class="cb-invest-header">
                <i class="fa-solid fa-briefcase"></i>
                <span>Confirmez l'enregistrement</span>
            </div>
            <div class="cb-invest-details">
                <div class="cb-invest-row"><span>Action</span><strong>${data.symbol}</strong></div>
                <div class="cb-invest-row"><span>Modèle</span><strong>${MODEL_LABELS[data.model] || data.model}</strong></div>
                <div class="cb-invest-row"><span>Sens</span><strong class="${data.action==='ACHETER'?'cb-buy':'cb-sell'}">${data.action}</strong></div>
                <div class="cb-invest-row"><span>Montant</span><strong>${data.amount} €</strong></div>
            </div>
            <p class="cb-invest-note">Cliquez sur le bouton ci-dessous pour enregistrer dans Mon Suivi</p>
            <div class="cb-invest-actions">
                <button class="cb-invest-confirm">Enregistrer dans Mon Suivi</button>
                <button class="cb-invest-cancel">Annuler</button>
            </div>
        `;

        // Insérer après la bulle bot (avec fallback sur le container)
        const wrap = bubble ? bubble.closest(".chatbot-msg") : null;
        if (wrap && wrap.parentNode) {
            wrap.parentNode.insertBefore(card, wrap.nextSibling);
        } else {
            const msgs = $("#chatbot-messages");
            if (msgs) msgs.appendChild(card);
        }

        // Forcer l'ouverture du panel si fermé — ouvrir directement sans réinitialiser
        const panel = $("#chatbot-panel");
        if (panel && !panel.classList.contains("chatbot-open")) {
            _positionPanel();
            panel.classList.remove("chatbot-hidden");
            panel.classList.add("chatbot-open");
            const tb = $("#chatbot-toggle");
            if (tb) tb.classList.add("chatbot-toggle-active");
        }

        // Badge rouge sur le bouton toggle pour signaler une action en attente
        const toggleBtn = $("#chatbot-toggle");
        if (toggleBtn && !toggleBtn.querySelector(".cb-pending-badge")) {
            const badge = document.createElement("span");
            badge.className = "cb-pending-badge";
            badge.textContent = "!";
            toggleBtn.appendChild(badge);
        }

        // Scroll précis : amener le bas de la carte dans la zone visible du panel
        function _scrollCardIntoPanel() {
            const msgs = $("#chatbot-messages");
            if (!msgs) return;
            const msgsRect = msgs.getBoundingClientRect();
            const cardRect = card.getBoundingClientRect();
            const overflow = cardRect.bottom - msgsRect.bottom;
            if (overflow > 0) {
                msgs.scrollTop += overflow + 16;
            } else {
                // Fallback si la carte est déjà dans la zone
                msgs.scrollTop = msgs.scrollHeight;
            }
        }
        setTimeout(_scrollCardIntoPanel, 100);
        setTimeout(_scrollCardIntoPanel, 400);
        setTimeout(_scrollCardIntoPanel, 800);

        // Supprimer le badge quand l'utilisateur interagit avec la carte
        card.addEventListener("click", function() {
            const b = toggleBtn && toggleBtn.querySelector(".cb-pending-badge");
            if (b) b.remove();
        }, { once: true });

        card.querySelector(".cb-invest-confirm").addEventListener("click", async function () {
            this.disabled = true;
            this.textContent = "Enregistrement…";
            const email = _getUserEmail() || "";
            console.log("[Chatbot] Enregistrer cliqué — email:", email, "data:", data);
            try {
                const resp = await fetch("/api/chat-invest", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ ...data, email }),
                });
                const result = await resp.json();
                console.log("[Chatbot] /api/chat-invest réponse:", resp.status, result);
                const MODEL_TABS = { sentiment: "Actualités", lstm: "LSTM (prix)", transformer: "Transformer (hybride)" };
                const tabLabel = MODEL_TABS[data.model] || data.model;
                if (result.success) {
                    card.innerHTML = `<div class="cb-invest-success">
                        Investissement enregistré<br>
                        <small>${data.symbol} · ${data.amount} € au prix de $${result.price}</small><br>
                        <small style="color:rgba(0,230,150,0.6)">Retrouvez-le dans <strong>Mon Suivi</strong> › onglet <strong>${tabLabel}</strong></small>
                        <br><a href="/mon-suivi?mode=${data.model}" class="cb-invest-link">Voir dans Mon Suivi</a>
                    </div>`;
                    // Injecter dans l'historique pour que le LLM régénère le marqueur la prochaine fois
                    _history.push({
                        role: "user",
                        content: `[Système] Investissement ${data.symbol} (${data.amount}€, ${data.model}) enregistré avec succès via le marqueur ##INVEST##. Pour tout prochain investissement, vous devez obligatoirement générer un nouveau marqueur ##INVEST## — sans marqueur, rien n'est enregistré.`
                    });
                    _saveCurrentConversation();
                } else {
                    card.innerHTML = `<div class="cb-invest-error" style="font-size:0.85rem;padding:14px">
                        Enregistrement échoué<br>
                        <strong style="color:#ff8080">${result.error || 'données invalides'}</strong><br>
                        <small>Vérifiez que vous êtes connecté et réessayez.</small>
                        <br><button onclick="this.closest('.cb-invest-card').remove()" style="margin-top:8px;padding:4px 12px;border-radius:6px;border:1px solid rgba(255,100,100,0.3);background:none;color:#ff8080;cursor:pointer;font-size:0.75rem">Fermer</button>
                    </div>`;
                }
            } catch(err) {
                console.error("[Chatbot] Erreur fetch invest:", err);
                card.innerHTML = `<div class="cb-invest-error" style="font-size:0.85rem;padding:14px">
                    Impossible de contacter le serveur.<br>
                    <small>Vérifiez votre connexion et réessayez.</small>
                </div>`;
            }
            scrollBottom();
        });

        card.querySelector(".cb-invest-cancel").addEventListener("click", function () {
            card.remove();
        });
    }

    // ── Extraction investissement (100% client, sans API) ────────

    const _SYMBOL_MAP = {
        'apple':'AAPL', 'aapl':'AAPL',
        'microsoft':'MSFT', 'msft':'MSFT',
        'tesla':'TSLA', 'tsla':'TSLA',
        'nvidia':'NVDA', 'nvda':'NVDA',
        'google':'GOOGL', 'alphabet':'GOOGL', 'googl':'GOOGL',
        'amazon':'AMZN', 'amzn':'AMZN',
        'meta':'META', 'facebook':'META',
        'bitcoin':'BTC-USD', 'btc':'BTC-USD', 'crypto':'BTC-USD',
    };
    const _MODEL_LIST = [
        ['lstm','lstm'],['ltsm','lstm'],['bilstm','lstm'],['réseau de neurones','lstm'],
        ['transformer','transformer'],['transformeur','transformer'],['hybride','transformer'],
        ['sentiment','sentiment'],['actualit','sentiment'],['news','sentiment'],
    ];

    // Regex d'intention : .? entre j et ai couvre TOUTES les variantes d'apostrophe
    const _INTENT_RE = /j.?ai\s*(investi|mis\b|achet|vendu|suivi|fait\b)|enregistr|vas-y/i;

    // Cherche un symbole ou un modèle dans une chaîne basse
    function _findSymbol(lo) {
        for (const [k, v] of Object.entries(_SYMBOL_MAP)) {
            if (lo.includes(k)) return v;
        }
        return null;
    }
    function _findModel(lo) {
        for (const [k, v] of _MODEL_LIST) {
            if (lo.includes(k)) return v;
        }
        return null;
    }

    // history = tableau de messages {role, content} — utilisé comme contexte si le
    // symbole/modèle n'est pas dans le message actuel
    function _extractInvestment(text, history) {
        console.log("[Chatbot] _extractInvestment appelé sur:", text.slice(0,80));
        if (!_INTENT_RE.test(text)) {
            console.log("[Chatbot] aucune intention d'investissement détectée");
            return null;
        }

        const lo = ' ' + text.toLowerCase() + ' ';

        // Contexte: tous les messages récents (pour trouver le symbole si non répété)
        const ctxLo = lo + ' ' + (history || []).slice(-10)
            .map(m => (m.content || '').toLowerCase()).join(' ') + ' ';

        // Symbol: d'abord dans le message actuel, puis dans le contexte
        const symbol = _findSymbol(lo) || _findSymbol(ctxLo);

        // Model: idem
        const model = _findModel(lo) || _findModel(ctxLo);

        // Amount : cherche un nombre + €/euro dans le message actuel
        let amount = null;
        const m1 = text.match(/(\d[\d\s]*(?:[.,]\d{1,2})?)\s*(?:€|euros?)/i);
        if (m1) amount = parseFloat(m1[1].replace(/\s/g,'').replace(',','.'));
        if (!amount) {
            const m2 = text.match(/(?:€|euros?)\s*(\d[\d\s]*(?:[.,]\d{1,2})?)/i);
            if (m2) amount = parseFloat(m2[1].replace(/\s/g,'').replace(',','.'));
        }
        if (!amount) {
            // fallback : plus grand nombre dans le texte
            const nums = text.match(/\b(\d{2,7}(?:[.,]\d{1,2})?)\b/g);
            if (nums) amount = Math.max(...nums.map(n => parseFloat(n.replace(',','.'))));
        }

        const action = /vend|short|baissier|sold/i.test(text) ? 'VENDRE' : 'ACHETER';

        console.log("[Chatbot] extraction →", {symbol, model, amount, action});
        if (symbol && amount > 0) {
            return { symbol, model: model || 'lstm', action, amount };
        }
        console.log("[Chatbot] extraction échouée — symbol:", symbol, "amount:", amount);
        return null;
    }

    // ── Envoi du message ─────────────────────────────────────────

    async function sendMessage() {
        if (_isStreaming) return;
        const input = $("#chatbot-input");
        if (!input) return;
        const text = input.value.trim();
        if (!text) return;

        console.log("[Chatbot] sendMessage appelé:", text.slice(0, 60));

        const welcome = $("#chatbot-welcome");
        if (welcome) welcome.remove();

        input.value  = "";
        _isStreaming = true;
        addMessage("user", text);
        _history.push({ role: "user", content: text });
        showTyping();

        // Extraction AVANT le fetch — message actuel + historique pour le contexte
        const pendingInvest  = _extractInvestment(text, _history);
        const isCompareQuery = _COMPARE_RE.test(text);
        const compareSymbol  = isCompareQuery ? _extractCompareSymbol(text, _history) : null;
        console.log("[Chatbot] pendingInvest:", pendingInvest, "| compareSymbol:", compareSymbol);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ messages: _history }),
            });
            if (!response.ok) throw new Error("Erreur serveur " + response.status);

            removeTyping();
            const botBubble = addMessage("bot", "");
            if (!botBubble) return;

            const reader  = response.body.getReader();
            const decoder = new TextDecoder();
            let fullText  = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                for (const line of decoder.decode(value, { stream: true }).split("\n")) {
                    if (!line.startsWith("data: ")) continue;
                    const chunk = line.slice(6).trim();
                    if (chunk === "[DONE]") break;
                    try {
                        const p = JSON.parse(chunk);
                        if (p.text)  { fullText += p.text; botBubble.textContent = fullText; scrollBottom(); }
                        if (p.error) { botBubble.textContent = p.error; }
                    } catch (_) {}
                }
            }

            // Sauvegarder la réponse bot dans l'historique
            const savedText = fullText || botBubble.textContent || "";
            _history.push({ role: "assistant", content: savedText });
            if (_history.length > 40) _history = _history.slice(-40);
            _saveCurrentConversation();

            // Toujours stripper le marqueur ##INVEST## du texte affiché (quel que soit l'intent)
            botBubble.textContent = _stripInvestMarker(savedText);

            // 1. Marqueur inline du LLM (prioritaire)
            const markerData = _parseInvestMarker(savedText);
            const hadInvestIntent = _INTENT_RE.test(text);
            if (markerData && markerData.amount > 0) {
                if (hadInvestIntent) {
                    console.log("[Chatbot] Marqueur LLM détecté:", markerData);
                    _showInvestConfirm(botBubble, markerData);
                } else {
                    console.log("[Chatbot] Marqueur ignoré — pas d'intention dans le message utilisateur");
                }
            } else if (markerData && markerData.amount <= 0) {
                console.log("[Chatbot] Marqueur ignoré — montant nul ou manquant");
            } else if (pendingInvest) {
                // 2. Extraction client sur le message utilisateur (toujours fiable)
                console.log("[Chatbot] Affichage carte confirmation (client):", pendingInvest);
                _showInvestConfirm(botBubble, pendingInvest);
            } else {
                // 3. Détection d'un faux-positif : le bot prétend avoir enregistré sans marqueur
                const falseSave = /enregistr|sauvegard|c.est fait|c.est not|confirm/i.test(savedText);
                if (falseSave && pendingInvest === null && /investi|achet|vendu|mis\b|suivi/i.test(text)) {
                    addMessage("bot", "Pour enregistrer votre investissement, j'ai besoin des détails complets : quelle action, quel modèle (LSTM / Transformer / Actualités) et quel montant ?");
                }
            }

            // 4. Comparaison des modèles — afficher la carte après la réponse LLM
            if (compareSymbol) {
                _loadAndShowCompare(compareSymbol, botBubble);
            }

        } catch (err) {
            removeTyping();
            addMessage("bot", "Impossible de contacter l'assistant.");
            console.error("[Chatbot]", err);
        } finally {
            _isStreaming = false;
        }
    }

    // ── Toggle panel ─────────────────────────────────────────────

    function togglePanel() {
        const panel = $("#chatbot-panel");
        const btn   = $("#chatbot-toggle");
        if (!panel || !btn) return;

        const isOpen = panel.classList.contains("chatbot-open");
        if (isOpen) {
            panel.classList.remove("chatbot-open");
            panel.classList.add("chatbot-hidden");
            btn.classList.remove("chatbot-toggle-active");
        } else {
            _positionPanel();
            panel.classList.remove("chatbot-hidden");
            panel.classList.add("chatbot-open");
            btn.classList.add("chatbot-toggle-active");

            // Re-init à chaque ouverture (re-vérifie la connexion)
            if (!_initialized) {
                _initialized = true;
            }
            _initSession();

            scrollBottom();
            setTimeout(_initPanelDrag, 50);
            setTimeout(() => { const i = $("#chatbot-input"); if (i) i.focus(); }, 320);
        }
    }

    // Charge la dernière conversation ou crée une nouvelle
    function _initSession() {
        // ── Vérification connexion ──────────────────────────────
        if (!_getUserEmail()) {
            _showLockedState();
            return;
        }

        _updateUserBadge();
        const store = _loadStore();

        if (store.activeId) {
            const conv = store.list.find(c => c.id === store.activeId);
            if (conv && conv.messages.length > 0) {
                _activeId = conv.id;
                _history  = conv.messages;
                const container = $("#chatbot-messages");
                if (container) {
                    const w = container.querySelector("#chatbot-welcome");
                    if (w) w.remove();
                    _history.forEach(function (msg) {
                        const role   = msg.role === "assistant" ? "bot" : msg.role;
                        const wrap   = document.createElement("div");
                        wrap.className = "chatbot-msg chatbot-msg-" + role;
                        const bubble = document.createElement("div");
                        bubble.className   = "chatbot-bubble";
                        bubble.textContent = msg.content;
                        wrap.appendChild(bubble);
                        container.appendChild(wrap);
                    });
                }
                scrollBottom();
                return;
            }
        }
        _activeId = "conv_" + Date.now();
    }

    function _showLockedState() {
        // Remplacer les messages par un message de verrouillage
        const container = $("#chatbot-messages");
        if (container) {
            container.innerHTML = `
                <div class="cb-locked-wrap">
                    <div class="cb-locked-icon"><i class="fa-solid fa-lock"></i></div>
                    <div class="cb-locked-title">Connexion requise</div>
                    <div class="cb-locked-desc">
                        Le Conseiller IA est réservé aux membres connectés.
                        Connectez-vous pour accéder à l'assistant.
                    </div>
                    <a href="/login" class="cb-locked-btn">
                        <i class="fa-solid fa-right-to-bracket"></i> Se connecter
                    </a>
                </div>
            `;
        }
        // Désactiver l'input et les boutons
        const input   = $("#chatbot-input");
        const send    = $("#chatbot-send");
        const mic     = $("#chatbot-mic");
        const newBtn  = $("#chatbot-new-btn");
        const histBtn = $("#chatbot-history-btn");
        if (input)   { input.disabled   = true; input.placeholder = "Connectez-vous pour utiliser l'assistant…"; }
        if (send)    send.disabled    = true;
        if (mic)     mic.disabled     = true;
        if (newBtn)  newBtn.disabled  = true;
        if (histBtn) histBtn.disabled = true;
    }

    function _updateUserBadge() {
        const email = _getUserEmail();
        const info  = $(".chatbot-header-info");
        if (!info || !email) return;
        const old = info.querySelector(".chatbot-user-badge");
        if (old) old.remove();
        const badge = document.createElement("div");
        badge.className   = "chatbot-user-badge";
        badge.textContent = email.split("@")[0];
        info.appendChild(badge);
    }

    // ── Drag panel ───────────────────────────────────────────────

    function _positionPanel() {
        const panel = $("#chatbot-panel");
        const btn   = $("#chatbot-toggle");
        if (!panel || !btn) return;
        const saved = _loadPanelPos();
        if (saved) { _applyPanelPos(saved.left, saved.top); return; }
        const r = btn.getBoundingClientRect();
        const panelW = 380, panelH = 580, m = 12;
        const vw = window.innerWidth, vh = window.innerHeight;
        let left = r.left + r.width / 2 - panelW / 2;
        let top  = r.top - panelH - m;
        if (top  < m)                  top  = r.bottom + m;
        if (left + panelW > vw - m)    left = vw - panelW - m;
        if (left < m)                  left = m;
        if (top  + panelH > vh - m)    top  = vh - panelH - m;
        _applyPanelPos(left, top);
    }

    function _applyPanelPos(l, t) {
        const p = $("#chatbot-panel");
        if (!p) return;
        p.style.left = l+"px"; p.style.top = t+"px"; p.style.right = "auto"; p.style.bottom = "auto";
    }
    function _savePanelPos(l, t) { try { localStorage.setItem(PANEL_POS_KEY, JSON.stringify({left:l,top:t})); } catch(_){} }
    function _loadPanelPos() {
        try {
            const raw = localStorage.getItem(PANEL_POS_KEY);
            if (!raw) return null;
            const p = JSON.parse(raw); const vw=window.innerWidth,vh=window.innerHeight;
            if (p.left<0||p.top<0||p.left>vw-100||p.top>vh-100) return null; return p;
        } catch(_){ return null; }
    }

    function _initPanelDrag() {
        const panel = $("#chatbot-panel"), header = $("#chatbot-header");
        if (!panel||!header||header._panelDragBound) return;
        header._panelDragBound = true;
        let sx,sy,sl,st,drag=false;
        function onStart(e) {
            if (e.target.closest("#chatbot-close")||e.target.closest("#chatbot-history-btn")||
                e.target.closest("#chatbot-new-btn")) return;
            const pt=e.touches?e.touches[0]:e; sx=pt.clientX; sy=pt.clientY;
            const r=panel.getBoundingClientRect(); sl=r.left; st=r.top; drag=false;
            document.addEventListener("mousemove",onMove); document.addEventListener("mouseup",onEnd);
            document.addEventListener("touchmove",onMove,{passive:false}); document.addEventListener("touchend",onEnd);
        }
        function onMove(e) {
            const pt=e.touches?e.touches[0]:e; const dx=pt.clientX-sx,dy=pt.clientY-sy;
            if (!drag&&Math.hypot(dx,dy)>4){drag=true;panel.style.transition="none";panel.style.opacity="0.92";}
            if (!drag) return; if (e.cancelable) e.preventDefault();
            const vw=window.innerWidth,vh=window.innerHeight,pw=panel.offsetWidth,ph=panel.offsetHeight,m=8;
            _applyPanelPos(Math.max(m,Math.min(sl+dx,vw-pw-m)),Math.max(m,Math.min(st+dy,vh-ph-m)));
        }
        function onEnd() {
            document.removeEventListener("mousemove",onMove); document.removeEventListener("mouseup",onEnd);
            document.removeEventListener("touchmove",onMove); document.removeEventListener("touchend",onEnd);
            if (drag){drag=false;panel.style.transition="";panel.style.opacity="";
                const r=panel.getBoundingClientRect(); _savePanelPos(r.left,r.top);}
        }
        header.addEventListener("mousedown",onStart); header.addEventListener("touchstart",onStart,{passive:true});
    }

    // ── Drag bouton ──────────────────────────────────────────────

    function _initDrag() {
        const btn = $("#chatbot-toggle");
        if (!btn||btn._dragBound) return; btn._dragBound=true;
        let sx,sy,sl,st,dragging=false;
        const saved=_loadPos();
        if (saved){_applyBtnPos(saved.left,saved.top);}
        else{_applyBtnPos(window.innerWidth-88,window.innerHeight-88);}
        function onStart(e){
            const pt=e.touches?e.touches[0]:e; sx=pt.clientX;sy=pt.clientY;
            const r=btn.getBoundingClientRect(); sl=r.left;st=r.top; dragging=false;
            document.addEventListener("mousemove",onMove); document.addEventListener("mouseup",onEnd);
            document.addEventListener("touchmove",onMove,{passive:false}); document.addEventListener("touchend",onEnd);
        }
        function onMove(e){
            const pt=e.touches?e.touches[0]:e; const dx=pt.clientX-sx,dy=pt.clientY-sy;
            if (!dragging&&Math.hypot(dx,dy)>5){dragging=true;btn.classList.add("cb-dragging");}
            if (!dragging) return; if(e.cancelable)e.preventDefault();
            const vw=window.innerWidth,vh=window.innerHeight,sz=btn.offsetWidth,m=8;
            _applyBtnPos(Math.max(m,Math.min(sl+dx,vw-sz-m)),Math.max(m,Math.min(st+dy,vh-sz-m)));
        }
        function onEnd(){
            document.removeEventListener("mousemove",onMove); document.removeEventListener("mouseup",onEnd);
            document.removeEventListener("touchmove",onMove); document.removeEventListener("touchend",onEnd);
            if(dragging){btn.classList.remove("cb-dragging");_snapToEdge();dragging=false;}
            else{togglePanel();}
        }
        btn.addEventListener("mousedown",onStart); btn.addEventListener("touchstart",onStart,{passive:true});
    }

    function _snapToEdge(){
        const btn=$("#chatbot-toggle"); if(!btn) return;
        const r=btn.getBoundingClientRect(),vw=window.innerWidth,vh=window.innerHeight,sz=r.width,m=12;
        const left=(r.left+sz/2<vw/2)?m:vw-sz-m, top=Math.max(m,Math.min(r.top,vh-sz-m));
        btn.style.transition="left 0.35s cubic-bezier(0.22,1,0.36,1),top 0.2s ease";
        _applyBtnPos(left,top); setTimeout(()=>{btn.style.transition="";},400); _savePos(left,top);
        const panel=$("#chatbot-panel");
        if(panel&&panel.classList.contains("chatbot-open")) setTimeout(_positionPanel,50);
    }
    function _applyBtnPos(l,t){const btn=$("#chatbot-toggle");if(!btn)return;btn.style.left=l+"px";btn.style.top=t+"px";btn.style.right="auto";btn.style.bottom="auto";}
    function _savePos(l,t){try{localStorage.setItem(POS_KEY,JSON.stringify({left:l,top:t}));}catch(_){}}
    function _loadPos(){
        try{const raw=localStorage.getItem(POS_KEY);if(!raw)return null;const p=JSON.parse(raw);const vw=window.innerWidth,vh=window.innerHeight;
            if(p.left<0||p.top<0||p.left>vw-40||p.top>vh-40)return null;return p;}catch(_){return null;}
    }

    // ── Event delegation ─────────────────────────────────────────

    function attachGlobalListeners() {
        // Utilise une propriété sur document pour éviter les doublons
        // si le script est chargé deux fois (Dash debug/hot-reload)
        if (document._chatbotBound) return;
        document._chatbotBound = true;
        _bound = true;

        document.addEventListener("click", function (e) {
            if (e.target.closest("#chatbot-close"))        { togglePanel(); return; }
            if (e.target.closest("#chatbot-send"))         { sendMessage(); return; }
            if (e.target.closest("#chatbot-mic"))          { toggleVoice(); return; }
            if (e.target.closest("#chatbot-history-btn"))  { _toggleHistoryView(); return; }
            if (e.target.closest("#chatbot-new-btn") ||
                e.target.closest("#chatbot-new-btn2"))     { _newConversation(); return; }
        });

        document.addEventListener("keydown", function (e) {
            if (e.target&&e.target.id==="chatbot-input"&&e.key==="Enter"&&!e.shiftKey) {
                e.preventDefault(); sendMessage();
            }
        });

        document.addEventListener("mousedown", function (e) {
            const panel=$("#chatbot-panel"),btn=$("#chatbot-toggle");
            if (!panel||panel.classList.contains("chatbot-hidden")) return;
            if (!panel.contains(e.target)&&btn&&!btn.contains(e.target)) togglePanel();
        });
    }

    // ── Init ─────────────────────────────────────────────────────

    function init() { attachGlobalListeners(); _initDrag(); }

    if (document.readyState==="loading") { document.addEventListener("DOMContentLoaded",init); }
    else { init(); }

    const _obs = new MutationObserver(function(){const btn=$("#chatbot-toggle");if(btn&&!btn._dragBound)_initDrag();});
    _obs.observe(document.body,{childList:true,subtree:true});

    window.addEventListener("resize",function(){
        const btn=$("#chatbot-toggle"); if(!btn)return;
        const r=btn.getBoundingClientRect(),vw=window.innerWidth,vh=window.innerHeight,sz=btn.offsetWidth,m=12;
        _applyBtnPos(Math.max(m,Math.min(r.left,vw-sz-m)),Math.max(m,Math.min(r.top,vh-sz-m)));
        const panel=$("#chatbot-panel");
        if(panel&&panel.classList.contains("chatbot-open"))_positionPanel();
    });

})();
