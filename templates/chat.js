'use strict';

(() => {
const session = window.LegalSession;
if (!session.requireSession()) return;

let activeController = null;
let leaving = false;
let activeChatId = null;

const API_URL = session.API_BASE + '/ask';
const CHATS_URL = session.API_BASE + '/chats';
const PROFILE_URL = session.API_BASE + '/profile';

const form = document.querySelector('#question-form');
const input = document.querySelector('#question');
const send = document.querySelector('#send');
const messages = document.querySelector('#messages');
const welcome = document.querySelector('#welcome');
const connection = document.querySelector('#connection');

const historyList = document.querySelector('#history-list');
const historyEmpty = document.querySelector('#history-empty');
const newChatButton = document.querySelector('#new-chat');

const menuToggle = document.querySelector('#menu-toggle');
const menuClose = document.querySelector('#menu-close');
const menuOverlay = document.querySelector('#menu-overlay');
const sideMenu = document.querySelector('#side-menu');

const accountSettings = document.querySelector('#account-settings');
const accountModal = document.querySelector('#account-modal');
const accountClose = document.querySelector('#account-close');
const accountForm = document.querySelector('#account-form');
const accountName = document.querySelector('#account-name');
const accountMessage = document.querySelector('#account-message');
const accountSave = document.querySelector('#account-save');
const menuUserName = document.querySelector('#menu-user-name');

let busy = false;
let language = 'ar';
let statusKey = 'ready';

const words = {
 ar: {
   ready:'جاهز للاستفسار',
   connected:'متصل',
   failed:'تعذّر الاتصال',
   offline:'غير متصل',
   user:'أنت · المستخدم',
   assistant:'المساعد القانوني',
   loading:'جاري البحث في النظام واللائحة...',
   error:'حدث خطأ أثناء معالجة سؤالك. يرجى المحاولة مرة أخرى.',
   retry:'إعادة المحاولة'
 },
 en: {
   ready:'Ready to help',
   connected:'Connected',
   failed:'Connection failed',
   offline:'Offline',
   user:'You · User',
   assistant:'Legal Assistant',
   loading:'Searching the law and implementing regulations...',
   error:'Something went wrong while processing your question. Please try again.',
   retry:'Try again'
 }
};

const t = key => words[language][key];
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;


function scrollLatest() {
  const area = document.querySelector('#scroll-area');

  requestAnimationFrame(() => {
    if (
      area.scrollHeight > area.clientHeight &&
      getComputedStyle(area).overflowY === 'auto'
    ) {
      area.scrollTo({
        top: area.scrollHeight,
        behavior: reducedMotion ? 'instant' : 'smooth'
      });
    } else {
      messages.lastElementChild?.scrollIntoView({
        behavior: reducedMotion ? 'instant' : 'smooth',
        block:'nearest'
      });
    }
  });
}


function refreshInput() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 155) + 'px';
  send.disabled = busy || !input.value.trim();
}


function setStatus(key, error = false) {
  statusKey = key;
  connection.querySelector('span').textContent = t(key);
  connection.classList.toggle('error', error);
}


function inline(parent, text) {
  for (const [index, part] of text.split(/\*\*(.+?)\*\*/g).entries()) {
    if (index % 2) {
      const strong = document.createElement('strong');
      strong.textContent = part;
      parent.append(strong);
    } else {
      parent.append(document.createTextNode(part));
    }
  }
}


function formatAnswer(container, text) {
  let list = null;

  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) {
      list = null;
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    const item = line.match(
      /^\s*(?:([-*•])|([0-9٠-٩]+)[.)ـ-])\s+(.+)$/
    );

    if (item) {
      const kind = item[1] ? 'ul' : 'ol';

      if (!list || list.tagName.toLowerCase() !== kind) {
        list = document.createElement(kind);

        if (item[2]) {
          list.start = Number(
            item[2].replace(
              /[٠-٩]/g,
              c => '٠١٢٣٤٥٦٧٨٩'.indexOf(c)
            )
          );
        }

        container.append(list);
      }

      const li = document.createElement('li');
      inline(li, item[3]);
      list.append(li);

    } else {
      list = null;

      const element = document.createElement(
        heading
          ? 'h' + Math.min(heading[1].length + 1, 4)
          : 'p'
      );

      inline(
        element,
        heading ? heading[2] : line
      );

      container.append(element);
    }
  }
}


