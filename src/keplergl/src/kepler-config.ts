/**
 * Kepler.gl configuration for Iron Age archaeological sites.
 * Color schemes based on kepler-gl-archeo skill palettes.
 */

export const TYPE_SITE_COLORS: Record<string, [number, number, number]> = {
  oppidum: [227, 26, 28],
  habitat: [31, 120, 180],
  'nécropole': [106, 61, 154],
  'dépôt': [255, 127, 0],
  sanctuaire: [51, 160, 44],
  atelier: [177, 89, 40],
  tumulus: [251, 154, 153],
  voie: [166, 206, 227],
  'indéterminé': [178, 223, 138],
};

export const PERIODE_COLORS: Record<string, [number, number, number]> = {
  Hallstatt: [217, 95, 2],
  'La Tène': [27, 158, 119],
  'Hallstatt/La Tène': [117, 112, 179],
  'indéterminé': [153, 153, 153],
};

export const MAP_CENTER = {latitude: 48.1, longitude: 7.5, zoom: 8};

export const KEPLER_CONFIG = {
  version: 'v1',
  config: {
    visState: {
      layers: [
        {
          id: 'sites-layer',
          type: 'point',
          config: {
            dataId: 'sites',
            label: 'Sites archéologiques',
            columns: {lat: 'latitude', lng: 'longitude'},
            isVisible: true,
            visConfig: {
              radius: 18,
              fixedRadius: false,
              opacity: 0.85,
              outline: true,
              thickness: 1.5,
              colorRange: {
                name: 'Archéo TypeSite',
                type: 'custom',
                category: 'Custom',
                colors: [
                  '#E31A1C', '#1F78B4', '#6A3D9A', '#FF7F00',
                  '#33A02C', '#B15928', '#FB9A99', '#A6CEE3', '#B2DF8A',
                ],
              },
            },
            colorField: {name: 'type_site', type: 'string'},
            textLabel: [
              {
                field: {name: 'nom_site', type: 'string'},
                color: [255, 255, 255],
                size: 14,
                offset: [0, 0],
                anchor: 'start',
                alignment: 'center',
              },
            ],
          },
        },
      ],
      interactionConfig: {
        tooltip: {
          fieldsToShow: {
            sites: [
              {name: 'nom_site', format: null},
              {name: 'type_site', format: null},
              {name: 'periode', format: null},
              {name: 'sous_periode', format: null},
              {name: 'commune', format: null},
              {name: 'pays', format: null},
              {name: 'precision_localisation', format: null},
            ],
          },
          compareMode: false,
          compareType: 'absolute',
          enabled: true,
        },
        brush: {size: 0.5, enabled: false},
        geocoder: {enabled: false},
        coordinate: {enabled: false},
      },
      filters: [],
    },
    mapState: {
      latitude: MAP_CENTER.latitude,
      longitude: MAP_CENTER.longitude,
      zoom: MAP_CENTER.zoom,
      bearing: 0,
      pitch: 0,
      dragRotate: true,
    },
    mapStyle: {
      styleType: 'carto-dark',
    },
  },
};
