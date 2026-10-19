/**
 * SIPEKA DF - Application Frontend Controller
 * Arsitektur: HTML murni untuk UI + Python (app.py) sebagai API backend logika.
 * Python menangani: ekstraksi PDF, komparasi data, validasi, riwayat, dan ekspor.
 * HTML/CSS/JS menangani: antarmuka pengguna, navigasi, filter, tampilan tabel & kartu.
 *
 * Semua ikon menggunakan SVG vector inline — tanpa emotikon.
 * UI responsif mobile-first dengan mode kartu & tabel yang bisa diswitch.
 */

// ==========================================================================
// Konstanta & State Global Sesi
// ==========================================================================

/**
 * BASE_API_URL: Titik akhir semua panggilan ke Python backend.
 * Selalu relatif (/api/...) karena Python server yang menyajikan HTML ini.
 * Jika suatu saat ingin akses dari port berbeda, ubah hanya di sini.
 */
const BASE_API_URL = "/api";

function getApiUrl(endpoint) {
    if (typeof window !== "undefined" && window.SIPEKA_API_BASE) {
        return window.SIPEKA_API_BASE + endpoint;
    }
    return BASE_API_URL + endpoint;
}

// State Global Sesi
const appState = {
    sessionStats: {
        examinationsCount: 0,
        rowsCompared: 0,
        matchedCount: 0,
        diffCount: 0,
        uncomparedCount: 0
    },
    mandorFile: null,
    kcsFile: null,
    currentComparison: null,
    mandorMeta: {},
    kcsMeta: {},
    mandorFilename: "",
    kcsFilename: "",
    mandorRawPreview: null,
    kcsRawPreview: null,
    filterStatus: "ALL",
    filterBlock: "ALL",
    searchQuery: "",
    onlyProblems: false,
    sortBy: "DEFAULT",
    viewMode: window.innerWidth <= 768 ? "cards" : "table"
};

// ==========================================================================
// Inisialisasi Aplikasi
// ==========================================================================
document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initMobileSidebar();
    initUploadDropzones();
    initFilterHandlers();
    initMobileViewSwitcher();
    loadHistoryList();
    updateDashboardStats();

    // Auto-adapt view mode pada resize window
    window.addEventListener("resize", () => {
        if (window.innerWidth > 768 && appState.viewMode === "cards") {
            setViewMode("table");
        }
    });
});

// Navigasi Tab Sidebar
function initNavigation() {
    const navLinks = document.querySelectorAll(".nav-link[data-tab]");
    navLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const targetTab = link.getAttribute("data-tab");
            switchTab(targetTab);
            closeMobileSidebar();
        });
    });

    const btnStart = document.getElementById("btn-goto-upload");
    if (btnStart) {
        btnStart.addEventListener("click", () => switchTab("upload"));
    }
}

// Mobile Sidebar Drawer
function initMobileSidebar() {
    const btnToggle = document.getElementById("btn-mobile-sidebar-toggle");
    const btnClose = document.getElementById("btn-sidebar-close");
    const backdrop = document.getElementById("sidebar-backdrop");
    const sidebar = document.getElementById("app-sidebar");

    if (btnToggle && sidebar && backdrop) {
        btnToggle.addEventListener("click", () => {
            sidebar.classList.add("show");
            backdrop.classList.add("show");
            document.body.style.overflow = "hidden";
        });
    }

    if (btnClose) {
        btnClose.addEventListener("click", closeMobileSidebar);
    }

    if (backdrop) {
        backdrop.addEventListener("click", closeMobileSidebar);
    }
}

