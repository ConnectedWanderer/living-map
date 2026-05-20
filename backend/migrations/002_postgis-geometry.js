exports.up = (pgm) => {
  pgm.createExtension("postgis", { ifNotExists: true });

  pgm.addColumns("events", {
    location_geom: { type: "geometry(Point, 4326)" },
  });

  pgm.sql(`
    UPDATE events
    SET location_geom = ST_SetSRID(ST_MakePoint(
      (location->'features'->0->'geometry'->'coordinates'->>0)::float,
      (location->'features'->0->'geometry'->'coordinates'->>1)::float
    ), 4326)
    WHERE location IS NOT NULL
  `);

  pgm.dropColumns("events", ["location"]);
  pgm.renameColumn("events", "location_geom", "location");
  pgm.createIndex("events", "location", { method: "gist" });
};

exports.down = (pgm) => {
  pgm.dropIndex("events", "location");
  pgm.renameColumn("events", "location", "location_geom");

  pgm.addColumns("events", {
    location: { type: "jsonb" },
  });

  pgm.sql(`
    UPDATE events
    SET location = jsonb_build_object(
      'type', 'FeatureCollection',
      'features', jsonb_build_array(
        jsonb_build_object(
          'type', 'Feature',
          'geometry', jsonb_build_object(
            'type', 'Point',
            'coordinates', jsonb_build_array(ST_X(location_geom), ST_Y(location_geom))
          ),
          'properties', '{}'::jsonb
        )
      )
    )
    WHERE location_geom IS NOT NULL
  `);

  pgm.dropColumns("events", ["location_geom"]);
};
