# E8 Leave-One-Feature-Family-Out Ablation Report

## Status

Complete when generated locally and checker passes.

## Design

- model: nearest-centroid transfer classifier.
- baseline: full 205-feature representation.
- ablations: full features minus one feature family at a time.

## Output rows

- prediction rows: 3024
- summary rows: 56
- delta rows: 56
- feature registry rows: 7

## Test split loss deltas versus full baseline

- minus_length_rhythm / paraphrase: macro_f1=0.381975, loss=0.413669, loss_delta_vs_full=0.032535
- minus_length_rhythm / modernize: macro_f1=0.56072, loss=0.234924, loss_delta_vs_full=0.018713
- minus_length_rhythm / simplify: macro_f1=0.436409, loss=0.359235, loss_delta_vs_full=0.04594
- minus_punctuation / paraphrase: macro_f1=0.404698, loss=0.298883, loss_delta_vs_full=-0.082251
- minus_punctuation / modernize: macro_f1=0.54109, loss=0.162491, loss_delta_vs_full=-0.05372
- minus_punctuation / simplify: macro_f1=0.435301, loss=0.26828, loss_delta_vs_full=-0.045015
- minus_lexical_richness / paraphrase: macro_f1=0.451894, loss=0.344086, loss_delta_vs_full=-0.037048
- minus_lexical_richness / modernize: macro_f1=0.621068, loss=0.174912, loss_delta_vs_full=-0.041299
- minus_lexical_richness / simplify: macro_f1=0.544596, loss=0.251384, loss_delta_vs_full=-0.061911
- minus_register_marker / paraphrase: macro_f1=0.398272, loss=0.34036, loss_delta_vs_full=-0.040774
- minus_register_marker / modernize: macro_f1=0.560215, loss=0.178417, loss_delta_vs_full=-0.037794
- minus_register_marker / simplify: macro_f1=0.447783, loss=0.290849, loss_delta_vs_full=-0.022446
- minus_function_word / paraphrase: macro_f1=0.378254, loss=0.416873, loss_delta_vs_full=0.035739
- minus_function_word / modernize: macro_f1=0.639354, loss=0.155773, loss_delta_vs_full=-0.060438
- minus_function_word / simplify: macro_f1=0.543546, loss=0.251581, loss_delta_vs_full=-0.061714
- minus_char3 / paraphrase: macro_f1=0.358137, loss=0.367531, loss_delta_vs_full=-0.013603
- minus_char3 / modernize: macro_f1=0.525521, loss=0.200147, loss_delta_vs_full=-0.016064
- minus_char3 / simplify: macro_f1=0.481296, loss=0.244372, loss_delta_vs_full=-0.068923
