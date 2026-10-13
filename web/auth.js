'use strict';
// Authenticate against FastAPI; persist the bearer token only in sessionStorage.
const session = window.LegalSession;
let busy = false;
let activeController = null;
let feedbackKey = '';
let backendFeedback = '';
const registering = document.body.dataset.authMode === 'register';
const form = document.querySelector('#auth-form');
const feedback = document.querySelector('#auth-feedback');
let language = 'ar';
try { language = localStorage.getItem('legal-assistant-language') === 'en' ? 'en' : 'ar'; } catch {}
const copy = {
 ar: {
  brand:'المساعد القانوني', law:'نظام الإجراءات الجزائية السعودي ولائحته التنفيذية', shortLaw:'نظام الإجراءات الجزائية السعودي', home:'المساعد القانوني، الصفحة الرئيسية', back:'العودة لتسجيل الدخول',
  loginTitle:'تسجيل الدخول', registerTitle:'إنشاء حساب', loginSubtitle:'مرحباً بعودتك. أدخل بيانات حسابك للمتابعة.', registerSubtitle:'أدخل بياناتك لإنشاء حساب في المساعد القانوني.',
  name:'الاسم الكامل', identifier:'البريد الإلكتروني أو رقم الجوال', password:'كلمة المرور', confirm:'تأكيد كلمة المرور', passwordHint:'استخدم 8 أحرف على الأقل.',
  loginPrompt:'ليس لديك حساب؟', registerPrompt:'لديك حساب بالفعل؟', show:'إظهار', hide:'إخفاء', showPassword:'إظهار كلمة المرور', hidePassword:'إخفاء كلمة المرور',
  submitting:'جاري الإرسال...', networkError:'تعذّر الاتصال بالخادم. تحقق من اتصالك وحاول مجدداً.', timeout:'انتهت مهلة الطلب. حاول مرة أخرى.', requestError:'تعذّرت معالجة الطلب.', invalidSession:'لم يرجع الخادم جلسة دخول صالحة.', storageError:'تعذّر حفظ الجلسة. اسمح بتخزين بيانات الجلسة في المتصفح.', required:'يرجى تعبئة هذا الحقل.', invalidIdentifier:'أدخل بريداً إلكترونياً أو رقم جوال سعودي صحيحاً.', shortPassword:'يجب أن تحتوي كلمة المرور على 8 أحرف على الأقل.', mismatch:'كلمتا المرور غير متطابقتين.',
  dark:'داكن', light:'فاتح', darkMode:'الوضع الداكن', switchDark:'التبديل إلى الوضع الداكن', switchLight:'التبديل إلى الوضع الفاتح',invalidCredentials: 'البريد الإلكتروني أو رقم الجوال أو كلمة المرور غير صحيحة.',
accountExists: 'البريد الإلكتروني أو رقم الجوال مسجل مسبقًا.',
serverError: 'حدث خطأ في الخادم. حاول مرة أخرى لاحقًا.'
 },
 en: {
  brand:'Legal Assistant', law:'Saudi Law of Criminal Procedure and its Implementing Regulations', shortLaw:'Saudi Law of Criminal Procedure', home:'Legal Assistant, home page', back:'Back to sign in',
  loginTitle:'Sign in', registerTitle:'Create an account', loginSubtitle:'Welcome back. Enter your account details to continue.', registerSubtitle:'Enter your details to create your Legal Assistant account.',
  name:'Full name', identifier:'Email address or mobile number', password:'Password', confirm:'Confirm password', passwordHint:'Use at least 8 characters.',
  loginPrompt:'New to Legal Assistant?', registerPrompt:'Already have an account?', show:'Show', hide:'Hide', showPassword:'Show password', hidePassword:'Hide password',
  submitting:'Submitting...', networkError:'Could not reach the server. Check your connection and try again.', timeout:'The request timed out. Please try again.', requestError:'The request could not be completed.', invalidSession:'The server did not return a valid sign-in session.', storageError:'Could not save the session. Allow session storage in your browser.', required:'Please fill out this field.', invalidIdentifier:'Enter a valid email address or Saudi mobile number.', shortPassword:'Your password must contain at least 8 characters.', mismatch:'The passwords do not match.',
  dark:'Dark', light:'Light', darkMode:'Dark mode', switchDark:'Switch to dark mode', switchLight:'Switch to light mode',invalidCredentials: 'Invalid email, phone number or password.',
accountExists: 'This email or phone number is already registered.',
serverError: 'A server error occurred. Please try again later.'
 }
};
const t = key => copy[language][key];

