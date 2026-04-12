function escapeXml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export function buildRssFeed(events) {
  const now = new Date().toUTCString();
  
  let xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <language>en</language>
    <title>Living Map Events Feed</title>
    <description>Random geo-tagged events for testing the Living Map application</description>
    <link>http://localhost:3001/feed</link>
    <lastBuildDate>${now}</lastBuildDate>
    <atom:link href="http://localhost:3001/feed" rel="self" type="application/rss+xml"/>`;
  
  for (const event of events) {
    xml += `
    <item>
      <category>${escapeXml(event.category)}</category>
      <title>${escapeXml(event.title)}</title>
      <link>${escapeXml(event.link)}</link>
      <description>${escapeXml(event.description)}</description>
      <guid isPermaLink="false">${escapeXml(event.id)}</guid>
      <pubDate>${event.pubDate}</pubDate>
      <dc:creator>Living Map</dc:creator>
    </item>`;
  }
  
  xml += `
  </channel>
</rss>`;
  
  return xml;
}