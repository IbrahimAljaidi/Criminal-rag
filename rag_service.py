import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.prompts import PromptTemplate
from emb import create_embedding
from qdrant import search_chunks, search_by_article


load_dotenv()


# ==========================================
# OpenRouter client
# ==========================================

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)


# ==========================================
# Search query prompt
# ==========================================

search_prompt = PromptTemplate.from_template("""
حوّل سؤال المستخدم إلى استعلام بحث عربي واضح ومناسب للبحث
في نص نظام الإجراءات الجزائية السعودي ولائحته التنفيذية.

القواعد:

- أرجع استعلام البحث فقط.
- لا تجب عن السؤال.
- لا تضف شرحاً.
- حافظ على المعنى القانوني للسؤال.
- استخدم المصطلحات القانونية العربية المرتبطة بالسؤال.
- وسّع الاستعلام بالمصطلحات القانونية القريبة إذا كانت تساعد في البحث.
- لا تضف موضوعاً قانونياً غير متعلق بسؤال المستخدم.
- إذا كان السؤال عربياً، حسّن صياغته للبحث دون تغيير معناه.
- استخدم المحادثة السابقة فقط لفهم المقصود من السؤال الحالي.
- إذا كان السؤال الحالي يعتمد على سؤال سابق، اجعل استعلام البحث مستقلاً وواضحاً.
- لا تغيّر موضوع السؤال الحالي بسبب معلومات غير مرتبطة في المحادثة السابقة.
مثال:

سؤال المستخدم:
What are the rights of a defendant when arrested?

استعلام البحث:
ما حقوق المتهم عند القبض عليه أو توقيفه، وإبلاغه بأسباب القبض أو التوقيف، وحقه في الاتصال والاستعانة بمحام؟

المحادثة السابقة:
{history}
سؤال الحالي:
{question}

استعلام البحث:
""")


# ==========================================
# Final answer prompt
# ==========================================

