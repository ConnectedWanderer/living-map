import pino from 'pino';

/** Create a pino logger instance with optional custom log level. */
export function createLogger(level?: string): pino.Logger {
  return pino({ level: level || 'info' });
}
