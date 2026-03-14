/**
 * D3 dropdowns: chart type, source, variable, transform.
 * Uses data join for options.
 */

import * as d3 from 'd3'
import { transformLabelScale } from './scales.js'
import type { Manifest, SelectionState, MapExtent, AcsGeography, MbtaOverlay } from '../manifest.js'

/** Extent options for choropleth view (Boston zoom vs whole area). */
const EXTENT_OPTIONS: { id: MapExtent; label: string }[] = [
  { id: 'whole', label: 'Whole area' },
  { id: 'boston', label: 'Boston zoom' },
]

/** ACS geography options (interactive only): unified 2010 vs native census boundaries. */
const ACS_GEOGRAPHY_OPTIONS: { id: AcsGeography; label: string }[] = [
  { id: 'unified_2010', label: 'Unified 2010' },
  { id: 'native', label: 'Native census geography' },
]

/** MBTA overlay options: none, major routes only, or major + bus routes. */
const MBTA_OVERLAY_OPTIONS: { id: MbtaOverlay; label: string }[] = [
  { id: 'none', label: 'None' },
  { id: 'major', label: 'Major Routes' },
  { id: 'major_and_bus', label: 'Major and Bus Routes' },
]

const SOURCE_LABELS: Record<string, string> = {
  acs: 'ACS',
  decennial: 'Decennial',
  decennial_extras: 'Decennial (extras)',
}

function getSourceData(manifest: Manifest, chartType: string) {
  const chart = manifest[chartType as keyof Manifest] as Record<string, { variables: unknown[] }> | undefined
  if (!chart || typeof chart !== 'object') return []
  const ids = ['acs', 'decennial', 'decennial_extras'] as const
  return ids
    .filter((id) => chart[id]?.variables?.length)
    .map((id) => ({ id, label: SOURCE_LABELS[id] ?? id }))
}

function getChartTypeData(manifest: Manifest) {
  return manifest.chartTypes.map((id) => ({
    id,
    label: id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  }))
}

function getVariableData(manifest: Manifest, chartType: string, source: string) {
  const chart = manifest[chartType as keyof Manifest] as Record<string, { variables: { id: string; label: string }[] }> | undefined
  if (!chart || typeof chart !== 'object') return []
  const data = chart[source]
  let vars = (data?.variables ?? []).map((v) => ({ id: v.id, label: v.label }))
  // Choropleth: decennial dropdown must not show extras variables (only in Decennial (extras) source)
  if (chartType === 'choropleth' && source === 'decennial') {
    const extrasIds = new Set(
      (chart['decennial_extras']?.variables ?? []).map((v: { id: string }) => v.id)
    )
    vars = vars.filter((v) => !extrasIds.has(v.id))
  }
  return vars
}

function getTransformData(manifest: Manifest, chartType: string, source: string, variable: string) {
  const chart = manifest[chartType as keyof Manifest] as Record<string, { variables: { id: string; transforms?: string[] }[] }> | undefined
  if (!chart || typeof chart !== 'object') return []
  const data = chart[source]
  const v = data?.variables?.find((x) => x.id === variable)
  const transforms = v?.transforms ?? ['default']
  return transforms.map((t) => ({ id: t, label: transformLabelScale(t) ?? t }))
}

/** Options for renderDropdowns (e.g. show geography dropdown on interactive page). */
export interface RenderDropdownsOptions {
  /** Show extent dropdown (Whole area / Boston zoom). Hidden on interactive page (user zooms manually). */
  showExtent?: boolean
  /** Show ACS geography dropdown (unified 2010 vs native). Interactive page only. */
  showGeography?: boolean
  /** Show MBTA overlay dropdown (None / Major / Major+Bus). Interactive page only. */
  showMbtaOverlay?: boolean
}