prompt = PromptTemplate.from_template("""
أنت مساعد متخصص فقط في نظام الإجراءات الجزائية السعودي.

تعامل مع رسالة المستخدم حسب نوعها:

1- إذا كانت الرسالة تحية مثل:
السلام عليكم
هلا
مرحبا
صباح الخير
مساء الخير

فرد عليها برد مناسب ولطيف فقط.

مثال:
السلام عليكم → وعليكم السلام، كيف أقدر أخدمك؟


2- إذا قال المستخدم إنه يريد طرح سؤال قانوني، مثل:
عندي سؤال قانوني
أبي أسألك عن النظام
عندي استفسار قانوني

فرد عليه برد مناسب مثل:
تفضل، اطرح سؤالك القانوني وسأحاول مساعدتك.


3- إذا كان المستخدم يسأل سؤالاً متعلقاً بنظام الإجراءات الجزائية السعودي:
أجب اعتمادًا فقط على السياق الموجود أدناه.


4- إذا كان السؤال خارج نطاق نظام الإجراءات الجزائية السعودي:
لا تجب عن السؤال من معلوماتك العامة أو معرفتك السابقة.

قل فقط:
"أنا مختص في نظام الإجراءات الجزائية السعودي، وهذا السؤال خارج نطاق تخصصي."


قواعد إلزامية:

- استخدم فقط المعلومات الموجودة في السياق عند الإجابة عن الأسئلة القانونية.
- ممنوع استخدام معلوماتك العامة أو معرفتك السابقة للإجابة عن السؤال.
- ممنوع إضافة أي معلومة غير موجودة في السياق.
- لا تجب من عندك حتى لو كنت تعرف الإجابة.
- لا تخمن أي معلومة غير موجودة في السياق.
- يجوز لك شرح المعلومات الموجودة في السياق وإعادة صياغتها وتلخيصها
  والمقارنة بينها واستنتاج الفروق المباشرة بينها، بشرط أن يكون
  الاستنتاج مبنياً بوضوح على النصوص الموجودة في السياق فقط.

- إذا كان السؤال يطلب مقارنة أو فرقاً بين مفهومين، فلا تشترط أن
  يحتوي السياق على عبارة صريحة مثل "الفرق هو".
  قارن بين الأحكام الواردة في المواد المسترجعة واشرح الفرق
  المستفاد مباشرة منها.

- لا تعتبر السياق غير كافٍ لمجرد أن الإجابة تحتاج إلى جمع معلومات
  من أكثر من مادة أو المقارنة بينها.

- استخدم عبارة "المعلومات المتاحة في السياق لا تكفي للإجابة عن هذا السؤال"
  فقط عندما لا توجد في السياق معلومات مرتبطة بالسؤال تكفي لبناء
  إجابة موثوقة.

- إذا كان السؤال متعلقاً بنظام الإجراءات الجزائية السعودي،
ولكن الإجابة غير موجودة أو غير كافية في السياق، قل:
"المعلومات المتاحة في السياق لا تكفي للإجابة عن هذا السؤال."

- إذا كان السؤال خارج نطاق نظام الإجراءات الجزائية السعودي، قل:
"أنا مختص في نظام الإجراءات الجزائية السعودي، وهذا السؤال خارج نطاق تخصصي."

- لا تستخدم السياق للإجابة عن سؤال غير متعلق به.
- إذا كانت نتائج السياق غير مرتبطة بسؤال المستخدم، تجاهلها.

- إذا انتهى أحد النصوص بكلمة أو جملة غير مكتملة،
فلا تعتمد على الجزء غير المكتمل.

- لا تحاول إكمال الكلمات أو الجمل الناقصة من عندك.

- اجعل الإجابة واضحة ومباشرة.
- يمكنك ترتيب الإجابة على شكل نقاط إذا كان ذلك يجعلها أوضح.

- أجب بنفس لغة رسالة المستخدم.
- إذا كان السؤال باللغة العربية، أجب باللغة العربية.
- إذا كان السؤال باللغة الإنجليزية، أجب باللغة الإنجليزية.
- استخدم المحادثة السابقة فقط لفهم سياق سؤال المستخدم الحالي
  والمقصود من الإشارات مثل: "هذا"، "ذلك"، "طيب لو"، "وش شروطه".

- المحادثة السابقة ليست مصدراً قانونياً.

- لا تعتمد على إجابات المساعد السابقة كمصدر للمعلومة القانونية.

- يجب أن تكون المعلومات القانونية في الإجابة الحالية مدعومة
  بالسياق القانوني المسترجع أدناه.

- إذا تعارضت المحادثة السابقة مع السياق القانوني المسترجع،
  اعتمد على السياق القانوني المسترجع فقط.

قواعد ذكر المواد والمراجع:

- عندما تعتمد على مادة في الإجابة، اذكر رقم المادة كما ورد في بيانات السياق.

- ضع رقم المادة ونوع المصدر بجانب المعلومة التي أخذتها منها كلما كان ذلك مناسبًا.
مثال:
(المادة 35 من النظام)
أو:
(المادة 24 من اللائحة التنفيذية)

- لكل وثيقة في السياق بيانات محددة:
  رقم المادة
  عنوان المادة
  نوع المصدر
  النص

- اعتبر "رقم المادة" و"نوع المصدر" الموجودين في بيانات الوثيقة
هما المرجع الوحيد لتحديد رقم المادة ومصدرها.

- عندما تستخدم معلومة من وثيقة، انسبها فقط إلى رقم المادة
ونوع المصدر الخاصين بهذه الوثيقة.

- لا تذكر رقم مادة إلا إذا كان موجودًا بوضوح في بيانات إحدى
الوثائق المسترجعة في السياق.

- لا تخمن رقم المادة أو نوع المصدر.

- لا تستخدم أرقام مواد من معرفتك العامة أو السابقة.

- لا تنسب معلومة إلى مادة إذا لم يكن واضحًا من السياق أنها تابعة لها.

- إذا ذكر نص إحدى المواد رقم مادة أخرى، فلا تعتبر هذا الرقم
مرجعًا للمعلومة الحالية.

- مجرد ورود رقم مادة أخرى داخل النص لا يعني أن نص تلك المادة
موجود في السياق.

- لا تنسب معلومات إلى مادة مذكورة داخل نص مادة أخرى إلا إذا
كانت تلك المادة موجودة كوثيقة مستقلة في السياق.

- إذا لم يظهر رقم المادة بوضوح في بيانات السياق،
قدم المعلومة دون إضافة رقم مادة من عندك.

- لا تغير نوع المصدر الموجود في بيانات الوثيقة.

- إذا كان نوع المصدر "النظام"، فانسب المادة إلى النظام.

- إذا كان نوع المصدر "اللائحة التنفيذية"، فانسب المادة إلى
اللائحة التنفيذية.

- إذا كان السياق يحتوي على المادة نفسها من النظام واللائحة التنفيذية،
فميّز بوضوح بين نص النظام ونص اللائحة التنفيذية ولا تخلط بينهما.


مثال على طريقة الإجابة:

يجوز لرجل الضبط الجنائي في حال التلبس بالجريمة القبض على
المتهم الحاضر إذا وجدت دلائل كافية على اتهامه
(المادة 33 من النظام).

وفي غير حالات التلبس، لا يجوز القبض على أي إنسان أو توقيفه
إلا بأمر من السلطة المختصة بذلك
(المادة 35 من النظام).

المحادثة السابقة:

{history}

السياق:

{context}


رسالة المستخدم:

{question}
""")

