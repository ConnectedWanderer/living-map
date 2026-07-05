import cors from 'cors';
import type { ErrorRequestHandler } from 'express';
import express from 'express';
import rateLimit from 'express-rate-limit';
import helmet from 'helmet';
import { closePool } from './db/client.ts';
import { refererValidator } from './middleware/referer-validator.ts';
import { tilesRouter } from './routes/tiles.ts';

export const app = express();

const corsOrigin = (process.env.CORS_ORIGIN || 'http://localhost:5173').replace(/\/+$/, '');
app.use(cors({ origin: corsOrigin }));
app.use(helmet());
app.use(
  rateLimit({
    windowMs: 15_000,
    max: 100,
    standardHeaders: true,
    legacyHeaders: false,
  }),
);
app.use('/tiles', refererValidator(corsOrigin));
app.use('/tiles', tilesRouter);

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
  console.error('Unhandled error:', err);
  res.status(500).json({ error: 'Internal server error' });
};
app.use(errorHandler);

const port = process.env.PORT ? Number(process.env.PORT) : 3002;
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
