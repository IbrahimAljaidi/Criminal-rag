from rag.rag_service import ask
while True:
    question = input("اكتب سؤالك: ")

    answer = ask(question)
    print("\nالإجابة:")
    print(answer)

    again=input("هل لديك سؤال أخر ؟(نعم/لا):")
    if again.lower() in ["لا","شكرا","لا شكرا"]:
        print("شكرا لاستخدامك الخدمة. إلى اللقاء!")
        break
    elif again.lower() in ["نعم","أكيد","بالطبع"]:
        continue
    else:
        print("الرجاء كتابة نعم أو لا.")