function addMessage(role, text, extra = '') {
  const article = document.createElement('article');
  article.className = `message ${role} ${extra}`;

  const label = document.createElement('div');
  label.className = 'message-label';
  label.textContent = t(
    role === 'user' ? 'user' : 'assistant'
  );

  const body = document.createElement('div');
  body.className = 'message-body';
  body.dir = 'auto';

  if (role === 'user') {
    body.textContent = text;
  } else {
    formatAnswer(body, text);
  }

  article.append(label, body);
  messages.append(article);
  scrollLatest();

  return article;
}


// ============================================================
// Side Menu
// ============================================================

function openMenu() {
  menuOverlay.hidden = false;

  requestAnimationFrame(() => {
    sideMenu.classList.add('open');
  });

  sideMenu.setAttribute('aria-hidden', 'false');
  menuToggle.setAttribute('aria-expanded', 'true');
}


function closeMenu() {
  sideMenu.classList.remove('open');
  sideMenu.setAttribute('aria-hidden', 'true');
  menuToggle.setAttribute('aria-expanded', 'false');

  setTimeout(() => {
    if (!sideMenu.classList.contains('open')) {
      menuOverlay.hidden = true;
    }
  }, 250);
}


menuToggle.addEventListener('click', openMenu);
menuClose.addEventListener('click', closeMenu);
menuOverlay.addEventListener('click', closeMenu);


// ============================================================
// Profile
// ============================================================

async function loadProfile() {
  try {
    const response = await fetch(PROFILE_URL, {
      headers: {
        'Authorization':
          'Bearer ' + session.getToken()
      }
    });

    if (response.status === 401) {
      endSession();
      return;
    }

    const data = await session.readJSON(response);

    if (!response.ok) return;

    accountName.value = data.name || '';
    menuUserName.textContent = data.name || '';

  } catch {
    // Profile failure should not stop the chat.
  }
}


function openAccountSettings() {
  closeMenu();

  accountMessage.hidden = true;
  accountMessage.classList.remove('error');

  accountModal.hidden = false;

  void loadProfile().then(() => {
    accountName.focus();
  });
}


function closeAccountSettings() {
  accountModal.hidden = true;
  accountMessage.hidden = true;
  accountMessage.classList.remove('error');
}


accountSettings.addEventListener(
  'click',
  openAccountSettings
);

accountClose.addEventListener(
  'click',
  closeAccountSettings
);

accountModal.addEventListener(
  'click',
  event => {
    if (event.target === accountModal) {
      closeAccountSettings();
    }
  }
);


accountForm.addEventListener(
  'submit',
  async event => {
    event.preventDefault();

    const name = accountName.value.trim();

    if (!name) return;

    accountSave.disabled = true;
    accountMessage.hidden = true;
    accountMessage.classList.remove('error');

    try {
      const response = await fetch(
        PROFILE_URL,
        {
          method:'PATCH',

          headers:{
            'Content-Type':'application/json',
            'Authorization':
              'Bearer ' + session.getToken()
          },

          body:JSON.stringify({name})
        }
      );

      if (response.status === 401) {
        endSession();
        return;
      }

      const data =
        await session.readJSON(response);

      if (!response.ok) {
        throw new Error(
          session.errorMessage(data) ||
          'تعذر تحديث الاسم.'
        );
      }

      accountName.value = data.name;
      menuUserName.textContent = data.name;

      accountMessage.textContent =
        language === 'ar'
          ? 'تم تحديث الاسم بنجاح.'
          : 'Name updated successfully.';

      accountMessage.hidden = false;

    } catch (error) {
      accountMessage.textContent =
        error.message ||
        (
          language === 'ar'
            ? 'تعذر تحديث الاسم.'
            : 'Unable to update the name.'
        );

      accountMessage.classList.add('error');
      accountMessage.hidden = false;

    } finally {
      accountSave.disabled = false;
    }
  }
);


// ============================================================
// Chat History
// ============================================================

function showNewChat() {
  activeChatId = null;

  messages.replaceChildren();
  welcome.hidden = false;
  input.value = '';

  historyList
    ?.querySelectorAll('.history-item')
    .forEach(item => {
      item.classList.remove('active');
    });

  refreshInput();
  input.focus();
}


