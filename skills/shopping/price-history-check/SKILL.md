---
name: price-history-check
description: "Check whether an Amazon price is actually a deal: cross-check an ASIN or product against CamelCamelCamel price history and other retailers before calling a sale price good. Use when the user asks if a price is a deal, whether to buy now or wait, or wants a price cross-check."
---

# Price History Check

An Amazon search result tells you today's price. It does not tell you whether that price is good. Sellers raise the list price before a "sale," park products at a high anchor price most of the year, and drop to the real price for events. The discount percentage on the card is marketing. The history is the evidence. This skill is the cross-check that runs before anyone calls a price a deal.

## When to use

- The user asks "is this a good price," "is this actually on sale," or "should I buy now or wait."
- A search (yours, via the `amazon-search` skill, or the user's own link) produced a price that a purchase decision depends on.
- A deal, flyer, or sale claim needs verifying before it is repeated to the user as fact.

## Inputs

Any one of: an ASIN, an Amazon product URL (the ASIN is in it), or a product name plus the storefront. If all you have is a name, get the ASIN first from an `amazon-search` run or a `shopping` skill search, and say which exact listing you checked; histories attach to listings, not product names, and variants (size, colour, generation) have different histories.

## The check, in order

1. **Today's price, from a live source.** Use the `amazon-search` skill for the storefront in question, or the user's own listing link. Note the price type it represents: sold-by-Amazon, or a third-party Marketplace seller. The two have different histories and different risk.
2. **History from CamelCamelCamel.** Open the product's page on the storefront's CamelCamelCamel site (ca.camelcamelcamel.com for Amazon.ca, camelcamelcamel.com for Amazon.com, and the matching country subdomain for other storefronts) at `/product/<ASIN>`. Read it in a real browser: plain text fetchers get a 403 from the site, while the page itself loads anonymously with no account. Read the price statistics for the matching price type (Amazon, Third-Party New): **current, lowest ever and its date, highest, average.** Coverage varies by type: a listing sold only through Marketplace sellers may have a full Third-Party New track and no Amazon-price data at all, and the page flags stale tracks ("price over 7 days old"). If the product is not tracked, say so and fall to step 4 with the history marked unavailable; an untracked product is not a verified deal or a fake one, it is an unknown.
3. **Place today's price against the history.** The verdict comes from three comparisons: today versus the all-time low (how much room is left), today versus the average (is "sale" just the normal price wearing a badge), and the shape over the last 3 to 6 months (a genuine drop, a flat line, or a spike-then-"discount" that only returns to normal). A list price that appeared recently, just before the discount, is the classic tell of an inflated anchor.
4. **Spot-check one or two other retailers** when the product is sold beyond Amazon, through the `shopping` skill or a web search: for Canadian shopping, Best Buy Canada, Canada Computers, Memory Express, Costco.ca, or Walmart Canada, whichever actually stock the category. One matching lower everyday price elsewhere ends the debate. Match the exact variant; a different size or generation is a different product.
5. **Report the verdict in one line first**, then the numbers: genuine deal (at or near the historical low), fair price (around the average, no urgency), inflated anchor (the "discount" returns to the usual price), or unknown (no history available). Give the low, the average, and today's price with its storefront and currency, and the date of the low. Prices move; say when the check ran.

## Limits and honesty

- **History lags and has gaps.** CamelCamelCamel polls; it is not a tick feed. A price that changed this morning may not show yet. Treat the stats as the record up to the last update the page reports.
- **Price types do not mix.** Never compare today's third-party price against the Amazon-price history, or the reverse. If only the other type's history exists, say the comparison is approximate.
- **Coupons, Subscribe & Save, and member prices** change the real total and usually do not appear in history tracks. If the decision depends on them, check the product page itself and price the actual checkout path, not the card.
- **Shipping decides close calls.** A lower sticker from a third-party or overseas seller with steep shipping is not cheaper. This is the same trap the `amazon-search` skill flags; it applies with full force here.
- **No history is an answer too.** New, niche, or frequently re-listed products may have no usable track. Report "no history available" plainly instead of substituting a guess, and lean on the retailer spot-check.

## Sharing and fresh setup

No setup and no accounts: the checks run on public pages and the platform's existing search and shopping tools. CamelCamelCamel offers the free Camelizer browser extension, which puts the same history chart on the Amazon product page itself; worth suggesting to a user who checks prices often, but never required for this skill.

Last verified: 2026-10-24 from a Muse VM, in a real browser with no account. ca.camelcamelcamel.com/product/B00XIKPUK4 (NAKED Whey 2LB, Amazon.ca) loaded its full chart and statistics table anonymously. That listing carries only a Third-Party New track (lowest $59.99 on 2024-07-15, average $72.32, tracked since 2024-07-15) and no Amazon-price data, and the page flagged its data as over 7 days old: a typical case, and exactly why the verdict rules above treat missing or stale tracks as unknowns rather than deals.
