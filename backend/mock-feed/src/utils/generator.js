const { v4: uuidv4 } = await import('uuid');

const eventTypes = [
  { type: 'Earthquake', templates: [
    'Magnitude {magnitude} earthquake reported in {location}',
    'Earthquake detected near {location}',
    'Seismic activity recorded in {location}'
  ]},
  { type: 'Protest', templates: [
    'Large protest underway in {location}',
    'Demonstrators gather in {location}',
    'Protests continue in {location} for second day'
  ]},
  { type: 'Accident', templates: [
    'Traffic accident reported in {location}',
    'Vehicle collision in {location} causes delays',
    'Multi-vehicle accident in {location}'
  ]},
  { type: 'Weather Alert', templates: [
    'Severe weather warning issued for {location}',
    'Storm system approaching {location}',
    'Heavy rainfall expected in {location}'
  ]},
  { type: 'Fire', templates: [
    'Fire breaks out in {location}',
    'Wildfire spreads near {location}',
    'Industrial fire reported in {location}'
  ]},
  { type: 'Flood', templates: [
    'Flooding reported in {location}',
    'Flash flood warning for {location}',
    'River levels rise in {location}'
  ]},
  { type: 'Traffic Incident', templates: [
    'Major traffic disruption in {location}',
    'Road closure due to incident in {location}',
    'Heavy congestion reported in {location}'
  ]},
  { type: 'Security Alert', templates: [
    'Security alert in {location}',
    'Police operation in {location}',
    'Increased security presence in {location}'
  ]},
  { type: 'Infrastructure', templates: [
    'Power outage reported in {location}',
    'Water main break in {location}',
    'Building collapse in {location}'
  ]},
  { type: 'Health', templates: [
    'Health emergency declared in {location}',
    'Disease outbreak reported in {location}',
    'Hospital overwhelmed in {location}'
  ]}
];

const locations = [
  'Tokyo', 'New York', 'London', 'Paris', 'Sydney', 'Berlin', 'Madrid',
  'Rome', 'Toronto', 'Mexico City', 'São Paulo', 'Mumbai', 'Beijing',
  'Seoul', 'Singapore', 'Dubai', 'Cairo', 'Moscow', 'Los Angeles',
  'Chicago', 'Miami', 'Seattle', 'Boston', 'Houston', 'Denver',
  'Amsterdam', 'Vienna', 'Stockholm', 'Oslo', 'Copenhagen', 'Helsinki',
  'Warsaw', 'Prague', 'Budapest', 'Athens', 'Lisbon', 'Barcelona',
  'Manchester', 'Liverpool', 'Glasgow', 'Birmingham', 'Leeds',
  'Hong Kong', 'Taipei', 'Bangkok', 'Jakarta', 'Kuala Lumpur',
  'Istanbul', 'Tel Aviv', 'Beirut', 'Riyadh', 'Abu Dhabi', 'Doha'
];

const magnitudes = [3.5, 4.2, 4.8, 5.1, 5.5, 5.9, 6.2, 6.7];

function randomElement(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateTimestamp() {
  const now = new Date();
  const hoursAgo = Math.random() * 24;
  const timestamp = new Date(now.getTime() - hoursAgo * 60 * 60 * 1000);
  return timestamp.toUTCString();
}

export function generateRandomEvents(count = 50) {
  const events = [];
  
  for (let i = 0; i < count; i++) {
    const eventType = randomElement(eventTypes);
    const location = randomElement(locations);
    const template = randomElement(eventType.templates);
    
    let title = template.replace('{location}', location);
    if (template.includes('{magnitude}')) {
      title = title.replace('{magnitude}', randomElement(magnitudes));
    }
    
    const id = uuidv4();
    const pubDate = generateTimestamp();
    
    events.push({
      id,
      title,
      link: `https://example.com/events/${id}`,
      description: `Event details for ${title.toLowerCase()}. This is a mock event for testing purposes.`,
      pubDate,
      category: eventType.type
    });
  }
  
  return events.sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate));
}