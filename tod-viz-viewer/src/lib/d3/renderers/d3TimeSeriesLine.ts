/**
 * D3 time-series line chart: selected block group vs weighted average across all block groups.
 * Weighting: per_population -> population-weighted; per_aland/raw/count/default -> land-area-weighted.
 */

import * as d3 from 'd3'

/** Sq m to sq mi conversion factor. */
const SQ_M_TO_SQ_MI = 1 / (1609.344 * 1609.344)

export interface TimeSeriesData {
  geoids: string[]
  years: number[]
  values: Record<string, (number | null)[]>
  population?: Record<string, (number | null)[]>
  landArea: number[]
  variableLabel: string
  transform: string
}

/**
 * Compute weighted average across block groups for each year.
 * per_population: population-weighted; per_aland/raw/count/default: land-area-weighted.
 */
function computeWeightedAverages(
  data: TimeSeriesData
): { year: number; avg: number }[] {
  const { years, values, population, landArea, transform } = data
  const usePopWeight = transform === 'per_population'
  const weights = usePopWeight ? population : undefined

  return years.map((year) => {
    const vals = values[String(year)]
    if (!vals) return { year, avg: NaN }

    let sumWv = 0
    let sumW = 0
    for (let i = 0; i < vals.length; i++) {
      const v = vals[i]
      if (v == null || !Number.isFinite(v)) continue
      const w = usePopWeight
        ? (weights?.[String(year)]?.[i] ?? 0)
        : (landArea?.[i] ?? 0)
      const weight = w > 0 ? w : 1
      sumWv += v * weight
      sumW += weight
    }
    const avg = sumW > 0 ? sumWv / sumW : NaN
    return { year, avg }
  })
}

/**
 * Render a time-series line chart: selected block group + weighted average.
 *
 * @param container - Parent element for the chart
 * @param data - Variable data with values, population, land area
 * @param selectedGeoid - GEOID of the clicked block group
 */
export function renderTimeSeriesLine(
  container: HTMLElement,
  data: TimeSeriesData,
  selectedGeoid: string
): void {
  const idx = data.geoids.indexOf(selectedGeoid)
  if (idx < 0) return

  const selectedSeries = data.years.map((year) => {
    const vals = data.values[String(year)]
    const v = vals?.[idx]
    return { year, value: v != null && Number.isFinite(v) ? v : null }
  })

  const avgSeries = computeWeightedAverages(data)

  const margin = { top: 20, right: 30, bottom: 40, left: 50 }
  const width = Math.max(300, container.clientWidth || 400) - margin.left - margin.right
  const height = 220 - margin.top - margin.bottom

  d3.select(container).selectAll('*').remove()

  const svg = d3
    .select(container)
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .attr('viewBox', [0, 0, width + margin.left + margin.right, height + margin.top + margin.bottom])

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  const allValues = [
    ...selectedSeries.map((d) => d.value).filter((v): v is number => v != null),
    ...avgSeries.map((d) => d.avg).filter(Number.isFinite),
  ]
  const yMin = allValues.length ? Math.min(...allValues) : 0
  const yMax = allValues.length ? Math.max(...allValues) : 1
  const yPadding = (yMax - yMin) * 0.05 || 0.1
  const yDomain = [Math.max(0, yMin - yPadding), yMax + yPadding]

  const xScale = d3
    .scaleLinear()
    .domain([Math.min(...data.years), Math.max(...data.years)])
    .range([0, width])

  const yScale = d3.scaleLinear().domain(yDomain).range([height, 0])

  const line = d3
    .line<{ year: number; value: number | null }>()
    .x((d) => xScale(d.year))
    .y((d) => (d.value != null ? yScale(d.value) : height))
    .defined((d) => d.value != null && Number.isFinite(d.value))

  const avgLine = d3
    .line<{ year: number; avg: number }>()
    .x((d) => xScale(d.year))
    .y((d) => (Number.isFinite(d.avg) ? yScale(d.avg) : height))
    .defined((d) => Number.isFinite(d.avg))

  g.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale).tickFormat(d3.format('d')))
    .selectAll('text')
    .style('font-size', '10px')

  g.append('g').call(d3.axisLeft(yScale).tickSize(-width).tickFormat(d3.format('.2f'))).selectAll('text').style('font-size', '10px')

  g.append('path')
    .datum(selectedSeries)
    .attr('fill', 'none')
    .attr('stroke', '#3182bd')
    .attr('stroke-width', 2)
    .attr('stroke-linecap', 'round')
    .attr('stroke-linejoin', 'round')
    .attr('d', line)

  g.append('path')
    .datum(avgSeries)
    .attr('fill', 'none')
    .attr('stroke', '#636363')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '4,4')
    .attr('stroke-linecap', 'round')
    .attr('stroke-linejoin', 'round')
    .attr('d', avgLine)

  const legend = g.append('g').attr('transform', `translate(${width - 120}, 0)`).attr('class', 'legend')
  legend
    .append('line')
    .attr('x1', 0)
    .attr('x2', 24)
    .attr('y1', 0)
    .attr('y2', 0)
    .attr('stroke', '#3182bd')
    .attr('stroke-width', 2)
  legend.append('text').attr('x', 28).attr('y', 4).attr('font-size', '10px').text('Selected BG')

  legend
    .append('line')
    .attr('x1', 0)
    .attr('x2', 24)
    .attr('y1', 16)
    .attr('y2', 16)
    .attr('stroke', '#636363')
    .attr('stroke-width', 1.5)
    .attr('stroke-dasharray', '4,4')
  legend.append('text').attr('x', 28).attr('y', 20).attr('font-size', '10px').text('Weighted avg')
}