function closeMobileSidebar() {
    const sidebar = document.getElementById("app-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (sidebar) sidebar.classList.remove("show");
    if (backdrop) backdrop.classList.remove("show");
    document.body.style.overflow = "";
}

function switchTab(tabId) {
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    document.querySelectorAll(".tab-section").forEach(s => s.classList.remove("active"));

    const activeLink = document.querySelector(`.nav-link[data-tab="${tabId}"]`);
    const activeSection = document.getElementById(`tab-${tabId}`);

    if (activeLink) activeLink.classList.add("active");
    if (activeSection) activeSection.classList.add("active");

    const titles = {
        dashboard: "Dashboard Utama",
        upload: "Pemeriksaan Data Baru",
        results: "Hasil Pemeriksaan Data",
        history: "Riwayat Pemeriksaan",
        guide: "Panduan Penggunaan",
        about: "Tentang Aplikasi SIPEKA DF"
    };
    const titleEl = document.getElementById("current-page-title");
    if (titleEl && titles[tabId]) {
        titleEl.textContent = titles[tabId];
    }
}

// Mobile View Switcher (Tabel vs Kartu)
function initMobileViewSwitcher() {
    const btnCards = document.getElementById("btn-view-cards");
    const btnTable = document.getElementById("btn-view-table");

    if (btnCards) {
        btnCards.addEventListener("click", () => setViewMode("cards"));
    }
    if (btnTable) {
        btnTable.addEventListener("click", () => setViewMode("table"));
    }
}

function setViewMode(mode) {
    appState.viewMode = mode;
    const btnCards = document.getElementById("btn-view-cards");
    const btnTable = document.getElementById("btn-view-table");
    const tableWrapper = document.getElementById("table-results-wrapper");
    const cardsContainer = document.getElementById("table-cards-container");

    if (btnCards && btnTable) {
        btnCards.classList.toggle("active", mode === "cards");
        btnTable.classList.toggle("active", mode === "table");
    }

    if (tableWrapper && cardsContainer) {
        if (mode === "cards") {
            tableWrapper.classList.add("hidden-view");
            cardsContainer.classList.add("active-view");
        } else {
            tableWrapper.classList.remove("hidden-view");
            cardsContainer.classList.remove("active-view");
        }
    }
}

// ==========================================================================
// Drag and Drop & File Upload Handling
// ==========================================================================
function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function initUploadDropzones() {
    setupZone("mandor", (file) => {
        appState.mandorFile = file;
        updateFileDisplay("mandor", file);
    });

    setupZone("kcs", (file) => {
        appState.kcsFile = file;
        updateFileDisplay("kcs", file);
    });

    const btnCompare = document.getElementById("btn-compare");
    if (btnCompare) {
        btnCompare.addEventListener("click", handleCompareSubmit);
    }
}

function setupZone(type, onFileSelected) {
    const zone = document.getElementById(`dropzone-${type}`);
    const input = document.getElementById(`file-input-${type}`);
    const removeBtn = document.getElementById(`btn-remove-${type}`);

    if (!zone || !input) return;

    zone.addEventListener("click", (e) => {
        if (e.target.closest(".btn-remove-file")) return;
        input.click();
    });

    input.addEventListener("change", () => {
        if (input.files && input.files[0]) {
            validateAndAssign(input.files[0], onFileSelected);
        }
    });

    // Drag events
    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("dragover");
    });

    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            validateAndAssign(e.dataTransfer.files[0], onFileSelected);
        }
    });

    if (removeBtn) {
        removeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (type === "mandor") appState.mandorFile = null;
            if (type === "kcs") appState.kcsFile = null;
            input.value = "";
            updateFileDisplay(type, null);
        });
    }
}

function validateAndAssign(file, callback) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        showAlert("danger", "Format file tidak didukung! Hanya file berekstensi .pdf yang diperbolehkan.");
        return;
    }
    if (file.size > 30 * 1024 * 1024) {
        showAlert("danger", "Ukuran file terlalu besar! Batas maksimum adalah 30 MB.");
        return;
    }
    callback(file);
}

function updateFileDisplay(type, file) {
    const badge = document.getElementById(`badge-file-${type}`);
    const nameEl = document.getElementById(`name-file-${type}`);
    const sizeEl = document.getElementById(`size-file-${type}`);
    const placeholder = document.getElementById(`placeholder-${type}`);
    const btnCompare = document.getElementById("btn-compare");

    if (file) {
        if (nameEl) nameEl.textContent = file.name;
        if (sizeEl) sizeEl.textContent = formatFileSize(file.size);
        if (badge) badge.classList.add("show");
        if (placeholder) placeholder.style.display = "none";
    } else {
        if (badge) badge.classList.remove("show");
        if (placeholder) placeholder.style.display = "block";
    }

    if (btnCompare) {
        btnCompare.disabled = !(appState.mandorFile && appState.kcsFile);
    }
}

