# Business Insights and Recommendations

## Key findings

1. **Delivery performance strongly affects customer experience.** On-time deliveries received an average review score of 4.29, compared with 2.57 for delayed deliveries.
2. **Longer delivery is associated with worse reviews.** Delivery days and review score had a correlation of -0.33.
3. **Customer retention is low.** Only 3.00% of delivered-order customers made more than one purchase.
4. **Health and beauty leads category performance.** `beleza_saude` generated approximately R$1,412,089.53 in gross order value.
5. **November 2017 was the peak month.** Delivered orders generated approximately R$1,153,364.20 in gross order value.
6. **Average spending differs across product categories.** One-way ANOVA produced F = 188.50 with p < 0.001.
7. **Payment method has little practical influence on order status.** The chi-square test was significant, but Cramer's V was only 0.0393.

## Statistical evidence

| Test | Question | Result |
|---|---|---|
| Welch's t-test | Do review scores differ between on-time and delayed orders? | Significant difference, t = 89.38, p < 0.001 |
| One-way ANOVA | Does average spending differ across major categories? | Significant difference, F = 188.50, p < 0.001 |
| Chi-square | Are payment method and order status associated? | Significant but extremely weak association, Cramer's V = 0.0393 |

## Recommendations

1. Track late-delivery rates by state and seller, and create operational alerts before estimated delivery dates are missed.
2. Review seller and carrier service levels for regions with persistent delays.
3. Launch post-delivery retention campaigns, loyalty benefits, and personalized offers for first-time customers.
4. Maintain inventory and seller capacity for high-performing categories while avoiding excessive dependence on a single category.
5. Monitor delivery metrics together with review scores as a customer-experience KPI.
6. Treat payment method as a low-priority predictor because its practical association with order status is extremely weak.

## Limitations

- Results describe the historical period covered by the dataset and should not be treated as current market forecasts.
- Correlation and group differences show association, not proof of causation.
- The final month may contain incomplete data.
- Some state and category comparisons have unequal sample sizes.
