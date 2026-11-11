"""Session 24 - the ten test questions, written the way customers type them.

Most of them share few or no words with the article that answers them. That's the point: keyword search should
struggle, meaning search shouldn't. Each pair is (question, the help-centre article that answers it).
"""

CASES = [
    ("my earbuds stopped working after two months", "warranty"),
    ("the parcel arrived smashed", "damaged-items"),
    ("can I pay the courier in cash when it arrives", "payments"),
    ("do you send orders abroad", "shipping"),
    ("swap my sneakers for a bigger size", "exchanges"),
    ("somebody phoned me asking for my OTP", "privacy-and-safety"),
    ("I want to talk to a real person", "support-contact"),
    ("when will I get my money back", "refunds"),
    ("remove one thing from my order before it ships", "cancellations"),
    ("my discount code is rejected", "coupons"),
]

# Nothing in the help centre answers these. Search still returns *something* - look at how low the scores are.
OUT_OF_SCOPE = [
    "do you sell used cars",
    "what's the weather in Hyderabad",
]

PASS_MARK = 8          # out of 10, for the top 3 results (hit@3)
