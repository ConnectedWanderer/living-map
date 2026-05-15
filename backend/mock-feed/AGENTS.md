# Mock Feed - AI Agent Guide

## Purpose

Mock RSS feed service that generates random geo-tagged events for testing the Living Map application.

## Architecture

```
src/
├── index.js         # Express server entry point
├── routes/
│   └── feed.js      # GET /feed endpoint
└── utils/
    ├── generator.js # Random event generation
    └── rss.js       # RSS 2.0 XML builder
```

## Format

RSS 2.0 matching France24 EN structure:

- Namespace: `xmlns:atom`, `xmlns:media`, `xmlns:dc`
- Channel fields: `language`, `title`, `description`, `link`, `lastBuildDate`, `atom:link`
- Item fields: `category`, `title`, `link`, `description`, `guid`, `pubDate`, `dc:creator`

Reference: `https://www.france24.com/en/rss`

## Adding New Event Types

Edit `src/utils/generator.js`:

1. Add new type object to `eventTypes` array:

```js
{ type: 'NewType', templates: [
  'Event description in {location}',
  'Another template with {location}'
]}
```

2. Templates use `{location}` placeholder (optional `{magnitude}`)

## Modifying Output

- **RSS XML structure**: Edit `src/utils/rss.js`
- **Event count**: Use `?count=N` query param (10-100)
- **Port**: Set via `.env` file (default 3001)

## Dependencies

- `express`: HTTP server
- `uuid`: Unique ID generation

No external RSS libraries - uses custom XML builder.

## Related Documentation

- [README.md](README.md) — Setup, endpoints, configuration