// ==========================================================================
// API Bandingkan Data Submit
// ==========================================================================
async function handleCompareSubmit() {
    if (!appState.mandorFile || !appState.kcsFile) {
        showAlert("warning", "Harap unggah kedua file (Laporan Mandor & Laporan KCS) sebelum menekan tombol Bandingkan Data.");
        return;
    }

    const btnCompare = document.getElementById("btn-compare");
    const spinner = document.getElementById("compare-spinner");
    const btnText = document.getElementById("compare-btn-text");

    btnCompare.disabled = true;
    if (spinner) spinner.classList.remove("d-none");
    if (btnText) btnText.textContent = "Mengekstrak & Membandingkan...";

    const formData = new FormData();
    formData.append("mandor_file", appState.mandorFile);
    formData.append("kcs_file", appState.kcsFile);

    try {
        const url = getApiUrl("/upload-and-compare");
        const response = await fetch(url, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            let errorMsg = data.error || "Gagal memproses file PDF.";
            if (data.is_scanned) {
                errorMsg = "File PDF berupa gambar/scan murni tanpa teks digital. Dokumen memerlukan OCR sebelum dapat diproses.";
            }
            showAlert("danger", errorMsg);
            return;
        }

        // Simpan ke state
        appState.currentComparison = data.comparison;
        appState.mandorMeta = data.mandor_meta || {};
        appState.kcsMeta = data.kcs_meta || {};
        appState.mandorFilename = data.mandor_filename;
        appState.kcsFilename = data.kcs_filename;
        appState.mandorRawPreview = data.mandor_raw_preview;
        appState.kcsRawPreview = data.kcs_raw_preview;

        // Update sesi statistik
        appState.sessionStats.examinationsCount += 1;
        appState.sessionStats.rowsCompared += (data.comparison.total_rows_compared || 0);
        appState.sessionStats.matchedCount += (data.comparison.status_counts?.Cocok || 0);
        appState.sessionStats.diffCount += (data.comparison.status_counts?.Berbeda || 0);
        appState.sessionStats.uncomparedCount += (data.comparison.status_counts?.["Perlu Verifikasi"] || 0);

        updateDashboardStats();
        loadHistoryList();

        if (data.validation && data.validation.has_warnings) {
            showValidationWarningModal(data.validation);
        }

        renderResultsView();
        switchTab("results");
        showAlert("success", `Pemeriksaan selesai! Membandingkan ${data.comparison.total_rows_compared} baris data panen dan angkut.`);

    } catch (err) {
        console.error("Comparison error:", err);
        showAlert("danger", "Terjadi kesalahan saat menghubungkan ke mesin pemroses Python. Pastikan server lokal tetap berjalan.");
    } finally {
        btnCompare.disabled = false;
        if (spinner) spinner.classList.add("d-none");
        if (btnText) btnText.textContent = "Bandingkan Data";
    }
}

