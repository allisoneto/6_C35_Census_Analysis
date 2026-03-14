/**
 * D3 choropleth renderer: native map with zoom, TOD markers, smooth year transitions.
 * Uses precomputed variable JSON; year changes update fill via D3 transition (no black flash).
 * Block group tooltip on hover; click shows time-series line chart below.
 */

import * as d3 from 'd3'
import type { SelectionState } from '../../manifest.js'
import { renderTimeSeriesLine, type TimeSeriesData } from './d3TimeSeriesLine.js'

const TRANSITION_MS = 150
/** Sq m to sq mi for tooltip display. */
const SQ_M_TO_SQ_MI = 1 / (1609.344 * 1609.344)
const MISSING_COLOR = '#e0e0e0'

/** Boston zoom bounds (lon, lat): west, south, east, north. Matches visualization/utils.py BOSTON_ZOOM_BOUNDS_WGS84. */
const BOSTON_ZOOM_BOUNDS: [number, number, number, number] = [-71.17, 42.3, -71.04, 42.4]

/** GeoJSON polygon for Boston extent (used to fit projection when extent=boston). */
const BOSTON_EXTENT_GEO: GeoJSON.Polygon = {
  type: 'Polygon',
  coordinates: [
    [
      [BOSTON_ZOOM_BOUNDS[0], BOSTON_ZOOM_BOUNDS[1]],
      [BOSTON_ZOOM_BOUNDS[2], BOSTON_ZOOM_BOUNDS[1]],
      [BOSTON_ZOOM_BOUNDS[2], BOSTON_ZOOM_BOUNDS[3]],
      [BOSTON_ZOOM_BOUNDS[0], BOSTON_ZOOM_BOUNDS[3]],
      [BOSTON_ZOOM_BOUNDS[0], BOSTON_ZOOM_BOUNDS[1]],
    ],
  ],
}

/** GTFS route_type 3 = Bus. Major routes exclude bus. */
const ROUTE_TYPE_BUS = 3

/** Massachusetts county FIPS to name (fallback when metadata lookup fails). Matches export_d3_data.py MA_COUNTY_NAMES. */
const MA_COUNTY_NAMES: Record<string, string> = {
  '001': 'Barnstable',
  '003': 'Berkshire',
  '005': 'Bristol',
  '007': 'Dukes',
  '009': 'Essex',
  '011': 'Franklin',
  '013': 'Hampden',
  '015': 'Hampshire',
  '017': 'Suffolk',
  '019': 'Nantucket',
  '021': 'Middlesex',
  '023': 'Plymouth',
  '025': 'Norfolk',
  '027': 'Worcester',
}

/** Base sizes for zoom-invariant rendering (scaled by 1/k in zoom handler). */
const BG_STROKE_BASE = 0.3
const LINE_STROKE_BASE = 3
const STOP_R_BASE = 4
const STOP_STROKE_BASE = 1
const TOD_R_BASE = 5

/** Stop-route point for overlay (lon, lat, route_color, route_type, route_id, stop_name, route_label). */
interface MbtaStopPoint {
  lon: number
  lat: number
  route_color: string
  route_type: number
  route_id: string
  stop_name: string
  route_label: string
}

/** Block group metadata: population by year, land area, county for tooltip and time-series. */
interface BlockGroupMetadata {
  geoids: string[]
  years: number[]
  population: Record<string, (number | null)[]>
  land_area: number[]
  county_fips: string[]
  county_name: string[]
}

/** Cached data to avoid refetch on year change. */
const cache = {
  geo: {} as Record<string, GeoJSON.FeatureCollection>,
  mbta: null as GeoJSON.FeatureCollection | null,
  stops: null as MbtaStopPoint[] | null,
  variable: {} as Record<string, VariableData>,
  tod: null as TodProject[] | null,
  metadata: {} as Record<string, BlockGroupMetadata>,
}

interface VariableData {
  geoids: string[]
  years: number[]
  values: Record<string, (number | null)[]>
  vmin: number
  vmax: number
}

interface TodProject {
  year: number
  name: string
  address: string
  city?: string
  lat: number
  lon: number
  source: string
  tod_type?: string
}

