let doughnutChart = null;
let lineChart = null;

document.addEventListener("turbolinks:load", function() {

    // Limpieza preventiva
    if (doughnutChart) {
        doughnutChart.destroy();
        doughnutChart = null;
    }
    if (lineChart) {
        lineChart.destroy();
        lineChart = null;
    }

    // Comprobamos si estamos en la página de métricas
    const canvasIngresos = document.getElementById('ingresosChart');
    const canvasServicios = document.getElementById('serviciosPopularesChart');
    if (!canvasIngresos || !canvasServicios) {
        return; // Salimos si no están los canvas
    }

    // Gráfico de Servicios Populares
    try {
        const labelsServicios = JSON.parse(document.getElementById('labels-servicios-data').textContent);
        const dataServicios = JSON.parse(document.getElementById('data-servicios-data').textContent);
        
        if (Array.isArray(labelsServicios) && Array.isArray(dataServicios) && dataServicios.length > 0) {
            doughnutChart = new Chart(canvasServicios.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: labelsServicios,
                    datasets: [{ data: dataServicios, backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1'] }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        } else {
            const ctx = canvasServicios.getContext('2d');
            ctx.clearRect(0, 0, canvasServicios.width, canvasServicios.height);
            ctx.textAlign = 'center'; ctx.font = '14px Segoe UI'; ctx.fillStyle = '#888';
            ctx.fillText('No hay datos de servicios para este período.', canvasServicios.width / 2, canvasServicios.height / 2);
        }
    } catch (e) { console.error("Error en gráfico de torta:", e); }

    // Gráfico de Análisis de Ingresos
    lineChart = new Chart(canvasIngresos.getContext('2d'), {
        type: 'line', 
        data: { labels: [], datasets: [{ label: 'Ingresos ($)', data: [] }] }, 
        options: { scales: { y: { beginAtZero: true } } }
    });

    const controles = document.querySelectorAll('.control-btn');
    let agrupacionActual = 'dia';

    function actualizarGraficoLineal() {
        const apiUrl = canvasIngresos.dataset.apiUrl;
        if (!apiUrl) return;

        const filtroDia = document.getElementById('filtro-dia');
        const filtroMes = document.getElementById('filtro-mes');
        const filtroAño = document.getElementById('filtro-año');
        let params = new URLSearchParams({ agrupar_por: agrupacionActual });
        if (agrupacionActual === 'dia') params.append('fecha', filtroDia.value);
        if (agrupacionActual === 'mes') params.append('mes', filtroMes.value);
        if (agrupacionActual === 'año') params.append('año', filtroAño.value);
        
        fetch(`${apiUrl}?${params.toString()}`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(response => response.json())
        .then(data => {
            if (lineChart) {
                lineChart.data.labels = data.labels;
                lineChart.data.datasets[0].data = data.data;
                lineChart.data.datasets[0].borderColor = 'aqua';
                lineChart.data.datasets[0].backgroundColor = 'rgba(0, 255, 255, 0.2)';
                lineChart.data.datasets[0].fill = true;
                lineChart.data.datasets[0].tension = 0.1;
                lineChart.update();
            }
        });
    }

    controles.forEach(btn => btn.addEventListener('click', function() {
        agrupacionActual = this.dataset.agrupar;
        controles.forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        document.querySelectorAll('.filtro-fecha').forEach(f => f.style.display = 'none');
        document.getElementById(`filtro-${agrupacionActual}`).style.display = 'block';
        actualizarGraficoLineal();
    }));
    document.querySelectorAll('.filtro-fecha').forEach(filtro => filtro.addEventListener('change', actualizarGraficoLineal));

    const hoy = new Date();
    const yyyy = hoy.getFullYear();
    const mm = String(hoy.getMonth() + 1).padStart(2, '0');
    const dd = String(hoy.getDate()).padStart(2, '0');
    document.getElementById('filtro-dia').value = `${yyyy}-${mm}-${dd}`;
    document.getElementById('filtro-mes').value = `${yyyy}-${mm}`;
    document.getElementById('filtro-año').value = yyyy;
    
    actualizarGraficoLineal();
});