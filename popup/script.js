'use strict';

const MAX_LENGTH = 2000;
const STORAGE_KEYS = {
  basicText: 'unoRandom_text_basic',
  advancedText: 'unoRandom_text_advanced',
  replacementPct: 'unoRandom_replacement_pct',
  emojiFrequency: 'unoRandom_emoji_frequency',
  theme: 'unoRandom_theme',
  initialized: 'unoRandom_initialized'
};

const INITIAL_TEXT = {
  basic: 'Привет, как дела? 🙏',
  advanced: 'Здравствуй, как [дела|делишки]? 😋'
};

const charMap = {
  'е': ['е', 'e'], 'Е': ['Е', 'E'],
  'т': ['т', 't'], 'Т': ['Т', 'T'],
  'о': ['о', 'o'], 'О': ['О', 'O'],
  'р': ['р', 'p'], 'Р': ['Р', 'P'],
  'а': ['а', 'a'], 'А': ['А', 'A'],
  'н': ['н', 'h'], 'Н': ['Н', 'H'],
  'к': ['к', 'k'], 'К': ['К', 'K'],
  'х': ['х', 'x'], 'Х': ['Х', 'X'],
  'с': ['с', 'c'], 'С': ['С', 'C'],
  'в': ['в', 'b'], 'В': ['В', 'B'],
  'м': ['м', 'm'], 'М': ['М', 'M']
};

const emojiMap = {
  positive: ['✨', '👍', '👏', '✅', '🌟', '💫', '🤝', '💡', '🎉', '🏆'],
  arrows: ['👉', '👇', '➡️', '⬇️', '🔽', '🔻', '➡', '⏩', '📌'],
  nature: ['🌸', '🌺', '🌷', '💐', '🌿', '🍀', '🍃', '🪻', '🌻'],
  emotions: ['😊', '😌', '😄', '🙂', '😉', '🥰', '🤗', '🤩', '😎']
};

let currentTab = 'basic';
let lastResult = '';
let copyResetTimeout = null;

const allEmojis = Object.values(emojiMap).flat();

document.addEventListener('DOMContentLoaded', () => {
  const tabButtons = Array.from(document.querySelectorAll('.tab-button'));
  const tabPanels = Array.from(document.querySelectorAll('.tab-panel'));
  const textareas = {
    basic: document.getElementById('input-basic'),
    advanced: document.getElementById('input-advanced')
  };
  const counters = {
    basic: document.querySelector('[data-counter="basic"]'),
    advanced: document.querySelector('[data-counter="advanced"]')
  };
  const replacementSlider = document.getElementById('replacementSlider');
  const replacementValue = document.getElementById('replacementValue');
  const emojiSlider = document.getElementById('emojiSlider');
  const emojiValue = document.getElementById('emojiValue');
  const generateButton = document.getElementById('generateButton');
  const regenerateButton = document.getElementById('regenerateButton');
  const copyButton = document.getElementById('copyButton');
  const postActions = document.getElementById('postActions');
  const errorMessage = document.getElementById('errorMessage');
  const resultContainer = document.getElementById('resultContainer');
  const themeToggle = document.getElementById('themeToggle');
  const donateLink = document.getElementById('donateLink');

  ensureInitialState(textareas, counters);
  restoreSliders();
  applyStoredTheme();

  tabButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const target = button.dataset.tab;
      if (target === currentTab) {
        return;
      }
      currentTab = target;
      updateTabs();
      textareas[currentTab].focus();
    });
  });

  Object.entries(textareas).forEach(([tab, textarea]) => {
    textarea.addEventListener('input', () => {
      const value = textarea.value;
      updateCharCounter(tab, value.length, counters);
      clearError(textarea, errorMessage);
      saveToStorage(getTextStorageKey(tab), value);
    });
  });

  replacementSlider.addEventListener('input', () => {
    updateReplacementLabel(replacementSlider.value, replacementValue);
    saveToStorage(STORAGE_KEYS.replacementPct, replacementSlider.value);
  });

  emojiSlider.addEventListener('input', () => {
    updateEmojiLabel(emojiSlider.value, emojiValue);
    saveToStorage(STORAGE_KEYS.emojiFrequency, emojiSlider.value);
  });

  generateButton.addEventListener('click', () => {
    const success = performGeneration({ textareas, replacementSlider, emojiSlider, resultContainer, errorMessage, counters, copyButton });
    if (success) {
      postActions.hidden = false;
      generateButton.hidden = true;
    }
  });

  regenerateButton.addEventListener('click', () => {
    const success = performGeneration({ textareas, replacementSlider, emojiSlider, resultContainer, errorMessage, counters, copyButton });
    if (success) {
      resetCopyButton(copyButton);
    }
  });

  copyButton.addEventListener('click', async () => {
    await handleCopy(copyButton, resultContainer);
  });

  resultContainer.addEventListener('click', async () => {
    await handleResultClickCopy(resultContainer, copyButton);
  });

  resultContainer.addEventListener('keydown', async (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      await handleResultClickCopy(resultContainer, copyButton);
    }
  });

  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      const success = performGeneration({ textareas, replacementSlider, emojiSlider, resultContainer, errorMessage, counters, copyButton });
      if (success) {
        postActions.hidden = false;
        generateButton.hidden = true;
      }
    }
  });

  themeToggle.addEventListener('change', () => {
    const theme = themeToggle.checked ? 'dark' : 'light';
    applyTheme(theme);
    saveToStorage(STORAGE_KEYS.theme, theme);
  });

  donateLink.addEventListener('click', (event) => {
    event.preventDefault();
    const url = 'https://www.buymeacoffee.com/';
    if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.create) {
      chrome.tabs.create({ url });
    } else {
      window.open(url, '_blank', 'noopener');
    }
  });

  function updateTabs() {
    tabButtons.forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.tab === currentTab);
      btn.setAttribute('aria-selected', String(btn.dataset.tab === currentTab));
    });
    tabPanels.forEach((panel) => {
      panel.classList.toggle('active', panel.dataset.tab === currentTab);
    });
  }

  function restoreSliders() {
    const storedReplacement = loadFromStorage(STORAGE_KEYS.replacementPct);
    const storedEmoji = loadFromStorage(STORAGE_KEYS.emojiFrequency);

    if (storedReplacement !== null) {
      replacementSlider.value = storedReplacement;
    }
    if (storedEmoji !== null) {
      emojiSlider.value = storedEmoji;
    }
    updateReplacementLabel(replacementSlider.value, replacementValue);
    updateEmojiLabel(emojiSlider.value, emojiValue);
  }

  function applyStoredTheme() {
    const storedTheme = loadFromStorage(STORAGE_KEYS.theme);
    if (storedTheme) {
      themeToggle.checked = storedTheme === 'dark';
      applyTheme(storedTheme);
      return;
    }
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    themeToggle.checked = prefersDark;
    applyTheme(prefersDark ? 'dark' : 'light');
  }
});

