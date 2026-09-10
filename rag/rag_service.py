import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore


load_dotenv()


# الاتصال بـ Qdrant
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)


# نفس موديل الـ Embedding المستخدم في تخزين البيانات
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


# ربط LangChain بالـ Collection الموجودة
vector_store = QdrantVectorStore(
    client=client,
    collection_name=os.getenv("QDRANT_COLLECTION"),
    embedding=embeddings,
    content_payload_key="text"
)


# إنشاء Retriever
retriever = vector_store.as_retriever(
    search_kwargs={"k": 5}
)

# موديل GPT الذي سيولد الإجابة النهائية
llm = ChatOpenAI(
    model="gpt-5.5"
)

# Prompt لتحويل السؤال إلى استعلام بحث عربي
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

مثال:

سؤال المستخدم:
What are the rights of a defendant when arrested?

استعلام البحث:
ما حقوق المتهم عند القبض عليه أو توقيفه، وإبلاغه بأسباب القبض أو التوقيف، وحقه في الاتصال والاستعانة بمحام؟

سؤال المستخدم:
{question}

استعلام البحث:
""")

# تعليمات الـ RAG
prompt = PromptTemplate.from_template("""
أنت مساعد متخصص في نظام الإجراءات الجزائية السعودي.

تعامل مع رسالة المستخدم حسب نوعها:

1- إذا كانت الرسالة تحية مثل:
السلام عليكم
هلا
مرحبا
صباح الخير
مساء الخير

فرد عليها برد مناسب ولطيف.

مثال:
السلام عليكم → وعليكم السلام، كيف أقدر أخدمك؟


2- إذا قال المستخدم إنه يريد طرح سؤال قانوني، مثل:
عندي سؤال قانوني
أبي أسألك عن النظام
عندي استفسار قانوني

فرد عليه برد مناسب مثل:
تفضل، اطرح سؤالك القانوني وسأحاول مساعدتك.


3- إذا كان المستخدم يسأل سؤالاً متعلقاً بنظام الإجراءات الجزائية:
أجب اعتمادًا فقط على السياق الموجود أدناه.


قواعد الإجابة القانونية:

- لا تستخدم معلومات قانونية من خارج السياق.
- لا تخمن أي معلومة غير موجودة في السياق.
- إذا لم تكن الإجابة موجودة في السياق، قل:
  "المعلومات المتاحة في السياق لا تكفي للإجابة عن هذا السؤال."
- إذا انتهى أحد النصوص بكلمة أو جملة غير مكتملة، فلا تعتمد على الجزء غير المكتمل.
- لا تحاول إكمال الكلمات أو الجمل الناقصة من عندك.
- اجعل الإجابة واضحة ومباشرة.
- يمكنك ترتيب الإجابة على شكل نقاط إذا كان ذلك يجعلها أوضح.


قواعد ذكر المواد والمراجع:

- عندما تعتمد على مادة نظامية في الإجابة، اذكر رقم المادة كما ورد في السياق.
- ضع رقم المادة بجانب المعلومة التي أخذتها منها.
- لا تذكر رقم مادة إلا إذا كان رقمها موجودًا بوضوح في السياق.
- لا تخمن رقم المادة.
- لا تنسب معلومة إلى مادة إذا لم يكن واضحًا من السياق أنها تابعة لها.
- إذا لم يظهر رقم المادة بوضوح، قدم المعلومة دون إضافة رقم مادة من عندك.


مثال على طريقة الإجابة:

يجوز للمحقق إصدار أمر بالقبض على المتهم إذا لم يحضر بعد تكليفه
بالحضور رسميًا دون عذر مقبول (المادة 107).

كما يجوز ذلك إذا خيف هربه أو كانت الجريمة في حال تلبس
(المادة 107).


السياق:
{context}


رسالة المستخدم:
{question}
""")

def ask(question):

    # تحويل سؤال المستخدم إلى استعلام بحث عربي
    search_query = create_search_query(question)

    # البحث في Qdrant باستخدام الاستعلام العربي
    docs = retriever.invoke(search_query)

    # جمع أفضل Chunks
    context = "\n\n".join(
        doc.page_content
        for doc in docs
    )

    # نرسل السؤال الأصلي + النصوص المسترجعة
    messages = prompt.invoke({
        "context": context,
        "question": question
    })

    # توليد الإجابة
    response = llm.invoke(messages)

    return response.content
def create_search_query(question):

    messages = search_prompt.invoke({
        "question": question
    })

    response = llm.invoke(messages)

    return response.content