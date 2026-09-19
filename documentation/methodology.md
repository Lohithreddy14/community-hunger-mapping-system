# Methodology - Preliminary Vulnerability Scoring

> **Read this first.** The score is a **preliminary academic model**. It gives an *estimated relative vulnerability category* from the indicators a user has entered. It does **not** measure hunger, it does not identify individual people, and it has **not** been validated with reliable real-world data. The weights and thresholds below are reasoned assumptions chosen so that the method is simple to explain, not values proven by research.

All parameters live at the top of `scoring.py`, so they can be changed in one place and every record is re-classified automatically (the category is calculated on demand and is not stored in the database).

---

## 1. Idea in one sentence

Convert each available indicator to a **risk value between 0 and 100**, combine them with **weights**, and convert the resulting **score (0-100)** into **Lower / Moderate / Higher**.

## 2. Indicators, risk values and weights

| # | Indicator | Weight | How it becomes a risk value (0-100) |
|---|---|---|---|
| 1 | Families needing assistance, as a percentage of total families | **0.45** | `risk = min(percentage / 40, 1) x 100`. So 0% gives 0, 20% gives 50, and 40% or more gives 100. |
| 2 | Food accessibility (rating entered by the user) | **0.25** | Good = 0, Moderate = 50, Poor = 100 |
| 3 | Number of nearby food-support centers (entered by the user) | **0.20** | 0 centers = 100, 1 = 60, 2 = 30, 3 or more = 0 |
| 4 | Average monthly household income (Rs.) | **0.10** | `risk = (40,000 - income) / 30,000 x 100`, limited to 0-100. Rs. 10,000 or less gives 100; Rs. 40,000 or more gives 0. |

Why these weights? The share of families reporting need is the most direct indicator, so it has the largest weight. Food accessibility and support-center availability describe how easily help and food can be reached. Income is an indirect indicator, so it has the smallest weight.

## 3. The formula

For the indicators that are **available**:

```
effective_weight_i = weight_i / (sum of the weights of the available indicators)
score              = sum( effective_weight_i x risk_i )          (result: 0 to 100)
```

If all four indicators are available, the effective weights equal the original weights.

## 4. Converting the score to a map category

| Score | Category | Map colour |
|---|---|---|
| less than 35 | Lower estimated vulnerability | Green |
| 35 up to (but not including) 65 | Moderate estimated vulnerability | Yellow |
| 65 or more | Higher estimated vulnerability | Red |

The colour on the map is always produced by these rules. Nothing is assigned randomly or by hand.

## 5. Handling missing values

- **Optional indicators** (food accessibility, nearby centers, income): if left blank, the indicator is **skipped** and the remaining weights are re-scaled so they add up to 1 again. No value is guessed. The details window marks skipped indicators as "not used", and the map popup shows how many of the four indicators were available.
- **Total families** (needed to compute the percentage in indicator 1): if blank, it is **estimated as `population / 4.5`**. This is an assumption (an assumed average household size) and is labelled "estimated" wherever it is shown. Entering the real number of families is always better.
- **Required fields** (population and families needing assistance) cannot be blank, so indicator 1 can always be calculated.
- The percentage is capped at 100% so unusual data cannot push the risk above 100.

## 6. Worked example 1 - all four indicators available

Community with 1,000 families, 100 of them needing assistance; accessibility Moderate; 1 nearby center; average income Rs. 25,000 per month.

| Indicator | Value | Risk | Weight | Contribution |
|---|---|---|---|---|
| Families needing assistance | 10% | 10 / 40 x 100 = 25 | 0.45 | 11.25 |
| Food accessibility | Moderate | 50 | 0.25 | 12.50 |
| Nearby centers | 1 | 60 | 0.20 | 12.00 |
| Household income | Rs. 25,000 | (40,000 - 25,000) / 30,000 x 100 = 50 | 0.10 | 5.00 |

**Score = 11.25 + 12.50 + 12.00 + 5.00 = 40.75, shown as 40.8 -> Moderate (yellow).**

## 7. Worked example 2 - missing values (sample record "Hilltop Nagar")

Population 5,200; total families **not entered**; 260 families needing assistance; accessibility Moderate; 2 nearby centers; income **not entered**.

- Estimated families = 5,200 / 4.5 = about 1,156. Percentage = 260 / 1,156 = 22.5%. Risk = 22.5 / 40 x 100 = 56.25.
- Income is skipped, so the available weights are 0.45 + 0.25 + 0.20 = 0.90. Effective weights: 0.45/0.90 = 0.500, 0.25/0.90 = 0.278, 0.20/0.90 = 0.222.

| Indicator | Risk | Effective weight | Contribution |
|---|---|---|---|
| Families needing assistance | 56.25 | 0.500 | 28.13 |
| Food accessibility (Moderate) | 50 | 0.278 | 13.89 |
| Nearby centers (2) | 30 | 0.222 | 6.67 |
| Income | not used | 0 | 0 |

**Score = 48.7 -> Moderate (yellow), based on 3 of 4 indicators.**

## 8. Additional information that is not part of the score

The map popup also shows the **nearest listed food-support center** and its distance in kilometres, calculated with the haversine (great-circle) formula from the coordinates. This is displayed for context only; it does not change the score. Because "nearby centers" in the score is a number typed by the user (and may include centers not listed in the system), the two can differ.

## 9. Validity and limitations (be ready to explain in a viva)

- The weights, the 40% cap, the income limits and the 35/65 thresholds are **assumptions**. A different reasonable choice would change some categories.
- The score is **relative and ordinal**. A community scoring 60 is not "twice as vulnerable" as one scoring 30.
- Results depend entirely on the quality of the input data. The sample data is fictional, so the sample categories only demonstrate how the system works.
- Important factors are not included yet, for example seasonal income, disability, child nutrition, dependency ratios, prices and transport.
- **Next steps for validation:** collect real survey data, compare the model's categories with expert or field assessments, test alternative weights (sensitivity analysis), and adjust the model based on evidence.

## 10. Where the code is

| Item | File |
|---|---|
| Weights, thresholds, formula | `scoring.py` (`WEIGHTS`, `analyse_community`, `categorize`) |
| Input rules | `validation.py` |
| API returning the analysis | `GET /api/analysis` and the `analysis` field of `GET /api/communities` |
| Tests of the formula | `tests/test_app.py` (`ScoringTests`) |
