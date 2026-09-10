import pymupdf


class PDFOCRExtractor:

    def __init__(self, pdf_path):
        # مسار ملف PDF الأصلي
        self.pdf_path = pdf_path


    def get_page_count(self):

        # فتح ملف PDF الأصلي
        pdf = pymupdf.open(self.pdf_path)

        # معرفة عدد الصفحات
        page_count = len(pdf)

        # إغلاق الملف
        pdf.close()

        return page_count


    def extract_page(self, page_number):

        # فتح ملف PDF الأصلي
        pdf = pymupdf.open(self.pdf_path)

        # إنشاء PDF مؤقت في RAM فقط
        # لا يتم حفظه على الجهاز
        page_pdf = pymupdf.open()

        # أخذ صفحة واحدة فقط من الملف الأصلي
        page_pdf.insert_pdf(
            pdf,
            from_page=page_number,
            to_page=page_number
        )

        # تحويل الصفحة إلى bytes
        # يعني تصبح موجودة في RAM
        page_bytes = page_pdf.tobytes()

        # إغلاق الملفات
        page_pdf.close()
        pdf.close()

        # نرجع بيانات الصفحة
        # وليس مسار ملف
        return page_bytes