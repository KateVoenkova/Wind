document.addEventListener('DOMContentLoaded', function() {
    // Контейнер и настройки
    const container = document.getElementById('graph-container');
    if (!container) return;
    const bookId = container.dataset.bookId;
    if (!bookId) return;

    const width = 1200;
    const height = 800;
    const nodeRadius = 15;
    let currentScale = 1;

    // Создание SVG и группы для элементов
    const svg = d3.select("#graph-container")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    const g = svg.append("g");

    // Кнопки управления
    const controls = d3.select("#graph-container")
        .append("div")
        .style("position", "absolute")
        .style("bottom", "20px")
        .style("left", "50%")
        .style("transform", "translateX(-50%)");

    controls.append("button")
        .text("+")
        .on("click", () => zoom(0.2));

    controls.append("button")
        .text("-")
        .on("click", () => zoom(-0.2));

    controls.append("button")
        .text("Показать всех")
        .on("click", fitToView);

    // Загрузка данных
    fetch(`/api/books/${bookId}/graph`)
        .then(response => response.json())
        .then(data => {
            // Симуляция без возможности перемещения
            const simulation = d3.forceSimulation(data.nodes)
                .force("charge", d3.forceManyBody().strength(-30)) // Меньшая сила отталкивания
                .force("link", d3.forceLink(data.links).id(d => d.id).distance(80))
                .force("center", d3.forceCenter(width/2, height/2));

            // Отрисовка связей
            const link = g.append("g")
                .selectAll("line")
                .data(data.links)
                .enter()
                .append("line")
                .attr("stroke", "#4a4a4a")
                .attr("stroke-width", 1);

            // Отрисовка узлов (без drag-and-drop)
            const node = g.append("g")
                .selectAll("circle")
                .data(data.nodes)
                .enter()
                .append("circle")
                .attr("r", nodeRadius)
                .attr("fill", "#4e79a7")
                .style("cursor", "pointer")
                .on("click", function(event, d) {
                    window.location.href = `/characters/${d.id}`;
                });

            // Подписи
            const labels = g.append("g")
                .selectAll("text")
                .data(data.nodes)
                .enter()
                .append("text")
                .text(d => d.name)
                .attr("font-size", 12)
                .attr("dx", nodeRadius + 5)
                .attr("dy", 4);

            // Обновление позиций
            simulation.on("tick", () => {
                link.attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                node.attr("cx", d => d.x)
                    .attr("cy", d => d.y);

                labels.attr("x", d => d.x)
                    .attr("y", d => d.y);
            });

            // Автомасштабирование при загрузке
            setTimeout(fitToView, 100);
        });

    // Функции масштабирования
    function zoom(scaleDelta) {
        currentScale = Math.min(3, Math.max(0.5, currentScale + scaleDelta));
        g.attr("transform", `scale(${currentScale})`);
    }

    function fitToView() {
        const bounds = g.node().getBBox();
        const scale = 0.9 / Math.max(bounds.width / width, bounds.height / height);
        currentScale = scale;

        g.transition()
            .duration(500)
            .attr("transform", `
                translate(${width/2 - (bounds.x + bounds.width/2) * scale},
                          ${height/2 - (bounds.y + bounds.height/2) * scale})
                scale(${scale})
            `);
    }
});