import re


TEXT_PATH = "data/criminal_procedure.txt"


def article_title_to_number(title):

    numbers = {
        "الأولى": 1,
        "الثانية": 2,
        "الثالثة": 3,
        "الرابعة": 4,
        "الخامسة": 5,
        "السادسة": 6,
        "السابعة": 7,
        "الثامنة": 8,
        "التاسعة": 9,
        "العاشرة": 10,
        "الحادية عشرة": 11,
        "الثانية عشرة": 12,
        "الثالثة عشرة": 13,
        "الرابعة عشرة": 14,
        "الخامسة عشرة": 15,
        "السادسة عشرة": 16,
        "السابعة عشرة": 17,
        "الثامنة عشرة": 18,
        "التاسعة عشرة": 19,
        "العشرون": 20,
    }

    title = title.replace("المادة", "").strip()

    if title in numbers:
        return numbers[title]

    tens = {
        "العشرون": 20,
        "الثلاثون": 30,
        "الأربعون": 40,
        "الخمسون": 50,
        "الستون": 60,
        "السبعون": 70,
        "الثمانون": 80,
        "التسعون": 90,
    }

    units = {
        "الحادية": 1,
        "الثانية": 2,
        "الثالثة": 3,
        "الرابعة": 4,
        "الخامسة": 5,
        "السادسة": 6,
        "السابعة": 7,
        "الثامنة": 8,
        "التاسعة": 9,
    }

    # Handle numbers from 21 to 99
    for tens_word, tens_value in tens.items():

        if title == tens_word:
            return tens_value

        for unit_word, unit_value in units.items():

            if title == f"{unit_word} و{tens_word}":
                return tens_value + unit_value

            if title == f"{unit_word} وال{tens_word[2:]}":
                return tens_value + unit_value

    # Handle article 100
    if title == "المائة":
        return 100

    # Handle articles from 101 to 199
    if "بعد المائة" in title:

        before_hundred = title.replace("بعد المائة", "").strip()

        if not before_hundred:
            return 100

        smaller_number = article_title_to_number(
            "المادة " + before_hundred
        )

        if smaller_number is not None:
            return 100 + smaller_number

    # Handle article 200
    if title == "المائتين":
        return 200

    # Handle articles after 200
    if "بعد المائتين" in title:

        before_two_hundred = title.replace(
            "بعد المائتين",
            ""
        ).strip()

        smaller_number = article_title_to_number(
            "المادة " + before_two_hundred
        )

        if smaller_number is not None:
            return 200 + smaller_number

    return None

def clean_article_text(text):

    # Remove page markers such as:
    # === الصفحة 53 ===
    text = re.sub(
        r"(?m)^\s*===\s*الصفحة\s+\d+\s*===\s*$",
        "",
        text
    )

    # Remove standalone table-of-contents marker
    text = re.sub(
        r"(?m)^\s*الفهرس\s*$",
        "",
        text
    )

    # Remove standalone Arabic page numbers
    text = re.sub(
        r"(?m)^\s*[٠-٩]+\s*$",
        "",
        text
    )

    # Remove repeated PDF header
    text = re.sub(
        r"(?m)^\s*نظام الإجراءات الجزائية ولائحته التنفيذية\s*$",
        "",
        text
    )

    # Remove standalone regulation marker from the end of a chunk
    text = re.sub(
        r"(?m)^\s*اللائحة\s*$",
        "",
        text
    )

    # Remove excessive empty lines
    text = re.sub(
        r"\n\s*\n+",
        "\n\n",
        text
    )

    return text.strip()

def split_by_articles(text):

    # Find article titles
    article_pattern = re.compile(
        r"(?m)^\s*(المادة\s+[^\n:]+):\s*$"
    )

    matches = list(article_pattern.finditer(text))

    chunks = []

    for i, match in enumerate(matches):

        start = match.start()

        # The current article ends when the next article starts
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        article_title = match.group(1).strip()
        article_number = article_title_to_number(
            article_title
        )

        article_text = text[start:end].strip()
        article_text = clean_article_text(
            article_text
            )

        # Check the section between the previous article
        # and the current article
        if i == 0:
            previous_section = text[:start]
        else:
            previous_section = text[
                matches[i - 1].end():start
            ]

        # If "اللائحة" appears before this article,
        # classify it as a regulation article
        regulation_marker = re.search(
            r"(?m)^\s*اللائحة\s*$",
            previous_section
        )

        if regulation_marker:
            source_type = "regulation"
        else:
            source_type = "system"

        chunks.append({
            "article_number": article_number,
            "article_title": article_title,
            "source_type": source_type,
            "text": article_text
        })

    return chunks


def load_and_split():

    with open(TEXT_PATH, "r", encoding="utf-8") as file:
        text = file.read()

    chunks = split_by_articles(text)

    return chunks

if __name__ == "__main__":

    chunks = load_and_split()

    for chunk in chunks:

        if (
            chunk["article_number"] == 107
            and chunk["source_type"] == "system"
        ):
            print("Article Number:", chunk["article_number"])
            print("Source Type:", chunk["source_type"])
            print("\nText:")
            print(chunk["text"])