/** Geo cache key: acs uses 'acs' or 'acs_native' by geography; decennial uses 'decennial'. */
function geoKey(selection: SelectionState): string {
  if (selection.source === 'acs') {
    return (selection.acsGeography ?? 'unified_2010') === 'native' ? 'acs_native' : 'acs'
  }
  return selection.source === 'decennial_extras' ? 'decennial_extras' : 'decennial'
}

function geoUrl(selection: SelectionState): string {
  const key = geoKey(selection)
  if (key === 'acs_native') {
    return '/data/geo/block_groups_acs_overlap_2020.geojson'
  }
  if (key === 'acs') {
    return '/data/geo/block_groups_acs_overlap.geojson'
  }
  return '/data/geo_decennial/block_groups_decennial_merged.geojson'
}

/** Variable JSON URL: acs_native uses acs_native_{var}_{transform}.json */
function variableUrl(selection: SelectionState): string {
  if (selection.source === 'acs' && (selection.acsGeography ?? 'unified_2010') === 'native') {
    return `/data/choropleth/acs_native_${selection.variable}_${selection.transform}.json`
  }
  return `/data/choropleth/${selection.source}_${selection.variable}_${selection.transform}.json`
}

/** Variable cache key (must match variableUrl). */
function variableKey(selection: SelectionState): string {
  if (selection.source === 'acs' && (selection.acsGeography ?? 'unified_2010') === 'native') {
    return `acs_native_${selection.variable}_${selection.transform}`
  }
  return `${selection.source}_${selection.variable}_${selection.transform}`
}

/** Metadata JSON URL for tooltip and time-series (population, land area, county). */
function metadataUrl(selection: SelectionState): string {
  const key = geoKey(selection)
  const name = key === 'acs_native' ? 'block_groups_acs_native_metadata' : `block_groups_${key}_metadata`
  return `/data/metadata/${name}.json`
}