function showValidationWarningModal(validation) {
    const listEl = document.getElementById("validation-warnings-list");
    if (!listEl) return;

    listEl.innerHTML = "";
    validation.warnings.forEach(w => {
        const item = document.createElement("li");
        item.className = "mb-2";
        item.innerHTML = `<strong>${w.field}:</strong> ${w.message}`;
        listEl.appendChild(item);
    });

    const modalEl = document.getElementById("modalValidationWarning");
    if (modalEl && window.bootstrap) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

// ==========================================================================
// Render Tampilan Hasil Pemeriksaan
// ==========================================================================
function renderResultsView() {
    const comp = appState.currentComparison;
    if (!comp) return;

    // Header info metadata
    const tglEl = document.getElementById("res-meta-date");
    const kebunEl = document.getElementById("res-meta-kebun");
    const afdEl = document.getElementById("res-meta-afd");
    const mFileEl = document.getElementById("res-meta-mandor-file");
    const kFileEl = document.getElementById("res-meta-kcs-file");

    if (tglEl) tglEl.textContent = appState.mandorMeta.tanggal_aktivitas || appState.kcsMeta.tanggal_aktivitas || "-";
    if (kebunEl) kebunEl.textContent = appState.mandorMeta.kebun || appState.kcsMeta.kebun || "-";
    if (afdEl) afdEl.textContent = appState.mandorMeta.afdeling || appState.kcsMeta.afdeling || "-";
    if (mFileEl) mFileEl.textContent = appState.mandorFilename || "-";
    if (kFileEl) kFileEl.textContent = appState.kcsFilename || "-";

    // Ringkasan Kartu Selisih
    const counts = comp.status_counts || {};
    document.getElementById("res-stat-total-rows").textContent = comp.total_rows_compared || 0;
    document.getElementById("res-stat-cocok").textContent = counts.Cocok || 0;
    document.getElementById("res-stat-berbeda").textContent = counts.Berbeda || 0;
    document.getElementById("res-stat-verifikasi").textContent = counts["Perlu Verifikasi"] || 0;
    document.getElementById("res-stat-selisih-total").textContent = (comp.total_selisih >= 0 ? "+" : "") + (comp.total_selisih || 0);
    document.getElementById("res-stat-affected-blocks").textContent = comp.affected_blocks_count || 0;
    document.getElementById("res-stat-affected-workers").textContent = comp.affected_workers_count || 0;

    // Banner Offsetting Differences
    const offsetBanner = document.getElementById("offset-difference-banner");
    if (offsetBanner) {
        if (comp.has_offsetting_differences) {
            offsetBanner.classList.remove("d-none");
        } else {
            offsetBanner.classList.add("d-none");
        }
    }

    // Filter Blok
    const blockSelect = document.getElementById("filter-block-select");
    if (blockSelect) {
        blockSelect.innerHTML = '<option value="ALL">Semua Blok</option>';
        const uniqueBlocks = [...new Set(comp.results.map(r => r.blok).filter(b => b && b !== "-"))].sort();
        uniqueBlocks.forEach(blk => {
            const opt = document.createElement("option");
            opt.value = blk;
            opt.textContent = `Blok ${blk}`;
            blockSelect.appendChild(opt);
        });
    }

    renderBlockBreakdownTable(comp.block_breakdown || []);
    renderAdditionalAttributes(comp.additional_attributes || []);
    applyFiltersAndRenderTable();
}

function renderAdditionalAttributes(attributes) {
    const tbody = document.getElementById("tbody-additional-attributes");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (!attributes || attributes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-2">Tidak ada data atribut tambahan</td></tr>';
        return;
    }

    attributes.forEach(a => {
        let badgeClass = "badge-cocok";
        if (a.status === "Berbeda") badgeClass = "badge-berbeda";
        else if (a.status.includes("Tidak")) badgeClass = "badge-verifikasi";

        const mVal = a.mandor_value !== null && a.mandor_value !== undefined ? a.mandor_value : "-";
        const kVal = a.kcs_value !== null && a.kcs_value !== undefined ? a.kcs_value : "-";
        const diffVal = a.selisih !== null && a.selisih !== undefined ? `${a.selisih >= 0 ? "+" : ""}${a.selisih}` : "-";

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><strong>${a.attribute}</strong></td>
            <td class="text-end">${mVal}</td>
            <td class="text-end">${kVal}</td>
            <td class="text-end fw-bold text-white">${diffVal}</td>
            <td class="text-center"><span class="badge-status ${badgeClass}">${a.status}</span></td>
            <td><small class="text-secondary">${a.keterangan || "-"}</small></td>
        `;
        tbody.appendChild(tr);
    });
}

function openRawExtractionModal() {
    const mPrev = appState.mandorRawPreview || {};
    const kPrev = appState.kcsRawPreview || {};

    const mSum = mPrev.subtotals_info || {};
    const kSum = kPrev.subtotals_info || {};

    document.getElementById("raw-mandor-format").textContent = mPrev.detected_format || "-";
    document.getElementById("raw-mandor-rows").textContent = mPrev.total_production_extracted || "0";
    document.getElementById("raw-mandor-total").textContent = (appState.currentComparison?.total_mandor || 0) + " Janjang";
    document.getElementById("raw-mandor-gt").textContent = mSum.grand_total ? `${mSum.grand_total} Janjang` : "-";

    document.getElementById("raw-kcs-format").textContent = kPrev.detected_format || "-";
    document.getElementById("raw-kcs-rows").textContent = kPrev.total_production_extracted || "0";
    document.getElementById("raw-kcs-total").textContent = (appState.currentComparison?.total_kcs || 0) + " Janjang";
    document.getElementById("raw-kcs-gt").textContent = kSum.grand_total ? `${kSum.grand_total} Janjang` : "-";

    const renderMiniGrid = (grid, tableEl) => {
        if (!tableEl) return;
        tableEl.innerHTML = "";
        if (!grid || grid.length === 0) {
            tableEl.innerHTML = '<tr><td class="text-muted p-2">Tidak ada data pratinjau tabel</td></tr>';
            return;
        }
        grid.forEach((row, rIdx) => {
            const tr = document.createElement("tr");
            row.forEach(cell => {
                const td = document.createElement(rIdx <= 1 ? "th" : "td");
                td.textContent = cell !== null && cell !== undefined ? String(cell).slice(0, 25) : "";
                td.className = "p-1 border border-secondary border-opacity-25 text-nowrap";
                tr.appendChild(td);
            });
            tableEl.appendChild(tr);
        });
    };

    renderMiniGrid(mPrev.sample_grid, document.getElementById("raw-mandor-table"));
    renderMiniGrid(kPrev.sample_grid, document.getElementById("raw-kcs-table"));

    const modalEl = document.getElementById("modalRawExtraction");
    if (modalEl && window.bootstrap) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

function renderBlockBreakdownTable(breakdown) {
    const tbody = document.getElementById("tbody-block-breakdown");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (breakdown.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">Tidak ada data blok</td></tr>';
        return;
    }

    breakdown.forEach((b, idx) => {
        const isMatched = b.selisih === 0 && b.discrepancies === 0;
        const badgeClass = isMatched ? "badge-cocok" : "badge-verifikasi";
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="text-center">${idx + 1}</td>
            <td><strong>Blok ${b.blok}</strong></td>
            <td class="text-end">${b.mandor_total}</td>
            <td class="text-end">${b.kcs_total}</td>
            <td class="text-end text-white"><strong>${b.selisih >= 0 ? "+" : ""}${b.selisih}</strong></td>
            <td class="text-center"><span class="badge-status ${badgeClass}">${b.status}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// ==========================================================================
// Filter, Search, dan Render Tabel Utama & Kartu Mobile
// ==========================================================================
function initFilterHandlers() {
    const searchInput = document.getElementById("search-input-results");
    const statusSelect = document.getElementById("filter-status-select");
    const blockSelect = document.getElementById("filter-block-select");
    const btnToggleProblems = document.getElementById("btn-toggle-problems");
    const sortSelect = document.getElementById("sort-results-select");

    if (searchInput) {
        searchInput.addEventListener("input", (e) => {
            appState.searchQuery = e.target.value.trim().toLowerCase();
            applyFiltersAndRenderTable();
        });
    }

    if (statusSelect) {
        statusSelect.addEventListener("change", (e) => {
            appState.filterStatus = e.target.value;
            applyFiltersAndRenderTable();
        });
    }

    if (blockSelect) {
        blockSelect.addEventListener("change", (e) => {
            appState.filterBlock = e.target.value;
            applyFiltersAndRenderTable();
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener("change", (e) => {
            appState.sortBy = e.target.value;
            applyFiltersAndRenderTable();
        });
    }

    if (btnToggleProblems) {
        btnToggleProblems.addEventListener("click", () => {
            appState.onlyProblems = !appState.onlyProblems;
            btnToggleProblems.textContent = appState.onlyProblems ? "Tampilkan Semua Data" : "Tampilkan Hanya Data Bermasalah";
            btnToggleProblems.classList.toggle("btn-glass-outline-danger", appState.onlyProblems);
            applyFiltersAndRenderTable();
        });
    }

    const btnRawPrev = document.getElementById("btn-show-raw-preview");
    if (btnRawPrev) btnRawPrev.addEventListener("click", openRawExtractionModal);

    const btnCsv = document.getElementById("btn-export-csv");
    if (btnCsv) btnCsv.addEventListener("click", exportCSV);

    const btnPrint = document.getElementById("btn-export-print");
    if (btnPrint) btnPrint.addEventListener("click", exportPrintHTML);
}

function applyFiltersAndRenderTable() {
    const comp = appState.currentComparison;
    if (!comp || !comp.results) return;

    let filtered = [...comp.results];

    if (appState.onlyProblems) {
        filtered = filtered.filter(r => r.status !== "Cocok");
    }

    if (appState.filterStatus !== "ALL") {
        if (appState.filterStatus === "VERIFIKASI") {
            filtered = filtered.filter(r => r.status !== "Cocok");
        } else {
            filtered = filtered.filter(r => r.status === appState.filterStatus);
        }
    }

    if (appState.filterBlock !== "ALL") {
        filtered = filtered.filter(r => r.blok === appState.filterBlock);
    }

    if (appState.searchQuery) {
        filtered = filtered.filter(r => {
            const b = (r.blok || "").toLowerCase();
            const p = (r.kode_pekerja || "").toLowerCase();
            return b.includes(appState.searchQuery) || p.includes(appState.searchQuery);
        });
    }

    if (appState.sortBy === "DIFF_DESC") {
        filtered.sort((a, b) => {
            const diffA = a.selisih !== null ? Math.abs(a.selisih) : 9999;
            const diffB = b.selisih !== null ? Math.abs(b.selisih) : 9999;
            return diffB - diffA;
        });
    } else if (appState.sortBy === "BLOK_ASC") {
        filtered.sort((a, b) => (a.blok || "").localeCompare(b.blok || ""));
    }

    renderTableRows(filtered);
    renderMobileCards(filtered);
}

function getBadgeClass(status) {
    if (status === "Cocok") return "badge-cocok";
    if (status === "Berbeda") return "badge-berbeda";
    if (status === "Hanya Ada di Mandor" || status === "Hanya Ada di KCS") return "badge-hanya-mandor";
    if (status === "Data Tidak Lengkap" || status === "Duplikat") return "badge-incomplet";
    return "badge-verifikasi";
}

// Render Tabel Desktop / Horizontal Scroll
function renderTableRows(rows) {
    const tbody = document.getElementById("tbody-comparison-results");
    const countEl = document.getElementById("showing-rows-count");
    if (!tbody) return;

    if (countEl) countEl.textContent = rows.length;

    tbody.innerHTML = "";
    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">Tidak ada data yang sesuai dengan kriteria filter.</td></tr>';
        return;
    }

    rows.forEach((r, idx) => {
        const badgeClass = getBadgeClass(r.status);
        const mStr = r.data_mandor !== null ? r.data_mandor : '<span class="text-muted">-</span>';
        const kStr = r.data_kcs !== null ? r.data_kcs : '<span class="text-muted">-</span>';
        let diffStr = '<span class="text-muted">-</span>';
        if (r.selisih !== null) {
            const sign = r.selisih > 0 ? "+" : "";
            const color = r.selisih === 0 ? "text-success" : "text-danger";
            diffStr = `<span class="fw-bold ${color}">${sign}${r.selisih}</span>`;
        }

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="text-center text-muted">${idx + 1}</td>
            <td>${r.tanggal || "-"}</td>
            <td><strong class="text-white">Blok ${r.blok || "-"}</strong></td>
            <td><code class="text-info">${r.kode_pekerja || "-"}</code></td>
            <td class="text-end">${mStr}</td>
            <td class="text-end">${kStr}</td>
            <td class="text-end">${diffStr}</td>
            <td><span class="badge-status ${badgeClass}">${r.status}</span></td>
            <td><small class="text-secondary">${r.keterangan || "-"}</small></td>
        `;

        tr.addEventListener("click", () => openRowDetailModal(r));
        tbody.appendChild(tr);
    });
}

// Render Kartu Khusus Mobile (Meningkatkan kenyamanan di layar HP)
function renderMobileCards(rows) {
    const container = document.getElementById("table-cards-container");
    if (!container) return;

    container.innerHTML = "";
    if (rows.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">Tidak ada data yang sesuai dengan kriteria filter.</div>';
        return;
    }

    rows.forEach((r, idx) => {
        const badgeClass = getBadgeClass(r.status);
        const mStr = r.data_mandor !== null ? r.data_mandor : "-";
        const kStr = r.data_kcs !== null ? r.data_kcs : "-";
        let diffStr = "-";
        let diffColor = "text-white";
        if (r.selisih !== null) {
            const sign = r.selisih > 0 ? "+" : "";
            diffColor = r.selisih === 0 ? "text-success" : "text-danger";
            diffStr = `${sign}${r.selisih}`;
        }

        const card = document.createElement("div");
        card.className = "mobile-row-card";
        card.innerHTML = `
            <div class="mobile-card-header">
                <div class="mobile-card-title">
                    <span class="text-muted">#${idx + 1}</span>
                    <span>Blok ${r.blok || "-"}</span>
                    <code>${r.kode_pekerja || "-"}</code>
                </div>
                <span class="badge-status ${badgeClass}">${r.status}</span>
            </div>
            <div class="mobile-card-metrics">
                <div>
                    <div class="mobile-metric-label">Mandor</div>
                    <div class="mobile-metric-value">${mStr}</div>
                </div>
                <div>
                    <div class="mobile-metric-label">KCS</div>
                    <div class="mobile-metric-value">${kStr}</div>
                </div>
                <div>
                    <div class="mobile-metric-label">Selisih</div>
                    <div class="mobile-metric-value ${diffColor}">${diffStr}</div>
                </div>
            </div>
            <div class="mobile-card-footer">
                <span>${r.tanggal || "-"}</span>
                <span class="text-info">Detail &rarr;</span>
            </div>
        `;

        card.addEventListener("click", () => openRowDetailModal(r));
        container.appendChild(card);
    });
}

// Modal Rincian Baris
function openRowDetailModal(row) {
    document.getElementById("modal-detail-blok").textContent = row.blok || "-";
    document.getElementById("modal-detail-pekerja").textContent = row.kode_pekerja || "-";
    document.getElementById("modal-detail-tanggal").textContent = row.tanggal || "-";
    document.getElementById("modal-detail-mandor").textContent = row.data_mandor !== null ? `${row.data_mandor} Janjang` : "Kosong / Tidak Tercatat";
    document.getElementById("modal-detail-kcs").textContent = row.data_kcs !== null ? `${row.data_kcs} Janjang` : "Kosong / Tidak Tercatat";
    document.getElementById("modal-detail-selisih").textContent = row.selisih !== null ? `${row.selisih >= 0 ? "+" : ""}${row.selisih} Janjang` : "-";
    document.getElementById("modal-detail-status").textContent = row.status;
    document.getElementById("modal-detail-alasan").textContent = row.detail?.reason || row.keterangan || "-";

    const modalEl = document.getElementById("modalRowDetail");
    if (modalEl && window.bootstrap) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

// ==========================================================================
// Ekspor Data (CSV & Cetak)
// ==========================================================================
async function exportCSV() {
    if (!appState.currentComparison) return;

    try {
        const url = getApiUrl("/export/csv");
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                comparison_result: appState.currentComparison,
                mandor_meta: appState.mandorMeta,
                kcs_meta: appState.kcsMeta,
                mandor_file: appState.mandorFilename,
                kcs_file: appState.kcsFilename
            })
        });

        if (!response.ok) throw new Error("Gagal mengunduh CSV");

        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = `Hasil_Pemeriksaan_SIPEKA_DF_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(blobUrl);
    } catch (e) {
        showAlert("danger", "Gagal mengekspor CSV: " + e.message);
    }
}

async function exportPrintHTML() {
    if (!appState.currentComparison) return;

    try {
        const url = getApiUrl("/export/html");
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                comparison_result: appState.currentComparison,
                mandor_meta: appState.mandorMeta,
                kcs_meta: appState.kcsMeta,
                mandor_file: appState.mandorFilename,
                kcs_file: appState.kcsFilename
            })
        });

        if (!response.ok) throw new Error("Gagal membuat dokumen cetak");

        const htmlText = await response.text();
        const printWindow = window.open("", "_blank");
        if (printWindow) {
            printWindow.document.write(htmlText);
            printWindow.document.close();
        } else {
            showAlert("warning", "Popup browser terblokir. Harap izinkan popup untuk mencetak laporan.");
        }
    } catch (e) {
        showAlert("danger", "Gagal membuka halaman cetak: " + e.message);
    }
}

// ==========================================================================
// Riwayat Pemeriksaan
// ==========================================================================
async function loadHistoryList() {
    const tbody = document.getElementById("tbody-history-list");
    if (!tbody) return;

    try {
        const url = getApiUrl("/history");
        const response = await fetch(url);
        const data = await response.json();

        tbody.innerHTML = "";
        const history = data.history || [];

        if (history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Belum ada riwayat pemeriksaan yang tersimpan.</td></tr>';
            return;
        }

        history.forEach((h, idx) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="text-center text-muted">${idx + 1}</td>
                <td><strong class="text-white">${h.timestamp_display || h.timestamp}</strong></td>
                <td><small class="text-white">${h.mandor_filename}</small><br><small class="text-secondary">vs ${h.kcs_filename}</small></td>
                <td>${h.tanggal_laporan || "-"}</td>
                <td>${h.afdeling || "-"}</td>
                <td class="text-center"><span class="badge-status badge-cocok">${h.matched_count || 0}</span></td>
                <td class="text-center"><span class="badge-status badge-berbeda">${h.diff_count || 0}</span></td>
                <td class="text-end">
                    <button class="btn-glass-outline btn-glass-outline-success me-1 btn-open-history" data-id="${h.id}">Lihat</button>
                    <button class="btn-glass-outline btn-glass-outline-danger btn-delete-history" data-id="${h.id}">Hapus</button>
                </td>
            `;

            tr.querySelector(".btn-open-history").addEventListener("click", () => openHistoricalRecord(h));
            tr.querySelector(".btn-delete-history").addEventListener("click", () => deleteHistoricalRecord(h.id));

            tbody.appendChild(tr);
        });

    } catch (e) {
        console.error("Gagal memuat riwayat:", e);
    }
}

