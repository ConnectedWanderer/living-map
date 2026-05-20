import crypto from "node:crypto";

interface RawArticle {
  guid?: string;
  title: string;
  description?: string;
  link: string;
  pubDate: string;
}

export interface NormalizedArticle {
  source_id: string;
  title: string;
  description: string | undefined;
  url: string;
  published_at: string;
  source: string;
}

export function normalizeArticle(raw: RawArticle, source: string): NormalizedArticle {
  const sourceId = raw.guid
    || crypto.createHash("sha256").update(raw.title + raw.pubDate).digest("hex");

  return {
    source_id: sourceId,
    title: raw.title,
    description: raw.description,
    url: raw.link,
    published_at: new Date(raw.pubDate).toISOString(),
    source,
  };
}
