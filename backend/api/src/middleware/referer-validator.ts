import type { RequestHandler } from 'express';

function extractOrigin(referer: string | undefined): string | null {
  if (!referer) return null;
  try {
    const url = new URL(referer);
    return `${url.protocol}//${url.host}`;
  } catch {
    return null;
  }
}

export function refererValidator(allowedOrigin: string): RequestHandler {
  return (req, res, next) => {
    if (allowedOrigin === '*') {
      return next();
    }

    const origin = req.headers.origin || extractOrigin(req.headers.referer as string | undefined);

    if (!origin) {
      res.status(403).json({ error: 'Forbidden' });
      return;
    }

    const allowed = allowedOrigin.split(',').map((o) => o.trim().replace(/\/+$/, ''));

    if (!allowed.includes(origin.replace(/\/+$/, ''))) {
      res.status(403).json({ error: 'Forbidden' });
      return;
    }

    next();
  };
}