function ensureInitialState(textareas, counters) {
  const initialized = loadFromStorage(STORAGE_KEYS.initialized);
  if (!initialized) {
    saveToStorage(getTextStorageKey('basic'), INITIAL_TEXT.basic);
    saveToStorage(getTextStorageKey('advanced'), INITIAL_TEXT.advanced);
    saveToStorage(STORAGE_KEYS.initialized, 'true');
  }

  ['basic', 'advanced'].forEach((tab) => {
    const textarea = textareas[tab];
    const storedValue = loadFromStorage(getTextStorageKey(tab));
    if (storedValue !== null) {
      textarea.value = storedValue;
    }
    updateCharCounter(tab, textarea.value.length, counters);
  });
}

function performGeneration({ textareas, replacementSlider, emojiSlider, resultContainer, errorMessage, counters, copyButton }) {
  const textarea = textareas[currentTab];
  const rawText = textarea.value;
  const trimmed = rawText.trim();

  if (!trimmed) {
    showError('Введите текст до 2000 символов.', textarea, errorMessage);
    return false;
  }

  if (trimmed.length > MAX_LENGTH) {
    showError('Слишком длинный текст (макс. 2000).', textarea, errorMessage);
    return false;
  }

  clearError(textarea, errorMessage);

  const replacementPct = Number(replacementSlider.value) || 0;
  const emojiFrequency = Number(emojiSlider.value) || 0;

  try {
    const expanded = currentTab === 'advanced' ? expandTemplates(rawText) : rawText;
    const randomized = randomizeString(expanded, replacementPct);
    const withEmoji = randomizeEmoji(randomized, emojiFrequency);
    updateResult(withEmoji, resultContainer);
    lastResult = withEmoji;
    resetCopyButton(copyButton);
    return true;
  } catch (error) {
    console.error(error);
    showError('Упс! Не получилось с первого раза — попробуйте ещё раз.', textarea, errorMessage);
    return false;
  }
}

function randomizeChar(char, pct) {
  const options = charMap[char];
  if (!options || pct <= 0) {
    return char;
  }
  const chance = Math.random() * 100;
  if (chance > pct) {
    return char;
  }
  const alternative = pickAlternative(options, char);
  return alternative ?? char;
}

function pickAlternative(options, original) {
  if (options.length <= 1) {
    return options[0];
  }
  const filtered = options.filter((option) => option !== original);
  const pool = filtered.length ? filtered : options;
  return pool[Math.floor(Math.random() * pool.length)];
}

