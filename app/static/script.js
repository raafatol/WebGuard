
"use strict";

// =========================================
// ELEMENTOS DEL ANALIZADOR
// =========================================

const analyzeForm = document.getElementById("analyze-form");
const domainInput = document.getElementById("domain");
const analyzeBtn = document.getElementById("analyze-btn");
const message = document.getElementById("message");
const results = document.getElementById("results");

const resultDomain = document.getElementById("result-domain");
const tlsStatus = document.getElementById("tls-status");
const tlsExpiry = document.getElementById("tls-expiry");
const httpStatus = document.getElementById("http-status");
const headersCount = document.getElementById("headers-count");
const headersList = document.getElementById("headers-list");
const recommendationsList = document.getElementById(
    "recommendations-list"
);

// =========================================
// FUNCIONES AUXILIARES
// =========================================

function getErrorMessage(data, fallback) {
    return typeof data?.detail === "string"
        ? data.detail
        : fallback;
}

function setStatus(element, text, className = "") {
    element.textContent = text;
    element.className = className;
}

// =========================================
// MOSTRAR RESULTADOS
// =========================================

function displayTLS(tls) {
    if (tls.valid === true) {
        setStatus(tlsStatus, "Certificado TLS válido", "ok");

        const days = tls.days_left;

        tlsExpiry.textContent =
            Number.isFinite(days)
                ? `Días hasta la caducidad: ${days}`
                : "Caducidad no disponible";
    } else if (tls.valid === false) {
        setStatus(tlsStatus, "Certificado TLS no válido", "error");
        tlsExpiry.textContent = tls.error || "";
    } else {
        setStatus(tlsStatus, "Certificado TLS no comprobado", "warning");
        tlsExpiry.textContent = tls.error || "No se pudo verificar el certificado.";
    }
}

function displayHTTP(http) {
    const status = http.http_status ?? http.status_code;

    httpStatus.textContent =
        status != null
            ? `Código HTTP: ${status}`
            : (http.error || "Respuesta HTTP no disponible");

    const headers = http.headers || {};

    const present = http.present_count ??
        Object.values(headers).filter(item =>
            item && item.present === true
        ).length;

    const total = http.total_headers ??
        Object.keys(headers).length;

    headersCount.textContent = `${present}/${total}`;

    headersList.replaceChildren();

    for (const [name, info] of Object.entries(headers)) {
        const item = document.createElement("div");
        item.className = "header-item";

        const label = document.createElement("strong");
        label.textContent = name;

        const statusText = document.createElement("span");
        
        if (info?.present === true) {
            statusText.textContent = info.value
                ? `Detectada: ${info.value}`
                : "Detectada";
            statusText.className = "ok";

        } else if (info?.present === false) {
            statusText.textContent = "No detectada";
            statusText.className = "warning";

        } else {
            statusText.textContent = "No comprobada";
            statusText.className = "warning";
        }

        item.append(label, statusText);
        headersList.appendChild(item);
    }
}


function displayRecommendations(recommendations) {
    recommendationsList.replaceChildren();

    for (const recommendation of recommendations || []) {
        const details = document.createElement("details");
        details.className = "recommendation-item";

        const summary = document.createElement("summary");

        const title = document.createElement("span");
        title.textContent =
            recommendation.title ||
            recommendation.header ||
            "Recomendación";

        const indicator = document.createElement("span");

        // Distinguimos los tres estados posibles.
        if (recommendation.status === "present") {
            indicator.textContent = "Detectada";
            indicator.className = "ok";

        } else if (recommendation.status === "missing") {
            indicator.textContent = "No detectada";
            indicator.className = "warning";

        } else {
            indicator.textContent = "No comprobada";
            indicator.className = "warning";
        }

        summary.append(title, indicator);

        const description = document.createElement("p");
        description.textContent =
            recommendation.description || "";

        const advice = document.createElement("p");

        if (recommendation.status === "unknown") {
            advice.textContent =
                "No se ha podido comprobar esta cabecera. " +
                "Intenta realizar el análisis de nuevo.";

        } else if (recommendation.recommendation) {
            advice.textContent =
                `Recomendación: ${recommendation.recommendation}`;

        } else {
            advice.textContent =
                "No se requiere ninguna recomendación específica " +
                "para esta cabecera.";
        }

        details.append(summary, description, advice);
        recommendationsList.appendChild(details);
    }
}

const monitorResultsPlaceholder = document.getElementById(
    "monitor-results-placeholder"
);

const monitorAnalysisGrid = document.querySelector(
    "#section-monitoring .monitor-analysis-grid"
);