function markActiveHistory(chatId) {
  historyList
    ?.querySelectorAll('.history-item')
    .forEach(item => {
      item.classList.toggle(
        'active',
        item.dataset.chatId === chatId
      );
    });
}


async function loadHistory() {
  if (
    !historyList ||
    leaving ||
    !session.requireSession()
  ) {
    return;
  }

  try {
    const response = await fetch(
      CHATS_URL,
      {
        headers:{
          'Authorization':
            'Bearer ' + session.getToken()
        }
      }
    );

    if (response.status === 401) {
      endSession();
      return;
    }

    const data =
      await session.readJSON(response);

    if (!response.ok) {
      throw new Error(
        'History request failed'
      );
    }

    const chats =
      Array.isArray(data?.chats)
        ? data.chats
        : [];

    historyList.replaceChildren();

    if (historyEmpty) {
      historyEmpty.hidden =
        chats.length !== 0;
    }

    chats.forEach(chat => {
      if (!chat?.chat_id) return;

      const button =
        document.createElement('button');

      button.type = 'button';
      button.className = 'history-item';
      button.dataset.chatId =
        String(chat.chat_id);

      button.textContent =
        chat.title ||
        (
          language === 'ar'
            ? 'محادثة'
            : 'Conversation'
        );

      button.addEventListener(
        'click',
        () => {
          void openChat(
            String(chat.chat_id)
          );
        }
      );

      historyList.append(button);
    });

    if (activeChatId) {
      markActiveHistory(activeChatId);
    }

  } catch {
    // History errors do not stop the main chat.
  }
}


async function openChat(chatId) {
  if (
    busy ||
    leaving ||
    !chatId
  ) {
    return;
  }

  try {
    const response = await fetch(
      `${CHATS_URL}/${encodeURIComponent(chatId)}`,
      {
        headers:{
          'Authorization':
            'Bearer ' + session.getToken()
        }
      }
    );

    if (response.status === 401) {
      endSession();
      return;
    }

    const data =
      await session.readJSON(response);

    if (!response.ok) {
      throw new Error(
        'Chat request failed'
      );
    }

    const exchanges =
      Array.isArray(data?.messages)
        ? data.messages
        : [];

    activeChatId = chatId;

    messages.replaceChildren();
    welcome.hidden = true;

    exchanges.forEach(exchange => {
      if (
        typeof exchange?.question ===
        'string'
      ) {
        addMessage(
          'user',
          exchange.question
        );
      }

      if (
        typeof exchange?.answer ===
        'string'
      ) {
        addMessage(
          'assistant',
          exchange.answer
        );
      }
    });

    markActiveHistory(chatId);
    closeMenu();
    scrollLatest();

  } catch {
    setStatus(
      'failed',
      true
    );
  }
}


newChatButton.addEventListener(
  'click',
  () => {
    if (busy) return;

    showNewChat();
    closeMenu();
  }
);


// ============================================================
// Ask FastAPI
// ============================================================

