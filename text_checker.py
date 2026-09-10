import re


# مسار ملف النص
TEXT_PATH = "data/criminal_procedure.txt"

# عدد صفحات PDF الأصلي
EXPECTED_PAGES = 119


# --------------------------------------------------
# 1. قراءة ملف النص
# --------------------------------------------------

with open(TEXT_PATH, "r", encoding="utf-8") as file:
    text = file.read()


# --------------------------------------------------
# 2. البحث عن أرقام الصفحات الموجودة
#
# يبحث عن:
# === الصفحة 1 ===
# === الصفحة 2 ===
# ...
# --------------------------------------------------

pages = re.findall(
    r"=== الصفحة (\d+) ===",
    text
)

# تحويل أرقام الصفحات من String إلى Integer
pages = [int(page) for page in pages]


# --------------------------------------------------
# 3. فحص الصفحات الناقصة
# --------------------------------------------------

missing_pages = []

for page_number in range(1, EXPECTED_PAGES + 1):

    if page_number not in pages:
        missing_pages.append(page_number)


# --------------------------------------------------
# 4. فحص الصفحات المكررة
# --------------------------------------------------

duplicate_pages = []

for page_number in pages:

    if pages.count(page_number) > 1:

        if page_number not in duplicate_pages:
            duplicate_pages.append(page_number)


# --------------------------------------------------
# 5. البحث عن [غير واضح]
# --------------------------------------------------

unclear_count = text.count("[غير واضح]")


# --------------------------------------------------
# 6. البحث عن رموز تدل على مشكلة في Encoding
# --------------------------------------------------

bad_character_count = text.count("�")


# --------------------------------------------------
# 7. طباعة التقرير
# --------------------------------------------------

print("\n===== تقرير فحص النص =====\n")

print(f"عدد الصفحات المتوقع: {EXPECTED_PAGES}")

print(f"عدد عناوين الصفحات الموجودة: {len(pages)}")


# الصفحات الناقصة
if missing_pages:
    print(f"❌ صفحات ناقصة: {missing_pages}")
else:
    print("✅ لا توجد صفحات ناقصة")


# الصفحات المكررة
if duplicate_pages:
    print(f"❌ صفحات مكررة: {duplicate_pages}")
else:
    print("✅ لا توجد صفحات مكررة")


# الكلمات غير الواضحة
if unclear_count > 0:
    print(
        f"⚠️ عدد [غير واضح]: {unclear_count}"
    )
else:
    print("✅ لا يوجد [غير واضح]")


# مشاكل Encoding
if bad_character_count > 0:
    print(
        f"❌ عدد الرموز التالفة � : {bad_character_count}"
    )
else:
    print("✅ لا توجد رموز Encoding تالفة")

# --------------------------------------------------
# معرفة الصفحات التي تحتوي على [غير واضح]
# --------------------------------------------------

unclear_pages = []

# تقسيم الملف حسب عناوين الصفحات
page_sections = re.split(
    r"=== الصفحة (\d+) ===",
    text
)

# الشكل بعد التقسيم يكون تقريباً:
# رقم الصفحة، النص، رقم الصفحة، النص...
for i in range(1, len(page_sections), 2):

    page_number = int(page_sections[i])
    page_text = page_sections[i + 1]

    if "[غير واضح]" in page_text:
        unclear_pages.append(page_number)


if unclear_pages:
    print(
        f"⚠️ الصفحات التي تحتوي [غير واضح]: {unclear_pages}"
    )

    # --------------------------------------------------
# عرض النص الموجود حول [غير واضح]
# --------------------------------------------------

print("\n===== أماكن [غير واضح] =====\n")

for i in range(1, len(page_sections), 2):

    # رقم الصفحة
    page_number = int(page_sections[i])

    # نص الصفحة
    page_text = page_sections[i + 1]

    # نبحث فقط في الصفحات التي تحتوي [غير واضح]
    if "[غير واضح]" in page_text:

        print(f"--- الصفحة {page_number} ---")

        # البحث عن كل ظهور لـ [غير واضح]
        for match in re.finditer(
            r"\[غير واضح\]",
            page_text
        ):

            # مكان بداية [غير واضح]
            position = match.start()

            # نأخذ 100 حرف قبلها
            start = max(0, position - 100)

            # نأخذ 100 حرف بعدها
            end = min(
                len(page_text),
                position + len("[غير واضح]") + 100
            )

            # النص المحيط بالمشكلة
            context = page_text[start:end]

            print(context)
            print("------------------------")
print("\n===== انتهى الفحص =====")