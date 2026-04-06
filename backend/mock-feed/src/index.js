import express from 'express';
import dotenv from 'dotenv';
import { registerRoutes } from './routes/feed.js';

dotenv.config();

const app = express();
const port = process.env.PORT || 3001;

registerRoutes(app);

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(port, () => {
  console.log(`Mock feed server running on http://localhost:${port}/feed`);
});