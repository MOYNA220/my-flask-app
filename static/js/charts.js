document.addEventListener('DOMContentLoaded', function() {
  // Only run on dashboard
  if (!document.querySelector('.dashboard-page')) return;

  // Sample data - in a real app, this would come from your API
  const salesData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
    datasets: [{
      label: 'Sales',
      data: [12000, 19000, 15000, 18000, 21000, 19500, 23000],
      backgroundColor: 'rgba(52, 152, 219, 0.2)',
      borderColor: 'rgba(52, 152, 219, 1)',
      borderWidth: 2,
      tension: 0.4
    }]
  };

  const profitData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
    datasets: [{
      label: 'Profit',
      data: [4000, 6000, 5000, 5500, 7000, 6500, 7500],
      backgroundColor: 'rgba(46, 204, 113, 0.2)',
      borderColor: 'rgba(46, 204, 113, 1)',
      borderWidth: 2,
      tension: 0.4
    }]
  };

  // Initialize charts
  const salesChartCtx = document.getElementById('sales-chart').getContext('2d');
  const profitChartCtx = document.getElementById('profit-chart').getContext('2d');

  new Chart(salesChartCtx, {
    type: 'line',
    data: salesData,
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'top',
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return '$' + context.raw.toLocaleString();
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return '$' + value.toLocaleString();
            }
          }
        }
      }
    }
  });

  new Chart(profitChartCtx, {
    type: 'bar',
    data: profitData,
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'top',
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return '$' + context.raw.toLocaleString();
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return '$' + value.toLocaleString();
            }
          }
        }
      }
    }
  });
});