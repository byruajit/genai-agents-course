"""Session 27 - the test questions. Two kinds, on purpose:

    "meaning"  customers' own words, few shared words with the answer   -> vectors should win (S24's ten, plus three)
    "exact"    codes, names, numbers, brand words                        -> BM25 should win

A good retriever has to pass BOTH. Each case: (question, corpus, expected doc_id, kind).
corpus "help" = the 14 help-centre articles (doc_id = article);  corpus "products" = the catalog (doc_id = SKU).
"""

CASES = [
    # ---- meaning (S24's ten) ----
    ("my earbuds stopped working after two months", "help", "warranty", "meaning"),
    ("the parcel arrived smashed", "help", "damaged-items", "meaning"),
    ("can I pay the courier in cash when it arrives", "help", "payments", "meaning"),
    ("do you send orders abroad", "help", "shipping", "meaning"),
    ("swap my sneakers for a bigger size", "help", "exchanges", "meaning"),
    ("somebody phoned me asking for my OTP", "help", "privacy-and-safety", "meaning"),
    ("I want to talk to a real person", "help", "support-contact", "meaning"),
    ("when will I get my money back", "help", "refunds", "meaning"),
    ("remove one thing from my order before it ships", "help", "cancellations", "meaning"),
    ("my discount code is rejected", "help", "coupons", "meaning"),
    # ---- meaning, catalog ----
    ("shoes for trekking in the mountains", "products", "SKU-FW-002", "meaning"),
    ("a speaker I can take to the pool", "products", "SKU-EL-001", "meaning"),
    ("something to keep my drinks cold all day", "products", "SKU-HK-001", "meaning"),
    # ---- exact: codes, names, numbers ----
    ("SKU-EL-004", "products", "SKU-EL-004", "exact"),
    ("price of SKU-FW-002", "products", "SKU-FW-002", "exact"),
    ("PowerCell", "products", "SKU-EL-004", "exact"),
    ("is the Stride available in UK 9", "products", "SKU-FW-001", "exact"),
    ("26cm pan", "products", "SKU-HK-002", "exact"),
    ("WELCOME10", "help", "coupons", "exact"),
    ("HDFC no-cost EMI", "help", "payments", "exact"),
    ("RuPay", "help", "payments", "exact"),
    ("COD refused, blocked for 90 days?", "help", "cancellations", "exact"),
]

# Nothing in the help centre answers these. Every method still returns *something* - the relevance gate's job is to
# return nothing instead.
OUT_OF_SCOPE = [
    ("do you sell used cars", "help"),
    ("what's the weather in Hyderabad", "help"),
    ("who won the cricket match yesterday", "help"),
]

PASS_MARK = 18          # hit@3 out of 22 for the best method