/** Render all dropdowns. */
export function renderDropdowns(
  root: d3.Selection<d3.BaseType, unknown, null, undefined>,
  manifest: Manifest,
  selection: SelectionState,
  onChange: (s: Partial<SelectionState>) => void,
  options?: RenderDropdownsOptions
): void {
  const controls = root
    .selectAll<HTMLDivElement, unknown>('.controls')
    .data([null])
    .join((enter) => enter.append('div').attr('class', 'controls'))

  const chartTypes = getChartTypeData(manifest)
  const sources = getSourceData(manifest, selection.chartType)
  const variables = getVariableData(manifest, selection.chartType, selection.source)
  // If current variable was filtered out (e.g. extras in decennial), reset to first valid
  const validVar = variables.find((v) => v.id === selection.variable)
  if (variables.length && !validVar) {
    const chart = manifest[selection.chartType as keyof Manifest] as Record<string, { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] }> | undefined
    const src = chart?.[selection.source]
    const vv = src?.variables?.find((x) => x.id === variables[0].id)
    onChange({
      variable: variables[0].id,
      variableLabel: variables[0].label,
      transform: vv?.transforms?.[0] ?? 'default',
      year: vv?.years?.[0] ?? selection.year,
      years: vv?.years ?? selection.years,
    })
  }
  const transforms = getTransformData(manifest, selection.chartType, selection.source, selection.variable)

  // Chart type
  renderSelect(controls, 'chart-type', 'Chart Type', chartTypes, selection.chartType, (id) => {
    const chart = manifest[id as keyof Manifest] as Record<string, { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] }> | undefined
    if (!chart) return
    const newSources = getSourceData(manifest, id)
    const srcKey = newSources.find((s) => chart[s.id]?.variables?.length)?.id ?? 'acs'
    const src = chart[srcKey]
    const vars = src?.variables ?? []
    const first = vars[0]
    const years = first?.years ?? []
    const firstYear = years[0] ?? new Date().getFullYear()
    const transforms = first?.transforms ?? ['default']
    onChange({
      chartType: id,
      source: srcKey as 'acs' | 'decennial' | 'decennial_extras',
      variable: first?.id ?? '',
      variableLabel: first?.label ?? '',
      transform: transforms[0] ?? 'default',
      year: firstYear,
      years,
    })
  })

  // Source
  renderSelect(controls, 'source', 'Data Source', sources, selection.source, (id) => {
    const chart = manifest[selection.chartType as keyof Manifest] as Record<string, { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] }> | undefined
    if (!chart) return
    const src = chart[id]
    const vars = src?.variables ?? []
    const first = vars[0]
    const years = first?.years ?? []
    const firstYear = years[0] ?? new Date().getFullYear()
    const transforms = first?.transforms ?? ['default']
    onChange({
      source: id as 'acs' | 'decennial' | 'decennial_extras',
      variable: first?.id ?? '',
      variableLabel: first?.label ?? '',
      transform: transforms[0] ?? 'default',
      year: firstYear,
      years,
    })
  })

  // Variable
  renderSelect(controls, 'variable', 'Variable', variables, selection.variable, (id) => {
    const v = variables.find((x) => x.id === id)
    if (!v) return
    const chart = manifest[selection.chartType as keyof Manifest] as Record<string, { variables: { id: string; label: string; transforms?: string[]; years: number[] }[] }> | undefined
    if (!chart) return
    const src = chart[selection.source]
    const vars = src?.variables ?? []
    const vv = vars.find((x) => x.id === id)
    const years = vv?.years ?? []
    const firstYear = years[0] ?? new Date().getFullYear()
    const transforms = vv?.transforms ?? ['default']
    onChange({
      variable: id,
      variableLabel: v.label,
      transform: transforms[0] ?? 'default',
      year: firstYear,
      years,
    })
  })

  // Extent (choropleth only): Boston zoom vs whole area. Hidden on interactive page (user zooms manually).
  const showExtent = options?.showExtent ?? true
  const extentContainer = controls
    .selectAll<HTMLDivElement, boolean>('.extent-container')
    .data([showExtent && selection.chartType === 'choropleth'])
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', 'extent-container')
          .style('display', (d) => (d ? 'block' : 'none')),
      (update) => update.style('display', (d) => (d ? 'block' : 'none')),
      (exit) => exit.remove()
    )

  extentContainer.each(function (show) {
    if (show) {
      const extent = selection.extent ?? 'whole'
      renderSelect(
        d3.select(this),
        'extent',
        'View',
        EXTENT_OPTIONS,
        extent,
        (id) => onChange({ extent: id as MapExtent })
      )
    }
  })

  // ACS geography (interactive only, ACS choropleth): unified 2010 vs native
  const showGeography = options?.showGeography ?? false
  const geographyContainer = controls
    .selectAll<HTMLDivElement, boolean>('.geography-container')
    .data([showGeography && selection.chartType === 'choropleth' && selection.source === 'acs'])
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', 'geography-container')
          .style('display', (d) => (d ? 'block' : 'none')),
      (update) => update.style('display', (d) => (d ? 'block' : 'none')),
      (exit) => exit.remove()
    )

  geographyContainer.each(function (show) {
    if (show) {
      const acsGeography = selection.acsGeography ?? 'unified_2010'
      renderSelect(
        d3.select(this),
        'geography',
        'Geography',
        ACS_GEOGRAPHY_OPTIONS,
        acsGeography,
        (id) => onChange({ acsGeography: id as AcsGeography })
      )
    }
  })

  // MBTA overlay (interactive choropleth only): None, Major Routes, Major and Bus Routes
  const showMbtaOverlay = options?.showMbtaOverlay ?? false
  const mbtaOverlayContainer = controls
    .selectAll<HTMLDivElement, boolean>('.mbta-overlay-container')
    .data([showMbtaOverlay && selection.chartType === 'choropleth'])
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', 'mbta-overlay-container')
          .style('display', (d) => (d ? 'block' : 'none')),
      (update) => update.style('display', (d) => (d ? 'block' : 'none')),
      (exit) => exit.remove()
    )

  mbtaOverlayContainer.each(function (show) {
    if (show) {
      const mbtaOverlay = selection.mbtaOverlay ?? 'major'
      renderSelect(
        d3.select(this),
        'mbta-overlay',
        'MBTA Overlay',
        MBTA_OVERLAY_OPTIONS,
        mbtaOverlay,
        (id) => onChange({ mbtaOverlay: id as MbtaOverlay })
      )
    }
  })

  // Transform/View (only if multiple): per_aland, proportion, etc. toggled here, not in variable name.
  // For choropleth, label as "View" so users toggle display (Count, Per sq m, Proportion) separately from variable.
  const showTransform = transforms.length > 1
  const transformLabel =
    selection.chartType === 'choropleth' ? 'View' : 'Transform'
  const transformContainer = controls
    .selectAll<HTMLDivElement, boolean>('.transform-container')
    .data([showTransform])
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', 'transform-container')
          .style('display', (d) => (d ? 'block' : 'none')),
      (update) => update.style('display', (d) => (d ? 'block' : 'none')),
      (exit) => exit.remove()
    )

  transformContainer.each(function (show) {
    if (show) {
      renderSelect(
        d3.select(this),
        'transform',
        transformLabel,
        transforms,
        selection.transform,
        (id) => onChange({ transform: id })
      )
    }
  })
}

