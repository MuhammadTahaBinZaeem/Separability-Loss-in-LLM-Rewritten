# Explanatory model: common shift versus uniform contraction

Recorded 2026-09-22 while the first domain-transfer run was executing, before
its performance results were inspected. This is another exploratory analysis,
not a preregistered extension or evidence of a new linguistic law.

JQL's current scope explicitly says computational application without substantive
theoretical advancement is insufficient. A possible measurement contribution
is to distinguish a common displacement from contraction of author-associated
centroid differences. Neither phenomenon is identifiable from original-trained
classification loss alone. Source:
https://www.tandfonline.com/journals/njql20/about-this-journal

Let x_w and y_w be original and rewritten feature centroids for work w, in
coordinates standardized using only original texts from the training works.
Fit the restricted mapping y_w = alpha*x_w + b + e_w. Here b is a common vector,
alpha is one scalar shared by all features/works, and e_w is the residual.
Unconstrained alpha is estimated by least squares after centering both matrices
over training works. Do not force alpha below one to manufacture contraction.

For evaluation centroids centered over the same six held-out authors,
B_y = alpha^2*B_x + B_e + 2*alpha*C_xe, where B denotes mean square centered
dispersion and C the mean centered cross-product. Under exact translation,
alpha=1 and B_y=B_x even if an unadapted classifier makes more errors. Under
exact scalar contraction with no residual, B_y=alpha^2*B_x. Real data can reject
this restricted explanation through poor prediction on unseen works. A ratio
below one alone cannot prove linguistic homogenization or information loss.

## Fixed evaluation

Use the already defined common cohorts, folds and shared original-fit features.
Panels: valid_full, w200_middle, w300_middle. Feature families: all retained
stylometric features and function words alone. All three rewrite instructions.
Fit on 12 equally weighted work centroids (two works per author); evaluate on
six different work centroids (one per author). No held-out centroid participates
in estimation of alpha, b, vocabulary or standardization.

Compare three fixed models: identity (alpha=1,b=0), common translation
(alpha=1,b=mean(y-x)), and scalar affine (alpha estimated, b=mean(y)-alpha*mean(x)).
Record every parameter, feature and train/test work ID, all held-out work
predictions and mean squared residuals. Report all panels and families, whether
or not the affine model improves. A scalar affine fit is deliberately simple;
do not add transformations after observing weak results in this extension.

Report held-out mean-square error and the paired improvement of translation
over identity and scalar affine over translation. Use 5,000 work-only bootstrap
replicates within the six fixed authors (three works per author), conditional
on these fitted mappings and observed centroids. These marginal descriptive
intervals omit passage/training uncertainty and are not confirmatory tests.
The work bootstrap does not turn 18 works into a population-wide law.

This may support a falsifiable methodological explanation, but established
affine algebra is not a novel theorem. Novelty must come from a well-validated
linguistic hypothesis and its evidence. Independent untouched-work replication
and genuine semantic/source review remain necessary for a strong submission.
