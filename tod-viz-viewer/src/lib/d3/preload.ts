/**
 * Preload resources for instant year slider response.
 * Current: preload images. Future: preload data for D3-native renderers.
 */

import type { SelectionState } from '../manifest.js'
import { getImagePath } from './renderers/pngRenderer.js'
import type { Manifest } from '../manifest.js'

/** Preload all year images for the given selection. */
export function preloadImages(
  selection: SelectionState,
  manifest: Manifest,
  getPath: (s: SelectionState, m: Manifest) => string
): void {
  for (const year of selection.years) {
    const s = { ...selection, year }
    const url = getPath(s, manifest)
    if (url) {
      const img = new Image()
      img.src = url
    }
  }
}
