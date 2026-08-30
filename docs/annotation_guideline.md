# Holdout Annotation Guideline

Written before annotation began. Committed to establish that labeling rules
were fixed in advance rather than settled case by case during labeling.

Sole annotator. Schema is the 11 DocLayNet v1.1 classes. No class is added,
merged, or omitted. Regions with no DocLayNet counterpart are left unlabeled
and logged in `notes`.

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

4. **Signatures.** DECIDE: excluded, or Picture. Apply uniformly.

5. **Agency logos and letterhead graphics.** DECIDE: Picture, or excluded when
   part of a header band.

6. **Repeated running headers and footers.** Page-header and Page-footer
   respectively, including contract numbers and page numbers.

7. **Scanned page skew.** Boxes are axis-aligned to the image, not to the
   skewed content. Box the content's bounding extent.

8. **DECIDE: minimum region size.** Regions below N pixels on either edge are
   not annotated. Record N.

## Ambiguity procedure

When a region does not clearly fall under a rule above, label it as a DocLayNet
annotator would and record page and reasoning in `notes`. The resulting list of
hard cases is reported in Analysis. Rules above are not revised mid-pass; any
revision requires re-checking all previously annotated pages.

## Order

Stratum rotation, four pages per cycle: bid_tabulation, scanned_addendum,
ifb_body, bid_forms. Partial completion yields coverage across all strata
rather than complete coverage of some.

## Field recovery

Annotated in the same pass. Same bounding box, additional text attribute
carrying the transcribed value. Blank issued forms have labels but no values;
these are recorded as label-present, value-absent.

## Excluded

No model predictions are used to seed, pre-populate, or suggest annotations.
All boxes drawn from scratch. Pre-annotation with the system under evaluation
would bias ground truth toward that system's outputs.
