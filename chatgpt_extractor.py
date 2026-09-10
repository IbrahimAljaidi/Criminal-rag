import io

from openai import OpenAI
from dotenv import load_dotenv


# قراءة OPENAI_API_KEY من .env
load_dotenv()

client = OpenAI()


def extract_text_with_chatgpt(page_bytes, page_number):

    # تحويل الـ bytes الموجودة في RAM
    # إلى ملف يمكن إرساله إلى OpenAI
    pdf_file = io.BytesIO(page_bytes)

    # نعطيه اسم فقط حتى يعرف OpenAI أنه PDF
    # هذا لا ينشئ ملف على جهازك
    pdf_file.name = f"page_{page_number + 1}.pdf"


    # رفع الصفحة إلى OpenAI
    uploaded_file = client.files.create(
        file=pdf_file,
        purpose="user_data"
    )


    # إرسال الصفحة إلى GPT
    response = client.responses.create(
        model="gpt-5.5",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": uploaded_file.id
                    },
                    {
                        "type": "input_text",
                        "text": """
مهمتك هي النسخ الحرفي للنص الموجود في صفحة PDF المرفقة.

قواعد إلزامية:
- استخرج فقط الكلمات والأرقام الظاهرة فعليًا في الصفحة.
- ممنوع إضافة أي كلمة من معرفتك.
- ممنوع إكمال الجمل الناقصة من عندك.
- ممنوع تصحيح أو إعادة صياغة النص.
- ممنوع التخمين.
- لا تلخص ولا تشرح.
- حافظ على أرقام المواد والفقرات كما تظهر.
- حافظ على ترتيب النص قدر الإمكان.
- إذا لم تستطع قراءة كلمة أو رقم بثقة، اكتب [غير واضح] مكانه.
- إذا كانت الجملة تبدأ في صفحة سابقة أو تستمر في الصفحة التالية، انسخ فقط الجزء الظاهر في هذه الصفحة.
- قبل إرجاع النتيجة، راجع النص مقابل الصفحة المرفقة وتأكد أن كل كلمة في إجابتك لها مقابل ظاهر في الصفحة.
- أرجع النص المستخرج فقط بدون أي تعليق أو مقدمة.
"""
                    }
                ]
            }
        ]
    )


    # أخذ النص الذي رجع من GPT
    text = response.output_text

    return text