analyzeForm.addEventListener("submit", async event => {
    event.preventDefault();

    const domain = domainInput.value.trim();
    if (!domain) return;

    analyzeBtn.disabled = true;
    results.hidden = true;
    monitorResultsPlaceholder.hidden = false;
    setStatus(message, "Analizando dominio...");

    try {
        const response = await fetch(
            `/analyze?domain=${encodeURIComponent(domain)}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(data, "No se pudo analizar el dominio")
            );
        }

        resultDomain.textContent = data.domain;
        displayTLS(data.tls || {});
        displayHTTP(data.http || {});
        displayRecommendations(data.recommendations);

        monitorResultsPlaceholder.hidden = true;
        results.hidden = false;

        monitorAnalysisGrid.classList.add("has-results");

        setStatus(message, "Análisis completado y guardado.", "ok");
                // Actualizar los datos de monitorización
        await Promise.all([
            loadDomains(),
            loadMonitoringStats(),
            loadClientStats(),
            loadAlerts()
        ]);

        // Actualizar el historial si está abierto
        if (
            !historyPanel.hidden &&
            historyDomain.textContent === data.domain
        ) {
            await loadHistory(data.domain);
        }
    } catch (error) {
        setStatus(message, error.message, "error");
    } finally {
        analyzeBtn.disabled = false;
    }
});

// =========================================
// DOMINIOS REGISTRADOS
// =========================================

const domainForm = document.getElementById("domain-form");
const newDomainInput = document.getElementById("new-domain");
const domainClientSelect = document.getElementById("domain-client");
const addDomainBtn = document.getElementById("add-domain-btn");
const domainMessage = document.getElementById("domain-message");
const domainsList = document.getElementById("domains-list");

function showDomainMessage(text, isError = false) {
    setStatus(domainMessage, text, isError ? "error" : "ok");
}

// =========================================
// MODAL DE ELIMINACIÓN
// =========================================

const deleteModal = document.getElementById("delete-modal");
const deleteDomainName = document.getElementById("delete-domain-name");
const cancelDeleteBtn = document.getElementById("cancel-delete-btn");
const confirmDeleteBtn = document.getElementById("confirm-delete-btn");

let pendingDelete = null;

function askDeleteConfirmation(domainName) {
    return new Promise(resolve => {
        deleteDomainName.textContent = domainName;
        pendingDelete = resolve;
        deleteModal.showModal();
    });
}

cancelDeleteBtn.addEventListener("click", () => {
    deleteModal.close();
});

confirmDeleteBtn.addEventListener("click", () => {
    if (pendingDelete) {
        const resolve = pendingDelete;
        pendingDelete = null;
        resolve(true);
    }

    deleteModal.close();
});

deleteModal.addEventListener("close", () => {
    if (pendingDelete) {
        const resolve = pendingDelete;
        pendingDelete = null;
        resolve(false);
    }
});

// =========================================
// HISTORIAL
// =========================================

const historyPanel = document.getElementById("history-panel");
const historyDomain = document.getElementById("history-domain");
const historyPlaceholder = document.getElementById(
    "monitor-history-placeholder"
);
const historyMessage = document.getElementById("history-message");
const historyBody = document.getElementById("history-body");
const closeHistoryBtn = document.getElementById("close-history-btn");

let historyRequestId = 0;

function formatDate(dateString) {
    if (!dateString) return "Fecha desconocida";

    // SQLite almacena CURRENT_TIMESTAMP en UTC.
    const date = new Date(
        dateString.replace(" ", "T") + "Z"
    );

    if (Number.isNaN(date.getTime())) {
        return dateString;
    }

    return date.toLocaleString("es-ES", {
        dateStyle: "short",
        timeStyle: "short"
    });
}

function createHistoryCell(row, text, className = "") {
    const cell = document.createElement("td");
    cell.textContent = text;

    if (className) {
        cell.className = className;
    }

    row.appendChild(cell);
}

async function loadHistory(domain) {
    const requestId = ++historyRequestId;

    historyPlaceholder.hidden = true;
    historyPanel.hidden = false;

    historyDomain.textContent = domain;
    historyBody.replaceChildren();
    setStatus(historyMessage, "Cargando historial...");

    try {
        const response = await fetch(
            `/history?domain=${encodeURIComponent(domain)}`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(data, "No se pudo cargar el historial")
            );
        }

        if (
            requestId !== historyRequestId ||
            historyPanel.hidden
        ) {
            return;
        }

        historyBody.replaceChildren();

        if (!Array.isArray(data) || data.length === 0) {
            setStatus(
                historyMessage,
                "Todavía no hay análisis guardados para este dominio."
            );
            return;
        }

        setStatus(
            historyMessage,
            `${data.length} análisis mostrados (máximo 50).`
        );

        for (const analysis of data) {
            const row = document.createElement("tr");

            createHistoryCell(
                row,
                formatDate(analysis.analyzed_at)
            );

            let tlsText = "No comprobado";
            let tlsClass = "history-unchecked";

            if (analysis.tls_valid === true) {
                tlsText = "Válido";
                tlsClass = "history-ok";
            } else if (analysis.tls_valid === false) {
                tlsText = "No válido";
                tlsClass = "history-error";
            }

            createHistoryCell(row, tlsText, tlsClass);

            createHistoryCell(
                row,
                analysis.http_status ?? "Sin datos"
            );

            const present = analysis.headers_present;
            const total = analysis.headers_total;

            const headersText =
                present != null && total != null
                    ? `${present}/${total}`
                    : "Sin datos";

            createHistoryCell(row, headersText);
            historyBody.appendChild(row);
        }

    } catch (error) {
        if (requestId === historyRequestId) {
            setStatus(historyMessage, error.message, "error");
        }
    }
}

closeHistoryBtn.addEventListener("click", () => {
    historyRequestId++;
    historyPanel.hidden = true;
    historyPlaceholder.hidden = false;
});

// =========================================
// CARGAR DOMINIOS
// =========================================

// =========================================
// TABLA DE DOMINIOS MONITORIZADOS
// =========================================

let monitoredDomains = [];

function createDomainCell(row, content, className = "") {
    const cell = document.createElement("td");

    if (className) {
        cell.className = className;
    }

    if (content instanceof Node) {
        cell.appendChild(content);
    } else {
        cell.textContent = content;
    }

    row.appendChild(cell);
    return cell;
}

function renderDomainsTable() {
    const filterInput = document.getElementById("monitor-domain-filter");
    const search = filterInput?.value.trim().toLowerCase() || "";

    domainsList.replaceChildren();

    const filteredDomains = monitoredDomains.filter(domain =>
        domain.domain.toLowerCase().includes(search) ||
        (domain.client_name || "").toLowerCase().includes(search)
    );

    if (filteredDomains.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 7;
        cell.className = "monitor-domains-empty";
        cell.textContent = monitoredDomains.length === 0
            ? "Todavía no has añadido dominios."
            : "No se encontraron dominios con esa búsqueda.";

        row.appendChild(cell);
        domainsList.appendChild(row);
        return;
    }

    for (const domain of filteredDomains) {
        const row = document.createElement("tr");
        const latest = domain.latest_analysis;

        // 1. Dominio
        const name = document.createElement("strong");
        name.className = "monitor-table-domain-name";
        name.textContent = domain.domain;
        createDomainCell(row, name);

        // 2. Cliente
        createDomainCell(
            row,
            domain.client_name || "Sin cliente",
            "monitor-table-client"
        );

        // 3. Estado TLS
        const tlsBadge = document.createElement("span");
        tlsBadge.className = "monitor-table-tls";

        if (!latest) {
            tlsBadge.textContent = "● Pendiente";
            tlsBadge.classList.add("status-unknown");
        } else if (latest.tls_valid === true) {
            tlsBadge.textContent = "● Válido";
            tlsBadge.classList.add("status-valid");
        } else if (latest.tls_valid === false) {
            tlsBadge.textContent = "● No válido";
            tlsBadge.classList.add("status-invalid");
        } else {
            tlsBadge.textContent = "● No comprobado";
            tlsBadge.classList.add("status-unchecked");
        }

        createDomainCell(row, tlsBadge);

        // 4. Último análisis
        createDomainCell(
            row,
            latest?.analyzed_at
                ? formatDate(latest.analyzed_at)
                : "Nunca",
            "monitor-table-date"
        );

        // 5. Respuesta HTTP
        const httpBadge = document.createElement("span");
        httpBadge.className = "monitor-http-badge";

        const httpStatus = latest?.http_status;

        if (httpStatus == null) {
            httpBadge.textContent = "Sin datos";
        } else {
            httpBadge.textContent = String(httpStatus);

            if (httpStatus >= 200 && httpStatus < 400) {
                httpBadge.classList.add("monitor-http-success");
            } else if (httpStatus >= 400 && httpStatus < 500) {
                httpBadge.classList.add("monitor-http-warning");
            } else if (httpStatus >= 500) {
                httpBadge.classList.add("monitor-http-error");
            }
        }

        createDomainCell(row, httpBadge);

        // 6. Cabeceras de seguridad
        const headersContainer = document.createElement("div");
        headersContainer.className = "monitor-headers-cell";

        const headersText = document.createElement("span");

        const present = latest?.headers_present;
        const total = latest?.headers_total;

        if (
            typeof present === "number" &&
            typeof total === "number" &&
            total > 0
        ) {
            headersText.textContent = `${present}/${total}`;

            const progress = document.createElement("div");
            progress.className = "monitor-headers-progress";

            const fill = document.createElement("div");
            fill.className = "monitor-headers-progress-fill";

            const percentage = Math.max(
                0,
                Math.min(100, (present / total) * 100)
            );

            fill.style.width = `${percentage}%`;

            progress.appendChild(fill);
            headersContainer.append(headersText, progress);
        } else {
            headersText.textContent = "Sin datos";
            headersContainer.appendChild(headersText);
        }

        createDomainCell(row, headersContainer);

        // 7. Acciones
        const actions = document.createElement("div");
        actions.className = "monitor-table-actions";

        const historyBtn = document.createElement("button");
        historyBtn.type = "button";
        historyBtn.className = "history-button";
        historyBtn.textContent = "Historial";

        historyBtn.addEventListener("click", () => {
            loadHistory(domain.domain);
        });

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "delete-domain-btn";
        deleteBtn.title = "Eliminar dominio";
        deleteBtn.setAttribute(
            "aria-label",
            `Eliminar ${domain.domain}`
        );

        deleteBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="17" height="17"
                 fill="none" stroke="currentColor"
                 stroke-width="1.8" stroke-linecap="round"
                 stroke-linejoin="round" aria-hidden="true">
                <path d="M3 6h18"/>
                <path d="M8 6V4h8v2"/>
                <path d="M5 6l1 15h12l1-15"/>
                <path d="M10 10v7"/>
                <path d="M14 10v7"/>
            </svg>
        `;

        deleteBtn.addEventListener("click", async () => {
            const confirmed = await askDeleteConfirmation(domain.domain);
            if (!confirmed) return;

            try {
                const response = await fetch(
                    `/domains/${domain.id}`,
                    { method: "DELETE" }
                );

                if (!response.ok) {
                    const data = await response.json();

                    throw new Error(
                        getErrorMessage(
                            data,
                            "No se pudo eliminar el dominio"
                        )
                    );
                }

                if (
                    !historyPanel.hidden &&
                    historyDomain.textContent === domain.domain
                ) {
                    historyRequestId++;
                    historyPanel.hidden = true;
                    historyPlaceholder.hidden = false;
                }

                showDomainMessage("Dominio eliminado correctamente.");

                // Actualizar los datos de monitorización y las alertas
                await Promise.all([
                    loadDomains(),
                    loadMonitoringStats(),
                    loadClientStats(),
                    loadAlerts()
                ]);

            } catch (error) {
                showDomainMessage(error.message, true);
            }
        });

        actions.append(historyBtn, deleteBtn);
        createDomainCell(row, actions);

        domainsList.appendChild(row);
    }
}

async function loadDomains() {
    try {
        const response = await fetch("/domains/status");

        if (!response.ok) {
            throw new Error("No se pudieron cargar los dominios");
        }

        const data = await response.json();

        if (!Array.isArray(data)) {
            throw new Error("La respuesta de dominios no es válida");
        }

        monitoredDomains = data;
        renderDomainsTable();

    } catch (error) {
        showDomainMessage(error.message, true);
    }
}

// =========================================
// AÑADIR DOMINIO
// =========================================

domainForm.addEventListener("submit", async event => {
    event.preventDefault();

    const domain = newDomainInput.value.trim();
    if (!domain) return;

    const clientId = domainClientSelect.value
    ? Number(domainClientSelect.value)
    : null;

    addDomainBtn.disabled = true;

    try {
        const response = await fetch("/domains", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                domain,
                client_id: clientId
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(data, "No se pudo añadir el dominio")
            );
        }

        newDomainInput.value = "";
        domainClientSelect.value = "";
        showDomainMessage("Dominio añadido correctamente.");

        await Promise.all([
            loadDomains(),
            loadMonitoringStats(),
            loadClientStats()
        ]);

    } catch (error) {
        showDomainMessage(error.message, true);
    } finally {
        addDomainBtn.disabled = false;
    }
});

// =========================================
// INICIALIZACIÓN
// =========================================

loadDomains();


/* =========================================
   WEBGUARD v0.6 - ALERTAS DE SEGURIDAD
   ========================================= */

const alertsList = document.getElementById("alerts-list");
const alertsMessage = document.getElementById("alerts-message");
const refreshAlertsBtn = document.getElementById("refresh-alerts-btn");


async function loadAlerts() {
    refreshAlertsBtn.disabled = true;
    alertsList.replaceChildren();

    setStatus(alertsMessage, "Cargando alertas...");

    try {
        const response = await fetch("/alerts");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(data, "No se pudieron cargar las alertas")
            );
        }

        if (!Array.isArray(data)) {
            throw new Error("La respuesta de alertas no es válida");
        }

        if (data.length === 0) {
            setStatus(
                alertsMessage,
                "No hay alertas registradas por el momento."
            );
            return;
        }

        setStatus(
            alertsMessage,
            `${data.length} alertas registradas (máximo 100).`
        );

        for (const alert of data) {

            // Tarjeta principal
            const item = document.createElement("article");
            item.className = "alert-item";

            const severity = alert.severity === "warning"
                ? "warning"
                : "info";

            item.classList.add(`alert-${severity}`);

            // Cabecera de la tarjeta
            const heading = document.createElement("div");
            heading.className = "alert-item-heading";

            const domain = document.createElement("strong");
            domain.className = "alert-item-domain";
            domain.textContent = alert.domain || "Dominio desconocido";

            const badge = document.createElement("span");
            badge.className = `alert-severity ${severity}`;
            badge.textContent = severity === "warning"
                ? "Advertencia"
                : "Información";

            heading.append(domain, badge);

            // Descripción
            const description = document.createElement("p");
            description.className = "alert-description";
            description.textContent =
                alert.message || "Cambio de seguridad detectado.";

            // Fecha
            const date = document.createElement("span");
            date.className = "alert-date";
            date.textContent = alert.created_at
                ? `Detectada: ${formatDate(alert.created_at)}`
                : "Fecha desconocida";

            item.append(heading, description, date);
            alertsList.appendChild(item);
        }

    } catch (error) {
        setStatus(alertsMessage, error.message, "error");

    } finally {
        refreshAlertsBtn.disabled = false;
    }
}


