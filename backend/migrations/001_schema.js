exports.up = (pgm) => {
  pgm.createExtension("postgis", { ifNotExists: true });

  pgm.createTable("sources", {
    id: { type: "serial", primaryKey: true },
    name: { type: "text", notNull: true, unique: true },
    type: { type: "text", notNull: true },
    config: { type: "jsonb", notNull: true, default: "{}" },
    schedule: { type: "text", notNull: true },
    enabled: { type: "boolean", notNull: true, default: true },
    created_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
    updated_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
  });

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
    created_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
    updated_at: { type: "timestamptz", notNull: true, default: pgm.func("now()") },
  });

  pgm.addConstraint("events", "uq_events_source_source_id", {
    unique: ["source", "source_id"],
  });

  pgm.createIndex("events", "location", { method: "gist" });
};

exports.down = (pgm) => {
  pgm.dropTable("events");
  pgm.dropTable("sources");
  pgm.dropExtension("postgis", { ifExists: true });
};