// Convert API errors into translation keys.
function getApiErrorKey(status, data) {
    if (status === 401) {
        return 'invalidCredentials';
    }

    if (status === 400) {
        const detail = String(data?.detail || '').toLowerCase();

        if (
            detail.includes('already') ||
            detail.includes('exists') ||
            detail.includes('registered') ||
            detail.includes('duplicate')
        ) {
            return 'accountExists';
        }
    }

    if (status >= 500) {
        return 'serverError';
    }

    return 'requestError';
}

function updateTheme() {
 const dark = document.documentElement.dataset.theme === 'dark';
 const button = document.querySelector('#theme-toggle');
 button.setAttribute('aria-pressed', String(dark));
 button.setAttribute('aria-label', t('darkMode'));
 button.title = t(dark ? 'switchLight' : 'switchDark');
 button.querySelector('span').textContent = t(dark ? 'light' : 'dark');
}
function updatePasswordButton(button) {
 const visible = document.getElementById(button.dataset.password).type === 'text';
 button.textContent = t(visible ? 'hide' : 'show');
 button.setAttribute('aria-label', t(visible ? 'hidePassword' : 'showPassword'));
 button.setAttribute('aria-pressed', String(visible));
}
function applyLanguage(next) {
 language = next === 'en' ? 'en' : 'ar';
 document.documentElement.lang = language;
 document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
 const keys = {title:registering ? 'registerTitle':'loginTitle', submit:registering ? 'registerTitle':'loginTitle', subtitle:registering ? 'registerSubtitle':'loginSubtitle', switchPrompt:registering ? 'registerPrompt':'loginPrompt', switchLink:registering ? 'loginTitle':'registerTitle'};
 document.querySelectorAll('[data-copy]').forEach(node => node.textContent = t(keys[node.dataset.copy] || node.dataset.copy));
 document.title = t(keys.title) + ' | ' + t('brand');
 document.querySelector('.brand strong').textContent = t('brand');
 document.querySelector('.brand small').textContent = t('shortLaw');
 document.querySelector('.brand').setAttribute('aria-label',t('home'));
 document.querySelector('meta[name="description"]').content = t(keys.subtitle);
 const button = document.querySelector('#language-toggle');
 button.textContent = language === 'ar' ? 'English' : 'العربية';
 button.lang = language === 'ar' ? 'en' : 'ar';
 button.setAttribute('aria-label', language === 'ar' ? 'Switch to English':'التبديل إلى العربية');
 document.querySelectorAll('.password-toggle').forEach(updatePasswordButton);
 document.querySelectorAll('.field-error[data-error]').forEach(node => node.textContent = t(node.dataset.error));
 if (!feedback.hidden && feedbackKey) {
    feedback.textContent = t(feedbackKey);
}
 updateSubmit();
 updateTheme();
 try { localStorage.setItem('legal-assistant-language',language); } catch {}
}
// Validate locally before sending the exact backend request schema.
function validateField(field) {
 let key = '';
 if (!field.value.trim()) key = 'required';
 else if (field.id === 'identifier' && !session.parseIdentifier(field.value)) key = 'invalidIdentifier';
 else if (registering && field.id === 'password' && field.value.length < 8) key = 'shortPassword';
 else if (field.id === 'confirm-password' && field.value !== document.querySelector('#password').value) key = 'mismatch';
 const error = document.getElementById(field.id+'-error');
 field.setAttribute('aria-invalid', String(Boolean(key)));
 const descriptions = field.id === 'password' && registering ? 'password-hint ' : '';
 field.setAttribute('aria-describedby', descriptions + error.id);
 error.textContent = key ? t(key) : '';
 if (key) error.dataset.error = key; else delete error.dataset.error;
 return !key;
}
function updateSubmit() {
 const submit = form.querySelector('[type="submit"]');
 submit.disabled = busy;
 submit.textContent = t(busy ? 'submitting' : (registering ? 'registerTitle' : 'loginTitle'));
 form.setAttribute('aria-busy', String(busy));
 form.querySelectorAll('input').forEach(field => field.readOnly = busy);
}
// Display the error in the currently selected language.
function showFeedback(key) {
    feedbackKey = key;
    feedback.textContent = t(key);
    feedback.hidden = false;
}
function clearPasswords() {
 form.querySelectorAll('[autocomplete$="password"]').forEach(field => {
  field.value = '';
  field.type = 'password';
 });
 document.querySelectorAll('.password-toggle').forEach(updatePasswordButton);
}
form.addEventListener('submit', async event => {
 event.preventDefault();
 if (busy) return;
 feedback.hidden = true;
 const invalid = [...form.querySelectorAll('input')].filter(field => !validateField(field));
 if (invalid.length) { invalid[0].focus(); return; }
 const parsed = session.parseIdentifier(document.querySelector('#identifier').value);
 const password = document.querySelector('#password').value;
 const name = registering ? document.querySelector('#name').value.trim() : '';
 const payload = registering
  ? {name, email: parsed.email, phone: parsed.phone, password}
  : {identifier: parsed.identifier, password};
 busy = true;
 updateSubmit();
 const controller = new AbortController();
 activeController = controller;
 const timeout = setTimeout(() => controller.abort(), 30000);
 try {
  const response = await fetch(session.API_BASE + (registering ? '/register' : '/login'), {
   method: 'POST',
   headers: {'Content-Type': 'application/json'},
   body: JSON.stringify(payload),
   signal: controller.signal
  });
  const data = await session.readJSON(response);
  if (!response.ok) {
    if (response.status === 401) {
        session.clear();
    }

    const errorKey = getApiErrorKey(response.status, data);
    showFeedback(errorKey);

    return;
}
  session.save(data, name);
  clearPasswords();
  window.location.replace(session.chatURL);
 } catch (error) {
  const key = ['storageError', 'invalidSession'].includes(error.message)
   ? error.message : (error.name === 'AbortError' ? 'timeout' : 'networkError');
  showFeedback(key);
 } finally {
  clearTimeout(timeout);
  activeController = null;
  busy = false;
  updateSubmit();
 }
});
form.querySelectorAll('input').forEach(field => field.addEventListener('input', () => {
 feedback.hidden = true;
 if (field.hasAttribute('aria-invalid')) validateField(field);
 if (registering && field.id === 'password') {
  const confirm = document.querySelector('#confirm-password');
  if (confirm.value) validateField(confirm);
 }
}));
document.querySelectorAll('.password-toggle').forEach(button => button.addEventListener('click', () => {
 const field = document.getElementById(button.dataset.password);
 field.type = field.type === 'password' ? 'text' : 'password';
 updatePasswordButton(button);
}));
document.querySelector('#language-toggle').addEventListener('click', () => applyLanguage(language === 'ar' ? 'en':'ar'));
document.querySelector('#theme-toggle').addEventListener('click', () => {
 const theme = document.documentElement.dataset.theme === 'dark' ? 'light':'dark';
 document.documentElement.dataset.theme = theme;
 try { localStorage.setItem('legal-assistant-theme',theme); } catch {}
 updateTheme();
});
// Clear password fields if a browser restores this page from its history cache.
window.addEventListener('pagehide', () => {
 activeController?.abort();
 clearPasswords();
});
window.addEventListener('pageshow', () => {
 try {
  document.documentElement.dataset.theme = localStorage.getItem('legal-assistant-theme') === 'dark' ? 'dark':'light';
  applyLanguage(localStorage.getItem('legal-assistant-language'));
 } catch { applyLanguage(language); }
});
applyLanguage(language);