// Actualizar las alertas al pulsar el botón
refreshAlertsBtn.addEventListener("click", loadAlerts);


// Cargar las alertas al abrir WebGuard
loadAlerts();



/* =========================================
   WEBGUARD v0.8 - NAVEGACIÓN
========================================= */

const navigationButtons = document.querySelectorAll(
    ".sidebar .nav-item"
);

const appSections = document.querySelectorAll(
    ".app-section"
);

function navigateTo(section) {
    const targetSection = document.getElementById(
        `section-${section}`
    );

    if (!targetSection) {
        console.error(`Sección no encontrada: ${section}`);
        return;
    }

    // Ocultar todas las secciones excepto la seleccionada.
    appSections.forEach(panel => {
        panel.hidden = panel !== targetSection;
    });

    // Actualizar el botón activo.
    navigationButtons.forEach(button => {
        const isActive = button.dataset.section === section;

        button.classList.toggle("active", isActive);

        if (isActive) {
            button.setAttribute("aria-current", "page");
        } else {
            button.removeAttribute("aria-current");
        }
    });
}

// Registrar los eventos de navegación.
navigationButtons.forEach(button => {
    button.addEventListener("click", async () => {
        const section = button.dataset.section;

        navigateTo(section);

        // Actualizar los clientes y sus dominios
        // cada vez que se abre la pestaña Clientes.
        if (section === "clients") {
        await Promise.all([
            loadClients(),
            loadClientStats()
        ]);
    }
    });
});

