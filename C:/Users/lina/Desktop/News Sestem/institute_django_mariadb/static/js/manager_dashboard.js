// manager_dashboard.js
// Fetch dashboard data and render charts & alerts
document.addEventListener('DOMContentLoaded', function () {
  const endpoint = '/api/manager/dashboard/';
  fetch(endpoint, { credentials: 'same-origin' })
    .then(response => {
      if (!response.ok) throw new Error('Network response was not ok');
      return response.json();
    })
    .then(data => {
      // Populate charts
      const kpiCtx = document.getElementById('kpiChart').getContext('2d');
      new Chart(kpiCtx, {
        type: 'bar',
        data: {
          labels: data.kpi_labels,
          datasets: [{
            label: 'عدد',
            data: data.kpi_values,
            backgroundColor: ['#2e86de', '#38ada9', '#e58e26']
          }]
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } }
        }
      });

      const financeCtx = document.getElementById('financeChart').getContext('2d');
      new Chart(financeCtx, {
        type: 'doughnut',
        data: {
          labels: data.finance_labels,
          datasets: [{
            data: data.finance_values,
            backgroundColor: ['#27ae60', '#c0392b']
          }]
        },
        options: { responsive: true }
      });

      // Populate alerts (Bootstrap toasts)
      const alertsContainer = document.getElementById('alertsContainer');
      data.alerts.forEach((msg, idx) => {
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-bg-warning border-0 mb-2';
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.innerHTML = `
          <div class="d-flex">
            <div class="toast-body">${msg}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
          </div>
        `;
        alertsContainer.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
      });
    })
    .catch(err => console.error('Dashboard fetch error:', err));
});
