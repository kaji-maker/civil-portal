/**
 * Civil Portal - Citizen Dashboard Application Script
 * Developer: Antigravity-Frontend
 * Date: June 16, 2026
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

/// State Management
let allContracts = [];       // Cache all preloaded contracts for O(1) in-memory filtering
let filteredContracts = [];  // Currently filtered contracts subset
let currentFilterStatus = 'all'; // 'all', 'active', 'flagged'
let currentPage = 1;
const limitPerPage = 20;

// DOM Elements
const totalVolumeVal = document.getElementById('total-volume-value');
const activeTendersCount = document.getElementById('active-tenders-count');
const flaggedAlertsCount = document.getElementById('flagged-alerts-count');
const cardTotalVolume = document.getElementById('card-total-volume');
const cardActiveTenders = document.getElementById('card-active-tenders');
const cardFlaggedAlerts = document.getElementById('card-flagged-alerts');

const contractsLoader = document.getElementById('contracts-loader');
const leaderboardLoader = document.getElementById('leaderboard-loader');
const contractsGrid = document.getElementById('contracts-grid');
const leaderboardList = document.getElementById('leaderboard-list');
const noContractsMessage = document.getElementById('no-contracts-message');

const contractSearch = document.getElementById('contract-search');

const paginationControls = document.getElementById('pagination-controls');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const pageIndicator = document.getElementById('page-indicator');

// Helper: Translate Latin digits to Nepalese/Devanagari digits
function translateDigitsToNepalese(inputStr) {
    const latinToDevanagari = {
        '0': '०', '1': '१', '2': '२', '3': '३', '4': '४',
        '5': '५', '6': '६', '7': '७', '8': '८', '9': '९'
    };
    return inputStr.split('').map(char => latinToDevanagari[char] || char).join('');
}

// Helper: Format Currency to Nepalese Style
function formatNepaleseCurrency(amount) {
    const value = parseFloat(amount);
    if (isNaN(value)) return 'रू ०.००';
    
    // Format number using ne-NP locale
    let formatted = new Intl.NumberFormat('ne-NP', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
    
    // Map digits to Devanagari to ensure local representation
    formatted = translateDigitsToNepalese(formatted);
    return `रू ${formatted}`;
}

// Helper: Format large currency inputs into Crore / Lakh dynamically
function formatNepaleseCompactCurrency(amount) {
    const value = parseFloat(amount);
    if (isNaN(value)) return 'रू ०.००';
    
    let num, suffix;
    if (value >= 10000000) { // 1 Crore = 10,000,000 (10 million)
        num = value / 10000000;
        suffix = 'करोड';
    } else if (value >= 100000) { // 1 Lakh = 100,000
        num = value / 100000;
        suffix = 'लाख';
    } else {
        return formatNepaleseCurrency(value);
    }
    
    let formatted = num.toFixed(2);
    formatted = translateDigitsToNepalese(formatted);
    return `रू ${formatted} ${suffix}`;
}

// Helper: Format Dates Elegantly
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;
        return date.toLocaleDateString('ne-NP', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        return dateString;
    }
}

// Helper: Calculate remaining days
function getDaysRemaining(deadlineStr) {
    if (!deadlineStr) return 0;
    try {
        const deadline = new Date(deadlineStr);
        let today = new Date();
        const baseDate = new Date("2026-06-16T21:46:22");
        if (today < baseDate) {
            today = baseDate;
        }
        const diffTime = deadline - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays > 0 ? diffDays : 0;
    } catch (e) {
        return 0;
    }
}

// Calculate macro statistics (Total Volume, Active, Flagged)
function calculateMacroStats(contracts) {
    const totalVolume = contracts.reduce((sum, c) => sum + (parseFloat(c.amount_allocated) || 0), 0);
    const activeCount = contracts.filter(c => c.tender_status === 'OPEN').length;
    const flaggedCount = contracts.filter(c => c.is_red_flagged === true).length;

    // Animate stats counters
    if (totalVolumeVal) animateCounter(totalVolumeVal, totalVolume, false, true);
    if (activeTendersCount) animateCounter(activeTendersCount, activeCount, false, false);
    if (flaggedAlertsCount) animateCounter(flaggedAlertsCount, flaggedCount, false, false);
}

// Micro-animation for counter rolling (Devanagari support)
function animateCounter(element, targetValue, isCurrency, isCompactCurrency) {
    let start = 0;
    const duration = 1000; // 1 second animation
    const startTime = performance.now();

    function updateCounter(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const easeProgress = progress * (2 - progress); // easeOutQuad
        const currentValue = start + easeProgress * (targetValue - start);

        if (isCompactCurrency) {
            element.textContent = formatNepaleseCompactCurrency(currentValue);
        } else if (isCurrency) {
            element.textContent = formatNepaleseCurrency(currentValue);
        } else {
            const rawValString = Math.floor(currentValue).toLocaleString('ne-NP');
            element.textContent = translateDigitsToNepalese(rawValString);
        }

        if (progress < 1) {
            requestAnimationFrame(updateCounter);
        } else {
            // Guarantee final value is exact
            if (isCompactCurrency) {
                element.textContent = formatNepaleseCompactCurrency(targetValue);
            } else if (isCurrency) {
                element.textContent = formatNepaleseCurrency(targetValue);
            } else {
                element.textContent = translateDigitsToNepalese(targetValue.toString());
            }
        }
    }
    requestAnimationFrame(updateCounter);
}

// Update counts in the status toggle bar
function updateToggleBarCounts() {
    const totalCount = allContracts.length;
    const activeCount = allContracts.filter(c => c.tender_status === 'OPEN').length;
    const flaggedCount = allContracts.filter(c => c.is_red_flagged === true).length;

    const btnShowAll = document.getElementById('btn-show-all');
    const btnActiveBids = document.getElementById('btn-active-bids');
    const btnFlaggedAudits = document.getElementById('btn-flagged-audits');

    if (btnShowAll) btnShowAll.innerHTML = `Show All (${translateDigitsToNepalese(totalCount.toString())})`;
    if (btnActiveBids) btnActiveBids.innerHTML = `Active Bids (${translateDigitsToNepalese(activeCount.toString())})`;
    if (btnFlaggedAudits) btnFlaggedAudits.innerHTML = `Flagged Audits (${translateDigitsToNepalese(flaggedCount.toString())})`;
}

// Fetch all Contracts from Backend API on startup (Preloading)
async function fetchContracts() {
    // Show Loading Spinner
    contractsLoader.classList.remove('hidden');
    contractsGrid.classList.add('hidden');
    noContractsMessage.classList.add('hidden');
    paginationControls.classList.add('hidden');

    const url = `${API_BASE_URL}/contracts?limit=10000`;

    try {
        console.log(`[HTTP GET] Preloading all contracts from: ${url}`);
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const payload = await response.json();
        allContracts = payload.data || [];
        
        // Compute overall macro statistics
        calculateMacroStats(allContracts);
        
        // Update toggle bar buttons
        updateToggleBarCounts();

        // Apply filters
        applyClientSideFilters();
    } catch (error) {
        console.error('Failed to preload contracts:', error);
        showConnectionError(contractsGrid, contractsLoader, 'procurement records');
    }
}

// Map department/buyer names on the fly
function getDepartmentClassification(deptName) {
    if (!deptName) return 'other';
    const name = deptName.toLowerCase();
    if (name.includes('roads') || name.includes('dor')) {
        return 'DoR';
    }
    if (name.includes('electricity') || name.includes('nea')) {
        return 'NEA';
    }
    if (name.includes('telecom') || name.includes('ndcl')) {
        return 'NDCL';
    }
    if (name.includes('municipality') || name.includes('metropolitan') || name.includes('rural')) {
        return 'municipalities';
    }
    return 'other';
}

// Apply client-side status, search, and dynamic intelligence toolbar filters
function applyClientSideFilters() {
    const query = contractSearch.value.trim().toLowerCase();
    
    const selectDept = document.getElementById('select-dept');
    const selectYear = document.getElementById('select-year');
    const selectMonth = document.getElementById('select-month');
    
    const deptVal = selectDept ? selectDept.value : 'all';
    const yearVal = selectYear ? selectYear.value : 'all';
    const monthVal = selectMonth ? selectMonth.value : 'all';

    filteredContracts = allContracts.filter(contract => {
        // 1. Status Toggle Filter
        if (currentFilterStatus === 'active' && contract.tender_status !== 'OPEN') {
            return false;
        }
        if (currentFilterStatus === 'flagged' && !contract.is_red_flagged) {
            return false;
        }

        // 2. Department Filter
        if (deptVal !== 'all') {
            const classification = getDepartmentClassification(contract.ministry_department);
            if (classification !== deptVal) {
                return false;
            }
        }

        // Parse date for Year/Month matching
        const dateStr = contract.award_date || contract.submission_deadline;

        // 3. Year Filter
        if (yearVal !== 'all') {
            if (!dateStr) return false;
            const yearStr = dateStr.substring(0, 4);
            const year = parseInt(yearStr, 10);
            if (isNaN(year)) return false;
            
            if (yearVal === '2026' && year !== 2026) return false;
            if (yearVal === '2025' && year !== 2025) return false;
            if (yearVal === 'prior' && year >= 2025) return false;
        }

        // 4. Month Filter
        if (monthVal !== 'all') {
            if (!dateStr) return false;
            const parts = dateStr.split('-');
            if (parts.length < 2) return false;
            const month = parseInt(parts[1], 10);
            if (isNaN(month) || month !== parseInt(monthVal, 10)) {
                return false;
            }
        }

        // 5. Search Filter (Tender ID, Procuring Entity/Buyer, Contractor/Winner, Title)
        if (query) {
            const tenderId = (contract.tender_id || '').toLowerCase();
            const procuringEntity = (contract.ministry_department || '').toLowerCase();
            const contractorName = (contract.contractor_name || '').toLowerCase();
            const projectTitle = (contract.title || '').toLowerCase();

            return tenderId.includes(query) || 
                   procuringEntity.includes(query) || 
                   contractorName.includes(query) ||
                   projectTitle.includes(query);
        }

        return true;
    });

    // Recalculate summary metrics dynamically for the currently filtered subset
    calculateMacroStats(filteredContracts);

    renderFilteredContracts();
}

// Render paginated cards
function renderFilteredContracts() {
    const totalFiltered = filteredContracts.length;
    const totalPages = Math.ceil(totalFiltered / limitPerPage) || 1;

    if (currentPage > totalPages) {
        currentPage = totalPages;
    }

    const startIdx = (currentPage - 1) * limitPerPage;
    const endIdx = startIdx + limitPerPage;
    const paginatedContracts = filteredContracts.slice(startIdx, endIdx);

    if (totalFiltered === 0) {
        noContractsMessage.classList.remove('hidden');
        contractsGrid.classList.add('hidden');
        paginationControls.classList.add('hidden');
        return;
    }

    noContractsMessage.classList.add('hidden');
    contractsGrid.classList.remove('hidden');

    renderContractsGrid(paginatedContracts);
    renderPaginationControlsClientSide(totalFiltered, totalPages);
}

// Render pagination info client-side
function renderPaginationControlsClientSide(totalFiltered, totalPages) {
    if (totalFiltered <= limitPerPage) {
        paginationControls.classList.add('hidden');
        return;
    }

    paginationControls.classList.remove('hidden');
    
    const currentNep = translateDigitsToNepalese(currentPage.toString());
    const totalNep = translateDigitsToNepalese(totalPages.toString());
    pageIndicator.textContent = `पृष्ठ ${currentNep} / ${totalNep}`;
    
    prevBtn.disabled = (currentPage === 1);
    nextBtn.disabled = (currentPage === totalPages);
}

// Render Contracts Cards Grid
function renderContractsGrid(contractsToRender) {
    contractsLoader.classList.add('hidden');
    contractsGrid.innerHTML = '';

    contractsToRender.forEach((contract, index) => {
        const card = document.createElement('div');
        const isOpen = contract.tender_status === 'OPEN';
        
        // Add open/flagged/competitive classes
        card.className = `contract-card ${isOpen ? 'open' : (contract.is_red_flagged ? 'flagged' : 'competitive')}`;
        card.style.animation = `card-appear 0.4s ease forwards ${index * 0.03}s`;
        card.style.opacity = 0; // Handled by CSS keyframes animation

        // Dynamic Badges
        let flagIndicator = '';
        if (isOpen) {
            const daysRemaining = getDaysRemaining(contract.submission_deadline);
            flagIndicator = `<div class="flag-badge open-badge">🔵 Active: ${translateDigitsToNepalese(daysRemaining.toString())} Days Remaining</div>`;
        } else if (contract.is_red_flagged) {
            flagIndicator = `<div class="flag-badge alert-badge">🚨 Audit Flag: Single Bidder</div>`;
        } else {
            flagIndicator = `<div class="flag-badge success-badge">🟢 Competitive Award</div>`;
        }

        const contractorName = isOpen ? 'Pending' : (contract.contractor_name || 'N/A');
        const budgetAmount = isOpen ? 'Pending' : formatNepaleseCurrency(contract.amount_allocated);

        // Render card content using structured citizen-friendly elements
        card.innerHTML = `
            <div class="card-header-badge-container">
                ${flagIndicator}
            </div>
            
            <div class="card-body">
                <h3 class="project-title" title="${contract.title}">${contract.title}</h3>
                
                <div class="primary-info">
                    <div class="info-group">
                        <span class="info-label">Procuring Office (Buyer)</span>
                        <span class="info-value buyer-name">${contract.ministry_department || 'Government Body'}</span>
                    </div>
                    <div class="info-group">
                        <span class="info-label">${isOpen ? 'Expected Contractor' : 'Final Winner'}</span>
                        <span class="info-value contractor-name highlight">${contractorName}</span>
                    </div>
                </div>

                <!-- Progressive Disclosure Toggle -->
                <div class="tech-meta-toggle-container">
                    <button class="tech-meta-btn" onclick="toggleTechMeta(this, event)">
                        <span>Show Technical Meta</span> <i class="fa-solid fa-chevron-down toggle-icon"></i>
                    </button>
                    
                    <div class="tech-meta-content hidden">
                        <div class="detail-row">
                            <span class="detail-label">Tender ID:</span>
                            <span class="detail-value code">${contract.tender_id || 'N/A'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">${isOpen ? 'Submission Deadline' : 'Award Date'}:</span>
                            <span class="detail-value">${isOpen ? formatDate(contract.submission_deadline) : formatDate(contract.award_date)}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Bidders Count:</span>
                            <span class="detail-value">${isOpen ? 'Pending' : translateDigitsToNepalese(contract.bidders_count.toString())}</span>
                        </div>
                        ${!isOpen && contract.contractor_reg_date ? `
                        <div class="detail-row">
                            <span class="detail-label">Contractor Reg. Date:</span>
                            <span class="detail-value">${formatDate(contract.contractor_reg_date)}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
            
            <div class="card-footer">
                <div class="budget-section">
                    <span class="budget-label">Allocated Budget</span>
                    <span class="budget-amount">${budgetAmount}</span>
                </div>
                <button class="audit-action-btn" onclick="openAuditModal('${contract.tender_id}')">
                    <i class="fa-solid fa-magnifying-glass-chart"></i> Audit
                </button>
            </div>
        `;

        contractsGrid.appendChild(card);
    });
}

// Global toggle for technical metadata (progressive disclosure)
window.toggleTechMeta = function(btn, event) {
    if (event) {
        event.stopPropagation();
    }
    const content = btn.nextElementSibling;
    const icon = btn.querySelector('.toggle-icon');
    const label = btn.querySelector('span');
    
    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        if (icon) icon.className = 'fa-solid fa-chevron-up toggle-icon';
        if (label) label.textContent = 'Hide Technical Meta';
        btn.classList.add('expanded');
    } else {
        content.classList.add('hidden');
        if (icon) icon.className = 'fa-solid fa-chevron-down toggle-icon';
        if (label) label.textContent = 'Show Technical Meta';
        btn.classList.remove('expanded');
    }
};

// Sync active visual classes for status filters
function syncFilterVisuals(status) {
    currentFilterStatus = status;

    // Sync status toggle bar buttons
    const btnShowAll = document.getElementById('btn-show-all');
    const btnActiveBids = document.getElementById('btn-active-bids');
    const btnFlaggedAudits = document.getElementById('btn-flagged-audits');

    if (btnShowAll) btnShowAll.classList.toggle('active', status === 'all');
    if (btnActiveBids) btnActiveBids.classList.toggle('active', status === 'active');
    if (btnFlaggedAudits) btnFlaggedAudits.classList.toggle('active', status === 'flagged');

    // Sync top-level macro cards
    if (cardTotalVolume) cardTotalVolume.classList.toggle('active-filter', status === 'all');
    if (cardActiveTenders) cardActiveTenders.classList.toggle('active-filter', status === 'active');
    if (cardFlaggedAlerts) cardFlaggedAlerts.classList.toggle('active-filter', status === 'flagged');
}

// Select active filter status and re-apply in-memory filtering
window.selectFilter = function(status) {
    currentPage = 1;
    syncFilterVisuals(status);
    applyClientSideFilters();
};

// Fetch Leaderboard from Backend API
async function fetchLeaderboard() {
    leaderboardLoader.classList.remove('hidden');
    leaderboardList.classList.add('hidden');

    const url = `${API_BASE_URL}/contracts/leaderboard`;

    try {
        console.log(`[HTTP GET] Fetching leaderboard from: ${url}`);
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const payload = await response.json();
        const leaderboardData = payload.leaderboard || [];

        renderLeaderboard(leaderboardData);
    } catch (error) {
        console.error('Failed to fetch leaderboard:', error);
        showConnectionError(leaderboardList, leaderboardLoader, 'contractor metrics');
    }
}

// Render Contractor Leaderboard Sidebar
function renderLeaderboard(data) {
    leaderboardLoader.classList.add('hidden');
    leaderboardList.innerHTML = '';
    leaderboardList.classList.remove('hidden');

    if (data.length === 0) {
        leaderboardList.innerHTML = `
            <div class="no-data-card" style="padding: 2rem 1rem;">
                <i class="fa-solid fa-building-columns" style="font-size: 1.5rem; color: var(--text-muted);"></i>
                <p style="font-size: 0.8rem; margin: 0.5rem 0 0 0;">No leaderboard data available.</p>
            </div>
        `;
        return;
    }

    data.forEach((item, index) => {
        const rank = index + 1;
        let rankClass = 'rank-other';
        if (rank === 1) rankClass = 'rank-1';
        else if (rank === 2) rankClass = 'rank-2';
        else if (rank === 3) rankClass = 'rank-3';

        // Translate rank number to Nepalese
        const rankNepalese = translateDigitsToNepalese(rank.toString());

        const itemEl = document.createElement('div');
        itemEl.className = 'leaderboard-item';
        
        // Check for anomalies counts to display warning indicator
        const anomaliesCount = parseInt(item.flagged_anomalies_count || 0, 10);
        let anomalyTag = '';
        if (anomaliesCount > 0) {
            const flagWord = anomaliesCount > 1 ? 'चेतावनीहरू' : 'चेतावनी'; // Warnings / Warning in Nepali
            const flagsNepalese = translateDigitsToNepalese(anomaliesCount.toString());
            anomalyTag = `<span class="anomaly-warning-pill">
                <i class="fa-solid fa-triangle-exclamation"></i> ${flagsNepalese} ${flagWord}
            </span>`;
        }

        const wonNepalese = translateDigitsToNepalese(item.contracts_won_count.toString());

        itemEl.innerHTML = `
            <div class="leaderboard-rank-info">
                <div class="rank-badge ${rankClass}">${rankNepalese}</div>
                <div class="leaderboard-details">
                    <span class="leaderboard-name" title="${item.contractor_name}">${item.contractor_name}</span>
                    <span class="leaderboard-stats">
                        ${wonNepalese} Projects ${anomalyTag}
                    </span>
                </div>
            </div>
            <div class="leaderboard-value">
                ${formatNepaleseCurrency(item.total_funding_allocated)}
            </div>
        `;
        
        leaderboardList.appendChild(itemEl);
    });
}

// Show Error Message on Fetch Failure
function showConnectionError(container, loader, dataName) {
    loader.classList.add('hidden');
    container.innerHTML = `
        <div class="no-data-card error-card">
            <i class="fa-solid fa-circle-xmark error-icon"></i>
            <h3>Network Link Interrupted</h3>
            <p>
                Failed to communicate with API services to retrieve ${dataName}. Verify that the backend server is active on http://localhost:8000.
            </p>
            <button onclick="retryConnection()" class="retry-btn">
                <i class="fa-solid fa-rotate-right"></i> Retry Connection
            </button>
        </div>
    `;
    container.classList.remove('hidden');
}

// Reconnect/Retry Connection
function retryConnection() {
    console.log('[Connection Status] Attempting to re-establish API connection...');
    fetchContracts();
    fetchLeaderboard();
}

// Open Audit Modal Details
window.openAuditModal = function(tenderId) {
    console.log(`[Audit Logger] Compliance inspection initiated for Tender: ${tenderId}`);
    
    // Find contract details from preloaded allContracts collection
    const contract = allContracts.find(c => c.tender_id === tenderId);
    if (!contract) return;
    
    // Update Modal DOM
    const modalProjectTitle = document.getElementById('modalProjectTitle');
    const modalTenderId = document.getElementById('modalTenderId');
    const modalBiddersCount = document.getElementById('modalBiddersCount');
    const modalBuyer = document.getElementById('modalBuyer');
    const modalAmount = document.getElementById('modalAmount');
    const modalAwardDate = document.getElementById('modalAwardDate');
    const modalRegDate = document.getElementById('modalRegDate');
    const modalRiskVerdict = document.getElementById('modalRiskVerdict');
    const modalRiskIndicator = document.getElementById('modalRiskIndicator');
    const modalFindingsLog = document.getElementById('modalFindingsLog');
    
    modalProjectTitle.textContent = contract.title;
    modalTenderId.textContent = contract.tender_id;
    
    const isOpen = contract.tender_status === 'OPEN';
    
    const biddersText = isOpen
        ? '० बोलपत्रदाताहरू'
        : (contract.bidders_count === 1 
            ? '१ (एकल बोलपत्रदाता)' 
            : translateDigitsToNepalese(contract.bidders_count.toString()) + ' बोलपत्रदाताहरू');
    modalBiddersCount.textContent = biddersText;
    
    modalBuyer.textContent = contract.ministry_department || 'N/A';
    modalAmount.textContent = isOpen ? 'Pending' : formatNepaleseCurrency(contract.amount_allocated);
    modalAwardDate.textContent = isOpen ? 'N/A' : formatDate(contract.award_date);
    modalRegDate.textContent = isOpen ? 'N/A' : formatDate(contract.contractor_reg_date);
    
    // Risk styling & findings log
    modalRiskIndicator.className = 'modal-risk-indicator'; // Reset
    modalFindingsLog.className = 'findings-log'; // Reset
    
    if (isOpen) {
        const daysRemaining = getDaysRemaining(contract.submission_deadline);
        const daysRemainingText = `${daysRemaining} Days Remaining`;
        modalRiskIndicator.classList.add('risk-open');
        modalRiskVerdict.textContent = '🔵 Status: ACTIVE BIDDING STAGE';
        modalFindingsLog.classList.add('open-log');
        
        modalFindingsLog.innerHTML = `
            <p><strong>Bidding Process Status:</strong></p>
            <p>• <strong>Active Procurement:</strong> This tender is currently open for bids. No contractor has been selected yet.</p>
            <p>• <strong>Submission Deadline:</strong> Submissions close on ${formatDate(contract.submission_deadline)} (${daysRemainingText}).</p>
            <p>• <strong>Audit Status:</strong> Compliance auditing will run automatically once bids are closed and the contract is awarded.</p>
        `;
    } else {
        // Calculate timeline deltas
        const awardDt = new Date(contract.award_date);
        const regDt = new Date(contract.contractor_reg_date);
        const deltaDays = Math.ceil((awardDt - regDt) / (1000 * 60 * 60 * 24));
        const deltaDaysNep = translateDigitsToNepalese(deltaDays.toString());

        if (contract.is_red_flagged) {
            modalRiskIndicator.classList.add('risk-high');
            modalRiskVerdict.textContent = '🚨 Forensic Verdict: HIGH RISK ANOMALY';
            modalFindingsLog.classList.add('flagged-log');
            
            let findingsHtml = '<p><strong>Forensic Flag Checklist:</strong></p>';
            if (contract.bidders_count === 1) {
                findingsHtml += `<p>• <strong>Bidders Anomaly:</strong> Only 1 bidder competed. Flagged as a non-competitive, single-bidder procurement assignment.</p>`;
            }
            if (deltaDays < 30) {
                findingsHtml += `<p>• <strong>Shell Company Suspect:</strong> Contractor registered just ${deltaDaysNep} days prior to winning this contract. Highly suspicious registration timeline.</p>`;
            }
            findingsHtml += `<p>• <strong>Risk Reasons:</strong> ${contract.red_flag_reason || 'N/A'}</p>`;
            modalFindingsLog.innerHTML = findingsHtml;
        } else {
            modalRiskIndicator.classList.add('risk-clean');
            modalRiskVerdict.textContent = '🟢 Forensic Verdict: CLEAN COMPETITIVE TENDER';
            modalFindingsLog.classList.add('clean-log');
            
            modalFindingsLog.innerHTML = `
                <p><strong>Forensic Analysis:</strong></p>
                <p>• <strong>Competitive Bidding:</strong> Healthy competitive bidding observed with ${biddersText}.</p>
                <p>• <strong>Established History:</strong> Contractor has an active registration history of ${deltaDaysNep} days prior to contract award, verifying standard operational standing.</p>
                <p>• <strong>Verdict:</strong> Audit indicators show clean clearances. No suspicious transaction signals detected.</p>
            `;
        }
    }
    
    // Display Modal
    const modalOverlay = document.getElementById('modalOverlay');
    modalOverlay.classList.remove('hidden');
};

// Close Modal helper
function closeModal() {
    const modalOverlay = document.getElementById('modalOverlay');
    modalOverlay.classList.add('hidden');
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Add CSS Keyframe animation to document dynamically
    const styleSheet = document.createElement('style');
    styleSheet.textContent = `
        @keyframes card-appear {
            from {
                opacity: 0;
                transform: translateY(15px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(styleSheet);

    // Initial load
    fetchContracts();
    fetchLeaderboard();

    // Event: Status toggle button clicks
    const btnShowAll = document.getElementById('btn-show-all');
    const btnActiveBids = document.getElementById('btn-active-bids');
    const btnFlaggedAudits = document.getElementById('btn-flagged-audits');

    if (btnShowAll) btnShowAll.addEventListener('click', () => selectFilter('all'));
    if (btnActiveBids) btnActiveBids.addEventListener('click', () => selectFilter('active'));
    if (btnFlaggedAudits) btnFlaggedAudits.addEventListener('click', () => selectFilter('flagged'));

    // Event: Top-level overview card clicks
    if (cardTotalVolume) cardTotalVolume.addEventListener('click', () => selectFilter('all'));
    if (cardActiveTenders) cardActiveTenders.addEventListener('click', () => selectFilter('active'));
    if (cardFlaggedAlerts) cardFlaggedAlerts.addEventListener('click', () => selectFilter('flagged'));

    // Event: Real-time search filter (in-memory)
    let searchDebounce;
    contractSearch.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => {
            currentPage = 1;
            applyClientSideFilters();
        }, 150); // Small debounce to keep typing smooth
    });

    // Event: Dropdown filter change listeners (in-memory)
    const selectDept = document.getElementById('select-dept');
    const selectYear = document.getElementById('select-year');
    const selectMonth = document.getElementById('select-month');

    if (selectDept) selectDept.addEventListener('change', () => { currentPage = 1; applyClientSideFilters(); });
    if (selectYear) selectYear.addEventListener('change', () => { currentPage = 1; applyClientSideFilters(); });
    if (selectMonth) selectMonth.addEventListener('change', () => { currentPage = 1; applyClientSideFilters(); });

    // Event: Pagination listeners (in-memory client side)
    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            renderFilteredContracts();
        }
    });

    nextBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(filteredContracts.length / limitPerPage) || 1;
        if (currentPage < totalPages) {
            currentPage++;
            renderFilteredContracts();
        }
    });

    // Event: Close Modal listeners
    const modalCloseBtn = document.getElementById('modalCloseBtn');
    const modalCloseFooterBtn = document.getElementById('modalCloseFooterBtn');
    const modalOverlay = document.getElementById('modalOverlay');
    const auditModal = document.getElementById('auditModal');
    
    modalCloseBtn.addEventListener('click', closeModal);
    modalCloseFooterBtn.addEventListener('click', closeModal);
    
    // Close when clicking backdrop overlay
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });
    // Prevent closing when clicking inside modal box
    auditModal.addEventListener('click', (e) => {
        e.stopPropagation();
    });
});
