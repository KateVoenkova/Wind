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
    let currentThreshold = 0;
    let graphData = { nodes: [], links: [] };

    // Цветовая шкала для связей (от светлого к темному)
    const colorScale = d3.scaleLinear()
        .domain([0, 1])
        .range(["#cccccc", "#4a4a4a"]);

    // Создание SVG и группы для элементов
    const svg = d3.select("#graph-container")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    const g = svg.append("g");

    // Создаем группу для элементов управления
    const controlsGroup = svg.append("g")
        .attr("transform", `translate(${width - 250}, 20)`);

    // Добавляем заголовок для фильтра
    controlsGroup.append("text")
        .attr("x", 0)
        .attr("y", 20)
        .text("Фильтр силы связей:")
        .attr("font-size", "14px")
        .attr("fill", "#333");

    // Добавляем прогресс-бар
    const slider = controlsGroup.append("g")
        .attr("transform", "translate(0, 40)");

    // Полоса прогресс-бара
    slider.append("rect")
        .attr("width", 200)
        .attr("height", 10)
        .attr("rx", 5)
        .attr("ry", 5)
        .attr("fill", "#eee");

    // Индикатор текущего значения
    const progress = slider.append("rect")
        .attr("width", 0)
        .attr("height", 10)
        .attr("rx", 5)
        .attr("ry", 5)
        .attr("fill", "#4e79a7");

    // Кружок для перетаскивания
    const handle = slider.append("circle")
        .attr("cx", 0)
        .attr("cy", 5)
        .attr("r", 10)
        .attr("fill", "#4e79a7")
        .call(d3.drag()
            .on("drag", draggedSlider));

    // Подписи для шкалы
    slider.append("text")
        .attr("x", 0)
        .attr("y", 30)
        .text("Слабые")
        .attr("font-size", "12px")
        .attr("fill", "#666");

    slider.append("text")
        .attr("x", 160)
        .attr("y", 30)
        .text("Сильные")
        .attr("font-size", "12px")
        .attr("fill", "#666")
        .attr("text-anchor", "end");

    // Кнопки управления масштабом (стильные круги)
    const zoomControls = svg.append("g")
        .attr("transform", `translate(${width - 100}, ${height - 50})`);

    zoomControls.append("rect")
        .attr("width", 90)
        .attr("height", 40)
        .attr("rx", 5)
        .attr("ry", 5)
        .attr("fill", "white")
        .attr("stroke", "#ddd");

    zoomControls.append("text")
        .attr("x", 45)
        .attr("y", 15)
        .text("Масштаб:")
        .attr("font-size", "12px")
        .attr("text-anchor", "middle")
        .attr("fill", "#333");

    const zoomIn = zoomControls.append("g")
        .attr("transform", "translate(15, 25)")
        .style("cursor", "pointer")
        .on("click", () => zoom(0.2));

    zoomIn.append("circle")
        .attr("r", 12)
        .attr("fill", "#4e79a7");

    zoomIn.append("text")
        .attr("x", 0)
        .attr("y", 5)
        .text("+")
        .attr("font-size", "16px")
        .attr("text-anchor", "middle")
        .attr("fill", "white");

    const zoomOut = zoomControls.append("g")
        .attr("transform", "translate(45, 25)")
        .style("cursor", "pointer")
        .on("click", () => zoom(-0.2));

    zoomOut.append("circle")
        .attr("r", 12)
        .attr("fill", "#4e79a7");

    zoomOut.append("text")
        .attr("x", 0)
        .attr("y", 5)
        .text("-")
        .attr("font-size", "16px")
        .attr("text-anchor", "middle")
        .attr("fill", "white");

    const resetZoom = zoomControls.append("g")
        .attr("transform", "translate(75, 25)")
        .style("cursor", "pointer")
        .on("click", fitToView);

    resetZoom.append("circle")
        .attr("r", 12)
        .attr("fill", "#4e79a7");

    resetZoom.append("text")
        .attr("x", 0)
        .attr("y", 5)
        .text("↻")
        .attr("font-size", "16px")
        .attr("text-anchor", "middle")
        .attr("fill", "white");

    // Загрузка данных
    fetch(`/api/books/${bookId}/graph`)
        .then(response => response.json())
        .then(data => {
            graphData = data;

            // Нормализуем веса связей от 0 до 1
            const maxWeight = d3.max(graphData.links, d => d.value) || 1;
            graphData.links.forEach(link => {
                link.normalizedWeight = link.value / maxWeight;
            });

            // Инициализируем прогресс-бар
            updateSlider(0);

            // Инициализируем граф
            initGraph();
        });

    function initGraph() {
        // Симуляция с более слабым отталкиванием
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("charge", d3.forceManyBody().strength(-30))
            .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(80))
            .force("center", d3.forceCenter(width/2, height/2))
            .force("collision", d3.forceCollide().radius(nodeRadius * 1.5));

        // Отрисовка связей (одинаковая толщина, разный цвет)
        const link = g.append("g")
            .selectAll("line")
            .data(graphData.links)
            .enter()
            .append("line")
            .attr("stroke-width", 1.5)
            .attr("stroke", d => colorScale(d.normalizedWeight))
            .attr("class", "link");

        // Отрисовка узлов
        const node = g.append("g")
            .selectAll("circle")
            .data(graphData.nodes)
            .enter()
            .append("circle")
            .attr("r", nodeRadius)
            .attr("fill", "#4e79a7")
            .style("cursor", "pointer")
            .attr("class", "node")
            .on("click", function(event, d) {
                window.location.href = `/characters/${d.id}`;
            });

        // Подписи
        const labels = g.append("g")
            .selectAll("text")
            .data(graphData.nodes)
            .enter()
            .append("text")
            .text(d => d.name)
            .attr("font-size", 12)
            .attr("dx", nodeRadius + 5)
            .attr("dy", 4)
            .attr("fill", "#333")
            .attr("paint-order", "stroke")
            .attr("stroke", "white")
            .attr("stroke-width", "3px")
            .attr("stroke-linecap", "round")
            .attr("stroke-linejoin", "round")
            .attr("class", "label");

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

        // Добавляем возможность масштабирования колесиком мыши
        svg.call(d3.zoom()
            .scaleExtent([0.5, 3])
            .on("zoom", (event) => {
                currentScale = event.transform.k;
                g.attr("transform", event.transform);
            }));

        // Добавляем возможность перемещения графа
        svg.call(d3.drag()
            .on("start", dragStarted)
            .on("drag", dragged)
            .on("end", dragEnded));
    }

    function updateGraph(threshold) {
        // Фильтруем связи по порогу
        d3.selectAll(".link")
            .style("display", d => d.normalizedWeight >= threshold ? "inline" : "none")
            .attr("stroke", d => colorScale(d.normalizedWeight));

        // Находим узлы, которые имеют хотя бы одну связь выше порога
        const activeNodes = new Set();
        graphData.links.forEach(link => {
            if (link.normalizedWeight >= threshold) {
                activeNodes.add(link.source.id);
                activeNodes.add(link.target.id);
            }
        });

        // Показываем/скрываем узлы
        d3.selectAll(".node, .label")
            .style("display", d => activeNodes.has(d.id) || activeNodes.size === 0 ? "inline" : "none");
    }

    function updateSlider(value) {
        currentThreshold = value;
        const pixelValue = value * 200;

        progress.attr("width", pixelValue);
        handle.attr("cx", pixelValue);

        updateGraph(value);
    }

    function draggedSlider(event) {
        const x = Math.max(0, Math.min(event.x, 200));
        const value = x / 200;
        updateSlider(value);
    }

    // Функции масштабирования
    function zoom(scaleDelta) {
        currentScale = Math.min(3, Math.max(0.5, currentScale + scaleDelta));
        g.transition()
            .duration(200)
            .attr("transform", `scale(${currentScale})`);
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

    // Функции для перемещения графа
    function dragStarted(event) {
        svg.style("cursor", "grabbing");
        g.selectAll("circle").style("pointer-events", "none");
        g.selectAll("text").style("pointer-events", "none");
    }

    function dragged(event) {
        const transform = d3.zoomTransform(svg.node());
        g.attr("transform", `
            translate(${transform.x + event.dx},${transform.y + event.dy})
            scale(${currentScale})
        `);
    }

    function dragEnded() {
        svg.style("cursor", "default");
        g.selectAll("circle").style("pointer-events", "all");
        g.selectAll("text").style("pointer-events", "all");
    }
});