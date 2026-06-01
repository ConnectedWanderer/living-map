import cors from 'cors';
import express from 'express';
import { tilesRouter } from './routes/tiles.ts';

export const app = express();

app.use(cors({ origin: process.env.CORS_ORIGIN || 'http://localhost:5173' }));
app.use('/tiles', tilesRouter);

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

const port = Number(process.env.PORT) || 3002;
export const server = app.listen(port, () => {
  console.log(`serving-api listening on port ${port}`);
});