async function askQuestion(
  question,
  retry = false
) {
  if (
    typeof question !== 'string' ||
    !question.trim() ||
    question.length > 12000
  ) {
    throw new Error(
      'Invalid question'
    );
  }

  if (
    leaving ||
    !session.requireSession()
  ) {
    return {
      status:'unauthorized'
    };
  }

  if (busy) {
    return {
      status:'busy'
    };
  }

  busy = true;
  welcome.hidden = true;

  if (!retry) {
    input.value = '';
  }

  refreshInput();

  document
    .querySelectorAll('.retry')
    .forEach(button => {
      button.disabled = true;
    });

  if (!retry) {
    addMessage(
      'user',
      question.trim()
    );
  }

  const loading = addMessage(
    'assistant',
    t('loading'),
    'loading'
  );

  const dots =
    document.createElement('span');

  dots.className = 'dots';

  dots.setAttribute(
    'aria-hidden',
    'true'
  );

  for (let i = 0; i < 3; i++) {
    dots.append(
      document.createElement('i')
    );
  }

  loading
    .querySelector('.message-body')
    .append(dots);

  const controller =
    new AbortController();

  activeController = controller;

  const timeout = setTimeout(
    () => controller.abort(),
    120000
  );

  try {
    const body = {
      question:question.trim(),
      platform:'website'
    };

    // Continue the current visible chat.
    if (activeChatId) {
      body.chat_id = activeChatId;
    }

    const response = await fetch(
      API_URL,
      {
        method:'POST',

        headers:{
          'Content-Type':
            'application/json',

          'Authorization':
            'Bearer ' +
            session.getToken()
        },

        body:JSON.stringify(body),

        signal:controller.signal
      }
    );

    if (response.status === 401) {
      endSession();

      return {
        status:'unauthorized'
      };
    }

    const data =
      await session.readJSON(response);

    if (!response.ok) {
      const failure =
        new Error('Request failed');

      failure.backendMessage =
        session.errorMessage(data);

      throw failure;
    }

    if (
      !data ||
      typeof data.answer !== 'string' ||
      !data.answer.trim()
    ) {
      throw new Error(
        'Invalid answer'
      );
    }

    if (leaving) {
      return {
        status:'cancelled'
      };
    }

    if (
      typeof data.chat_id === 'string' &&
      data.chat_id
    ) {
      activeChatId =
        data.chat_id;
    }

    loading.remove();

    addMessage(
      'assistant',
      data.answer
    );

    setStatus('connected');

    void loadHistory();

    return {
      status:'answered',
      answer:data.answer
    };

  } catch (failure) {
    loading.remove();

    if (leaving) {
      return {
        status:'cancelled'
      };
    }

    setStatus(
      'failed',
      true
    );

    const error = addMessage(
      'assistant',
      t('error'),
      'error'
    );

    if (failure.backendMessage) {
      error.dataset.backendError =
        'true';

      error
        .querySelector(
          '.message-body p'
        )
        .textContent =
          failure.backendMessage;
    }

    const button =
      document.createElement('button');

    button.type = 'button';
    button.className = 'retry';
    button.textContent = t('retry');

    button.addEventListener(
      'click',
      () => {
        error.remove();

        void askQuestion(
          question,
          true
        );
      }
    );

    error
      .querySelector('.message-body')
      .append(button);

    scrollLatest();

    return {
      status:'error'
    };

  } finally {
    clearTimeout(timeout);

    activeController = null;
    busy = false;

    refreshInput();

    document
      .querySelectorAll('.retry')
      .forEach(button => {
        button.disabled = false;
      });
  }
}


// ============================================================
// Chat Events
// ============================================================

form.addEventListener(
  'submit',
  event => {
    event.preventDefault();

    if (
      !busy &&
      input.value.trim()
    ) {
      void askQuestion(
        input.value
      );
    }
  }
);


input.addEventListener(
  'input',
  refreshInput
);


input.addEventListener(
  'keydown',
  event => {
    if (
      event.key === 'Enter' &&
      !event.shiftKey &&
      !event.isComposing
    ) {
      event.preventDefault();
      form.requestSubmit();
    }
  }
);


document
  .querySelectorAll('.suggestion')
  .forEach(button => {
    button.addEventListener(
      'click',
      () => {
        void askQuestion(
          button
            .querySelector('.question')
            .textContent
        );
      }
    );
  });


window.addEventListener(
  'offline',
  () => setStatus(
    'offline',
    true
  )
);


window.addEventListener(
  'online',
  () => setStatus('ready')
);


if (!navigator.onLine) {
  setStatus(
    'offline',
    true
  );
}


// ============================================================
// Optional Browser Tool
// ============================================================

if (
  document.modelContext?.registerTool
) {
  const lifecycle =
    new AbortController();

  try {
    Promise.resolve(
      document.modelContext.registerTool(
        {
          name:
            'ask_legal_question',

          description:
            'Send a question to the legal assistant and display the answer in the conversation.',

          inputSchema:{
            type:'object',

            properties:{
              question:{
                type:'string',
                minLength:1,
                maxLength:12000
              }
            },

            required:['question'],
            additionalProperties:false
          },

          annotations:{
            readOnlyHint:false,
            untrustedContentHint:true
          },

          execute:
            ({question}) =>
              askQuestion(question)
        },

        {
          signal:lifecycle.signal
        }
      )
    ).catch(() => {});

  } catch {}

  window.addEventListener(
    'pagehide',
    () => lifecycle.abort(),
    {once:true}
  );
}


// ============================================================
// Language
// ============================================================

const translatedElements = [];