async function openHistoricalRecord(rec) {
    let target = rec;
    if (!target.comparison_result && target.id) {
        try {
            const url = getApiUrl(`/history/${target.id}`);
            const res = await fetch(url);
            const data = await res.json();
            if (data.success && data.record) {
                target = data.record;
            }
        } catch (e) {
            console.warn("Gagal fetch detail riwayat:", e);
        }
    }
    if (!target.comparison_result) {
        showAlert("warning", "Data perbandingan pada riwayat ini tidak tersedia.");
        return;
    }
    appState.currentComparison = target.comparison_result;
    appState.mandorMeta = target.mandor_meta || {};
    appState.kcsMeta = target.kcs_meta || {};
    appState.mandorFilename = target.mandor_filename;
    appState.kcsFilename = target.kcs_filename;

    renderResultsView();
    switchTab("results");
    showAlert("info", `Membuka riwayat pemeriksaan: ${target.timestamp_display || target.timestamp}`);
}

async function deleteHistoricalRecord(recId) {
    if (!confirm("Apakah Anda yakin ingin menghapus catatan riwayat pemeriksaan ini?")) return;

    try {
        const url = getApiUrl(`/history/${recId}`);
        const response = await fetch(url, { method: "DELETE" });
        if (response.ok) {
            showAlert("success", "Riwayat berhasil dihapus.");
            loadHistoryList();
        }
    } catch (e) {
        showAlert("danger", "Gagal menghapus riwayat.");
    }
}

