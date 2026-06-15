import cors from 'cors';
import express from 'express';
import { tilesRouter } from './routes/tiles.ts';
import { closePool } from './db/client.ts';
import type { ErrorRequestHandler } from 'express';

export const app = express();

app.use(cors({ origin: process.env.CORS_ORIGIN || 'http://localhost:5173' }));
app.use('/tiles', tilesRouter);

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
};
app.use(errorHandler);

const port = Number(process.env.PORT) || 3002;
export const server = app.listen(port, () => {
  console.log(`serving-api listening on port ${port}`);
});

function shutdown() {
  console.log('Shutting down gracefully...');
  server.close(async () => {
    await closePool();
    process.exit(0);
  });
  setTimeout(() => {
    console.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10_000).unref();
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
