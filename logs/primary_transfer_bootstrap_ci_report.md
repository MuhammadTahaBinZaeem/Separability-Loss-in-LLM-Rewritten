# Primary Transfer Bootstrap CI Report

- bootstrap replicates per comparison: 5000
- paired passages per comparison: 54
- seed: 20260609

## Test split focus

- nearest_centroid / paraphrase: loss=0.381134, 95% CI [0.261805, 0.502832], nonpositive_rate=0.0
- nearest_centroid / modernize: loss=0.216211, 95% CI [0.099657, 0.346396], nonpositive_rate=0.0
- nearest_centroid / simplify: loss=0.313294, 95% CI [0.193906, 0.448514], nonpositive_rate=0.0
- diagonal_gaussian_nb / paraphrase: loss=0.336928, 95% CI [0.200441, 0.471742], nonpositive_rate=0.0
- diagonal_gaussian_nb / modernize: loss=0.170812, 95% CI [0.050751, 0.304165], nonpositive_rate=0.0018
- diagonal_gaussian_nb / simplify: loss=0.311061, 95% CI [0.172679, 0.45574], nonpositive_rate=0.0
- linear_discriminant_shrinkage / paraphrase: loss=0.386699, 95% CI [0.265921, 0.504839], nonpositive_rate=0.0
- linear_discriminant_shrinkage / modernize: loss=0.178694, 95% CI [0.071128, 0.301491], nonpositive_rate=0.0002
- linear_discriminant_shrinkage / simplify: loss=0.357297, 95% CI [0.229058, 0.496117], nonpositive_rate=0.0
