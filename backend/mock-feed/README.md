# Mock Feed

Mock RSS feed service for testing the Living Map application.

## Quick Start

```bash
cd backend/mock-feed
npm install
npm run dev
```

## Endpoint

- **URL**: `http://localhost:3001/feed`
- **Optional query**: `?count=N` (N between 10-100, default: 50)

Example:

```bash
curl http://localhost:3001/feed?count=20
```

## Configuration

Create a `.env` file in this directory:

```
PORT=3001
```

## Output Format

RSS 2.0 with English content. Each item includes:

- `title`: Event description with location
- `description`: Event details
- `category`: Event type (Earthquake, Protest, Fire, etc.)
- `pubDate`: Random timestamp within last 24 hours
- `guid`: Unique identifier

## Event Types

- Earthquake
- Protest
- Accident
- Weather Alert
- Fire
- Flood
- Traffic Incident
- Security Alert
- Infrastructure
- Health
