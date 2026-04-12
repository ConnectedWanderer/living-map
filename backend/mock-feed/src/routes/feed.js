import { generateRandomEvents } from '../utils/generator.js';
import { buildRssFeed } from '../utils/rss.js';

export function registerRoutes(app) {
  app.get('/feed', (req, res) => {
    const count = Math.min(Math.max(parseInt(req.query.count) || 50, 1), 100);
    const events = generateRandomEvents(count);
    const feed = buildRssFeed(events);
    
    res.set('Content-Type', 'application/rss+xml; charset=utf-8');
    res.send(feed);
  });
}