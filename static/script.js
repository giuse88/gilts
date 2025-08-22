let currentSort = { column: -1, direction: 'asc' };
let bondsData = [];
let yieldCurveChart = null;
let currentTab = 'Bills';

async function loadBonds() {
    const dateSelect = document.getElementById('dateSelect');
    const selectedDate = dateSelect.value;
    const loading = document.getElementById('loading');
    const tableBody = document.getElementById('bondsTableBody');
    const bondCount = document.getElementById('bondCount');
    
    if (!selectedDate) return;
    
    loading.style.display = 'block';
    tableBody.innerHTML = '';
    
    try {
        const response = await fetch(`/api/bonds?date=${selectedDate}&type=${currentTab}`);
        bondsData = await response.json();
        
        if (bondsData.error) {
            throw new Error(bondsData.error);
        }
        
        displayBonds(bondsData);
        bondCount.textContent = `${bondsData.length} ${currentTab} bonds`;
        
        // Only load yield curve if date changed (not tab change)
        if (!window.lastLoadedDate || window.lastLoadedDate !== selectedDate) {
            await loadYieldCurve(selectedDate);
            window.lastLoadedDate = selectedDate;
        }
        
    } catch (error) {
        console.error('Error loading bonds:', error);
        tableBody.innerHTML = '<tr><td colspan="10" class="error">Error loading bond data</td></tr>';
        bondCount.textContent = '';
    } finally {
        loading.style.display = 'none';
    }
}

function displayBonds(bonds) {
    const tableBody = document.getElementById('bondsTableBody');
    tableBody.innerHTML = '';
    
    bonds.forEach(bond => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="isin">${bond.isin}</td>
            <td class="gilt-name">${bond.gilt_name}</td>
            <td class="number">${bond.coupon}</td>
            <td class="date">${bond.maturity}</td>
            <td class="number">${bond.clean_price}</td>
            <td class="number">${bond.dirty_price}</td>
            <td class="number">${bond.yield}</td>
            <td class="number">${bond.mod_duration}</td>
            <td class="number">${bond.accrued_interest}</td>
        `;
        tableBody.appendChild(row);
    });
}

function sortTable(columnIndex) {
    const table = document.getElementById('bondsTable');
    const headers = table.querySelectorAll('th');
    
    // Clear previous sort indicators
    headers.forEach(header => {
        const arrow = header.querySelector('.sort-arrow');
        if (arrow) arrow.textContent = '↕';
    });
    
    // Determine sort direction
    if (currentSort.column === columnIndex) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = columnIndex;
        currentSort.direction = 'asc';
    }
    
    // Update sort indicator
    const currentHeader = headers[columnIndex];
    const arrow = currentHeader.querySelector('.sort-arrow');
    if (arrow) {
        arrow.textContent = currentSort.direction === 'asc' ? '↑' : '↓';
    }
    
    // Sort the data
    const sortedBonds = [...bondsData].sort((a, b) => {
        const columns = ['isin', 'gilt_name', 'coupon', 'maturity', 'clean_price', 'dirty_price', 'yield', 'mod_duration', 'accrued_interest'];
        const key = columns[columnIndex];
        
        let aVal = a[key];
        let bVal = b[key];
        
        // Handle N/A values
        if (aVal === 'N/A' && bVal === 'N/A') return 0;
        if (aVal === 'N/A') return 1;
        if (bVal === 'N/A') return -1;
        
        // Convert to numbers for numeric columns
        if (columnIndex >= 2 && columnIndex !== 3) { // All except maturity
            aVal = parseFloat(aVal.replace(/[£%,]/g, '')) || 0;
            bVal = parseFloat(bVal.replace(/[£%,]/g, '')) || 0;
        }
        
        // Date comparison for maturity
        if (columnIndex === 3) {
            aVal = new Date(aVal);
            bVal = new Date(bVal);
        }
        
        if (aVal < bVal) return currentSort.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    displayBonds(sortedBonds);
}

async function loadYieldCurve(date) {
    try {
        const response = await fetch(`/api/yield-curve?date=${date}`);
        const curveData = await response.json();
        
        if (curveData.error) {
            console.error('Yield curve error:', curveData.error);
            return;
        }
        
        displayYieldCurve(curveData);
        
    } catch (error) {
        console.error('Error loading yield curve:', error);
    }
}

function displayYieldCurve(curveData) {
    const ctx = document.getElementById('yieldCurveChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (yieldCurveChart) {
        yieldCurveChart.destroy();
    }
    
    // Format maturity labels
    const maturityLabels = curveData.maturities.map(mat => {
        if (mat < 1) {
            return `${Math.round(mat * 12)}M`;
        } else {
            return `${mat}Y`;
        }
    });
    
    yieldCurveChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: maturityLabels,
            datasets: [{
                label: 'Yield (%)',
                data: curveData.yields,
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 5,
                pointHoverRadius: 8,
                pointBackgroundColor: '#2563eb',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Maturity',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: '#e5e7eb',
                        lineWidth: 1
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Yield (%)',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: '#e5e7eb',
                        lineWidth: 1
                    },
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(2) + '%';
                        }
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: `UK Gilt Yield Curve - ${curveData.business_date}`,
                    font: {
                        size: 16,
                        weight: 'bold'
                    },
                    padding: 20
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Yield: ${context.parsed.y.toFixed(3)}%`;
                        }
                    }
                }
            }
        }
    });
}

function showTab(tabType) {
    // Update tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(btn => btn.classList.remove('active'));
    
    const activeButton = [...tabButtons].find(btn => 
        (tabType === 'Bills' && btn.textContent.includes('Bills')) ||
        (tabType === 'Conventional' && btn.textContent.includes('Bond')) ||
        (tabType === 'Index-linked' && btn.textContent.includes('Index-linked')) ||
        (tabType === 'Strips' && btn.textContent.includes('Strips'))
    );
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Update current tab and reload data
    currentTab = tabType;
    loadBonds();
}

// Add keyboard shortcuts
document.addEventListener('keydown', function(event) {
    if (event.ctrlKey || event.metaKey) {
        switch(event.key) {
            case 'r':
                event.preventDefault();
                loadBonds();
                break;
        }
    }
});