const btnClearAllHistory = document.getElementById("btn-clear-all-history");
if (btnClearAllHistory) {
    btnClearAllHistory.addEventListener("click", async () => {
        if (!confirm("PERINGATAN: Apakah Anda yakin ingin menghapus SELURUH riwayat pemeriksaan? Tindakan ini tidak dapat dibatalkan.")) return;
        try {
            const url = getApiUrl("/history");
            const response = await fetch(url, { method: "DELETE" });
            if (response.ok) {
                showAlert("success", "Seluruh riwayat berhasil dikosongkan.");
                loadHistoryList();
            }
        } catch (e) {
            showAlert("danger", "Gagal mengosongkan riwayat.");
        }
    });
}

// ==========================================================================
// Dashboard Stats Updater
// ==========================================================================
function updateDashboardStats() {
    const s = appState.sessionStats;
    const elExam = document.getElementById("dash-stat-exam");
    const elRows = document.getElementById("dash-stat-rows");
    const elMatch = document.getElementById("dash-stat-match");
    const elDiff = document.getElementById("dash-stat-diff");
    const elUncomp = document.getElementById("dash-stat-uncomp");

    if (elExam) elExam.textContent = s.examinationsCount;
    if (elRows) elRows.textContent = s.rowsCompared;
    if (elMatch) elMatch.textContent = s.matchedCount;
    if (elDiff) elDiff.textContent = s.diffCount;
    if (elUncomp) elUncomp.textContent = s.uncomparedCount;

    const emptyNotice = document.getElementById("dash-empty-session-notice");
    const activeNotice = document.getElementById("dash-active-session-summary");
    if (emptyNotice && activeNotice) {
        if (s.examinationsCount === 0) {
            emptyNotice.classList.remove("d-none");
            activeNotice.classList.add("d-none");
        } else {
            emptyNotice.classList.add("d-none");
            activeNotice.classList.remove("d-none");
        }
    }
}

// ==========================================================================
// Toast / Alert Notification Helper
// ==========================================================================
function showAlert(type, message) {
    const container = document.getElementById("global-alert-container");
    if (!container) return;

    const alert = document.createElement("div");
    alert.className = `alert alert-${type} alert-dismissible fade show shadow-lg border-0`;
    alert.style.cssText = "font-size: 13px; background: rgba(14, 32, 24, 0.95); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.15) !important; color: #fff;";
    alert.role = "alert";
    alert.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            <div>${message}</div>
        </div>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Tutup"></button>
    `;

    container.appendChild(alert);

    setTimeout(() => {
        if (alert.parentNode) {
            alert.classList.remove("show");
            setTimeout(() => alert.remove(), 250);
        }
    }, 6000);
}