// Mostrar Resumen al iniciar WebGuard.
navigateTo("overview");


/* =========================================
   WEBGUARD v0.8 — GESTIÓN DE CLIENTES
========================================= */

const clientForm = document.getElementById("client-form");
const toggleClientFormBtn = document.getElementById("toggle-client-form-btn");
const cancelClientFormBtn = document.getElementById("cancel-client-form-btn");
const clientFormContainer = document.getElementById("client-form-container");
const clientNameInput = document.getElementById("client-name");
const clientEmailInput = document.getElementById("client-email");
const createClientBtn = document.getElementById("create-client-btn");
const clientMessage = document.getElementById("client-message");
const clientsList = document.getElementById("clients-list");
const clientsSearchInput = document.getElementById("clients-search-input");


const editClientModal = document.getElementById("edit-client-modal");
const editClientForm = document.getElementById("edit-client-form");
const editClientNameInput = document.getElementById("edit-client-name");
const editClientEmailInput = document.getElementById("edit-client-email");
const editClientMessage = document.getElementById("edit-client-message");
const cancelEditClientBtn = document.getElementById(
    "cancel-edit-client-btn"
);
const saveEditClientBtn = document.getElementById(
    "save-edit-client-btn"
);

let editingClientId = null;


const deleteClientModal = document.getElementById("delete-client-modal");
const deleteClientName = document.getElementById("delete-client-name");
const deleteClientMessage = document.getElementById("delete-client-message");
const cancelDeleteClientBtn = document.getElementById(
    "cancel-delete-client-btn"
);
const confirmDeleteClientBtn = document.getElementById(
    "confirm-delete-client-btn"
);

let deletingClientId = null;

// Estadísticas generales de la sección Clientes
async function loadClientStats() {
    const totalElement = document.getElementById("clients-stat-total");
    const domainsElement = document.getElementById("clients-stat-domains");
    const issuesElement = document.getElementById("clients-stat-issues");

    try {
        const [clientsResponse, domainsResponse] = await Promise.all([
            fetch("/clients"),
            fetch("/domains/status")
        ]);

        if (!clientsResponse.ok || !domainsResponse.ok) {
            throw new Error("No se pudieron cargar las estadísticas");
        }

        const clients = await clientsResponse.json();
        const domains = await domainsResponse.json();

        if (!Array.isArray(clients) || !Array.isArray(domains)) {
            throw new Error("Datos de estadísticas no válidos");
        }

        const associatedDomains = domains.filter(
            domain => domain.client_id !== null && domain.client_id !== undefined
        );

        const tlsIssues = associatedDomains.filter(
            domain => domain.latest_analysis?.tls_valid === false
        );

        totalElement.textContent = clients.length;
        domainsElement.textContent = associatedDomains.length;
        issuesElement.textContent = tlsIssues.length;

    } catch (error) {
        console.error("Error al cargar estadísticas de clientes:", error);
        totalElement.textContent = "—";
        domainsElement.textContent = "—";
        issuesElement.textContent = "—";
    }
}

// Consultar los clientes registrados
async function loadClients() {
    clientsList.replaceChildren();

    const loading = document.createElement("p");
    loading.className = "clients-empty";
    loading.textContent = "Cargando clientes...";
    clientsList.appendChild(loading);

    try {
        const response = await fetch("/clients");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(data, "No se pudieron cargar los clientes")
            );
        }

        if (!Array.isArray(data)) {
            throw new Error("La respuesta de clientes no es válida");
        }

        clientsList.replaceChildren();

        // Filtrar por nombre o correo del cliente.
        const searchTerm = clientsSearchInput.value.trim().toLowerCase();

        const filteredClients = data.filter(client => {
            const name = (client.name || "").toLowerCase();
            const email = (client.email || "").toLowerCase();

            return name.includes(searchTerm) || email.includes(searchTerm);
        });

        if (data.length === 0) {
            const empty = document.createElement("p");
            empty.className = "clients-empty";
            empty.textContent = "Todavía no has registrado clientes.";
            clientsList.appendChild(empty);
            return;
        }

        if (filteredClients.length === 0) {
            const empty = document.createElement("p");
            empty.className = "clients-empty";
            empty.textContent = "No se encontraron clientes.";
            clientsList.appendChild(empty);
            return;
        }

        for (const client of filteredClients) {
            const item = document.createElement("div");
            item.className = "client-item";

            const details = document.createElement("div");
            details.className = "client-details";

            const name = document.createElement("strong");
            name.className = "client-item-name";
            name.textContent = client.name;


            const domainCounter = document.createElement("span");
            domainCounter.className = "client-domain-count";
            domainCounter.textContent = "Cargando...";

            const nameRow = document.createElement("div");
            nameRow.className = "client-name-row";
            nameRow.append(name, domainCounter);


            const email = document.createElement("p");
            email.className = "client-item-email";
            email.textContent = client.email || "Sin correo electrónico";

            
           details.append(nameRow, email);

            const actions = document.createElement("div");
            actions.className = "client-actions";

            const editBtn = document.createElement("button");
            editBtn.type = "button";
            editBtn.className = "client-edit-btn";
            editBtn.textContent = "Editar";

            const deleteBtn = document.createElement("button");
            deleteBtn.type = "button";
            deleteBtn.className = "client-delete-btn";
            deleteBtn.textContent = "Eliminar";

            
            editBtn.addEventListener("click", () => {
                editingClientId = client.id;

                editClientNameInput.value = client.name;
                editClientEmailInput.value = client.email || "";

                setStatus(editClientMessage, "");

                editClientModal.showModal();
                editClientNameInput.focus();
            });

            
            deleteBtn.addEventListener("click", () => {
                deletingClientId = client.id;
                deleteClientName.textContent = client.name;

                setStatus(deleteClientMessage, "");
                deleteClientModal.showModal();
            });

            
            actions.append(editBtn, deleteBtn);

            const clientHeader = document.createElement("div");
            clientHeader.className = "client-item-header";

            // Indicador visual del desplegable
            const expandIcon = document.createElement("span");
            expandIcon.className = "client-expand-icon";
            expandIcon.textContent = "⌄";
            expandIcon.setAttribute("aria-hidden", "true");

            // Zona pulsable para desplegar el cliente
            const toggleBtn = document.createElement("button");
            toggleBtn.type = "button";
            toggleBtn.className = "client-toggle-btn";
            toggleBtn.setAttribute("aria-expanded", "false");
            toggleBtn.setAttribute(
                "aria-label",
                `Mostrar dominios de ${client.name}`
            );

            toggleBtn.append(details, expandIcon);

            // Mantener los botones Editar y Eliminar independientes
            clientHeader.append(toggleBtn, actions);

            const domainsContainer = document.createElement("div");
            domainsContainer.className = "client-domains";
            domainsContainer.hidden = true;

            toggleBtn.addEventListener("click", () => {
                const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
                const nextExpanded = !expanded;

                domainsContainer.hidden = !nextExpanded;
                toggleBtn.setAttribute("aria-expanded", String(nextExpanded));

                toggleBtn.setAttribute(
                    "aria-label",
                    `${nextExpanded ? "Ocultar" : "Mostrar"} dominios de ${client.name}`
                );

                item.classList.toggle("expanded", nextExpanded);
            });

            item.append(clientHeader, domainsContainer);
            clientsList.appendChild(item);

            // Seguimos cargando los datos para actualizar el contador,
            // aunque los dominios estén inicialmente ocultos.
            loadClientDomains(client.id, domainsContainer);


        }

    } catch (error) {
        clientsList.replaceChildren();
        setStatus(clientMessage, error.message, "error");
    }
}

