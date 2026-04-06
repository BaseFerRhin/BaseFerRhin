import express from 'express';
import cors from 'cors';
import path from 'path';
import {fileURLToPath} from 'url';
import {DuckDBInstance} from '@duckdb/node-api';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const isProduction = process.env.NODE_ENV === 'production';

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors());
app.use(express.json());

// DuckDB returns BigInt for integers — make JSON.stringify handle them
BigInt.prototype.toJSON = function () { return Number(this); };

// ── DuckDB connection ────────────────────────────────────────────────
const DB_PATH = path.resolve(__dirname, '../data/sites.duckdb');
const instance = await DuckDBInstance.create(DB_PATH, {access_mode: 'READ_ONLY'});
const conn = await instance.connect();

function toJS(val) {
  if (typeof val === 'bigint') return Number(val);
  if (Array.isArray(val)) return val.map(toJS);
  return val;
}

async function query(sql) {
  const reader = await conn.runAndReadAll(sql);
  const columns = reader.columnNames();
  const rows = reader.getRows();
  return rows.map(row => {
    const obj = {};
    columns.forEach((col, i) => {
      obj[col] = toJS(row[i]);
    });
    return obj;
  });
}

// ── API Routes ───────────────────────────────────────────────────────

app.get('/api/sites', async (_req, res) => {
  try {
    const rows = await query(`
      SELECT s.*, p.periode, p.sous_periode, p.phase_id,
             p.datation_debut, p.datation_fin
      FROM sites s
      LEFT JOIN phases p ON s.site_id = p.site_id
      ORDER BY s.nom_site
    `);
    res.json(rows);
  } catch (err) {
    res.status(500).json({error: err.message});
  }
});

app.get('/api/sites/geojson', async (_req, res) => {
  try {
    const rows = await query(`
      SELECT s.site_id, s.nom_site, s.commune, s.pays, s.region_admin,
             s.latitude, s.longitude, s.precision_loc, s.type_site,
             s.description, s.surface_m2, s.altitude_m,
             p.periode, p.sous_periode,
             (SELECT COUNT(*) FROM sources src WHERE src.site_id = s.site_id) AS sources_count
      FROM sites s
      LEFT JOIN phases p ON s.site_id = p.site_id
      WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
      ORDER BY s.nom_site
    `);

    const features = rows.map(r => ({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [Number(r.longitude), Number(r.latitude)],
      },
      properties: {
        site_id: r.site_id,
        nom_site: r.nom_site,
        commune: r.commune,
        pays: r.pays,
        region_admin: r.region_admin,
        precision_localisation: r.precision_loc,
        type_site: r.type_site,
        description: r.description,
        surface_m2: r.surface_m2 ? Number(r.surface_m2) : null,
        altitude_m: r.altitude_m ? Number(r.altitude_m) : null,
        periode: r.periode,
        sous_periode: r.sous_periode,
        sources_count: Number(r.sources_count),
      },
    }));

    res.json({type: 'FeatureCollection', features});
  } catch (err) {
    res.status(500).json({error: err.message});
  }
});

app.get('/api/phases', async (_req, res) => {
  try {
    const rows = await query('SELECT * FROM phases ORDER BY site_id');
    res.json(rows);
  } catch (err) {
    res.status(500).json({error: err.message});
  }
});

app.get('/api/sources', async (_req, res) => {
  try {
    const rows = await query('SELECT * FROM sources ORDER BY site_id');
    res.json(rows);
  } catch (err) {
    res.status(500).json({error: err.message});
  }
});

app.get('/api/stats', async (_req, res) => {
  try {
    const totals = await query('SELECT COUNT(*) as n FROM sites');
    const types = await query(
      'SELECT type_site, COUNT(*) as n FROM sites GROUP BY type_site ORDER BY n DESC'
    );
    const periodes = await query(
      'SELECT periode, COUNT(*) as n FROM phases GROUP BY periode ORDER BY n DESC'
    );
    const pays = await query(
      'SELECT pays, COUNT(*) as n FROM sites GROUP BY pays ORDER BY n DESC'
    );
    res.json({
      total_sites: Number(totals[0].n),
      by_type: types.map(r => ({type_site: r.type_site, count: Number(r.n)})),
      by_periode: periodes.map(r => ({periode: r.periode, count: Number(r.n)})),
      by_pays: pays.map(r => ({pays: r.pays, count: Number(r.n)})),
    });
  } catch (err) {
    res.status(500).json({error: err.message});
  }
});

app.get('/api/site/:siteId', async (req, res) => {
  try {
    const sites = await query(
      `SELECT * FROM sites WHERE site_id = '${req.params.siteId.replace(/'/g, "''")}'`
    );
    if (!sites.length) return res.status(404).json({error: 'Site non trouvé'});
    const phases = await query(
      `SELECT * FROM phases WHERE site_id = '${req.params.siteId.replace(/'/g, "''")}'`
    );
    const sources = await query(
      `SELECT * FROM sources WHERE site_id = '${req.params.siteId.replace(/'/g, "''")}'`
    );
    res.json({...sites[0], phases, sources});
  } catch (err) {
    res.status(500).json({error: err.message});
  }
});

// ── SQL query endpoint (for exploration) ─────────────────────────────
app.post('/api/query', async (req, res) => {
  const {sql} = req.body;
  if (!sql) return res.status(400).json({error: 'Missing sql field'});
  const forbidden = /\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b/i;
  if (forbidden.test(sql)) {
    return res.status(403).json({error: 'Only SELECT queries allowed'});
  }
  try {
    const rows = await query(sql);
    res.json({rows, count: rows.length});
  } catch (err) {
    res.status(400).json({error: err.message});
  }
});

// ── Serve static frontend in production ──────────────────────────────
if (isProduction) {
  const distPath = path.resolve(__dirname, '../dist');
  app.use(express.static(distPath));
  app.get('*', (_req, res) => res.sendFile(path.join(distPath, 'index.html')));
}

app.listen(PORT, () => {
  console.log(`\n  🏺 BaseFerRhin API  →  http://localhost:${PORT}/api/sites`);
  console.log(`  📊 Stats           →  http://localhost:${PORT}/api/stats`);
  console.log(`  🗄️  DuckDB          →  ${DB_PATH}`);
  if (isProduction) {
    console.log(`  🗺️  Kepler.gl       →  http://localhost:${PORT}\n`);
  } else {
    console.log(`  🗺️  Kepler.gl dev   →  http://localhost:5173\n`);
  }
});
