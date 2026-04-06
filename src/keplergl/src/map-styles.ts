/**
 * Free map styles for Kepler.gl — no Mapbox token required.
 * Uses CARTO basemaps (open, no auth) and OpenStreetMap.
 */

const CARTO_DARK: any = {
  id: 'carto-dark',
  label: 'CARTO Dark',
  url: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  layerGroups: [],
};

const CARTO_POSITRON: any = {
  id: 'carto-positron',
  label: 'CARTO Positron',
  url: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  layerGroups: [],
};

const CARTO_VOYAGER: any = {
  id: 'carto-voyager',
  label: 'CARTO Voyager',
  url: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
  layerGroups: [],
};

export const FREE_MAP_STYLES = [CARTO_DARK, CARTO_POSITRON, CARTO_VOYAGER];
export const DEFAULT_STYLE_ID = 'carto-dark';
