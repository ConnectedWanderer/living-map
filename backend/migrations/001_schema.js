exports.up = (pgm) => {
  pgm.createExtension("postgis", { ifNotExists: true });

  pgm.createSchema("living_map", { ifNotExists: true });

  pgm.createTable("sources", {
    id: { type: "serial", primaryKey: true },
    name: { type: "text", notNull: true, unique: true },
    type: { type: "text", notNull: true },
    config: { type: "jsonb", notNull: true, default: "{}" },
    schedule: { type: "text", notNull: true },
    enabled: { type: "boolean", notNull: true, default: true },
    created_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
    updated_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
  }, { schema: "living_map" });

  pgm.createTable("events", {
    id: { type: "serial", primaryKey: true },
    source: { type: "text", notNull: true },
    source_id: { type: "text", notNull: true },
    title: { type: "text", notNull: true },
    description: { type: "text" },
    url: { type: "text" },
    published_at: { type: "timestamptz" },
    location: { type: "geometry(Point, 4326)" },
    location_name: { type: "text" },
    country: { type: "text" },
    created_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
    updated_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
  }, { schema: "living_map" });

  pgm.addConstraint("events", "uq_events_source_source_id", {
    unique: ["source", "source_id"],
    schema: "living_map",
  });

  pgm.createIndex("events", "location", { method: "gist", schema: "living_map" });
  pgm.createIndex("events", "published_at", { schema: "living_map" });

  pgm.sql(`
    INSERT INTO living_map.sources (name, type, config, schedule, enabled)
    VALUES (
      'nyt-world',
      'rss',
      '{"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "source": "nyt-world"}',
      '*/15 * * * *',
      true
    ) ON CONFLICT (name) DO NOTHING;
  `);
};

exports.down = (pgm) => {
  pgm.dropTable({ schema: "living_map", name: "events" }, { ifExists: true, cascade: true });
  pgm.dropTable({ schema: "living_map", name: "sources" }, { ifExists: true, cascade: true });
  pgm.dropSchema("living_map", { ifExists: true, cascade: true });
};
