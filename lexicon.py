"""Hinglish / English word lists and regex rules. Pure data: no logic, easy to review and extend."""
import re

from trustcart.textnorm import tokenize

FUNCTION_WORDS = set(tokenize(
    "hai h hain ka ki ke ko me mein pe par se kya kitna kitne kitni kaunsa kaunsi konsa konsi kaun wala wali wale ho hoga "
    "hogi jo ya aur toh to bhi hi nahi nahin kar karu karoge karte karke sakte sakti sakta jayega jayegi chalega chalegi "
    "milega milegi milti milte dikhao dikha do batao bata bataiye chahiye chahie aana aayega liye abhi ab ok pls plz please "
    "inme inse isme gaya gayi tha thi kiya liya du de dena ek ye yeh wo woh mera meri mujhe mere hum aap kab kahan kaise "
    "kyun din paise same cheez andar ander tak kam zyada jyada sabse which is the a an of for in on and or with i my "
    "dhul dho hone lagta lagega lagti aa chota kharab karna sale ghar baarish bhig paani what how much do you have there "
    "available stock price rate cost kimat daam under below within upto max less than show me options option cheapest "
    "sasta sasti mehenga mehnga costliest kaha hota hote ka-sa ji bhai sir yaar aaya aaye nahi wapas use pasand aur "
    "size colour color time full discount chhoot off cheaper cheap kaunsi me-hai batao inme vs versus"
))
CONTEXT_WORDS = {"inme", "inse", "isme", "in"}  # words that refer back to the previous turn's results

ATTRIBUTE_RULES: list[tuple[str, tuple[str, ...], bool]] = [
    # (regex on normalised text, catalogue keys that answer it, consume matched words from the product search)
    (r"water ?proof|water resist\w*|waterresistant|paani|pani|baarish|barish|bhig\w*|swimming", ("water_resistant", "water_resistance_rating"), True),
    (r"dishwasher(?: safe)?|dishwasher me", ("dishwasher_safe",), True),
    (r"induction (?:compatible|pe|par|me|ke liye|chalega|chalegi)", ("induction_compatible",), True),
    (r"microwave(?: safe| me)?", ("microwave_safe",), True),
    (r"paraben(?: free)?", ("paraben_free",), True),
    (r"sulphate(?: free)?|sulfate(?: free)?", ("sulphate_free",), True),
    (r"warranty", ("warranty_months",), True),
    (r"noise cancel\w*|\banc\b", ("noise_cancellation",), True),
    (r"weight|wajan|vajan", ("weight_g", "weight_kg"), True),
    (r"battery (?:backup|life)|kitna chalega|kitni der chalega|runtime|ek charge me", ("battery_life_hours", "runtime_min"), True),
    (r"kitne watt|kitni watt|watt kitn\w*", ("wattage_w", "output_w"), True),
    (r"kitni moti|thickness|moti hai", ("thickness_mm",), True),
    (r"shoe compartment", ("shoe_compartment",), True),
    (r"laptop (?:aayega|aa jayega|fit|aa sakta)", ("fits_laptop_upto_in",), True),
    (r"bluetooth (?:hai|h|support)\b", ("connectivity",), False),
    (r"auto ?(?:cut ?off|shut ?off|shutoff)|auto cut", ("auto_shutoff",), True),
    (r"\bsizes?\b (?:milega|available|hai)|size milega", ("sizes",), True),
    (r"washing machine(?: me)?|dho sak\w*|dhul sak\w*|machine wash|wash kar", ("care",), True),
    (r"made in \w+", ("country_of_origin",), True),
    (r"full charge hone me|charging time|charge hone me", ("charging_time",), True),
    (r"\bisi\b|\bbis\b", ("certification",), True),
    (r"\brating\b|\bstars?\b|review", ("rating", "review_count"), True),
]
POLICY_GAP_RULES = [
    r"\bemi\b|instal+ment|pay later|no cost", r"gift ?wrap|gift pack", r"loyalty|reward|points?\b|coins?\b|membership",
    r"\bstore\b.*\b(?:kahan|where|address)|showroom|branch|outlet|offline",
    r"invoice|gst bill|bulk|wholesale|installation|exchange offer", r"price drop|price protection",
]
# (regex, policy sub-section). First match wins; kept in the order most-specific first.
POLICY_RULES: list[tuple[str, str]] = [
    (r"ship ho gaya|dispatch ho|shipped|dispatched", "5.2"),
    (r"cancel", "5.1"),
    (r"restocking|return (?:free|charge|fee)", "1.2"),
    (r"price match|match (?:the )?price|(?:amazon|flipkart|other site)\w* pe", "7.4"),
    (r"coupon|promo code|discount code", "7.3"),
    (r"\bgst\b", "7.1"),
    (r"(?:khol|opened|open|use|used).*(?:shampoo|lotion|face ?wash|lip balm|perfume|deodorant|sunscreen|hair oil|cream)|(?:shampoo|lotion|face ?wash|lip balm|perfume|deodorant|sunscreen|hair oil|cream).*(?:khol|opened|use kiya)", "6.1"),
    (r"(?:seal|khol|opened|use).*(?:earbud|earphone|airdope|earpod)|(?:earbud|earphone|airdope).*(?:seal|khol|opened|used)", "6.2"),
    (r"(?:trimmer).*(?:use kiya|used|return)", "6.3"),
    (r"warranty (?:claim|kaise|kahan|process)|claim kaise", "3.4"),
    (r"exchange|size .*(?:chota|bada|fit nahi)", "1.6"),
    (r"refund|paise .*wapas|money back|wapas aayenge", "1.5"),
    (r"damaged|defective|wrong item|galat|toota|tuta|kharab", "1.7"),
    (r"sale me|on sale|discounted item|offer pe liya|sale item", "7.5"),
    (r"return (?:kaise|how)|how to return", "1.4"),
    (r"\breturn|wapas kar", "1.1"),
    (r"\bcod\b|cash on delivery", "4.2"),
    (r"pre ?order|back ?order|out of stock wala|stock aane", "2.5"),
    (r"international|outside india|abroad|dubai|usa|\buk\b|singapore|nepal|canada|australia|videsh|deliver\w* (?:karte|hota)", "2.3"),
    (r"tracking|track kar|order track", "2.4"),
    (r"delivery (?:time|kitne din|kab)|kitne din me (?:aayega|deliver)|kab tak aayega|timeline", "2.2"),
    (r"delivery|shipping|deliver charge|free delivery|\border\b.*(?:charge|lagega)", "2.1"),
    (r"payment|pay kar|\bupi\b|net ?banking|wallet|credit card|debit card|card pe", "4.1"),
    (r"customer (?:care|support)|helpline|contact|support number|complaint", "8.1"),
]
OUT_OF_CATALOGUE_WORDS = {"phone", "smartphone", "mobile", "laptop", "tv", "television", "fridge", "refrigerator", "ac",
                          "washing machine", "grocery", "medicine", "jewellery", "bike", "car", "scooter"}