// Filtrar los clientes visibles mientras se escribe.
clientsSearchInput.addEventListener("input", () => {
    const searchTerm = clientsSearchInput.value.trim().toLowerCase();

    const clientItems = clientsList.querySelectorAll(".client-item");

    let visibleCount = 0;

    clientItems.forEach(item => {
        const name = item.querySelector(".client-item-name")?.textContent.toLowerCase() || "";
        const email = item.querySelector(".client-item-email")?.textContent.toLowerCase() || "";

        const matches = name.includes(searchTerm) || email.includes(searchTerm);

        item.hidden = !matches;

        if (matches) {
            visibleCount++;
        }
    });

    const previousMessage = clientsList.querySelector(".clients-search-empty");
    if (previousMessage) {
        previousMessage.remove();
    }

    if (clientItems.length > 0 && visibleCount === 0) {
        const empty = document.createElement("p");
        empty.className = "clients-empty clients-search-empty";
        empty.textContent = "No se encontraron clientes.";
        clientsList.appendChild(empty);
    }
});

// Abrir o cerrar el formulario de creación de clientes
function setClientFormExpanded(expanded) {
    clientFormContainer.hidden = !expanded;

    toggleClientFormBtn.setAttribute(
        "aria-expanded",
        String(expanded)
    );

    toggleClientFormBtn.textContent = expanded
        ? "− Ocultar formulario"
        : "+ Nuevo cliente";

    if (expanded) {
        clientNameInput.focus();
    }
}

toggleClientFormBtn.addEventListener("click", () => {
    const expanded = toggleClientFormBtn.getAttribute("aria-expanded") === "true";

    setClientFormExpanded(!expanded);
});

// Cancelar la creación
cancelClientFormBtn.addEventListener("click", () => {
    clientForm.reset();
    setStatus(clientMessage, "");
    setClientFormExpanded(false);
});

// Registrar un nuevo cliente
clientForm.addEventListener("submit", async event => {
    event.preventDefault();

    const name = clientNameInput.value.trim();
    const email = clientEmailInput.value.trim();

    if (!name) {
        setStatus(clientMessage, "Introduce el nombre del cliente.", "error");
        return;
    }

    createClientBtn.disabled = true;
    setStatus(clientMessage, "Creando cliente...");

    try {
        const response = await fetch("/clients", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name,
                email: email || null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(data, "No se pudo crear el cliente")
            );
        }

        clientForm.reset();

        await Promise.all([
            loadClients(),
            loadDomainClients(),
            loadClientStats()
        ]);

        setClientFormExpanded(false);

        setStatus(
            clientMessage,
            "Cliente creado correctamente.",
            "ok"
        );

    } catch (error) {
        setStatus(clientMessage, error.message, "error");
    } finally {
        createClientBtn.disabled = false;
    }
});

// Cargar clientes al iniciar WebGuard
loadClients();


/* =========================================
   WEBGUARD v0.8 — MODAL DE EDICIÓN
========================================= */

// Cancelar edición
cancelEditClientBtn.addEventListener("click", () => {
    editClientModal.close();
});

// Limpiar el cliente seleccionado al cerrar
editClientModal.addEventListener("close", () => {
    editingClientId = null;
    setStatus(editClientMessage, "");
});

