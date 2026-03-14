/**
 * Svelte store for selection state.
 * Passed to D3 for rendering; updated when user changes dropdowns or slider.
 */

import { writable } from 'svelte/store'
import type { SelectionState } from './manifest.js'

/** Default empty selection; updated when manifest loads. */
export const selection = writable<SelectionState | null>(null)
