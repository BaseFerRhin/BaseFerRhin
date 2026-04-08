import React, {useEffect, useState} from 'react';
import {useDispatch} from 'react-redux';
import KeplerGl from '@kepler.gl/components';
import {addDataToMap} from '@kepler.gl/actions';
import {processGeojson} from '@kepler.gl/processors';
import {theme as keplerDarkTheme} from '@kepler.gl/styles';
import AutoSizer from 'react-virtualized/dist/commonjs/AutoSizer';
import {KEPLER_CONFIG} from './kepler-config';
import {FREE_MAP_STYLES} from './map-styles';

const MAPBOX_TOKEN = (import.meta as any).env?.VITE_MAPBOX_TOKEN || 'not-needed';

const ARCHEO_THEME = {
  ...keplerDarkTheme,
  sidePanelBg: '#1a1a2e',
  sidePanelHeaderBg: '#16213e',
  titleTextColor: '#e8c547',
  subtextColorActive: '#e8c547',
};

interface Stats {
  total_sites: number;
  by_type: {type_site: string; count: number}[];
  by_periode: {periode: string; count: number}[];
}

export default function App() {
  const dispatch = useDispatch();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [geojsonRes, statsRes] = await Promise.all([
          fetch('/api/sites/geojson'),
          fetch('/api/stats'),
        ]);
        const geojson = await geojsonRes.json();
        const statsData = await statsRes.json();
        setStats(statsData);

        const processedData = processGeojson(geojson);

        dispatch(
          addDataToMap({
            datasets: {
              info: {
                label: 'Sites de l\'âge du Fer — Rhin supérieur',
                id: 'sites',
              },
              data: processedData,
            },
            options: {centerMap: false, readOnly: false},
            config: KEPLER_CONFIG as any,
          })
        );
        setLoaded(true);
      } catch (err) {
        console.error('Erreur chargement données:', err);
      }
    }
    loadData();
  }, [dispatch]);

  return (
    <div style={{position: 'absolute', width: '100%', height: '100%'}}>
      {/* Header */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 48,
          zIndex: 100,
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 20px',
          gap: 16,
          borderBottom: '1px solid #2a2a4a',
        }}
      >
        <span style={{fontSize: 20, fontWeight: 700, color: '#e8c547'}}>
          🏺
        </span>
        <span style={{fontSize: 15, fontWeight: 600, color: '#fff', letterSpacing: 0.5}}>
          BaseFerRhin
        </span>
        <span style={{fontSize: 12, color: '#8899aa'}}>
          Sites de l'âge du Fer — Rhin supérieur
        </span>
        <div style={{flex: 1}} />
        {stats && (
          <div style={{display: 'flex', gap: 16, fontSize: 12, color: '#ccc'}}>
            <span>
              <strong style={{color: '#e8c547'}}>{stats.total_sites}</strong> sites
            </span>
            {stats.by_periode.map(p => (
              <span key={p.periode}>
                {p.periode}: <strong>{p.count}</strong>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Map */}
      <div style={{position: 'absolute', top: 48, left: 0, right: 0, bottom: 0}}>
        <AutoSizer>
          {({height, width}: {height: number; width: number}) => (
            <KeplerGl
              id="map"
              mapboxApiAccessToken={MAPBOX_TOKEN}
              mapboxApiUrl=""
              mapStyles={FREE_MAP_STYLES}
              mapStylesReplaceDefault={true}
              width={width}
              height={height}
              appName="BaseFerRhin"
              version="v0.1"
              theme={ARCHEO_THEME}
            />
          )}
        </AutoSizer>
      </div>

      {/* Loading overlay */}
      {!loaded && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0,0,0,0.7)',
            zIndex: 200,
            color: '#fff',
            fontSize: 18,
          }}
        >
          Chargement des sites archéologiques…
        </div>
      )}
    </div>
  );
}
