/**
 * Types for the census visualization manifest and selection state.
 */

export interface ManifestVariable {
  id: string
  label: string
  transforms?: string[]
  years: number[]
}

export interface ManifestSourceData {
  variables: ManifestVariable[]
}

export interface ManifestChartType {
  acs: ManifestSourceData
  decennial: ManifestSourceData
  decennial_extras?: ManifestSourceData
}

export interface Manifest {
  chartTypes: string[]
  choropleth: ManifestChartType
  pie_chart: ManifestChartType
  bar_chart: ManifestChartType
  stacked_bar: ManifestChartType
  scatter: ManifestChartType
}

/** Map extent: whole area or zoomed-in Boston (MBTA rapid transit core). */
export type MapExtent = 'whole' | 'boston'

/** ACS geography: unified 2010 boundaries (many nulls in 2022+) or native census boundaries (changes at 2020). */
export type AcsGeography = 'unified_2010' | 'native'

/** MBTA overlay mode: none, major routes only (excludes bus), or major + bus routes. */
export type MbtaOverlay = 'none' | 'major' | 'major_and_bus'

/** Selection state passed to D3 and renderers. */
export interface SelectionState {
  chartType: string
  source: 'acs' | 'decennial' | 'decennial_extras'
  variable: string
  variableLabel: string
  transform: string
  /** Map extent for choropleth: whole region or Boston zoom. Default 'whole'. */
  extent?: MapExtent
  /** ACS geography (interactive only): unified 2010 or native. Default 'unified_2010'. */
  acsGeography?: AcsGeography
  /** MBTA overlay (choropleth only): none, major routes, or major + bus. Default 'major'. */
  mbtaOverlay?: MbtaOverlay
  year: number
  years: number[]
  imagePath: string
}

/** Unified spec for chart display: either image URL or D3 render function. */
export type VisualizationSpec =
  | { type: 'image'; url: string }
  | { type: 'd3'; render: (container: HTMLElement, selection: SelectionState) => void }

/** Renderer: (selection, manifest) => VisualizationSpec */
export type Renderer = (
  selection: SelectionState,
  manifest: Manifest
) => VisualizationSpec
