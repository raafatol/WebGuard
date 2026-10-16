
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
        setStatus(tlsStatus, "Estado TLS no disponible", "warning");
        tlsExpiry.textContent = tls.error || "";
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

analyzeForm.addEventListener("submit", async event => {
    event.preventDefault();

    const domain = domainInput.value.trim();
    if (!domain) return;

    analyzeBtn.disabled = true;
    results.hidden = true;
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

        results.hidden = false;
        setStatus(message, "Análisis completado y guardado.", "ok");

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

            let tlsText = "Sin datos";
            let tlsClass = "history-neutral";

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
});

// =========================================
// CARGAR DOMINIOS
// =========================================

async function loadDomains() {
    domainsList.replaceChildren();

    try {
        const response = await fetch("/domains/status");
        const data = await response.json();

        if (!response.ok) {
            throw new Error("No se pudieron cargar los dominios");
        }

        if (!Array.isArray(data) || data.length === 0) {
            const empty = document.createElement("p");
            empty.textContent = "Todavía no has añadido dominios.";
            domainsList.appendChild(empty);
            return;
        }

        for (const domain of data) {
            
            const item = document.createElement("div");
            item.className = "domain-item domain-monitor-card";

            const info = document.createElement("div");
            info.className = "domain-monitor-info";

            const heading = document.createElement("div");
            heading.className = "domain-monitor-heading";

            const name = document.createElement("strong");
            name.textContent = domain.domain;

            const tlsBadge = document.createElement("span");
            tlsBadge.className = "domain-tls-badge";

            const latest = domain.latest_analysis;

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
                tlsBadge.textContent = "TLS sin datos";
                tlsBadge.classList.add("status-unknown");
            }

            heading.append(name, tlsBadge);
            info.appendChild(heading);

            const metrics = document.createElement("div");
            metrics.className = "domain-monitor-metrics";

            function addMetric(label, value) {
                const metric = document.createElement("div");
                metric.className = "domain-monitor-metric";

                const metricLabel = document.createElement("span");
                metricLabel.className = "metric-label";
                metricLabel.textContent = label;

                const metricValue = document.createElement("strong");
                metricValue.textContent = value;

                metric.append(metricLabel, metricValue);
                metrics.appendChild(metric);
            }

            if (latest) {
                addMetric(
                    "Último análisis",
                    formatDate(latest.analyzed_at)
                );

                addMetric(
                    "Respuesta HTTP",
                    latest.http_status != null
                        ? String(latest.http_status)
                        : "Sin datos"
                );

                addMetric(
                    "Caducidad TLS",
                    latest.tls_days_left != null
                        ? `${latest.tls_days_left} días`
                        : "Sin datos"
                );

                addMetric(
                    "Cabeceras detectadas",
                    latest.headers_present != null &&
                    latest.headers_total != null
                        ? `${latest.headers_present}/${latest.headers_total}`
                        : "Sin datos"
                );
            } else {
                addMetric("Último análisis", "Nunca");
                addMetric("Respuesta HTTP", "Sin datos");
                addMetric("Caducidad TLS", "Sin datos");
                addMetric("Cabeceras detectadas", "Sin datos");
            }

            info.appendChild(metrics);

            const actions = document.createElement("div");
            actions.className = "domain-actions";


            const historyBtn = document.createElement("button");
            historyBtn.type = "button";
            historyBtn.className = "history-button";
            historyBtn.textContent = "Ver historial";

            historyBtn.addEventListener("click", () => {
                loadHistory(domain.domain);
            });

            const deleteBtn = document.createElement("button");
            deleteBtn.type = "button";
            deleteBtn.className = "delete-domain-btn";
            deleteBtn.textContent = "Eliminar";

            deleteBtn.addEventListener("click", async () => {
                const confirmed = await askDeleteConfirmation(
                    domain.domain
                );

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
                    }

                    showDomainMessage("Dominio eliminado correctamente.");
                    await loadDomains();

                } catch (error) {
                    showDomainMessage(error.message, true);
                }
            });

            actions.append(historyBtn, deleteBtn);
            item.append(info, actions);
            domainsList.appendChild(item);
        }

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

    addDomainBtn.disabled = true;

    try {
        const response = await fetch("/domains", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ domain })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                getErrorMessage(data, "No se pudo añadir el dominio")
            );
        }

        newDomainInput.value = "";
        showDomainMessage("Dominio añadido correctamente.");
        await loadDomains();

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