ACCESSORY_WORDS = {"stand", "bag", "backpack", "sleeve", "case", "cover", "charger", "cable", "holder", "compartment", "aayega"}
SUPER_MIN = re.compile(r"\b(?:sasta|sasti|sastha|cheapest|cheaper|cheap|lowest|least|sabse kam|kam price|minimum)\b")
SUPER_MAX = re.compile(r"\b(?:mehenga|mehnga|mahanga|costliest|most expensive|expensive|highest|sabse zyada|maximum price)\b")
COMPARE_SPLIT = re.compile(r"\s(?:vs|versus|ya|or)\s")
LIST_WORDS = re.compile(r"\b(?:dikhao|dikha|show|options?|chahiye|chahie|suggest|recommend|list)\b")
STOCK_WORDS = re.compile(r"\b(?:stock|available|availability|milega|milegi|milta|miljayega|abhi)\b")
PRICE_WORDS = re.compile(r"\b(?:price|rate|kitne|kitna|kitni|cost|kimat|daam|kitne ka|rupe|batao)\b")
DISCOUNT_WORDS = re.compile(r"\b(?:discount|chhoot|chhut|off)\b")
IN_STOCK_FILTER = re.compile(r"stock me ho|jo stock|available ho|jo available|in stock wala|stock wala")
BUDGET_PATTERNS = [
    re.compile(r"(?:under|below|within|upto|up to|max|maximum|less than)\s*(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(k)?\b"),
    re.compile(r"\b(\d+(?:\.\d+)?)\s*(k)?\s*(?:rs\.?|rupees|inr)?\s*(?:ke\s+andar|ke\s+ander|andar|tak|se\s+kam|se\s+neeche|ke\s+neeche|ke\s+under|ke\s+bhitar)\b"),
    re.compile(r"\b(\d+(?:\.\d+)?)\s*(k)?\s*budget\b"),
]
