# Architecture Documentation

## System Design

| Document                                                     | Description                                      | Status   |
| ------------------------------------------------------------ | ------------------------------------------------ | -------- |
| [Architecture Overview](./architecture/overview.md)          | System-wide architecture, tech stack, data flow  | Approved |
| [Location Extraction](./architecture/location-extraction.md) | NLP service for extracting coordinates from text | Draft    |

## Decisions

| Document                                                                                     | Description                      | Status   |
| -------------------------------------------------------------------------------------------- | -------------------------------- | -------- |
| [ADR-001: Location Extraction Approach](./decisions/ADR-001-location-extraction-approach.md) | Decision to use spaCy + text2geo | Accepted |
| [ADR-002: NER Evaluation Protocol](./decisions/ADR-002-ner-evaluation-protocol.md) | NER quality evaluation with entity-level exact match | Accepted |
