---
layout: page
title: Bibliometrics
permalink: /bibliometrics/
nav: true
nav_order: 3
---

<div id="loading" style="text-align:center; padding: 2rem; color: #888;">
  Loading data...
</div>

<div id="charts" style="display:none;">

  <h3>Scientific production</h3>
  <div id="chart-pub-year"></div>

  <h3>Top journals</h3>
  <div id="chart-journals"></div>

  <h3>Research topics</h3>
  <div id="chart-concepts"></div>

  <h3>Co-authorship network</h3>
  <div id="chart-network"></div>

</div>

<script src="https://cdn.jsdelivr.net/npm/plotly.js@3.0.1/dist/plotly.min.js"></script>
<script>
fetch('/assets/data/biblio_stats.json')
  .then(r => r.json())
  .then(data => {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('charts').style.display = 'block';

    const blue = '#2e4283';
    const layout_base = {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor:  'rgba(0,0,0,0)',
      font: { family: 'inherit' }
    };

    // per year production
    Plotly.newPlot('chart-pub-year', [
    {
        x: Object.keys(data.publications_per_year),
        y: Object.values(data.publications_per_year),
        type: 'bar',
        name: 'Publications',
        marker: { color: 'rgba(46, 66, 131, 0.5)' }
    },
    {
        x: Object.keys(data.citations_per_year),
        y: Object.values(data.citations_per_year),
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Citations',
        yaxis: 'y2',
        line: { color: '#e07b2e', width: 2 },
        marker: { color: '#e07b2e' }
    }
    ], Object.assign({}, layout_base, {
    yaxis:  { title: 'Publications', rangemode: 'tozero' },
    yaxis2: { 
        title: 'Citations', 
        overlaying: 'y', 
        side: 'right',
        showgrid: false,
        rangemode: 'tozero',
    },
    legend: { orientation: 'h' },
    shapes: [
        {
        type: 'line',
        x0: '2014', x1: '2014',
        y0: 0, y1: 1,
        yref: 'paper',
        line: { color: '#2a9d8f', width: 2, dash: 'dot' }
        },
        {
        type: 'line',
        x0: '2019', x1: '2019',
        y0: 0, y1: 1,
        yref: 'paper',
        line: { color: '#2a9d8f', width: 2, dash: 'dot' }
        }
    ],
    annotations: [
        {
        x: '2014', y: 1,
        yref: 'paper',
        text: 'C2MC',
        showarrow: false,
        xanchor: 'left',
        yanchor: 'bottom',
        font: { color: '#2a9d8f', size: 11 },
        textangle: 0
        },
        {
        x: '2019', y: 1,
        yref: 'paper',
        text: 'iC2MC',
        showarrow: false,
        xanchor: 'left',
        yanchor: 'bottom',
        font: { color: '#2a9d8f', size: 11 },
        textangle: 0
        }
    ]
    }));

    // Top journaux
    const journals = Object.entries(data.top_journals)
      .sort((a, b) => a[1] - b[1]);
    Plotly.newPlot('chart-journals', [{
      x: journals.map(j => j[1]),
      y: journals.map(j => j[0]),
      type: 'bar',
      orientation: 'h',
      marker: { color: blue }
    }], { ...layout_base,
      margin: { l: 250 },
      xaxis: { title: 'Publications' }
    });

    // Concepts — treemap
    const concepts = Object.entries(data.concepts).slice(0, 30);
    Plotly.newPlot('chart-concepts', [{
      type: 'treemap',
      labels: concepts.map(c => c[0]),
      parents: concepts.map(() => ''),
      values: concepts.map(c => c[1]),
      marker: { colorscale: [[0, '#c8d0e8'], [1, blue]] }
    }], { ...layout_base, margin: { t: 0 } });

    // Réseau de co-auteurs
    const network = data.coauthor_network;
    const mainAuthors = new Set(network.main_authors);

    // Construire les nœuds
    const authorCounts = network.author_pub_count;
    const nodes = Object.keys(authorCounts);

    // Layout circulaire simple
    const n = nodes.length;
    const nodeX = {}, nodeY = {};
    nodes.forEach((name, i) => {
    const angle = (2 * Math.PI * i) / n;
    nodeX[name] = Math.cos(angle);
    nodeY[name] = Math.sin(angle);
    });

    // Liens
    const linkTraces = Object.entries(network.links).map(([key, weight]) => {
    const [a1, a2] = key.split('|');
    if (!nodeX[a1] || !nodeX[a2]) return null;
    return {
        type: 'scatter',
        x: [nodeX[a1], nodeX[a2], null],
        y: [nodeY[a1], nodeY[a2], null],
        mode: 'lines',
        line: { width: Math.min(weight, 8), color: 'rgba(46, 66, 131, 0.2)' },
        hoverinfo: 'none',
        showlegend: false
    };
    }).filter(Boolean);

    // Nœuds
    const nodeTrace = {
    type: 'scatter',
    x: nodes.map(n => nodeX[n]),
    y: nodes.map(n => nodeY[n]),
    mode: 'markers+text',
    text: nodes,
    textposition: 'top center',
    hovertext: nodes.map(n => `${n}: ${authorCounts[n]} publications`),
    hoverinfo: 'text',
    marker: {
        size: nodes.map(n => Math.max(8, Math.min(30, authorCounts[n] * 2))),
        color: nodes.map(n => mainAuthors.has(n) ? blue : 'rgba(46, 66, 131, 0.3)'),
        line: { width: 1, color: blue }
    },
    showlegend: false
    };

    Plotly.newPlot('chart-network',
    [...linkTraces, nodeTrace],
    Object.assign({}, layout_base, {
        height: 600,
        xaxis: { showgrid: false, zeroline: false, showticklabels: false },
        yaxis: { showgrid: false, zeroline: false, showticklabels: false },
        margin: { t: 20, b: 20, l: 20, r: 20 }
    })
    );


  });
</script>