# ADR 0011: Deterministic PDF layout and prose normalization

- Status: Accepted
- Date: 2026-08-16

## Context

The first similarity baseline for the 20-page DDD book sample exposed three extraction defects:
line-break hyphenation remained in prose, running page titles were indexed as content, and the
two visual lines of `Предисловие редакторской группы` became separate same-level headings.

These defects must be corrected before content-role classification and token-aware chunking. The
normalization behavior must remain deterministic, must not require an LLM or language dictionary,
and must not expose `pdfplumber` values outside the PDF adapter.

## Decision

Normalize PDF layout in two stages while preserving the existing `DocumentParser` and
`DocumentNormalizer` ports.

The `PdfParser` adapter cleans positioned lines before classifying `DocumentNode` values:

- inspect a configurable number of lines at the start and end of every page;
- identify bare page numbers, numbered running titles such as `20 | Предисловие`, and short
  punctuation-only page ornaments as page furniture;
- identify unnumbered margin text repeated on at least two pages as page furniture when its font
  is not larger than ordinary body text;
- merge consecutive same-level heading lines on one page when their visual gap is within the
  configured heading-join threshold;
- preserve newline boundaries inside extracted prose paragraphs for the next stage.

The technology-independent `DeterministicDocumentNormalizer` performs PDF dehyphenation only for
nodes carrying page provenance. It removes a hyphen followed by a physical line break between
letters. It retains the hyphen when the complete hyphenated word also occurs intact in the same
document, when the left fragment is an uppercase abbreviation, or when the right fragment is a
known hyphenated particle. Normal whitespace collapsing then removes the remaining physical line
breaks.

Code blocks are not dehyphenated. TXT and Markdown nodes do not receive PDF-specific
dehyphenation. Page furniture is retained and marked for the content-role indexing policy defined
separately by ADR 0012.

## Consequences

- The PDF adapter remains the only component aware of font sizes, visual gaps, and page edges.
- The domain normalizer remains independent of PDF libraries and selects PDF behavior from the
  existing application-owned page provenance.
- Parsed PDF paragraphs can contain physical newlines; normalized paragraphs retain the previous
  single-space prose contract.
- The behavior is reproducible and covered by synthetic multi-page PDF fixtures plus a dry-run on
  the representative 20-page book sample.
- Dictionary-free dehyphenation can still make mistakes for a compound that is split at its only
  occurrence. Corpus evaluation must precede expanding the heuristics.
- This changes parsing semantics. Existing searchable versions remain immutable; evaluation uses
  a newly uploaded document version and a complete reindex.
- The separate content-role policy decides whether identified page furniture is eligible for
  chunking, embedding, and indexing.

## Rejected alternatives

- Remove every hyphen followed by whitespace: rejected because the parser previously discarded
  the distinction between a physical line break and ordinary whitespace.
- Use a language dictionary or morphological analyzer: rejected because it adds language-specific
  dependencies and still cannot reliably resolve technical names.
- Use an LLM for cleanup: rejected because normalization must be deterministic and inexpensive.
- Put layout coordinates into domain values: rejected because current citations require page
  provenance, not permanent coupling to one PDF library's geometry model.
