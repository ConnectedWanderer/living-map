# Next Steps

## Observability: Grafana for Scaleway Logs

**Current state:** Logs viewed ad-hoc via [Scaleway Console](../docs/architecture/deployment.md#monitoring) or `scw container logs`. No external monitoring — the deployment guide notes "No external monitoring service required at this scale."

**Problem:** As the project grows, ad-hoc log inspection becomes insufficient. There's no way to:

- Search across all services (ingestion-worker, LES, tile API) in one view
- Set up alerts for job failures or latency spikes
- Query structured logs (e.g. "how many LES runs produced empty results last week?")
- Visualize trends over time (error rate, processing time per document)

**Proposed approach:** Integrate Scaleway's Managed Grafana or self-host Grafana + Loki to centralize logs from all serverless containers and jobs. Services already emit structured JSON logs, so the main work is:

1. Configure log shipping from Scaleway Serverless to a Grafana datasource
2. Build dashboards for each service (throughput, error rate, latency percentiles)
3. Set up alerting rules for critical failures
4. Document the observability stack in a new ADR

**Links:** [Deployment Monitoring](../docs/architecture/deployment.md#monitoring)

---

## Location Extraction: Accuracy & Precision

**Current state:** The LES uses spaCy small models (`en_core_news_sm`, `fr_core_news_sm`) and geonamescache for offline geocoding. Disambiguation relies on heuristic scoring (position, entity type weighting, preposition context). See [Location Extraction Architecture](../docs/architecture/location-extraction.md).

### Goal 1: Increase recall (identify more locations)

- **Upgrade spaCy models** — swap `_sm` for `_md` or `_lg` models to improve entity recognition accuracy (especially for less common place names)
- **Add more languages** — extend the `_MODEL_MAP` beyond EN/FR (e.g. DE, ES, IT) as multilingual articles appear in feeds
- **Gazetteer booster** — as explored in [ADR-020](../docs/decisions/ADR-020-gazetteer-as-ner-recall-booster.md), use a gazetteer-based NER recall booster to catch locations the spaCy model misses
- **Expand evaluation corpus** — add more diverse article types with marginal/obscure location references to measure recall improvements

### Goal 2: Reduce false positives (avoid misidentifying locations)

- **Improve disambiguation heuristics** — the current weighted scoring (GPE 2.5x vs LOC 1.0x, position boost) is simple. Consider:
  - Contextual rejection: ignore entities that appear in non-geographic contexts (e.g. "Washington" in "Washington said..." vs "...Washington, DC")
  - Confidence thresholds: drop low-scoring matches instead of always picking the best
  - Cross-entity consistency: if multiple GPE entities point to the same region, boost that region
- **Geocoding quality** — geonamescache uses population-based disambiguation. For low-population places sharing names with famous cities (e.g. Paris, TX vs Paris, France), add fallback heuristics or a secondary geocoder
- **Evaluation-driven iteration** — extend the NER evaluation protocol ([ADR-002](../docs/decisions/ADR-002-ner-evaluation-protocol.md)) to track false-positive rate, and gate model changes on not regressing precision below a threshold

**Links:** [Location Extraction Architecture](../docs/architecture/location-extraction.md), [Evaluation Guide](../docs/evaluation.md), [ADR-001](../docs/decisions/ADR-001-location-extraction-approach.md), [ADR-020](../docs/decisions/ADR-020-gazetteer-as-ner-recall-booster.md)
