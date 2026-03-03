/**
 * DocuFlow — Frontend Application v2
 * ====================================
 * Dashboard + Chat + Upload — SPA con navegación por vistas.
 */

(() => {
    "use strict";

    // ════════════════════════════════════════════════════════════
    //  DOM REFS
    // ════════════════════════════════════════════════════════════
    const $app         = document.getElementById("app");
    const $messages    = document.getElementById("messages");
    const $welcome     = document.getElementById("welcome");
    const $form        = document.getElementById("chat-form");
    const $input       = document.getElementById("query-input");
    const $sendBtn     = document.getElementById("btn-send");
    const $clearBtn    = document.getElementById("btn-clear");
    const $kSelector   = document.getElementById("k-selector");

    // Upload
    const $dropzone      = document.getElementById("dropzone");
    const $fileInput     = document.getElementById("file-input");
    const $fileQueue     = document.getElementById("file-queue");
    const $fileQueueList = document.getElementById("file-queue-list");
    const $btnUpload     = document.getElementById("btn-upload");
    const $btnClearQueue = document.getElementById("btn-clear-queue");
    const $uploadResult  = document.getElementById("upload-result");
    const $btnReindex    = document.getElementById("btn-reindex");

    // Nav
    const $navDot        = document.getElementById("nav-dot");
    const $navStatusText = document.getElementById("nav-status-text");

    // File Filter (in chat)
    const $btnFileFilter   = document.getElementById("btn-file-filter");
    const $fileFilterPanel = document.getElementById("file-filter-panel");
    const $fileFilterList  = document.getElementById("file-filter-list");
    const $filterCount     = document.getElementById("filter-count");
    const $btnSelectAll    = document.getElementById("btn-select-all");
    const $btnSelectNone   = document.getElementById("btn-select-none");

    // ════════════════════════════════════════════════════════════
    //  STATE
    // ════════════════════════════════════════════════════════════
    let isProcessing  = false;
    let chatHistory   = [];
    let pendingFiles  = [];
    let selectedFiles = new Set();  // archivos seleccionados para filtro (vacío = todos)
    let allFiles      = [];         // lista de {name, type, size_kb} del backend

    // Configure Marked.js
    if (typeof marked !== "undefined") {
        marked.setOptions({ breaks: true, gfm: true });
    }

    // ════════════════════════════════════════════════════════════
    //  NAVIGATION
    // ════════════════════════════════════════════════════════════

    function navigateTo(viewName) {
        // Hide all views
        document.querySelectorAll(".view").forEach(v => v.classList.remove("view--active"));
        // Show target view
        const target = document.getElementById("view-" + viewName);
        if (target) target.classList.add("view--active");

        // Update nav links
        document.querySelectorAll(".navbar__link").forEach(l => {
            l.classList.toggle("active", l.dataset.view === viewName);
        });

        // Refresh data when navigating
        if (viewName === "dashboard") { checkHealth(); loadFiles(); }
        if (viewName === "upload") { loadCurrentFiles(); }
        if (viewName === "chat") { loadFilterFiles(); $input.focus(); }
    }

    // Click handlers for navigation (nav links, action cards, back buttons, brand)
    $app.addEventListener("click", (e) => {
        const navEl = e.target.closest("[data-view]");
        if (navEl) {
            e.preventDefault();
            navigateTo(navEl.dataset.view);
        }
    });


    // ════════════════════════════════════════════════════════════
    //  UTILITIES
    // ════════════════════════════════════════════════════════════

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function renderMarkdown(text) {
        if (typeof marked !== "undefined") return marked.parse(text);
        return escapeHtml(text).replace(/\n/g, "<br>");
    }

    function scrollToBottom() {
        requestAnimationFrame(() => { $messages.scrollTop = $messages.scrollHeight; });
    }

    function autoResize() {
        $input.style.height = "auto";
        $input.style.height = Math.min($input.scrollHeight, 150) + "px";
    }

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
        return (bytes / 1048576).toFixed(1) + " MB";
    }


    // ════════════════════════════════════════════════════════════
    //  CHAT — MESSAGE RENDERING
    // ════════════════════════════════════════════════════════════

    function hideWelcome() { if ($welcome) $welcome.style.display = "none"; }
    function showWelcome() { if ($welcome) $welcome.style.display = "flex"; }

    function addUserMessage(text) {
        hideWelcome();
        const div = document.createElement("div");
        div.className = "message message--user";
        div.innerHTML = `
            <div class="message__avatar">Tú</div>
            <div class="message__body">
                <div class="message__role">Tú</div>
                <div class="message__content"><p>${escapeHtml(text)}</p></div>
            </div>`;
        $messages.appendChild(div);
        scrollToBottom();
    }

    function addTypingIndicator() {
        const div = document.createElement("div");
        div.className = "message message--assistant";
        div.id = "typing-indicator";
        div.innerHTML = `
            <div class="message__avatar">DF</div>
            <div class="message__body">
                <div class="message__role">DocuFlow</div>
                <div class="message__content">
                    <div class="typing">
                        <div class="typing__dot"></div>
                        <div class="typing__dot"></div>
                        <div class="typing__dot"></div>
                    </div>
                </div>
            </div>`;
        $messages.appendChild(div);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById("typing-indicator");
        if (el) el.remove();
    }

    function buildSourcesHtml(sourceDetails) {
        if (!sourceDetails || sourceDetails.length === 0) return "";
        const uid = "src-" + Date.now();
        const items = sourceDetails.map(s => {
            const icon = s.doc_type === "pdf"
                ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`
                : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/></svg>`;
            const scorePercent = Math.round(s.score * 100);
            const snippet = s.snippet ? `<div class="source-item__snippet">${escapeHtml(s.snippet)}</div>` : "";
            return `
                <div class="source-item">
                    <div class="source-item__icon">${icon}</div>
                    <div>
                        <span class="source-item__name">${escapeHtml(s.filename)}</span>
                        <span class="source-item__type">${escapeHtml(s.doc_type)}</span>
                        ${snippet}
                    </div>
                    <span class="source-item__score">${scorePercent}%</span>
                </div>`;
        }).join("");

        return `
            <div class="message__sources">
                <button class="sources-toggle" data-target="${uid}" type="button">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    ${sourceDetails.length} fuente${sourceDetails.length > 1 ? "s" : ""} utilizada${sourceDetails.length > 1 ? "s" : ""}
                </button>
                <div class="sources-list" id="${uid}">${items}</div>
            </div>`;
    }

    function addAssistantMessage(answer, sourceDetails) {
        const div = document.createElement("div");
        div.className = "message message--assistant";
        div.innerHTML = `
            <div class="message__avatar">DF</div>
            <div class="message__body">
                <div class="message__role">DocuFlow</div>
                <div class="message__content">${renderMarkdown(answer)}</div>
                ${buildSourcesHtml(sourceDetails)}
            </div>`;
        $messages.appendChild(div);
        scrollToBottom();
    }

    function addErrorMessage(text) {
        const div = document.createElement("div");
        div.className = "message message--assistant message--error";
        div.innerHTML = `
            <div class="message__avatar">!</div>
            <div class="message__body">
                <div class="message__role">Error</div>
                <div class="message__content">${escapeHtml(text)}</div>
            </div>`;
        $messages.appendChild(div);
        scrollToBottom();
    }


    // ════════════════════════════════════════════════════════════
    //  API COMMUNICATION
    // ════════════════════════════════════════════════════════════

    async function sendQuery(query) {
        const k = parseInt($kSelector.value, 10);
        const body = { query, k };

        // Si hay archivos seleccionados (filtro activo), enviarlos
        if (selectedFiles.size > 0 && selectedFiles.size < allFiles.length) {
            body.files_filter = Array.from(selectedFiles);
        }

        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Error del servidor (HTTP ${response.status})`);
        }
        return response.json();
    }

    async function checkHealth() {
        const dotBackend = document.getElementById("dot-backend");
        const dotQdrant  = document.getElementById("dot-qdrant");
        const dotDocs    = document.getElementById("dot-docs");
        const lblBackend = document.getElementById("label-backend");
        const lblQdrant  = document.getElementById("label-qdrant");
        const lblDocs    = document.getElementById("label-docs");

        try {
            const res  = await fetch("/api/health");
            const data = await res.json();

            // Navbar status
            $navDot.className = "navbar__dot ok";
            $navStatusText.textContent = "Online";

            // Backend
            dotBackend.className = "status-dot ok";
            lblBackend.className = "status-label ok";
            lblBackend.textContent = "Online";

            // Qdrant
            if (data.qdrant === "connected") {
                dotQdrant.className = "status-dot ok";
                lblQdrant.className = "status-label ok";
                lblQdrant.textContent = "Conectado";
            } else {
                dotQdrant.className = "status-dot err";
                lblQdrant.className = "status-label err";
                lblQdrant.textContent = "Error";
            }

            // Docs
            if (data.documents_count > 0) {
                dotDocs.className = "status-dot ok";
                lblDocs.className = "status-label ok";
                lblDocs.textContent = `${data.documents_count}`;
            } else {
                dotDocs.className = "status-dot warn";
                lblDocs.className = "status-label warn";
                lblDocs.textContent = "Vacío";
            }

            // Tech info
            const infoLlm = document.getElementById("info-llm");
            const infoEmbed = document.getElementById("info-embed");
            const infoCol = document.getElementById("info-collection");
            if (infoLlm) infoLlm.textContent = data.llm_model || "—";
            if (infoEmbed) infoEmbed.textContent = data.embedding_model || "—";
            if (infoCol) infoCol.textContent = data.collection || "—";

        } catch {
            $navDot.className = "navbar__dot err";
            $navStatusText.textContent = "Offline";

            if (dotBackend) { dotBackend.className = "status-dot err"; lblBackend.className = "status-label err"; lblBackend.textContent = "Offline"; }
            if (dotQdrant)  { dotQdrant.className = "status-dot err"; lblQdrant.className = "status-label err"; lblQdrant.textContent = "—"; }
            if (dotDocs)    { dotDocs.className = "status-dot err"; lblDocs.className = "status-label err"; lblDocs.textContent = "—"; }
        }
    }

    async function loadFiles() {
        const container = document.getElementById("files-list-dashboard");
        if (!container) return;
        try {
            const res = await fetch("/api/files");
            const data = await res.json();
            if (!data.files || data.files.length === 0) {
                container.innerHTML = `<p class="text-muted">No hay archivos. Ve a "Subir Archivos" para añadir.</p>`;
                return;
            }
            container.innerHTML = data.files.map(f => {
                const icon = f.type === "pdf"
                    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`
                    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/></svg>`;
                return `
                    <div class="file-item">
                        <span class="file-item__icon">${icon}</span>
                        <span class="file-item__name">${escapeHtml(f.name)}</span>
                        <span class="file-item__type">${f.type.toUpperCase()}</span>
                        <span class="file-item__meta">${f.size_kb} KB</span>
                        <button class="file-item__delete" data-filename="${escapeHtml(f.name)}" title="Eliminar archivo">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        </button>
                    </div>`;
            }).join("");
        } catch {
            container.innerHTML = `<p class="text-muted">Error al cargar archivos.</p>`;
        }
    }

    async function loadCurrentFiles() {
        const container = document.getElementById("current-files-list");
        if (!container) return;
        try {
            const res = await fetch("/api/files");
            const data = await res.json();
            if (!data.files || data.files.length === 0) {
                container.innerHTML = `<p class="text-muted">No hay archivos en el directorio data/</p>`;
                return;
            }
            container.innerHTML = data.files.map(f => {
                const icon = f.type === "pdf"
                    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`
                    : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/></svg>`;
                return `
                    <div class="file-item">
                        <span class="file-item__icon">${icon}</span>
                        <span class="file-item__name">${escapeHtml(f.name)}</span>
                        <span class="file-item__type">${f.type.toUpperCase()}</span>
                        <span class="file-item__meta">${f.size_kb} KB</span>
                        <button class="file-item__delete" data-filename="${escapeHtml(f.name)}" title="Eliminar archivo">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                        </button>
                    </div>`;
            }).join("");
        } catch {
            container.innerHTML = `<p class="text-muted">Error al cargar archivos.</p>`;
        }
    }


    // ════════════════════════════════════════════════════════════
    //  CHAT HANDLERS
    // ════════════════════════════════════════════════════════════

    async function handleSubmit(e) {
        e.preventDefault();
        const query = $input.value.trim();
        if (!query || isProcessing) return;

        isProcessing = true;
        $sendBtn.disabled = true;
        $input.value = "";
        $input.style.height = "auto";

        addUserMessage(query);
        chatHistory.push({ role: "user", content: query });
        addTypingIndicator();

        try {
            const data = await sendQuery(query);
            removeTypingIndicator();
            addAssistantMessage(data.answer, data.source_details || []);
            chatHistory.push({ role: "assistant", content: data.answer, sources: data.sources });
        } catch (err) {
            removeTypingIndicator();
            addErrorMessage(err.message || "Error de conexión con el servidor.");
        } finally {
            isProcessing = false;
            $sendBtn.disabled = false;
            $input.focus();
        }
    }

    function handleClear() {
        chatHistory = [];
        const msgs = $messages.querySelectorAll(".message");
        msgs.forEach(m => m.remove());
        showWelcome();
    }


    // ════════════════════════════════════════════════════════════
    //  UPLOAD HANDLERS
    // ════════════════════════════════════════════════════════════

    function addFilesToQueue(fileList) {
        for (const f of fileList) {
            const ext = f.name.split(".").pop().toLowerCase();
            if (!["pdf", "csv"].includes(ext)) continue;
            if (pendingFiles.some(p => p.name === f.name)) continue;
            pendingFiles.push(f);
        }
        renderFileQueue();
    }

    function renderFileQueue() {
        if (pendingFiles.length === 0) {
            $fileQueue.style.display = "none";
            return;
        }
        $fileQueue.style.display = "block";
        $fileQueueList.innerHTML = pendingFiles.map((f, i) => {
            const ext = f.name.split(".").pop().toLowerCase();
            const icon = ext === "pdf"
                ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`
                : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/></svg>`;
            return `
                <div class="file-queue-item">
                    ${icon}
                    <span class="file-queue-item__name">${escapeHtml(f.name)}</span>
                    <span class="file-queue-item__size">${formatSize(f.size)}</span>
                    <button class="file-queue-item__remove" data-idx="${i}" type="button" title="Quitar">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    </button>
                </div>`;
        }).join("");
    }

    async function handleUpload() {
        if (pendingFiles.length === 0) return;

        $btnUpload.disabled = true;
        $btnUpload.innerHTML = `<span class="spinner"></span> Subiendo...`;
        $uploadResult.style.display = "none";

        const formData = new FormData();
        pendingFiles.forEach(f => formData.append("files", f));

        try {
            const res = await fetch("/api/upload", { method: "POST", body: formData });
            const data = await res.json();

            if (res.ok) {
                $uploadResult.className = "upload-result upload-result--success";
                $uploadResult.innerHTML = `<strong>${data.message}</strong>` +
                    (data.errors.length > 0 ? `<br>Advertencias: ${data.errors.join(", ")}` : "");
                $uploadResult.style.display = "block";
                pendingFiles = [];
                renderFileQueue();
                loadCurrentFiles();
                loadFiles();
            } else {
                $uploadResult.className = "upload-result upload-result--error";
                $uploadResult.innerHTML = `<strong>Error:</strong> ${data.detail || "Error desconocido"}`;
                $uploadResult.style.display = "block";
            }
        } catch (err) {
            $uploadResult.className = "upload-result upload-result--error";
            $uploadResult.innerHTML = `<strong>Error de conexión:</strong> ${err.message}`;
            $uploadResult.style.display = "block";
        } finally {
            $btnUpload.disabled = false;
            $btnUpload.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                Subir Archivos`;
        }
    }

    async function handleReindex() {
        $btnReindex.disabled = true;
        $btnReindex.innerHTML = `<span class="spinner"></span> Reindexando...`;

        try {
            const res = await fetch("/api/reindex", { method: "POST" });
            const data = await res.json();

            $uploadResult.style.display = "block";
            if (res.ok) {
                $uploadResult.className = "upload-result upload-result--success";
                $uploadResult.innerHTML = `<strong>${data.message}</strong>`;
                checkHealth();
                loadFiles();
            } else {
                $uploadResult.className = "upload-result upload-result--error";
                $uploadResult.innerHTML = `<strong>Error:</strong> ${data.detail || "Error desconocido"}`;
            }
        } catch (err) {
            $uploadResult.className = "upload-result upload-result--error";
            $uploadResult.innerHTML = `<strong>Error:</strong> ${err.message}`;
            $uploadResult.style.display = "block";
        } finally {
            $btnReindex.disabled = false;
            $btnReindex.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                Reindexar Ahora`;
        }
    }


    // ════════════════════════════════════════════════════════════
    //  FILE FILTER (chat view)
    // ════════════════════════════════════════════════════════════

    function toggleFilterPanel() {
        const visible = $fileFilterPanel.style.display !== "none";
        $fileFilterPanel.style.display = visible ? "none" : "block";
    }

    async function loadFilterFiles() {
        try {
            const res = await fetch("/api/files");
            const data = await res.json();
            allFiles = data.files || [];

            if (allFiles.length === 0) {
                $fileFilterList.innerHTML = `<p class="text-muted">No hay archivos indexados.</p>`;
                updateFilterCount();
                return;
            }

            // Si selectedFiles está vacío, seleccionar todos por defecto
            if (selectedFiles.size === 0) {
                allFiles.forEach(f => selectedFiles.add(f.name));
            }

            renderFilterList();
        } catch {
            $fileFilterList.innerHTML = `<p class="text-muted">Error al cargar archivos.</p>`;
        }
    }

    function renderFilterList() {
        $fileFilterList.innerHTML = allFiles.map(f => {
            const checked = selectedFiles.has(f.name) ? "checked" : "";
            const icon = f.type === "pdf"
                ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`
                : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#3fb950" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/></svg>`;
            return `
                <label class="file-filter-item">
                    <input type="checkbox" value="${escapeHtml(f.name)}" ${checked}>
                    ${icon}
                    <span class="file-filter-item__name">${escapeHtml(f.name)}</span>
                    <span class="file-filter-item__type">${f.type.toUpperCase()}</span>
                    <span class="file-filter-item__meta">${f.size_kb} KB</span>
                </label>`;
        }).join("");
        updateFilterCount();
    }

    function updateFilterCount() {
        const total = allFiles.length;
        const selected = selectedFiles.size;
        const allSelected = selected === 0 || selected >= total;

        if (allSelected) {
            $filterCount.textContent = `Todos los archivos seleccionados (${total})`;
            $btnFileFilter.classList.remove("btn-icon--filter-active");
        } else {
            $filterCount.textContent = `${selected} de ${total} archivo${total > 1 ? "s" : ""} seleccionado${selected > 1 ? "s" : ""}`;
            $btnFileFilter.classList.add("btn-icon--filter-active");
        }
    }

    function handleFilterChange(e) {
        if (e.target.type !== "checkbox") return;
        const name = e.target.value;
        if (e.target.checked) {
            selectedFiles.add(name);
        } else {
            selectedFiles.delete(name);
        }
        updateFilterCount();
    }

    function selectAllFiles() {
        selectedFiles.clear();
        allFiles.forEach(f => selectedFiles.add(f.name));
        renderFilterList();
    }

    function selectNoFiles() {
        selectedFiles.clear();
        renderFilterList();
    }


    // ════════════════════════════════════════════════════════════
    //  DELETE FILE
    // ════════════════════════════════════════════════════════════

    async function deleteFile(filename) {
        if (!confirm(`¿Eliminar "${filename}"? Deberás reindexar después.`)) return;

        try {
            const res = await fetch(`/api/files/${encodeURIComponent(filename)}`, {
                method: "DELETE",
            });
            const data = await res.json();

            if (res.ok) {
                // Quitar del filtro si estaba seleccionado
                selectedFiles.delete(filename);
                allFiles = allFiles.filter(f => f.name !== filename);
                renderFilterList();
                loadFiles();
                loadCurrentFiles();
            } else {
                alert(data.detail || "Error al eliminar.");
            }
        } catch (err) {
            alert("Error de conexión: " + err.message);
        }
    }


    // ════════════════════════════════════════════════════════════
    //  EVENT LISTENERS
    // ════════════════════════════════════════════════════════════

    // Chat
    $form.addEventListener("submit", handleSubmit);
    $input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(e); }
    });
    $input.addEventListener("input", autoResize);
    $clearBtn.addEventListener("click", handleClear);

    // Sources & Suggestions (delegated)
    $messages.addEventListener("click", (e) => {
        const btn = e.target.closest(".sources-toggle");
        if (btn) {
            const list = document.getElementById(btn.dataset.target);
            if (list) { btn.classList.toggle("open"); list.classList.toggle("open"); }
            return;
        }
        const sug = e.target.closest(".suggestion");
        if (sug && sug.dataset.query) {
            $input.value = sug.dataset.query;
            autoResize();
            handleSubmit(new Event("submit"));
        }
    });

    // Upload — Dropzone
    $dropzone.addEventListener("click", () => $fileInput.click());
    $fileInput.addEventListener("change", () => {
        addFilesToQueue($fileInput.files);
        $fileInput.value = "";
    });

    $dropzone.addEventListener("dragover", (e) => { e.preventDefault(); $dropzone.classList.add("drag-over"); });
    $dropzone.addEventListener("dragleave", () => $dropzone.classList.remove("drag-over"));
    $dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        $dropzone.classList.remove("drag-over");
        addFilesToQueue(e.dataTransfer.files);
    });

    // File queue remove
    $fileQueueList.addEventListener("click", (e) => {
        const btn = e.target.closest(".file-queue-item__remove");
        if (btn) {
            const idx = parseInt(btn.dataset.idx, 10);
            pendingFiles.splice(idx, 1);
            renderFileQueue();
        }
    });

    $btnUpload.addEventListener("click", handleUpload);
    $btnClearQueue.addEventListener("click", () => { pendingFiles = []; renderFileQueue(); });
    $btnReindex.addEventListener("click", handleReindex);

    // File Filter
    $btnFileFilter.addEventListener("click", toggleFilterPanel);
    $fileFilterList.addEventListener("change", handleFilterChange);
    $btnSelectAll.addEventListener("click", selectAllFiles);
    $btnSelectNone.addEventListener("click", selectNoFiles);

    // Delete file (delegated on any .file-item__delete buttons)
    document.addEventListener("click", (e) => {
        const delBtn = e.target.closest(".file-item__delete");
        if (delBtn && delBtn.dataset.filename) {
            e.stopPropagation();
            deleteFile(delBtn.dataset.filename);
        }
    });


    // ════════════════════════════════════════════════════════════
    //  INIT
    // ════════════════════════════════════════════════════════════

    checkHealth();
    loadFiles();
    setInterval(checkHealth, 30_000);

})();
