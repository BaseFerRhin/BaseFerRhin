import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import wasm from 'vite-plugin-wasm';
import {resolve} from 'path';

export default defineConfig({
  plugins: [wasm(), react()],
  server: {
    port: 5173,
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: true,
    rollupOptions: {
      input: {main: resolve(__dirname, 'index.html')},
    },
    target: 'esnext',
    commonjsOptions: {
      include: [/node_modules/],
      transformMixedEsModules: true,
    },
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'production'),
    'process.env.MapboxAccessToken': JSON.stringify(process.env.MAPBOX_TOKEN || ''),
    'process.env.NODE_DEBUG': JSON.stringify(false),
  },
  resolve: {
    dedupe: ['styled-components', 'apache-arrow'],
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  optimizeDeps: {
    exclude: ['parquet-wasm'],
    include: [
      'apache-arrow',
      'buffer',
      'react',
      'react-dom',
      'react-redux',
      'redux',
      'styled-components',
      '@kepler.gl/components',
      '@kepler.gl/reducers',
      '@kepler.gl/actions',
      '@kepler.gl/processors',
      '@kepler.gl/schemas',
      '@kepler.gl/constants',
      '@kepler.gl/utils',
      '@kepler.gl/table',
      '@kepler.gl/layers',
      '@kepler.gl/deckgl-layers',
      '@kepler.gl/effects',
      '@kepler.gl/styles',
      '@kepler.gl/tasks',
      '@deck.gl/core',
      '@deck.gl/layers',
      '@deck.gl/aggregation-layers',
      '@deck.gl/geo-layers',
      '@deck.gl/mesh-layers',
      '@deck.gl/extensions',
      '@luma.gl/core',
      '@luma.gl/engine',
      '@luma.gl/gltools',
      '@luma.gl/shadertools',
      '@luma.gl/webgl',
      '@loaders.gl/core',
      '@loaders.gl/gltf',
      '@loaders.gl/images',
      '@loaders.gl/parquet',
      '@math.gl/core',
      '@math.gl/web-mercator',
      'gl-matrix',
      'lodash',
    ],
    esbuildOptions: {target: 'es2020'},
  },
});
