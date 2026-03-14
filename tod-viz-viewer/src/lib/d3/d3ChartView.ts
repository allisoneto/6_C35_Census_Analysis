/**
 * D3 chart view: displays either an image (PNG) or a D3-rendered chart.
 * Consumes VisualizationSpec from the active renderer.
 */

import * as d3 from 'd3'
import type { SelectionState, VisualizationSpec } from '../manifest.js'

const TRANSITION_MS = 150

/** Render the chart area based on spec. */
export function renderChartView(
  root: d3.Selection<d3.BaseType, unknown, null, undefined>,
  spec: VisualizationSpec,
  year: number,
  selection: SelectionState
): void {
  // Key by URL so D3 detects changes when year/variable changes
  const container = root
    .selectAll<HTMLDivElement, VisualizationSpec>('.chart-view-container')
    .data([spec], (d) => (d.type === 'image' ? d.url : 'd3'))
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', 'chart-view-container')
          .style('position', 'relative')
          .style('min-height', '400px'),
      (update) => update,
      (exit) => exit.remove()
    )

  container.each(function (d) {
    const sel = d3.select(this)
    sel.selectAll('*').remove()

    if (d.type === 'image') {
      const img = sel
        .append('img')
        .attr('alt', `Census visualization ${year}`)
        .attr('src', d.url)
        .style('max-width', '100%')
        .style('height', 'auto')
        .style('opacity', 0)
        .on('error', function () {
          d3.select(this).style('display', 'none')
          sel
            .append('div')
            .attr('class', 'image-error')
            .style('padding', '2rem')
            .style('color', '#666')
            .style('text-align', 'center')
            .text('Image not found. Run the visualization scripts to generate.')
        })

      img
        .transition()
        .duration(TRANSITION_MS)
        .style('opacity', 1)
    } else if (d.type === 'd3') {
      const div = sel
        .append('div')
        .style('width', '100%')
        .style('min-height', '400px')
      if (div.node()) {
        d.render(div.node(), selection)
      }
    }
  })
}