function renderSelect(
  parent: d3.Selection<d3.BaseType, unknown, null, undefined>,
  id: string,
  label: string,
  options: { id: string; label: string }[],
  value: string,
  onChange: (id: string) => void
): void {
  const wrap = parent
    .selectAll<HTMLDivElement, string>(`div.${id}-wrap`)
    .data([id])
    .join(
      (enter) =>
        enter
          .append('div')
          .attr('class', `${id}-wrap`)
          .style('display', 'inline-block')
          .style('margin-right', '7px')
          .style('margin-bottom', '5px'),
      (update) => update,
      (exit) => exit.remove()
    )

  wrap.selectAll('label').data([label]).join('label').text((d) => d).attr('for', `${id}-select`)

  const select = wrap
    .selectAll<HTMLSelectElement, string[]>(`select#${id}-select`)
    .data([options])
    .join(
      (enter) =>
        enter
          .append('select')
          .attr('id', `${id}-select`)
          .attr('class', 'chart-select')
          .style('margin-left', '2px')
          .style('padding', '2px 5px')
          .on('change', function () {
            const id = (this as HTMLSelectElement).value
            onChange(id)
          }),
      (update) => update,
      (exit) => exit.remove()
    )

  const opts = select
    .selectAll<HTMLOptionElement, { id: string; label: string }>('option')
    .data(options, (d) => d.id)
    .join(
      (enter) =>
        enter
          .append('option')
          .attr('value', (d) => d.id)
          .text((d) => d.label),
      (update) => update.text((d) => d.label),
      (exit) => exit.remove()
    )

  select.property('value', value)
}