// Guardar cambios
editClientForm.addEventListener("submit", async event => {
    event.preventDefault();

    if (editingClientId === null) return;

    const name = editClientNameInput.value.trim();
    const email = editClientEmailInput.value.trim();

    if (!name) {
        setStatus(
            editClientMessage,
            "El nombre del cliente no puede estar vacío.",
            "error"
        );
        return;
    }

    const clientId = editingClientId;

    saveEditClientBtn.disabled = true;
    cancelEditClientBtn.disabled = true;
    setStatus(editClientMessage, "Guardando cambios...");

    try {
        const response = await fetch(`/clients/${clientId}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name,
                email: email || null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    data,
                    "No se pudo actualizar el cliente"
                )
            );
        }

        editClientModal.close();

        await loadClients();
        await loadDomainClients();

        setStatus(
            clientMessage,
            "Cliente actualizado correctamente.",
            "ok"
        );

    } catch (error) {
        setStatus(editClientMessage, error.message, "error");
    } finally {
        saveEditClientBtn.disabled = false;
        cancelEditClientBtn.disabled = false;
    }
});


/* =========================================
   WEBGUARD v0.8 — SELECTOR DE CLIENTES
========================================= */

async function loadDomainClients() {
    const previousSelection = domainClientSelect.value;

    domainClientSelect.replaceChildren();

    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "Sin cliente asignado";
    domainClientSelect.appendChild(defaultOption);

    domainClientSelect.disabled = true;

    try {
        const response = await fetch("/clients");
        const clients = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    clients,
                    "No se pudieron cargar los clientes"
                )
            );
        }

        if (!Array.isArray(clients)) {
            throw new Error("La respuesta de clientes no es válida");
        }

        for (const client of clients) {
            const option = document.createElement("option");
            option.value = String(client.id);
            option.textContent = client.name;
            domainClientSelect.appendChild(option);
        }

        if (
            previousSelection &&
            [...domainClientSelect.options].some(
                option => option.value === previousSelection
            )
        ) {
            domainClientSelect.value = previousSelection;
        }

        domainClientSelect.disabled = false;

    } catch (error) {
        console.error("Error al cargar clientes:", error);
        showDomainMessage(error.message, true);
    }
}

loadDomainClients();


/* =========================================
   WEBGUARD v0.8 — ELIMINACIÓN DE CLIENTES
========================================= */

cancelDeleteClientBtn.addEventListener("click", () => {
    deleteClientModal.close();
});

deleteClientModal.addEventListener("close", () => {
    deletingClientId = null;
    setStatus(deleteClientMessage, "");
});

confirmDeleteClientBtn.addEventListener("click", async () => {
    if (deletingClientId === null) return;

    const clientId = deletingClientId;

    confirmDeleteClientBtn.disabled = true;
    cancelDeleteClientBtn.disabled = true;

    setStatus(deleteClientMessage, "Eliminando cliente...");

    try {
        const response = await fetch(`/clients/${clientId}`, {
            method: "DELETE"
        });

        if (!response.ok) {
            const data = await response.json();

            throw new Error(
                getErrorMessage(
                    data,
                    "No se pudo eliminar el cliente"
                )
            );
        }

        deleteClientModal.close();

        // Actualizar clientes, selectores y estadísticas
        await Promise.all([
            loadClients(),
            loadDomainClients(),
            loadClientStats()
        ]);

        setStatus(
            clientMessage,
            "Cliente eliminado correctamente.",
            "ok"
        );

    } catch (error) {
        setStatus(deleteClientMessage, error.message, "error");
    } finally {
        confirmDeleteClientBtn.disabled = false;
        cancelDeleteClientBtn.disabled = false;
    }
});



/* =========================================
   WEBGUARD v0.8 — DOMINIOS POR CLIENTE
========================================= */

async function loadClientDomains(clientId, container) {
    container.replaceChildren();

    const loading = document.createElement("p");
    loading.className = "client-domains-empty";
    loading.textContent = "Cargando dominios...";
    container.appendChild(loading);

    try {
        const response = await fetch(
            `/clients/${clientId}/domains`
        );

        const domains = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(
                    domains,
                    "No se pudieron cargar los dominios"
                )
            );
        }

        if (!Array.isArray(domains)) {
            throw new Error("Respuesta de dominios no válida");
        }


        const statusResponse = await fetch("/domains/status");

        if (!statusResponse.ok) {
            throw new Error(
                "No se pudieron cargar los estados de seguridad"
            );
        }

        const domainStatuses = await statusResponse.json();

        if (!Array.isArray(domainStatuses)) {
            throw new Error("Respuesta de estados no válida");
        }

        const statusById = new Map(
            domainStatuses.map(domain => [domain.id, domain.latest_analysis])
        );

        container.replaceChildren();


        // Actualizar el contador de dominios del cliente
        const clientCard = container.closest(".client-item");
        const domainCounter = clientCard?.querySelector(".client-domain-count");

        if (domainCounter) {
            const count = domains.length;
            domainCounter.textContent =
                `${count} ${count === 1 ? "dominio" : "dominios"}`;
        }


        if (domains.length === 0) {
            const empty = document.createElement("p");
            empty.className = "client-domains-empty";
            empty.textContent = "Este cliente todavía no tiene dominios.";
            container.appendChild(empty);
            return;
        }

        
    for (const domain of domains) {
        const item = document.createElement("div");
        item.className = "client-domain-item";

        // Icono y nombre del dominio
        const domainInfo = document.createElement("div");
        domainInfo.className = "client-domain-info";

        const icon = document.createElement("span");
        icon.textContent = "🌐";

        const name = document.createElement("strong");
        name.textContent = domain.domain;

        domainInfo.append(icon, name);

        // Botones de acciones
        const actions = document.createElement("div");
        actions.className = "client-domain-actions";

        const historyBtn = document.createElement("button");
        historyBtn.type = "button";
        historyBtn.className = "history-button";
        historyBtn.textContent = "Ver historial";

        historyBtn.addEventListener("click", () => {
            navigateTo("monitoring");
            loadHistory(domain.domain);
        });

        const deleteBtn = document.createElement("button");
        deleteBtn.type = "button";
        deleteBtn.className = "delete-domain-btn";
        deleteBtn.textContent = "Eliminar";

        deleteBtn.addEventListener("click", async () => {
            const confirmed = await askDeleteConfirmation(domain.domain);

            if (!confirmed) return;

            deleteBtn.disabled = true;
            historyBtn.disabled = true;

            try {
                const response = await fetch(
                    `/domains/${domain.id}`,
                    { method: "DELETE" }
                );

                if (!response.ok) {
                    const data = await response.json();

                    throw new Error(
                        getErrorMessage(
                            data,
                            "No se pudo eliminar el dominio"
                        )
                    );
                }

                // Cerrar su historial si está abierto
                if (
                    !historyPanel.hidden &&
                    historyDomain.textContent === domain.domain
                ) {
                    historyRequestId++;
                    historyPanel.hidden = true;
                }

                // Actualizar dominios y estadísticas de ambas pestañas
                await Promise.all([
                    loadDomains(),
                    loadMonitoringStats(),
                    loadClientStats()
                ]);

                await loadClientDomains(clientId, container);

                setStatus(
                    clientMessage,
                    "Dominio eliminado correctamente.",
                    "ok"
                );

            } catch (error) {
                setStatus(clientMessage, error.message, "error");
                deleteBtn.disabled = false;
                historyBtn.disabled = false;
            }
        });

        
            actions.append(historyBtn, deleteBtn);

            const latest = statusById.get(domain.id);

            const domainContent = document.createElement("div");
            domainContent.className = "client-domain-content";

            const metrics = document.createElement("div");
            metrics.className = "client-domain-metrics";

            const tlsBadge = document.createElement("span");
            tlsBadge.className = "domain-tls-badge";

            if (!latest) {
                tlsBadge.textContent = "Pendiente de análisis";
                tlsBadge.classList.add("status-unknown");
            } else if (latest.tls_valid === true) {
                tlsBadge.textContent = "TLS válido";
                tlsBadge.classList.add("status-valid");
            } else if (latest.tls_valid === false) {
                tlsBadge.textContent = "TLS no válido";
                tlsBadge.classList.add("status-invalid");
            } else {
                tlsBadge.textContent = "TLS no comprobado";
                tlsBadge.classList.add("status-unchecked");
            }

            domainInfo.appendChild(tlsBadge);

            metrics.append(
                createClientDomainMetric(
                    "Último análisis",
                    latest ? formatDate(latest.analyzed_at) : "Nunca"
                ),
                createClientDomainMetric(
                    "Respuesta HTTP",
                    latest?.http_status != null
                        ? String(latest.http_status)
                        : "Sin datos"
                ),
                createClientDomainMetric(
                    "Cabeceras detectadas",
                    latest?.headers_present != null &&
                    latest?.headers_total != null
                        ? `${latest.headers_present}/${latest.headers_total}`
                        : "Sin datos"
                )
            );

            domainContent.append(domainInfo, metrics);

            item.append(domainContent, actions);
            container.appendChild(item);

    }

    } catch (error) {
        container.replaceChildren();

        const errorText = document.createElement("p");
        errorText.className = "error";
        errorText.textContent = error.message;

        container.appendChild(errorText);
    }
}


function createClientDomainMetric(label, value) {
    const metric = document.createElement("div");
    metric.className = "domain-monitor-metric";

    const metricLabel = document.createElement("span");
    metricLabel.className = "metric-label";
    metricLabel.textContent = label;

    const metricValue = document.createElement("strong");
    metricValue.textContent = value;

    metric.append(metricLabel, metricValue);

    return metric;
}

/* =========================================
   WEBGUARD — ESTADÍSTICAS DEL DASHBOARD
========================================= */

const statDomains = document.getElementById("stat-domains");
const statSecure = document.getElementById("stat-secure");
const statAlerts = document.getElementById("stat-alerts");
const statClients = document.getElementById("stat-clients");

async function loadDashboard() {

    const stats = [
        statDomains,
        statSecure,
        statAlerts,
        statClients
    ];

    // Mostrar estado de carga.
    stats.forEach(element => {
        element.textContent = "…";
    });

    try {

        const endpoints = [
            "/domains/status",
            "/alerts",
            "/clients"
        ];

        const responses = await Promise.all(
            endpoints.map(endpoint => fetch(endpoint))
        );

        for (const response of responses) {
            if (!response.ok) {
                throw new Error(
                    "No se pudieron cargar las estadísticas"
                );
            }
        }

        const [domains, alerts, clients] = await Promise.all(
            responses.map(response => response.json())
        );

        if (
            !Array.isArray(domains) ||
            !Array.isArray(alerts) ||
            !Array.isArray(clients)
        ) {
            throw new Error(
                "Formato de respuesta no válido"
            );
        }

        const validTLS = domains.filter(domain =>
            domain.latest_analysis?.tls_valid === true
        ).length;

        statDomains.textContent = domains.length;
        statSecure.textContent = validTLS;
        statAlerts.textContent = alerts.length;
        statClients.textContent = clients.length;

        // =========================================
        // ACTIVIDAD RECIENTE DEL DASHBOARD
        // =========================================

        const activityList = document.getElementById(
            "dashboard-activity-list"
        );

        activityList.replaceChildren();

        if (domains.length === 0) {

            const empty = document.createElement("p");
            empty.className = "dashboard-empty";
            empty.textContent =
                "Todavía no hay dominios monitorizados. " +
                "Añade uno desde Monitorización para ver sus análisis aquí.";

            activityList.appendChild(empty);

        } else {

            const recentDomains = [...domains]
                .sort((a, b) => {
                    const dateA = a.latest_analysis?.analyzed_at || "";
                    const dateB = b.latest_analysis?.analyzed_at || "";

                    return dateB.localeCompare(dateA);
                })
                .slice(0, 5);

            const tableWrapper = document.createElement("div");
            tableWrapper.className = "dashboard-table-wrapper";

            const table = document.createElement("table");
            table.className = "dashboard-analysis-table";

            const thead = document.createElement("thead");
            const headerRow = document.createElement("tr");

            ["Dominio", "Estado", "TLS", "Cabeceras", "Fecha"].forEach(label => {
                const th = document.createElement("th");
                th.textContent = label;
                headerRow.appendChild(th);
            });

            thead.appendChild(headerRow);

            const tbody = document.createElement("tbody");

            for (const domain of recentDomains) {

                const analysis = domain.latest_analysis;
                const row = document.createElement("tr");

                // Dominio
                const domainCell = document.createElement("td");
                domainCell.className = "dashboard-domain-cell";
                domainCell.textContent = domain.domain;

                // Estado conocido
                const statusCell = document.createElement("td");
                const statusBadge = document.createElement("span");
                statusBadge.className = "dashboard-table-status";

                if (!analysis) {
                    statusBadge.textContent = "Pendiente";
                    statusBadge.classList.add("status-unknown");
                } else if (analysis.tls_valid === true) {
                    statusBadge.textContent = "TLS válido";
                    statusBadge.classList.add("status-valid");
                } else if (analysis.tls_valid === false) {
                    statusBadge.textContent = "TLS inválido";
                    statusBadge.classList.add("status-invalid");
                } else {
                    statusBadge.textContent = "Sin dato TLS";
                    statusBadge.classList.add("status-unknown");
                }

                statusCell.appendChild(statusBadge);

                // TLS
                const tlsCell = document.createElement("td");

                if (analysis?.tls_valid === true) {
                    tlsCell.textContent = "✓";
                    tlsCell.className = "dashboard-tls-valid";
                } else if (analysis?.tls_valid === false) {
                    tlsCell.textContent = "✕";
                    tlsCell.className = "dashboard-tls-invalid";
                } else {
                    tlsCell.textContent = "—";
                }

                // =========================================
                // CABECERAS DE SEGURIDAD
                // =========================================

                const headersCell = document.createElement("td");
                headersCell.className = "dashboard-headers-cell";

                const present = analysis?.headers_present;
                const total = analysis?.headers_total;

                if (
                    Number.isInteger(present) &&
                    Number.isInteger(total) &&
                    total > 0 &&
                    present >= 0 &&
                    present <= total
                ) {
                    const percentage = (present / total) * 100;

                    const container = document.createElement("div");
                    container.className = "dashboard-headers-container";

                    const progress = document.createElement("div");
                    progress.className = "dashboard-headers-progress";

                    const fill = document.createElement("div");
                    fill.className = "dashboard-headers-fill";
                    fill.style.width = `${percentage}%`;

                    const label = document.createElement("span");
                    label.className = "dashboard-headers-label";
                    label.textContent = `${present}/${total}`;
                    label.title = `${present} de ${total} cabeceras detectadas`;

                    progress.appendChild(fill);
                    container.append(progress, label);
                    headersCell.appendChild(container);

                } else {
                    headersCell.textContent = "—";
                    headersCell.classList.add("dashboard-muted-cell");
                }

                // Fecha
                const dateCell = document.createElement("td");
                dateCell.className = "dashboard-date-cell";

                if (analysis?.analyzed_at) {
                    const date = new Date(analysis.analyzed_at);

                    dateCell.textContent = Number.isNaN(date.getTime())
                        ? analysis.analyzed_at
                        : date.toLocaleString("es-ES", {
                            dateStyle: "short",
                            timeStyle: "short"
                        });
                } else {
                    dateCell.textContent = "Sin analizar";
                }

                row.append(
                    domainCell,
                    statusCell,
                    tlsCell,
                    headersCell,
                    dateCell
                );

                tbody.appendChild(row);
            }

            table.append(thead, tbody);
            tableWrapper.appendChild(table);
            activityList.appendChild(tableWrapper);
        }

    } catch (error) {

        console.error(
            "Error al cargar el dashboard:",
            error
        );

        stats.forEach(element => {
            element.textContent = "—";
        });

    }
}

// Cargar estadísticas al iniciar WebGuard.
loadDashboard();

// Actualizar al entrar en Resumen.
document.querySelector(
    '[data-section="overview"]'
).addEventListener("click", loadDashboard);

/* =========================================
   WEBGUARD — TÍTULO DINÁMICO
========================================= */

const topbarTitle = document.getElementById("topbar-title");

const sectionTitles = {
    overview: "Dashboard",
    monitoring: "Monitorización",
    clients: "Clientes",
    reports: "Informes",
    settings: "Configuración"
};

document.querySelectorAll(".sidebar .nav-item").forEach(button => {
    button.addEventListener("click", () => {
        const section = button.dataset.section;

        if (sectionTitles[section]) {
            topbarTitle.textContent = sectionTitles[section];
        }
    });
});

// Título inicial
topbarTitle.textContent = "Dashboard";

/* =========================================
   WEBGUARD — NOTIFICACIONES
========================================= */

const notificationsButton = document.getElementById("notifications-btn");
const notificationsPanel = document.getElementById("notifications-panel");
const notificationsCount = document.getElementById("notifications-count");
const notificationsMessage = document.getElementById("notifications-message");
const notificationsViewAlerts = document.getElementById("notifications-view-alerts");

async function loadNotifications() {
    try {
        const response = await fetch("/alerts");

        if (!response.ok) {
            throw new Error("No se pudieron cargar las alertas");
        }

        const alerts = await response.json();

        if (!Array.isArray(alerts)) {
            throw new Error("Respuesta de alertas no válida");
        }

        const count = alerts.length;

        notificationsCount.textContent = count > 99 ? "99+" : String(count);
        notificationsCount.hidden = count === 0;

        notificationsMessage.textContent = count === 0
            ? "No hay alertas registradas."
            : `Hay ${count} alerta${count === 1 ? "" : "s"} registrada${count === 1 ? "" : "s"}.`;

    } catch (error) {
        console.error("Error al cargar notificaciones:", error);
        notificationsCount.hidden = true;
        notificationsMessage.textContent = "No se pudieron cargar las alertas.";
    }
}

notificationsButton.addEventListener("click", async () => {
    const opening = notificationsPanel.hidden;

    notificationsPanel.hidden = !opening;
    notificationsButton.setAttribute("aria-expanded", String(opening));

    if (opening) {
        await loadNotifications();
    }
});

document.addEventListener("click", (event) => {
    if (!event.target.closest(".topbar-notifications")) {
        notificationsPanel.hidden = true;
        notificationsButton.setAttribute("aria-expanded", "false");
    }
});

notificationsViewAlerts.addEventListener("click", () => {
    notificationsPanel.hidden = true;
    notificationsButton.setAttribute("aria-expanded", "false");

    document.querySelector(
        '.sidebar .nav-item[data-section="monitoring"]'
    ).click();
});

loadNotifications();

/* =========================================
   WEBGUARD — MENÚ DE USUARIO
========================================= */

const accountButton = document.getElementById("account-btn");
const accountPanel = document.getElementById("account-panel");
const accountSettingsButton = document.getElementById("account-settings-btn");

accountButton.addEventListener("click", () => {
    const opening = accountPanel.hidden;

    accountPanel.hidden = !opening;
    accountButton.setAttribute("aria-expanded", String(opening));

    // Cerrar notificaciones si estaban abiertas.
    if (opening) {
        notificationsPanel.hidden = true;
        notificationsButton.setAttribute("aria-expanded", "false");
    }
});

document.addEventListener("click", (event) => {
    if (!event.target.closest(".topbar-account")) {
        accountPanel.hidden = true;
        accountButton.setAttribute("aria-expanded", "false");
    }
});

accountSettingsButton.addEventListener("click", () => {
    accountPanel.hidden = true;
    accountButton.setAttribute("aria-expanded", "false");

    const settingsNav = document.querySelector(
        '.sidebar [data-section="settings"]'
    );

    if (settingsNav) {
        settingsNav.click();
    }
});

/* =========================================
   WEBGUARD — CONFIGURACIÓN
========================================= */

const settingsCheckApi = document.getElementById("settings-check-api");
const settingsApiStatus = document.getElementById("settings-api-status");

settingsCheckApi.addEventListener("click", async () => {
    settingsApiStatus.textContent = "Comprobando...";
    settingsApiStatus.classList.remove("is-online", "is-offline");
    settingsCheckApi.disabled = true;

    try {
        const response = await fetch("/clients", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        settingsApiStatus.textContent = "Conectado";
        settingsApiStatus.classList.add("is-online");

    } catch (error) {
        console.error("Error al comprobar la API:", error);

        settingsApiStatus.textContent = "Sin conexión";
        settingsApiStatus.classList.add("is-offline");

    } finally {
        settingsCheckApi.disabled = false;
    }
});

/* =========================================
   WEBGUARD — ESTADÍSTICAS MONITORIZACIÓN
========================================= */

async function loadMonitoringStats() {
    const domainsElement = document.getElementById("monitor-stat-domains");
    const secureElement = document.getElementById("monitor-stat-secure");
    const issuesElement = document.getElementById("monitor-stat-issues");
    const recentElement = document.getElementById("monitor-stat-recent");

    try {
        const response = await fetch("/domains/status");

        if (!response.ok) {
            throw new Error("No se pudieron cargar las estadísticas");
        }

        const domains = await response.json();

        if (!Array.isArray(domains)) {
            throw new Error("Formato de dominios incorrecto");
        }

        const secure = domains.filter(
            domain => domain.latest_analysis?.tls_valid === true
        ).length;

        const issues = domains.filter(
            domain => domain.latest_analysis?.tls_valid === false
        ).length;

        const dates = domains
            .map(domain => domain.latest_analysis?.analyzed_at)
            .filter(Boolean)
            .map(date => new Date(date))
            .filter(date => !Number.isNaN(date.getTime()));

        const latestDate = dates.length
            ? new Date(Math.max(...dates.map(date => date.getTime())))
            : null;

        domainsElement.textContent = domains.length;
        secureElement.textContent = secure;
        issuesElement.textContent = issues;

        const total = domains.length;

        const securePercentage = total > 0
            ? Math.round((secure / total) * 100)
            : 0;

        const issuesPercentage = total > 0
            ? Math.round((issues / total) * 100)
            : 0;

        document.getElementById("monitor-secure-extra").textContent =
            `${securePercentage}%`;

        document.getElementById("monitor-issues-extra").textContent =
            `${issuesPercentage}%`;

        recentElement.textContent = latestDate
            ? latestDate.toLocaleDateString("es-ES", {
                day: "2-digit",
                month: "2-digit",
                year: "2-digit"
            })
            : "Sin análisis";

    } catch (error) {
        console.error("Error al cargar estadísticas:", error);

        domainsElement.textContent = "—";
        secureElement.textContent = "—";
        issuesElement.textContent = "—";
        recentElement.textContent = "—";
    }
}

loadMonitoringStats();

document.querySelector(
    '.sidebar [data-section="monitoring"]'
)?.addEventListener("click", loadMonitoringStats);

/* =========================================
   WEBGUARD — CONTROLES TABLA DOMINIOS
========================================= */

const monitorAddDomainToggle = document.getElementById(
    "monitor-show-add-domain"
);

const monitorAddDomainPanel = document.getElementById(
    "monitor-add-domain-panel"
);

monitorAddDomainToggle.addEventListener("click", () => {
    const willOpen = monitorAddDomainPanel.hidden;

    monitorAddDomainPanel.hidden = !willOpen;
    monitorAddDomainToggle.setAttribute(
        "aria-expanded",
        String(willOpen)
    );

    if (willOpen) {
        document.getElementById("new-domain").focus();
    }
});

// =========================================
// BUSCADOR DE DOMINIOS
// =========================================

document.getElementById("monitor-domain-filter")
    .addEventListener("input", renderDomainsTable);