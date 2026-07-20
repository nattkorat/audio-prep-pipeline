# Roadmap

Likely next improvements:

## Streaming Manifest Writes

Very large corpora currently build result lists before manifest writing.
Streaming records during conversion would reduce memory use and make progress
visible earlier.

## Richer Progress Reporting

Chunking has progress bars. Conversion could add similar reporting and summary
counts for large runs.

## Dataset Splits

Future manifest tooling could create train, validation, and test splits after
validation.