async function loadMetadata(selection: SelectionState): Promise<BlockGroupMetadata | null> {
  const key = geoKey(selection)
  if (cache.metadata[key]) return cache.metadata[key]
  try {
    const data = await fetchJson<BlockGroupMetadata>(metadataUrl(selection))
    cache.metadata[key] = data
    return data
  } catch {
    return null
  }
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`)
  return res.json()
}

async function loadGeo(selection: SelectionState): Promise<GeoJSON.FeatureCollection> {
  const key = geoKey(selection)
  if (cache.geo[key]) return cache.geo[key]
  const geo = await fetchJson<GeoJSON.FeatureCollection>(geoUrl(selection))
  cache.geo[key] = geo
  return geo
}

async function loadMbta(): Promise<GeoJSON.FeatureCollection | null> {
  if (cache.mbta !== null) return cache.mbta
  try {
    cache.mbta = await fetchJson<GeoJSON.FeatureCollection>('/data/lines/lines.geojson')
  } catch {
    cache.mbta = null
  }
  return cache.mbta
}

/** Extract lon, lat from GeoJSON feature (properties or geometry). */
function extractLonLat(f: GeoJSON.Feature): [number, number] | null {
  const p = f.properties
  let lon = p?.station_longitude ?? p?.lon ?? p?.longitude
  let lat = p?.station_latitude ?? p?.lat ?? p?.latitude
  if (lon != null && lat != null) return [Number(lon), Number(lat)]
  const geom = f.geometry
  if (!geom) return null
  if (geom.type === 'Point' && Array.isArray(geom.coordinates) && geom.coordinates.length >= 2) {
    return [Number(geom.coordinates[0]), Number(geom.coordinates[1])]
  }
  if (geom.type === 'Polygon' && Array.isArray(geom.coordinates) && geom.coordinates[0]?.length) {
    const ring = geom.coordinates[0]
    let sumLon = 0, sumLat = 0, n = 0
    for (const c of ring) {
      if (Array.isArray(c) && c.length >= 2) {
        sumLon += Number(c[0])
        sumLat += Number(c[1])
        n++
      }
    }
    if (n > 0) return [sumLon / n, sumLat / n]
  }
  return null
}

/** Load MBTA stops (one per stop-route) with centroid and route info. Tries multiple sources. */
async function loadStops(): Promise<MbtaStopPoint[]> {
  if (cache.stops !== null) return cache.stops
  const urls = [
    '/data/stops/mbta_stops_for_map.json',
    '/data/stops/mbta_stops_flattened_.geojson',
    '/data/mbta_stops_for_map.json',
  ]
  for (const url of urls) {
    try {
      const data = await fetchJson<GeoJSON.FeatureCollection | Record<string, unknown>[]>(url)
      const points: MbtaStopPoint[] = []
      if (Array.isArray(data)) {
        for (const p of data) {
          if (p.lon != null && p.lat != null) {
            let color = String(p.route_color ?? '#333333').trim()
            if (color && !color.startsWith('#')) color = '#' + color
            const routeLabel = p.route_short_name ?? p.route_label ?? p.route_id ?? ''
            points.push({
              lon: Number(p.lon),
              lat: Number(p.lat),
              route_color: color || '#333333',
              route_type: typeof p.route_type === 'number' ? p.route_type : -1,
              route_id: String(p.route_id ?? ''),
              stop_name: String(p.stop_name ?? ''),
              route_label: String(routeLabel),
            })
          }
        }
      } else {
        const fc = data as GeoJSON.FeatureCollection
        for (const f of fc?.features ?? []) {
          const coords = extractLonLat(f)
          if (!coords) continue
          const [lon, lat] = coords
          const p = f.properties ?? {}
          let color = String(p.route_color ?? '#333333').trim()
          if (color && !color.startsWith('#')) color = '#' + color
          const routeType = typeof p.route_type === 'number' ? p.route_type : parseInt(String(p.route_type ?? ''), 10)
          points.push({
            lon,
            lat,
            route_color: color || '#333333',
            route_type: isNaN(routeType) ? -1 : routeType,
            route_id: String(p.route_id ?? ''),
            stop_name: String(p.stop_name ?? p.stop_code ?? ''),
            route_label: String(p.route_short_name ?? p.route_long_name ?? p.route_id ?? ''),
          })
        }
      }
      if (points.length > 0) {
        cache.stops = points
        return points
      }
    } catch {
      continue
    }
  }
  cache.stops = []
  return []
}

/** Normalize hex color for stroke/fill (ensure # prefix). */
function normalizeRouteColor(c: unknown): string {
  const s = String(c ?? '#333333').trim()
  if (!s) return '#333333'
  return s.startsWith('#') ? s : '#' + s
}

/** Filter MBTA line features by overlay mode. */
function filterMbtaFeatures(
  features: GeoJSON.Feature[],
  overlay: 'none' | 'major' | 'major_and_bus'
): GeoJSON.Feature[] {
  if (overlay === 'none') return []
  if (overlay === 'major_and_bus') return features
  // major: exclude bus (route_type 3, or route_desc contains "bus")
  return features.filter((f) => {
    const rt = f.properties?.route_type
    const n = typeof rt === 'number' ? rt : parseInt(String(rt ?? ''), 10)
    if (!isNaN(n) && n === ROUTE_TYPE_BUS) return false
    const desc = String(f.properties?.route_desc ?? '').toLowerCase()
    if (desc.includes('bus')) return false
    return true
  })
}

/** Filter stop points by overlay mode (must match visible routes). */
function filterStopsByOverlay(stops: MbtaStopPoint[], overlay: 'none' | 'major' | 'major_and_bus'): MbtaStopPoint[] {
  if (overlay === 'none') return []
  if (overlay === 'major_and_bus') return stops
  // major: exclude bus stops
  return stops.filter((s) => s.route_type !== ROUTE_TYPE_BUS)
}

async function loadVariableData(selection: SelectionState): Promise<VariableData> {
  const key = variableKey(selection)
  if (cache.variable[key]) return cache.variable[key]
  const data = await fetchJson<VariableData>(variableUrl(selection))
  cache.variable[key] = data
  return data
}

async function loadTod(): Promise<TodProject[]> {
  if (cache.tod) return cache.tod
  try {
    cache.tod = await fetchJson<TodProject[]>('/data/tod_projects.json')
  } catch {
    cache.tod = []
  }
  return cache.tod
}

/** Build tooltip HTML for an MBTA stop (station name, line/bus number). */
function stopTooltipHtml(d: MbtaStopPoint): string {
  const name = d.stop_name || 'Unknown station'
  const route = d.route_label || d.route_id || '—'
  return `<strong>${escapeHtml(name)}</strong><br/>${escapeHtml(route)}`
}

/** Build tooltip HTML for a TOD project (name, town, type, year). */
function todTooltipHtml(d: TodProject): string {
  const town = d.city ?? '—'
  const type = d.tod_type ?? 'TOD'
  return `<strong>${escapeHtml(d.name)}</strong><br/>${escapeHtml(town)} · ${escapeHtml(type)} · ${d.year}`
}

/** Build tooltip HTML for a block group (GEOID, town, population, land area, value). */
function bgTooltipHtml(
  geoid: string,
  town: string,
  population: number | null,
  landAreaSqMi: number | null,
  value: number | null,
  variableLabel: string
): string {
  const popStr = population != null ? population.toLocaleString() : '—'
  const areaStr = landAreaSqMi != null ? landAreaSqMi.toFixed(4) : '—'
  const valStr = value != null ? value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : '—'
  return [
    `<strong>${escapeHtml(geoid)}</strong>`,
    `County: ${escapeHtml(town)}`,
    `Population: ${popStr}`,
    `Land area: ${areaStr} sq mi`,
    `${escapeHtml(variableLabel)}: ${valStr}`,
  ].join('<br/>')
}

function escapeHtml(s: string): string {
  const div = document.createElement('div')
  div.textContent = s
  return div.innerHTML
}

/** Create or get a shared tooltip div for TOD markers. Appended to container. */
function ensureTodTooltip(container: HTMLElement): HTMLDivElement {
  let tip = container.querySelector('.tod-tooltip') as HTMLDivElement | null
  if (!tip) {
    tip = document.createElement('div')
    tip.className = 'tod-tooltip'
    tip.style.cssText =
      'position:absolute;pointer-events:none;z-index:100;padding:6px 10px;background:rgba(0,0,0,0.85);color:#fff;font-size:12px;line-height:1.4;border-radius:6px;max-width:240px;box-shadow:0 2px 8px rgba(0,0,0,0.3);opacity:0;transition:opacity 0.15s;'
    container.style.position = 'relative'
    container.appendChild(tip)
  }
  return tip
}

function showError(container: HTMLElement, message: string): void {
  container.innerHTML = ''
  const div = document.createElement('div')
  div.style.cssText = 'padding: 2rem; text-align: center; color: #666;'
  div.textContent = message
  container.appendChild(div)
}

function showLoading(container: HTMLElement): void {
  container.innerHTML = ''
  const div = document.createElement('div')
  div.style.cssText = 'padding: 2rem; text-align: center; color: #666;'
  div.textContent = 'Loading map data…'
  container.appendChild(div)
}

/**
 * Update or clear the time-series panel below the map.
 * Uses land-area weighting for raw/count/default; population for per_population; land-area for per_aland.
 */
function updateTimeSeriesPanel(
  chartViewContainer: HTMLElement | null,
  selection: SelectionState,
  variableData: VariableData,
  metadata: BlockGroupMetadata | null,
  selectedGeoid: string | undefined
): void {
  if (!chartViewContainer) return

  let panel = chartViewContainer.querySelector('.time-series-panel') as HTMLDivElement | null
  if (!selectedGeoid) {
    if (panel) {
      panel.style.display = 'none'
      panel.innerHTML = ''
    }
    return
  }

  if (!panel) {
    panel = document.createElement('div')
    panel.className = 'time-series-panel'
    panel.style.cssText =
      'margin-top:16px;padding:12px;background:#f8f8f8;border-radius:8px;border:1px solid #ddd;'
    chartViewContainer.appendChild(panel)
  }
  panel.style.display = 'block'

  if (!metadata) {
    panel.innerHTML = '<p style="color:#666;font-size:12px;">Metadata not available for time series.</p>'
    return
  }

  const transform = selection.transform
  const tsData: TimeSeriesData = {
    geoids: variableData.geoids,
    years: variableData.years,
    values: variableData.values,
    population: metadata.population,
    landArea: metadata.land_area,
    variableLabel: selection.variableLabel ?? selection.variable,
    transform,
  }
  renderTimeSeriesLine(panel, tsData, selectedGeoid)
}

/** Render or update choropleth. Container may already have SVG (year update). */
export function renderChoropleth(container: HTMLElement, selection: SelectionState): void {
  const existingSvg = container.querySelector('.choropleth-svg')
  const extent = selection.extent ?? 'whole'
  const acsGeography = selection.acsGeography ?? 'unified_2010'
  const mbtaOverlay = selection.mbtaOverlay ?? 'major'
  const prevExtent = (container as HTMLElement & { __choroplethExtent?: string }).__choroplethExtent
  const prevGeography = (container as HTMLElement & { __choroplethGeography?: string }).__choroplethGeography
  const prevMbtaOverlay = (container as HTMLElement & { __choroplethMbtaOverlay?: string }).__choroplethMbtaOverlay
  const isUpdate =
    !!existingSvg && prevExtent === extent && prevGeography === acsGeography && prevMbtaOverlay === mbtaOverlay

  if (isUpdate) {
    // Year-only change (same extent and geography): update fills and TOD markers in place
    ;(container as HTMLElement & { __choroplethSelection?: SelectionState }).__choroplethSelection = selection
    updateYear(container, selection)
    return
  }

  // Initial render or extent/geography/overlay change: fetch data and build map
    ;(container as HTMLElement & { __choroplethExtent?: string }).__choroplethExtent = extent
  ;(container as HTMLElement & { __choroplethGeography?: string }).__choroplethGeography = acsGeography
  ;(container as HTMLElement & { __choroplethMbtaOverlay?: string }).__choroplethMbtaOverlay = mbtaOverlay
  ;(container as HTMLElement & { __choroplethSelection?: SelectionState }).__choroplethSelection = selection
  initChoropleth(container, selection)
}

function updateYear(container: HTMLElement, selection: SelectionState): void {
  const key = variableKey(selection)
  const data = cache.variable[key]
  if (!data) return

  const values = data.values[String(selection.year)]
  if (!values) return

  const vmin = data.vmin
  const vmax = data.vmax
  const geoids = data.geoids
  const colorScale = d3.scaleSequential(d3.interpolateViridis).domain([vmin, vmax])

  const svg = d3.select(container).select<SVGSVGElement>('.choropleth-svg')
  const mapLayer = svg.select<SVGGElement>('.map-layer')
  const paths = mapLayer.selectAll<SVGPathElement, GeoJSON.Feature>('.bg-path')

  paths
    .transition()
    .duration(TRANSITION_MS)
    .attr('fill', (d) => {
      const geoid = d.properties?.GEOID ?? d.properties?.GEOID10
      const idx = geoid ? geoids.indexOf(String(geoid)) : -1
      const v = idx >= 0 ? values[idx] : null
      return v != null ? colorScale(v) : MISSING_COLOR
    })

  // Update TOD markers
  const todLayer = svg.select<SVGGElement>('.tod-layer')
  const projection = (window as unknown as { __choroplethProjection?: d3.GeoProjection }).__choroplethProjection
  if (todLayer.empty() || !projection) return

  const tod = cache.tod ?? []
  const filtered = tod.filter((p) => p.year <= selection.year)

  const circles = todLayer.selectAll<SVGCircleElement, TodProject>('.tod-marker').data(filtered, (d) => `${d.name}-${d.year}`)

  circles.exit().transition().duration(TRANSITION_MS).attr('r', 0).remove()

  // Use current zoom scale so new markers spawn at correct size (zoom-invariant rendering)
  const zoomTransform = d3.zoomTransform(svg.node() as SVGSVGElement)
  const k = zoomTransform.k
  const rScaled = TOD_R_BASE / k

  const tooltip = ensureTodTooltip(container)
  circles
    .enter()
    .append('circle')
    .attr('class', 'tod-marker')
    .attr('r', 0)
    .attr('fill', '#c8a96e')
    .attr('stroke', '#fff')
    .attr('stroke-width', 1.5 / k)
    .attr('cursor', 'pointer')
    .on('mouseover', function (event: MouseEvent, d: TodProject) {
      tooltip.innerHTML = todTooltipHtml(d)
      tooltip.style.opacity = '1'
      const rect = container.getBoundingClientRect()
      tooltip.style.left = `${event.clientX - rect.left + 12}px`
      tooltip.style.top = `${event.clientY - rect.top + 12}px`
    })
    .on('mousemove', function (event: MouseEvent) {
      const rect = container.getBoundingClientRect()
      tooltip.style.left = `${event.clientX - rect.left + 12}px`
      tooltip.style.top = `${event.clientY - rect.top + 12}px`
    })
    .on('mouseout', function () {
      tooltip.style.opacity = '0'
    })
    .merge(circles as d3.Selection<SVGCircleElement, TodProject, SVGGElement, unknown>)
    .transition()
    .duration(TRANSITION_MS)
    .attr('r', rScaled)
    .attr('stroke-width', 1.5 / k)
    .attr('cx', (d) => {
      const [x, y] = projection([d.lon, d.lat])
      return x ?? 0
    })
    .attr('cy', (d) => {
      const [x, y] = projection([d.lon, d.lat])
      return y ?? 0
    })
}

async function initChoropleth(container: HTMLElement, selection: SelectionState): Promise<void> {
  showLoading(container)

  const mbtaOverlay = selection.mbtaOverlay ?? 'major'
  const loadStopsPromise = mbtaOverlay !== 'none' ? loadStops() : Promise.resolve([] as MbtaStopPoint[])

  try {
    const [geo, mbta, variableData, metadata, tod, stops] = await Promise.all([
      loadGeo(selection),
      loadMbta(),
      loadVariableData(selection),
      loadMetadata(selection),
      loadTod(),
      loadStopsPromise,
    ])
    cache.tod = tod

    const values = variableData.values[String(selection.year)]
    if (!values) {
      showError(container, `No data for year ${selection.year}`)
      return
    }

    // Clear any previous time-series panel on full rebuild (variable/extent change)
    const chartView = container.parentElement
    if (chartView) {
      const prevPanel = chartView.querySelector('.time-series-panel')
      if (prevPanel) prevPanel.remove()
    }
    ;(container as HTMLElement & { __selectedGEOID?: string }).__selectedGEOID = undefined

    container.innerHTML = ''
    const width = container.clientWidth || 800
    const height = Math.max(400, width * 0.6)

    const svg = d3
      .select(container)
      .append('svg')
      .attr('class', 'choropleth-svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])

    // Fit projection: whole area uses full geo; Boston zoom uses bounds polygon (matches PNG boston_zoom)
    const extent = selection.extent ?? 'whole'
    const fitObject = extent === 'boston' ? BOSTON_EXTENT_GEO : geo
    const projection = d3.geoMercator().fitSize([width, height], fitObject)
    ;(window as unknown as { __choroplethProjection?: d3.GeoProjection }).__choroplethProjection = projection
    const pathGen = d3.geoPath().projection(projection)

    const colorScale = d3
      .scaleSequential(d3.interpolateViridis)
      .domain([variableData.vmin, variableData.vmax])

    const zoomLayer = svg.append('g').attr('class', 'zoom-layer')
    const mapLayer = zoomLayer.append('g').attr('class', 'map-layer')
    const geoids = variableData.geoids

    const bgTooltip = ensureTodTooltip(container)
    const variableLabel = selection.variableLabel ?? selection.variable

    mapLayer
      .selectAll('.bg-path')
      .data(geo.features)
      .join('path')
      .attr('class', 'bg-path')
      .attr('d', pathGen)
      .attr('fill', (d) => {
        const geoid = d.properties?.GEOID ?? d.properties?.GEOID10
        const idx = geoid ? geoids.indexOf(String(geoid)) : -1
        const v = idx >= 0 ? values[idx] : null
        return v != null ? colorScale(v) : MISSING_COLOR
      })
      .attr('stroke', '#999')
      .attr('stroke-width', BG_STROKE_BASE)
      .attr('cursor', 'pointer')
      .on('mouseover', function (event: MouseEvent, d: GeoJSON.Feature) {
        const geoid = String(d.properties?.GEOID ?? d.properties?.GEOID10 ?? '')
        // Use metadata.geoids for lookup when available (source of truth for county/population)
        const lookupGeoids = metadata?.geoids ?? geoids
        const idx = geoid ? lookupGeoids.indexOf(geoid) : -1
        const currentYear = (container as HTMLElement & { __choroplethSelection?: SelectionState }).__choroplethSelection?.year ?? selection.year
        const v = idx >= 0 ? (variableData.values[String(currentYear)]?.[idx] ?? null) : null
        // Town/county: prefer COUNTYFP from GeoJSON feature (always correct for hovered feature); fallback to metadata
        const countyFips = String(d.properties?.COUNTYFP ?? d.properties?.COUNTYFP10 ?? d.properties?.COUNTYFP20 ?? '').padStart(3, '0')
        const town = countyFips
          ? (MA_COUNTY_NAMES[countyFips] ?? countyFips)
          : (idx >= 0 ? (metadata?.county_name?.[idx] ?? '—') : '—')
        const pop = idx >= 0 ? (metadata?.population?.[String(currentYear)]?.[idx] ?? null) : null
        const aland = metadata?.land_area?.[idx] ?? (d.properties?.ALAND10 ?? d.properties?.ALAND ?? d.properties?.ALAND20) as number | undefined
        const landSqMi = aland != null && aland > 0 ? aland * SQ_M_TO_SQ_MI : null
        bgTooltip.innerHTML = bgTooltipHtml(geoid, town, pop, landSqMi, v, variableLabel)
        bgTooltip.style.opacity = '1'
        const rect = container.getBoundingClientRect()
        bgTooltip.style.left = `${event.clientX - rect.left + 12}px`
        bgTooltip.style.top = `${event.clientY - rect.top + 12}px`
      })
      .on('mousemove', function (event: MouseEvent) {
        const rect = container.getBoundingClientRect()
        bgTooltip.style.left = `${event.clientX - rect.left + 12}px`
        bgTooltip.style.top = `${event.clientY - rect.top + 12}px`
      })
      .on('mouseout', function () {
        bgTooltip.style.opacity = '0'
      })
      .on('click', function (_event: MouseEvent, d: GeoJSON.Feature) {
        const geoid = String(d.properties?.GEOID ?? d.properties?.GEOID10 ?? '')
        if (!geoid) return
        const prev = (container as HTMLElement & { __selectedGEOID?: string }).__selectedGEOID
        const next = prev === geoid ? undefined : geoid
        ;(container as HTMLElement & { __selectedGEOID?: string }).__selectedGEOID = next
        updateTimeSeriesPanel(container.parentElement, selection, variableData, metadata, next)
        // Visual feedback: highlight selected path (stroke color only; zoom handler controls stroke-width)
        mapLayer.selectAll('.bg-path').attr('stroke', (p: GeoJSON.Feature) => {
          const g = String(p.properties?.GEOID ?? p.properties?.GEOID10 ?? '')
          return g === next ? '#1a1a1a' : '#999'
        })
      })

    // MBTA lines overlay (filtered by overlay mode: none / major / major_and_bus)
    const filteredLines = mbta?.features?.length
      ? filterMbtaFeatures(mbta.features, mbtaOverlay)
      : []
    if (filteredLines.length > 0) {
      const linesLayer = zoomLayer.append('g').attr('class', 'mbta-layer')
      linesLayer
        .selectAll('path')
        .data(filteredLines)
        .join('path')
        .attr('d', pathGen)
        .attr('fill', 'none')
        .attr('stroke', (d) => normalizeRouteColor(d.properties?.route_color))
        .attr('stroke-width', LINE_STROKE_BASE)
        .attr('stroke-linecap', 'round')
    }

    // MBTA stop dots (proportionally small, colored by route, grey outline, tooltip)
    const filteredStops = filterStopsByOverlay(stops, mbtaOverlay)
    if (filteredStops.length > 0) {
      const stopsLayer = zoomLayer.append('g').attr('class', 'mbta-stops-layer')
      const stopTooltip = ensureTodTooltip(container)
      stopsLayer
        .selectAll('circle')
        .data(filteredStops)
        .join('circle')
        .attr('class', 'mbta-stop-dot')
        .attr('r', STOP_R_BASE)
        .attr('fill', (d) => d.route_color)
        .attr('stroke', '#888')
        .attr('stroke-width', STOP_STROKE_BASE)
        .attr('cursor', 'pointer')
        .attr('cx', (d) => {
          const [x] = projection([d.lon, d.lat])
          return x ?? 0
        })
        .attr('cy', (d) => {
          const [, y] = projection([d.lon, d.lat])
          return y ?? 0
        })
        .on('mouseover', function (event: MouseEvent, d: MbtaStopPoint) {
          stopTooltip.innerHTML = stopTooltipHtml(d)
          stopTooltip.style.opacity = '1'
          const rect = container.getBoundingClientRect()
          stopTooltip.style.left = `${event.clientX - rect.left + 12}px`
          stopTooltip.style.top = `${event.clientY - rect.top + 12}px`
        })
        .on('mousemove', function (event: MouseEvent) {
          const rect = container.getBoundingClientRect()
          stopTooltip.style.left = `${event.clientX - rect.left + 12}px`
          stopTooltip.style.top = `${event.clientY - rect.top + 12}px`
        })
        .on('mouseout', function () {
          stopTooltip.style.opacity = '0'
        })
    }

    // TOD markers with hover tooltip (name, town, type, year)
    const filtered = tod.filter((p) => p.year <= selection.year)
    const todLayer = zoomLayer.append('g').attr('class', 'tod-layer')
    const tooltip = ensureTodTooltip(container)
    todLayer
      .selectAll('.tod-marker')
      .data(filtered, (d: TodProject) => `${d.name}-${d.year}`)
      .join('circle')
      .attr('class', 'tod-marker')
      .attr('r', TOD_R_BASE)
      .attr('fill', '#c8a96e')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .attr('cursor', 'pointer')
      .attr('cx', (d) => {
        const [x] = projection([d.lon, d.lat])
        return x ?? 0
      })
      .attr('cy', (d) => {
        const [, y] = projection([d.lon, d.lat])
        return y ?? 0
      })
      .on('mouseover', function (event: MouseEvent, d: TodProject) {
        tooltip.innerHTML = todTooltipHtml(d)
        tooltip.style.opacity = '1'
        const rect = container.getBoundingClientRect()
        tooltip.style.left = `${event.clientX - rect.left + 12}px`
        tooltip.style.top = `${event.clientY - rect.top + 12}px`
      })
      .on('mousemove', function (event: MouseEvent) {
        const rect = container.getBoundingClientRect()
        tooltip.style.left = `${event.clientX - rect.left + 12}px`
        tooltip.style.top = `${event.clientY - rect.top + 12}px`
      })
      .on('mouseout', function () {
        tooltip.style.opacity = '0'
      })

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 50])
      .on('zoom', (event) => {
        zoomLayer.attr('transform', event.transform)
        const k = event.transform.k
        zoomLayer.selectAll('.bg-path').attr('stroke-width', BG_STROKE_BASE / k)
        zoomLayer.selectAll('.mbta-layer path').attr('stroke-width', LINE_STROKE_BASE / k)
        zoomLayer.selectAll('.mbta-stop-dot').attr('r', STOP_R_BASE / k).attr('stroke-width', STOP_STROKE_BASE / k)
        zoomLayer.selectAll('.tod-marker').attr('r', TOD_R_BASE / k).attr('stroke-width', 1.5 / k)
      })
    svg.call(zoom)

  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    const acsGeo = selection.acsGeography ?? 'unified_2010'
    const hint =
      acsGeo === 'native'
        ? 'Native geography requires block_groups_acs_overlap_2020.* (run acs build with tl_2020_25_bg.shp) and acs_native_*.json (run export_d3_data.py).'
        : 'Run: python tod-viz-viewer/scripts/export_d3_data.py'
    showError(container, `Failed to load map: ${msg}. ${hint}`)
  }
}
