# Credit & Due Rules / বাকি ও ক্রেডিট লিমিটের নিয়ম

বিষয়: credit_rules

## Bangla

### কাকে বাকি দেওয়া যায়
- নিয়মিত **ডিলার / এলাকাভিত্তিক কাস্টমার** যাদের ফোন ও ঠিকানা সিস্টেমে আছে।
- নতুন কাস্টমারকে প্রথমবার সাধারণত বাকি নয়; চাইলে মালিক **সর্বোচ্চ ২,০০০ টাকা** পরীক্ষামূলক লিমিট দিতে পারেন।
- Walk-in কাস্টমারকে বাকি দেওয়া নিষেধ (`credit_limit = 0`)।

### লিমিট কীভাবে ঠিক হয়
- ছোট খুচরা: সাধারণত **৫,০০০ টাকা**।
- নিয়মিত ডিলার: **২০,০০০–৫০,০০০ টাকা**, পেমেন্ট হিস্টোরি দেখে।
- সিস্টেমে `credit_limit` অতিক্রম করলে বাকি সেল ব্লক হবে — স্টাফ নিজে বাড়াবে না, মালিক আপডেট করবেন।

### বাকি দেরিতে দিলে কী হয়
- নির্ধারিত তারিখের **৭ দিন** পরে রিমাইন্ডার SMS যাবে।
- **১৫ দিন** পরে নতুন বাকি সেল বন্ধ রাখা ভালো; আগে বকেয়া আদায়।
- বারবার দেরি হলে লিমিট কমিয়ে দেওয়া হবে।

### কালেকশন
- আংশিক কালেকশন গ্রহণযোগ্য (ক্যাশ/bKash/Nagad)।
- কালেকশন অবশ্যই সিস্টেমে এন্ট্রি করতে হবে; খাতায় আলাদা হিসাব রাখা যাবে না।

## English

### Who may buy on credit
- Regular **dealers / area customers** with phone and address stored in the system.
- New customers usually get no credit on first visit; the owner may grant a trial limit of up to **BDT 2,000**.
- Walk-in customers must not get credit (`credit_limit = 0`).

### How limits are set
- Small retail: typically **BDT 5,000**.
- Regular dealers: **BDT 20,000–50,000**, based on payment history.
- Sales that would exceed `credit_limit` are blocked — staff must not raise the limit; only the owner updates it.

### Late payment
- Reminder SMS after **7 days** past the due date.
- After **15 days**, pause new credit sales until dues are collected.
- Repeated delays → reduce the credit limit.

### Collections
- Partial collections are OK (cash / bKash / Nagad).
- Every collection must be entered in the system — no parallel paper-only ledger.