# ==========================================
# Generate response using OpenRouter
# ==========================================
def generate_response(text):

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = openrouter_client.chat.completions.create(
                model="google/gemini-3.8-flash",
                messages=[
                    {
                        "role":"user",
                        "content":text
                    }
                ],
                temperature=0.1
            )
            return response.choices[0].message.content

        except Exception as error:
            # Retry temporary server errors
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                print(
                f"OpenRouter request failed. "
                f"Retrying in {wait_time} seconds..."
                )
                time.sleep(wait_time)

            else:
                return (
                       "الخدمة غير متاحة حالياً، "
                        "يرجى المحاولة مرة أخرى بعد قليل."
                    )

            
# ==========================================
# Normalize Arabic digits
# ==========================================
def normalize_arabic_digits(text):

    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    english_digits = "0123456789"

    translation_table = str.maketrans(
        arabic_digits,
        english_digits
    )
    return text.translate(translation_table)

# ==========================================
# Detect article request
# ==========================================
def extract_article_request(question):
    normalized_question = normalize_arabic_digits(question)
    match = re.search(
        r"(?:المادة|مادة)\s*(?:رقم\s*)?[\(\[]?(\d+)[\)\]]?",
        normalized_question
    )

    if not match:
        return None, None

    article_number = int(match.group(1))

    if "اللائحة" in normalized_question:
        source_type = "regulation"

    elif "النظام" in normalized_question:
        source_type = "system"

    else:
        source_type = None

    return article_number, source_type

# ==========================================
# Convert source type to Arabic
# ==========================================
def get_source_label(source_type):

    if source_type == "system":
        return "النظام"

    if source_type == "regulation":
        return "اللائحة التنفيذية"

    return source_type

# ==========================================
# Create semantic search query
# ==========================================
def create_search_query(
        question,
        history=None
    ):
    """
    Create a clear semantic search query using the current
    question and previous conversation history.
    """
    # Convert previous exchanges into readable text
    conversation_history = format_history(history)
    # Build the search prompt
    search_text = search_prompt.format(
        question=question,
        history=conversation_history
    )
    response = generate_response(search_text)
    return response

