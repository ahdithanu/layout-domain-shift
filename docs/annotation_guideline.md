# Holdout Annotation Guideline

Written before annotation began. Committed to establish that labeling rules
were fixed in advance rather than settled case by case during labeling.

Sole annotator. Schema is the 11 DocLayNet v1.1 classes. No class is added,
merged, or omitted. Regions with no DocLayNet counterpart are left unlabeled
and logged in `notes`.

Corpus: 25 pages, 5 documents, 3 issuers, 4 strata. Page selection and
text-layer classification are recorded in `data/holdout/manifest.csv` and were
produced by `src/build_holdout.py` from measured page properties, not by
inspection.

## Governing principle

Label by DocLayNet semantic role, not by visual container. Fills, borders,
shading, and highlighting are styling and do not determine class.

## Resolved cases

1. **Highlighted response blocks** (LA County addendum). Green fill with an
   underline rule is styling. Label the block Text. Not Table, not a form field.

2. **ASCII-ruled tables** (Caltrans bid summary). Rows of hyphens and pipes are
   the table's borders. Label Table, box drawn to include the rules. Applies to
   the itemized proposal grid and the multi-bidder comparison.

3. **Empty form grids** (Caltrans forms for bid). One Table covering the whole
   grid including its header row. Not one region per row.

4. **Signatures.** Excluded. DocLayNet's Picture class covers figures and images
   in document body content. A handwritten signature is neither, and labeling it
   Picture would create a ground-truth instance the checkpoint was never trained
   to emit, producing a false negative that does not reflect model behavior.

5. **Agency logos and letterhead graphics.** Picture when the graphic is
   discrete and can be boxed without capturing text. Excluded when fused into a
   header band with text baked in. Under this rule the Caltrans logo on the
   forms cover is Picture; the LA County letterhead band is excluded.

6. **Repeated running headers and footers.** Page-header and Page-footer
   respectively, including contract numbers and page numbers.

7. **Scanned page skew.** Boxes are axis-aligned to the image, not to the
   skewed content. Box the content's bounding extent.

8. **Minimum region size.** Regions smaller than 10 pixels on either edge at
   150 dpi are not annotated. This excludes rule fragments and scan speckle
   while retaining page numbers.

9. **Multi-column body text.** One region per column, not one spanning both.
   Matches DocLayNet convention.

10. **Continuation regions across pages.** A paragraph or table split by a page
    break is annotated as a separate region on each page. No cross-page linking.

11. **Column headers within a table.** Included inside the Table region, not
    labeled separately as Section-header.

## Ambiguity procedure

When a region does not clearly fall under a rule above, label it as a DocLayNet
annotator would and record page and reasoning in `notes`. The resulting list of
hard cases is reported in Analysis. Rules above are not revised mid-pass; any
revision requires re-checking all previously annotated pages.

## Order

Stratum rotation, four pages per cycle: bid_tabulation, scanned_addendum,
ifb_body, bid_forms. Partial completion yields coverage across all strata
rather than complete coverage of some. If annotation is halted before all 25
pages are complete, the number of completed pages per stratum is reported.

## Field recovery

Annotated in the same pass. Same bounding box, additional text attribute
carrying the transcribed value. Blank issued forms have labels but no values;
these are recorded as label-present, value-absent, and are excluded from
field-recovery accuracy since there is no value to recover.

## Excluded

No model predictions are used to seed, pre-populate, or suggest annotations.
All boxes drawn from scratch. Pre-annotation with the system under evaluation
would bias ground truth toward that system's outputs by an amount that cannot
be quantified or disclosed.

## Known limitations

Single annotator, so no inter-annotator agreement can be computed. Drift across
the pass is mitigated by fixing rules in advance and by stratum rotation rather
than sequential completion.

Caltrans is the issuer for 3 of 5 documents. Per-class results reflect that
concentration and are reported with document counts alongside page counts.

13. **Table titles.** [Included inside the Table region | Labeled Caption].
    Applied uniformly to all bordered charts and tables.

13. **Table titles.** [Included inside the Table region | Labeled Caption].
    Applied uniformly to all bordered charts and tables.

13. **Table titles.** [Included inside the Table region | Labeled Caption].
    Applied uniformly to all bordered charts and tables.

14. **Signature blocks.** Rule 4 excludes dedicated signature regions. Where a
    signature sits within a larger block (heading, rule line, role, date), the
    block is annotated Text and the signature is not carved out.

15. **Professional stamps and seals.** Picture. Discrete graphics boxable
    without capturing body text, per rule 5.

16. **Multi-section forms.** Rule 3 (one Table per empty form grid) applies to a
    single contiguous grid. Where a bordered form contains multiple distinct
    grids separated by banners or prose, each grid is its own Table, banners are
    Section-header, and prose blocks are Text.
