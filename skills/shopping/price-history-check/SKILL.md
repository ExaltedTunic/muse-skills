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

Any one of: an ASIN, an Amazon product URL (the ASIN is in it), or a product name plus the storefront. If all you have is a name, get the ASIN first from an `amazon-search` run or a `shopping` skill search, and say which exact listing you checked; histories attach to listings, not product names, and variants (size, colour, generation) have different histories. For a variant product, resolve the specific child ASIN for the exact option being priced (the size, colour, or pack count selected) before querying the history; the parent listing's track describes a different product.

## The check, in order

1. **Today's price, from a live source.** Use the `amazon-search` skill for the storefront in question, or the user's own listing link. Note the price type it represents: sold-by-Amazon, or a third-party Marketplace seller. The two have different histories and different risk.
2. **Verify the exact offer on the product page, when its identity is not already established.** A search result does not reliably establish the seller, the fulfillment channel (shipped by Amazon vs seller-fulfilled), the condition, or which variant is actually priced. When any of those is unknown from the search results, a product-page verification step is required before any history verdict: open the `/dp/<ASIN>` page and record the exact offer (seller, fulfillment, condition, and the variant and child ASIN being priced), the comparison track the history will be read against (Amazon or Third-Party New), the source URLs (the search result and the product page), and the last-observed time of today's price. If that evidence cannot be obtained, the verdict stays **unknown / approximate** and must say why, naming the field that could not be established, rather than quietly comparing against the wrong track. Keep shipping and coupons separate from the tracked base price in this record too: they change the real total, never the history comparison.
3. **History from CamelCamelCamel.** CamelCamelCamel covers only some Amazon storefronts: the US storefront on the bare domain (camelcamelcamel.com), plus country subdomains for ca, uk, de, fr, es, it and au (ca.camelcamelcamel.com for Amazon.ca, and so on). Open the product's page there at `/product/<ASIN>`. Read it in a real browser: plain text fetchers get a 403 from the site, while the page itself loads anonymously with no account. Read the price statistics for the matching price type (Amazon, Third-Party New): **current, lowest ever and its date, highest, average.** Coverage varies by type: a listing sold only through Marketplace sellers may have a full Third-Party New track and no Amazon-price data at all, and the page flags stale tracks ("price over 7 days old"). Other Amazon storefronts have no CamelCamelCamel site at all; for those storefronts, and for products CamelCamelCamel does not track, go to step 4 (Keepa) before treating the history as unavailable. An untracked product is not a verified deal or a fake one, it is an unknown.
4. **History from Keepa, when CamelCamelCamel cannot answer.** Open the product's page on keepa.com (search by ASIN, or the product URL `keepa.com/#!product/<domain-id>-<ASIN>`) in a real browser. Keepa tracks more storefronts than CamelCamelCamel, including Amazon.co.jp, .in, .com.mx and .com.br, and it often carries the Amazon-price track for listings where CamelCamelCamel is blank or third-party only. Read the same statistics for the matching price type: current, lowest ever and its date, highest, average. Some Keepa detail sits behind an account; read what the page shows anonymously and never sign up or log in for a price check. If the Keepa page cannot be read or the product is not tracked there either, the history is unavailable: say so, continue to the retailer spot-check, and let the verdict rest on that rather than treating the miss as evidence for or against a deal.
5. **Place today's price against the history.** The verdict comes from three comparisons: today versus the all-time low (how much room is left), today versus the average (is "sale" just the normal price wearing a badge), and the shape over the last 3 to 6 months (a genuine drop, a flat line, or a spike-then-"discount" that only returns to normal). A list price that appeared recently, just before the discount, is the classic tell of an inflated anchor.
6. **Spot-check one or two other retailers** when the product is sold beyond Amazon, through the `shopping` skill or a web search: for Canadian shopping, Best Buy Canada, Canada Computers, Memory Express, Costco.ca, or Walmart Canada, whichever actually stock the category. One matching lower everyday price elsewhere ends the debate. Match the exact variant; a different size or generation is a different product.
7. **Report the verdict in one line first**, then the numbers: genuine deal (at or near the historical low), fair price (around the average, no urgency), inflated anchor (the "discount" returns to the usual price), or unknown (no history available). Give the low, the average, and today's price with its storefront and currency, and the date of the low. Prices move; say when the check ran.

## Limits and honesty

- **History lags and has gaps.** CamelCamelCamel polls; it is not a tick feed. A price that changed this morning may not show yet. Treat the stats as the record up to the last update the page reports.
- **Price types do not mix.** Never compare today's third-party price against the Amazon-price history, or the reverse. If only the other type's history exists, say the comparison is approximate.
- **Coupons, Subscribe & Save, and member prices** change the real total and usually do not appear in history tracks. If the decision depends on them, check the product page itself and price the actual checkout path, not the card.
- **Shipping decides close calls.** A lower sticker from a third-party or overseas seller with steep shipping is not cheaper. This is the same trap the `amazon-search` skill flags; it applies with full force here.
- **No history is an answer too.** New, niche, or frequently re-listed products may have no usable track. Report "no history available" plainly instead of substituting a guess, and lean on the retailer spot-check.

## Sharing and fresh setup

No setup and no accounts: the checks run on public pages and the platform's existing search and shopping tools. CamelCamelCamel offers the free Camelizer browser extension, which puts the same history chart on the Amazon product page itself; worth suggesting to a user who checks prices often, but never required for this skill.

Last verified: 2026-10-24 from a Muse VM, in a real browser with no account. ca.camelcamelcamel.com/product/B00XIKPUK4 (NAKED Whey 2LB, Amazon.ca) loaded its full chart and statistics table anonymously. That listing carries only a Third-Party New track (lowest $59.99 on 2024-07-15, average $72.32, tracked since 2024-07-15) and no Amazon-price data, and the page flagged its data as over 7 days old: a typical case, and exactly why the verdict rules above treat missing or stale tracks as unknowns rather than deals.