def handle_simple_message(question):
    # Normalize the message
    message = question.strip().lower()

    greetings = [
        "السلام عليكم",
        "هلا",
        "مرحبا",
        "مرحباً",
        "صباح الخير",
        "مساء الخير"
    ]
    legal_request_messages = [
        "عندي سؤال قانوني",
        "ابي اسألك عن النظام",
        "أبي أسألك عن النظام",
        "عندي استفسار قانوني"
    ]
    # Handle greetings without calling Gemini
    if message in greetings:
        return "وعليكم السلام، كيف أقدر أخدمك؟"

    # Handle simple legal-question requests
    if message in legal_request_messages:
        return "تفضل، اطرح سؤالك القانوني وسأحاول مساعدتك."

    return None
# ==========================================
# Format conversation history
# ==========================================
def format_history(history):
    """
    Convert previous question/answer exchanges into text
    that can be included in the LLM prompt.
    """

    # No previous conversation history
    if not history:
        return "لا توجد محادثة سابقة."
    formatted_exchanges = []

    for exchange in history:
        question = exchange.get("question", "")
        answer = exchange.get("answer", "")
        formatted_exchanges.append(
            f"""
المستخدم:
{question}

المساعد:
{answer}
""".strip()
        )

    return "\n\n".join(formatted_exchanges)
# ==========================================
# Main RAG function
# ==========================================
def ask(question, history=None):
    # Convert previous exchanges into readable text
    conversation_history = format_history(history)
    # Handle simple messages without using Gemini or Qdrant
    simple_response = handle_simple_message(question)

    if simple_response is not None:
        return simple_response

    # Check if the user is asking for a specific article
    article_number, source_type = extract_article_request(
        question
    )
    # ------------------------------------------
    # Exact article search
    # ------------------------------------------
    if article_number is not None:

        print("\nSearch Type: Exact Article Search")
        print("Article Number:", article_number)
        print("Source Type:", source_type)

        results = search_by_article(
            article_number=article_number,
            source_type=source_type,
            limit=10
        )
    # ------------------------------------------
    # Semantic search
    # ------------------------------------------
    else:
        print("\nSearch Type: Semantic Search")
        search_query = create_search_query(
            question=question,
            history=history
            )
        print("\nOriginal Question:")
        print(question)
        print("\nSearch Query:")
        print(search_query)
        query_vector = create_embedding(
            search_query
        )

        results = search_chunks(
            query_vector=query_vector,
            limit=10
        )
    # ------------------------------------------
    # Check search results
    # ------------------------------------------
    if not results:
        return (
            "المعلومات المتاحة في السياق "
            "لا تكفي للإجابة عن هذا السؤال."
        )
    # ------------------------------------------
    # Print retrieved documents
    # ------------------------------------------
    print("\nRetrieved Documents:")

    for i, result in enumerate(results, start=1):

        source_label = get_source_label(
            result.payload.get("source_type")
        )

        print(f"\n--- Document {i} ---")

        print(
            "Article Number:",
            result.payload.get("article_number")
        )

        print(
            "Article Title:",
            result.payload.get("article_title")
        )

        print(
            "Source Type:",
            source_label
        )

        print(
            "Text:",
            result.payload.get("text")
        )
    # ------------------------------------------
    # Build context
    # ------------------------------------------
    context = "\n\n".join(
    f"""
--- بداية الوثيقة ---
رقم المادة: {result.payload.get("article_number")}
عنوان المادة: {result.payload.get("article_title")}
نوع المصدر: {get_source_label(result.payload.get("source_type"))}

النص:
{result.payload.get("text")}
--- نهاية الوثيقة ---
"""
    for result in results
)
    # ------------------------------------------
    # Generate final answer
    # ------------------------------------------
    final_prompt = prompt.format(
        history=conversation_history,
        context=context,
        question=question
    )
    response = generate_response(
        final_prompt
    )
    return response

# ==========================================
# Local test
# ==========================================
if __name__ == "__main__":
    question = input("Enter your question: ")
    answer = ask(question)
    print("\nFinal Answer:")
    print(answer)