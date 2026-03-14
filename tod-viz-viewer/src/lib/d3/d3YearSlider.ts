/**
 * D3 year slider: scalePoint, axis, brush for selecting year.
 */

import * as d3 from 'd3'
import { yearFormat } from './scales.js'

const SLIDER_WIDTH = 600
const SLIDER_HEIGHT = 60
const THUMB_R = 8

/** Render the year slider. */
export function renderYearSlider(
  root: d3.Selection<d3.BaseType, unknown, null, undefined>,
  years: number[],
  selectedYear: number,
  onChange: (year: number) => void
): void {
  if (years.length === 0) return

  const minYear = Math.min(...years)
  const maxYear = Math.max(...years)
  const domainMax = minYear === maxYear ? minYear + 1 : maxYear
  const scale = d3
    .scaleLinear<number>()
    .domain([minYear, domainMax])
    .range([THUMB_R, SLIDER_WIDTH - THUMB_R])
    .clamp(true)

  /** Find nearest year for a pixel position. */
  const yearAtPos = (px: number) => {
    const val = scale.invert(px)
    return years.reduce((a, b) =>
      Math.abs(b - val) < Math.abs(a - val) ? b : a
    )
  }

  const svg = root
    .selectAll<SVGSVGElement, number[]>('svg.year-slider')
    .data([years])
    .join(
      (enter) =>
        enter
          .append('svg')
          .attr('class', 'year-slider')
          .attr('width', SLIDER_WIDTH)
          .attr('height', SLIDER_HEIGHT),
      (update) => update,
      (exit) => exit.remove()
    )

  svg.selectAll('*').remove()

  const g = svg.append('g').attr('transform', `translate(0, ${THUMB_R})`)

  // Track line
  g.append('line')
    .attr('x1', THUMB_R)
    .attr('x2', SLIDER_WIDTH - THUMB_R)
    .attr('y1', 0)
    .attr('y2', 0)
    .attr('stroke', '#ccc')
    .attr('stroke-width', 2)

  // Axis - show each year as a tick
  const axis = d3
    .axisBottom(scale)
    .tickValues(years)
    .tickFormat((d) => yearFormat(d as number))
    .tickSizeOuter(0)
    .tickSizeInner(4)

  g.append('g')
    .attr('transform', `translate(0, 20)`)
    .call(axis)
    .selectAll('text')
    .attr('font-size', '10px')

  // Clickable track (append BEFORE thumb so thumb is on top and receives drag)
  g
    .append('rect')
    .attr('x', THUMB_R)
    .attr('y', -THUMB_R - 4)
    .attr('width', SLIDER_WIDTH - 2 * THUMB_R)
    .attr('height', THUMB_R * 2 + 8)
    .attr('fill', 'transparent')
    .style('cursor', 'pointer')
    .style('pointer-events', 'all')
    .on('click', function (event) {
      event.stopPropagation()
      const [px] = d3.pointer(event, svg.node())
      const nearest = yearAtPos(px)
      onChange(nearest)
    })

  // Thumb (draggable circle) - on top so it receives drag events
  const x = scale(selectedYear) ?? SLIDER_WIDTH / 2

  const thumb = g
    .append('circle')
    .attr('class', 'year-thumb')
    .attr('cx', x)
    .attr('cy', 0)
    .attr('r', THUMB_R)
    .attr('fill', '#4a90d9')
    .attr('stroke', '#2a70b9')
    .attr('stroke-width', 2)
    .style('cursor', 'grab')
    .style('pointer-events', 'all')
    .call(
      d3
        .drag<SVGCircleElement, unknown>()
        .subject(function () {
          const el = this
          return { x: parseFloat(d3.select(el).attr('cx')), y: 0 }
        })
        .on('drag', function (event) {
          const [px] = d3.pointer(event, svg.node())
          const clampedX = Math.max(THUMB_R, Math.min(SLIDER_WIDTH - THUMB_R, px))
          d3.select(this).attr('cx', clampedX)
          onChange(yearAtPos(clampedX))
        })
        .on('end', function (event) {
          const [px] = d3.pointer(event, svg.node())
          const clampedX = Math.max(THUMB_R, Math.min(SLIDER_WIDTH - THUMB_R, px))
          onChange(yearAtPos(clampedX))
        })
    )
}
