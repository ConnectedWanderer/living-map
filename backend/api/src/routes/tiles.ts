import { Router } from 'express';
import { getPool } from '../db/client.ts';
import { getTile } from '../services/tiles.ts';

export const tilesRouter = Router();

tilesRouter.get('/:z/:x/:y.pbf', async (req, res) => {
  const z = Number(req.params.z);
  const x = Number(req.params.x);
  const y = Number(req.params.y);

  if (!Number.isInteger(z) || z < 0 || z > 22) {
    res.status(400).send('Invalid z: must be integer 0-22');
    return;
  }

  const maxCoord = 2 ** z;
  if (!Number.isInteger(x) || x < 0 || x >= maxCoord) {
    res.status(400).send(`Invalid x: must be integer 0-${maxCoord - 1}`);
    return;
  }
  if (!Number.isInteger(y) || y < 0 || y >= maxCoord) {
    res.status(400).send(`Invalid y: must be integer 0-${maxCoord - 1}`);
    return;
  }

  const pool = getPool();
  const tile = await getTile(pool, z, x, y);

  if (!tile) {
    res.status(204).end();
    return;
  }

  res.type('application/vnd.mapbox-vector-tile').send(tile);
});