function translate(
  selector,
  english,
  attribute = null
) {
  const element =
    document.querySelector(selector);

  if (!element) {
    throw new Error(
      'Missing translation target: ' +
      selector
    );
  }

  translatedElements.push({
    element,
    attribute,

    ar:attribute
      ? element.getAttribute(attribute)
      : element.textContent,

    en:english
  });
}


translate(
  'title',
  'Legal Assistant | Saudi Law of Criminal Procedure'
);

translate(
  'meta[name="description"]',
  'Ask about the Saudi Law of Criminal Procedure and its Implementing Regulations.',
  'content'
);

translate(
  '.brand',
  'Legal Assistant, home page',
  'aria-label'
);

translate(
  '.brand strong',
  'Legal Assistant'
);

translate(
  '.brand small',
  'Saudi Law of Criminal Procedure'
);

translate(
  '.scope',
  'Law & Implementing Regulations'
);

translate(
  '.section-label > span:first-child',
  'Legal inquiries'
);

translate(
  '.label-note',
  'Know the law. Understand your rights.'
);

translate(
  '.eyebrow',
  'Law of Criminal Procedure · Saudi Arabia'
);

translate(
  '.welcome-prefix',
  'Welcome to the '
);

translate(
  '#welcome-title > span:last-child',
  'Legal Assistant'
);

translate(
  '.welcome > p',
  'Ask about the Saudi Law of Criminal Procedure and its Implementing Regulations.'
);

translate(
  '.suggestions-heading > span:first-child',
  'Start with a question'
);

translate(
  '.suggestions-heading > span:last-child',
  'Or write your question below'
);


const examples = [
  [
    'Arrest of the accused',
    'When may an accused person be arrested?'
  ],
  [
    'Articles of the law',
    'What does Article 107 of the law say?'
  ],
  [
    'Rights of the accused',
    'What rights does an accused person have upon arrest?'
  ],
  [
    'Legal procedures',
    'What is the difference between arrest and detention under the law?'
  ]
];


examples.forEach(
  ([category,question],index) => {
    translate(
      `.suggestion:nth-child(${index + 1}) .question-category`,
      category
    );

    translate(
      `.suggestion:nth-child(${index + 1}) .question`,
      question
    );
  }
);


translate(
  '.source-copy',
  'Focused on the law and its implementing regulations'
);

translate(
  '#messages',
  'Conversation',
  'aria-label'
);

translate(
  'label[for="question"]',
  'Your legal question'
);

translate(
  '#question',
  'Ask about the Saudi Law of Criminal Procedure...',
  'placeholder'
);

translate(
  '.composer-bottom > span',
  'Enter to send · Shift + Enter for a new line'
);

translate(
  '#send > span',
  'Send'
);

translate(
  '.disclaimer-copy',
  'This assistant provides general information and does not replace advice from a qualified legal professional.'
);

translate(
  '.footer > span:first-child',
  'Legal Assistant'
);

translate(
  '.footer > span:last-child',
  'Saudi Law of Criminal Procedure and its Implementing Regulations'
);


// Side menu translations
translate(
  '#menu-toggle',
  'Open menu',
  'aria-label'
);

translate(
  '#side-menu',
  'Main menu',
  'aria-label'
);

translate(
  '#account-settings > span',
  'Account settings'
);

translate(
  '#new-chat > span',
  'New Chat'
);

translate(
  '.history-title > span',
  'History'
);

translate(
  '#history-empty',
  'No previous conversations.'
);

translate(
  '#logout > span',
  'Sign out'
);

translate(
  '#account-title',
  'Account settings'
);

translate(
  '.account-modal-header p',
  'You can change your name.'
);

translate(
  'label[for="account-name"]',
  'Name'
);

translate(
  '#account-save',
  'Save changes'
);


const toggle =
  document.querySelector(
    '#language-toggle'
  );