function randomizeString(text, pct) {
  if (pct <= 0) {
    return text;
  }
  const urlPattern = /(https?:\/\/[^\s]+)/gi;
  let lastIndex = 0;
  let result = '';
  let match;

  while ((match = urlPattern.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;
    result += transformSegment(text.slice(lastIndex, start), pct);
    result += match[0];
    lastIndex = end;
  }

  result += transformSegment(text.slice(lastIndex), pct);
  return result;
}

function transformSegment(segment, pct) {
  let transformed = '';
  for (const char of segment) {
    transformed += randomizeChar(char, pct);
  }
  return transformed;
}

function randomizeEmoji(text, frequency) {
  if (frequency <= 0) {
    return text;
  }
  const tokens = text.split(/(\s+)/);
  let wordCount = 0;
  let nextInsert = frequency;
  let lastEmojiUsed = '';

  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (token.trim() === '') {
      continue;
    }
    if (/^https?:\/\//i.test(token.trim())) {
      continue;
    }
    wordCount += 1;
    if (wordCount >= nextInsert) {
      const emoji = pickEmoji(lastEmojiUsed);
      lastEmojiUsed = emoji;
      if (!tokens[i].endsWith(' ')) {
        tokens[i] = tokens[i] + ' ';
      }
      tokens[i] += emoji;
      nextInsert = wordCount + frequency;
    }
  }

  return tokens.join('');
}

function pickEmoji(lastEmoji) {
  if (!allEmojis.length) {
    return '';
  }
  let emoji = '';
  let attempts = 0;
  while (attempts < 5) {
    emoji = allEmojis[Math.floor(Math.random() * allEmojis.length)];
    if (emoji !== lastEmoji) {
      break;
    }
    attempts += 1;
  }
  return emoji || allEmojis[0];
}

function expandTemplates(text) {
  const pattern = /\[([^\[\]]+?)\]/g;
  return text.replace(pattern, (_, group) => {
    const variants = group.split('|').map((part) => part.trim()).filter(Boolean);
    if (!variants.length) {
      return _;
    }
    const choice = variants[Math.floor(Math.random() * variants.length)];
    return choice;
  });
}

function updateResult(text, container) {
  container.textContent = text;
  container.classList.toggle('has-content', Boolean(text.trim()));
}

function showError(message, textarea, errorElement) {
  errorElement.textContent = message;
  errorElement.classList.add('visible');
  textarea.classList.add('error');
  textarea.focus();
}

function clearError(textarea, errorElement) {
  if (errorElement) {
    errorElement.textContent = '';
    errorElement.classList.remove('visible');
  }
  textarea.classList.remove('error');
}

async function handleCopy(copyButton, resultContainer) {
  if (!lastResult) {
    return;
  }
  const success = await copyTextToClipboard(lastResult);
  if (success) {
    indicateCopy(copyButton, resultContainer);
  }
}

async function handleResultClickCopy(resultContainer, copyButton) {
  if (!lastResult) {
    return;
  }
  const success = await copyTextToClipboard(lastResult);
  if (success) {
    indicateCopy(copyButton, resultContainer);
  }
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (error) {
      console.error('Clipboard API copy failed', error);
    }
  }
  return legacyCopy(text);
}

function legacyCopy(text) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'absolute';
  textarea.style.left = '-9999px';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  const selection = document.getSelection();
  const selectedRange = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
  textarea.select();
  let success = false;
  try {
    success = document.execCommand('copy');
  } catch (error) {
    console.error('execCommand copy failed', error);
    success = false;
  }
  document.body.removeChild(textarea);
  if (selectedRange && selection) {
    selection.removeAllRanges();
    selection.addRange(selectedRange);
  }
  return success;
}

function indicateCopy(copyButton, resultContainer) {
  if (copyButton) {
    copyButton.textContent = 'Скопировано!';
  }
  resultContainer.classList.add('copied');
  if (copyResetTimeout) {
    clearTimeout(copyResetTimeout);
  }
  copyResetTimeout = setTimeout(() => {
    resetCopyButton(copyButton);
    resultContainer.classList.remove('copied');
  }, 1500);
}

function resetCopyButton(copyButton) {
  if (copyButton) {
    copyButton.textContent = 'Скопировать';
  }
}

function updateCharCounter(tab, length, counters) {
  const counter = counters[tab];
  if (counter) {
    counter.textContent = `${Math.min(length, MAX_LENGTH)}/${MAX_LENGTH}`;
  }
}

function updateReplacementLabel(value, label) {
  label.textContent = `${value}%`;
}

function updateEmojiLabel(value, label) {
  const numeric = Number(value);
  if (numeric <= 0) {
    label.textContent = 'Без эмодзи';
  } else if (numeric === 1) {
    label.textContent = 'Каждое слово';
  } else {
    label.textContent = `1/${numeric} слов`;
  }
}

function getTextStorageKey(tab) {
  return tab === 'advanced' ? STORAGE_KEYS.advancedText : STORAGE_KEYS.basicText;
}

function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (error) {
    console.error('localStorage save failed', error);
  }
}

function loadFromStorage(key) {
  try {
    const value = localStorage.getItem(key);
    return value === null ? null : value;
  } catch (error) {
    console.error('localStorage load failed', error);
    return null;
  }
}

function applyTheme(theme) {
  if (theme === 'dark') {
    document.body.classList.add('dark-theme');
    document.body.classList.remove('light-theme');
  } else {
    document.body.classList.remove('dark-theme');
    document.body.classList.add('light-theme');
  }
}
