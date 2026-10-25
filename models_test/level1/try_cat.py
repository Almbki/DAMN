import json

import cat

bank = {q["item_id"]: q for q in json.load(open("questions.json", encoding="utf-8"))}
s = cat.start_assessment()

while True:
    item = cat.get_next_item(s)
    if item is None:
        break
    print(f"[{s.last_domain}] {bank[item]['text']}")
    while True:
        try:
            r = int(input("1-5: "))
            if 1 <= r <= 5:
                break
        except ValueError:
            pass
    cat.submit_response(s, item, r)

print(json.dumps(cat.get_trait_profile(s), ensure_ascii=False, indent=2))