function setLanguage(next) {
  language =
    next === 'en'
      ? 'en'
      : 'ar';

  document.documentElement.lang =
    language;

  document.documentElement.dir =
    language === 'ar'
      ? 'rtl'
      : 'ltr';


  for (
    const item
    of translatedElements
  ) {
    if (item.attribute) {
      item.element.setAttribute(
        item.attribute,
        item[language]
      );
    } else {
      item.element.textContent =
        item[language];
    }
  }


  toggle.textContent =
    language === 'ar'
      ? 'English'
      : 'العربية';

  toggle.lang =
    language === 'ar'
      ? 'en'
      : 'ar';

  toggle.setAttribute(
    'aria-label',
    language === 'ar'
      ? 'Switch to English'
      : 'التبديل إلى العربية'
  );


  connection
    .querySelector('span')
    .textContent =
      t(statusKey);


  messages
    .querySelectorAll('.message')
    .forEach(message => {
      message
        .querySelector(
          '.message-label'
        )
        .textContent =
          t(
            message.classList
              .contains('user')
              ? 'user'
              : 'assistant'
          );

      if (
        message.classList
          .contains('loading') ||
        (
          message.classList
            .contains('error') &&
          !message.dataset.backendError
        )
      ) {
        message
          .querySelector(
            '.message-body p'
          )
          .textContent =
            t(
              message.classList
                .contains('loading')
                ? 'loading'
                : 'error'
            );
      }
    });


  document
    .querySelectorAll('.retry')
    .forEach(button => {
      button.textContent =
        t('retry');
    });


  updateThemeButton();
  refreshInput();


  try {
    localStorage.setItem(
      'legal-assistant-language',
      language
    );
  } catch {}
}


toggle.addEventListener(
  'click',
  () => {
    setLanguage(
      language === 'ar'
        ? 'en'
        : 'ar'
    );
  }
);


let savedLanguage = 'ar';


try {
  savedLanguage =
    localStorage.getItem(
      'legal-assistant-language'
    ) || 'ar';
} catch {}


setLanguage(savedLanguage);


// ============================================================
// Theme
// ============================================================

function updateThemeButton() {
  const button =
    document.querySelector(
      '#theme-toggle'
    );

  const dark =
    document.documentElement
      .dataset.theme === 'dark';

  button.setAttribute(
    'aria-pressed',
    String(dark)
  );

  button.setAttribute(
    'aria-label',
    language === 'ar'
      ? 'الوضع الداكن'
      : 'Dark mode'
  );

  button
    .querySelector('span')
    .textContent =
      language === 'ar'
        ? (
          dark
            ? 'فاتح'
            : 'داكن'
        )
        : (
          dark
            ? 'Light'
            : 'Dark'
        );

  button.title =
    language === 'ar'
      ? (
        dark
          ? 'التبديل إلى الوضع الفاتح'
          : 'التبديل إلى الوضع الداكن'
      )
      : (
        dark
          ? 'Switch to light mode'
          : 'Switch to dark mode'
      );
}


document
  .querySelector(
    '#theme-toggle'
  )
  .addEventListener(
    'click',
    () => {
      const next =
        document.documentElement
          .dataset.theme === 'dark'
          ? 'light'
          : 'dark';

      document.documentElement
        .dataset.theme =
          next;

      try {
        localStorage.setItem(
          'legal-assistant-theme',
          next
        );
      } catch {}

      updateThemeButton();
    }
  );


updateThemeButton();


// ============================================================
// Session
// ============================================================

function endSession() {
  leaving = true;

  activeController?.abort();

  messages.replaceChildren();
  input.value = '';

  session.logout();
}


document
  .querySelector('#logout')
  .addEventListener(
    'click',
    endSession
  );


document.addEventListener(
  'keydown',
  event => {
    if (event.key !== 'Escape') {
      return;
    }

    if (!accountModal.hidden) {
      closeAccountSettings();
    } else {
      closeMenu();
    }
  }
);


window.addEventListener(
  'pagehide',
  () => {
    leaving = true;

    activeController?.abort();

    document.documentElement
      .style.visibility =
        'hidden';
  }
);


window.addEventListener(
  'pageshow',
  () => {
    if (!session.requireSession()) {
      return;
    }

    leaving = false;

    try {
      document.documentElement
        .dataset.theme =
          localStorage.getItem(
            'legal-assistant-theme'
          ) === 'dark'
            ? 'dark'
            : 'light';

      setLanguage(
        localStorage.getItem(
          'legal-assistant-language'
        )
      );

    } catch {
      updateThemeButton();
    }

    document.documentElement
      .style.visibility =
        'visible';
  }
);


// Always start with a fresh visible chat.
showNewChat();

// Load MongoDB data.
void loadHistory();
void loadProfile();

document.documentElement
  .style.visibility =
    'visible';

})();