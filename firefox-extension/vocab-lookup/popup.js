const DICTIONARY_API_BASE = "https://api.dictionaryapi.dev";
const TRANSLATION_API_BASE = "https://api.mymemory.translated.net";

const elements = {
  term: document.getElementById("term"),
  meaning: document.getElementById("meaning"),
  exampleSentence: document.getElementById("exampleSentence"),
  lookupSummary: document.getElementById("lookupSummary"),
  summaryTerm: document.getElementById("summaryTerm"),
  summaryPhonetic: document.getElementById("summaryPhonetic"),
  savedState: document.getElementById("savedState"),
  translationResult: document.getElementById("translationResult"),
  definitionResult: document.getElementById("definitionResult"),
  lexicalDetails: document.getElementById("lexicalDetails"),
  partOfSpeech: document.getElementById("partOfSpeech"),
  phonetic: document.getElementById("phonetic"),
  definitionEnglish: document.getElementById("definitionEnglish"),
  playAudio: document.getElementById("playAudio"),
  playSelectedAudio: document.getElementById("playSelectedAudio"),
  status: document.getElementById("status"),
  refreshSelection: document.getElementById("refreshSelection"),
  lookupWord: document.getElementById("lookupWord"),
  saveWord: document.getElementById("saveWord"),
};

let currentAudioUrl = "";
let currentPronunciationText = "";
let currentLookupResult = null;
let currentAudio = null;
let lookupInFlight = false;

function setStatus(message) {
  elements.status.textContent = message;
}

function cleanText(value) {
  return (value || "").replace(/\s+/g, " ").trim();
}

function normalizeLocalTerm(value) {
  return cleanText(value).toLowerCase();
}

function statusLabel(value) {
  return value ? value.replace(/_/g, " ") : "";
}

async function getLocalVocabulary() {
  const data = await browser.storage.local.get("localVocabulary");
  return data.localVocabulary && typeof data.localVocabulary === "object"
    ? data.localVocabulary
    : {};
}

async function getLocalVocabularyEntry(term) {
  const normalizedTerm = normalizeLocalTerm(term);
  if (!normalizedTerm) {
    return null;
  }
  const localVocabulary = await getLocalVocabulary();
  return localVocabulary[normalizedTerm] || null;
}

async function saveLocalVocabularyEntry(result, fallbackTerm) {
  const now = new Date().toISOString();
  const term = cleanText(result?.normalized_term || result?.term || fallbackTerm);
  const normalizedTerm = normalizeLocalTerm(term);
  if (!normalizedTerm) {
    throw new Error("No word selected.");
  }

  const localVocabulary = await getLocalVocabulary();
  const existing = localVocabulary[normalizedTerm] || {};
  const entry = {
    ...existing,
    vocab_id: existing.vocab_id || `local-${Date.now()}`,
    term,
    normalized_term: normalizedTerm,
    meaning: cleanText(result?.meaning) || cleanText(elements.meaning.value) || "",
    translation_vi: cleanText(result?.translation_vi) || "",
    definition_en: cleanText(result?.definition_en) || "",
    example_sentence:
      cleanText(result?.example_sentence) ||
      cleanText(elements.exampleSentence.value) ||
      "",
    part_of_speech: cleanText(result?.part_of_speech) || "",
    phonetic: cleanText(result?.phonetic) || "",
    audio_url: cleanText(result?.audio_url) || "",
    dictionary_provider: cleanText(result?.dictionary_provider) || "",
    translation_provider: cleanText(result?.translation_provider) || "",
    source_type: "firefox_local",
    saved_status: "local_only",
    created_at: existing.created_at || now,
    updated_at: now,
  };
  localVocabulary[normalizedTerm] = entry;
  await browser.storage.local.set({ localVocabulary });
  return entry;
}

function firstDictionaryResult(payload) {
  const entry = Array.isArray(payload) ? payload[0] : null;
  if (!entry) {
    return {};
  }

  let phonetic = cleanText(entry.phonetic);
  let audioUrl = "";
  for (const item of entry.phonetics || []) {
    phonetic = phonetic || cleanText(item.text);
    audioUrl = audioUrl || cleanText(item.audio);
    if (phonetic && audioUrl) {
      break;
    }
  }
  if (audioUrl.startsWith("//")) {
    audioUrl = `https:${audioUrl}`;
  }

  for (const meaning of entry.meanings || []) {
    const definition = (meaning.definitions || []).find((item) =>
      cleanText(item.definition),
    );
    if (definition) {
      return {
        definition_en: cleanText(definition.definition),
        example_sentence: cleanText(definition.example),
        part_of_speech: cleanText(meaning.partOfSpeech),
        phonetic,
        audio_url: audioUrl,
      };
    }
  }

  return {
    phonetic,
    audio_url: audioUrl,
  };
}

function translationResult(payload) {
  return cleanText(payload?.responseData?.translatedText);
}

async function directLookup(term, contextSentence = "") {
  const normalizedTerm = normalizeLocalTerm(term);
  let dictionaryData = {};
  let translationVi = "";

  try {
    const response = await fetch(
      `${DICTIONARY_API_BASE}/api/v2/entries/en/${encodeURIComponent(normalizedTerm)}`,
    );
    if (response.ok) {
      dictionaryData = firstDictionaryResult(await response.json());
    }
  } catch {
    dictionaryData = {};
  }

  try {
    const params = new URLSearchParams({
      q: term,
      langpair: "en|vi",
    });
    const response = await fetch(`${TRANSLATION_API_BASE}/get?${params}`);
    if (response.ok) {
      translationVi = translationResult(await response.json());
    }
  } catch {
    translationVi = "";
  }

  return {
    term,
    normalized_term: normalizedTerm,
    meaning: translationVi || dictionaryData.definition_en || "",
    translation_vi: translationVi,
    definition_en: dictionaryData.definition_en || "",
    example_sentence: dictionaryData.example_sentence || contextSentence,
    part_of_speech: dictionaryData.part_of_speech || "",
    phonetic: dictionaryData.phonetic || "",
    audio_url: dictionaryData.audio_url || "",
    dictionary_provider: dictionaryData.definition_en ? "dictionaryapi.dev" : "",
    translation_provider: translationVi ? "mymemory" : "",
    already_saved: false,
    saved_vocab_id: null,
    saved_status: null,
  };
}

function resetLookupUi() {
  currentLookupResult = null;
  currentAudioUrl = "";
  currentPronunciationText = "";
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  window.speechSynthesis?.cancel();
  elements.lookupSummary.hidden = true;
  elements.summaryTerm.textContent = "";
  elements.summaryPhonetic.textContent = "";
  elements.savedState.textContent = "";
  elements.savedState.classList.remove("is-new", "is-saved");
  elements.translationResult.textContent = "";
  elements.definitionResult.textContent = "";
  elements.partOfSpeech.textContent = "";
  elements.phonetic.textContent = "";
  elements.definitionEnglish.textContent = "";
  elements.lexicalDetails.hidden = true;
  elements.playAudio.hidden = true;
  elements.saveWord.hidden = false;
  elements.saveWord.disabled = false;
}

function renderLookupResult(result, fallbackTerm) {
  currentLookupResult = result;
  currentAudioUrl = result.audio_url || "";
  const term = result.normalized_term || result.term || fallbackTerm;
  currentPronunciationText = term;
  const vietnameseMeaning = result.translation_vi || result.meaning || "";
  const definition = result.definition_en || "";
  const savedStatus = statusLabel(result.saved_status);

  elements.lookupSummary.hidden = false;
  elements.summaryTerm.textContent = term;
  elements.summaryPhonetic.textContent = result.phonetic || "";
  elements.translationResult.textContent =
    vietnameseMeaning || "No Vietnamese meaning found yet.";
  elements.definitionResult.textContent = definition;
  elements.definitionResult.hidden = !definition;

  elements.savedState.classList.toggle("is-saved", result.already_saved);
  elements.savedState.classList.toggle("is-new", !result.already_saved);
  elements.savedState.textContent = result.already_saved
    ? `Saved: ${savedStatus || "local only"}`
    : "Not saved yet";

  elements.term.value = term;
  if (vietnameseMeaning) {
    elements.meaning.value = vietnameseMeaning;
  }
  if (result.example_sentence) {
    elements.exampleSentence.value = result.example_sentence;
  }

  elements.partOfSpeech.textContent = result.part_of_speech || "";
  elements.partOfSpeech.hidden = !result.part_of_speech;
  elements.phonetic.textContent = result.phonetic || "";
  elements.definitionEnglish.textContent = definition;
  elements.playAudio.hidden = !term;
  elements.playAudio.title = currentAudioUrl
    ? "Play dictionary audio"
    : "Play browser pronunciation";
  elements.lexicalDetails.hidden = !(
    result.part_of_speech ||
    result.phonetic ||
    definition
  );
  elements.saveWord.hidden = Boolean(result.already_saved);
}

async function getActiveTabSelection() {
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  if (!tab?.id) {
    return null;
  }

  try {
    return await browser.tabs.sendMessage(tab.id, {
      type: "SLSS_GET_SELECTION",
    });
  } catch {
    try {
      const results = await browser.tabs.executeScript(tab.id, {
        code: `(() => {
          const clamp = (value, maxLength) => {
            const normalized = (value || "").replace(/\\s+/g, " ").trim();
            return normalized.length > maxLength
              ? normalized.slice(0, maxLength - 1) + "..."
              : normalized;
          };
          const selection = window.getSelection();
          const term = clamp(selection ? selection.toString() : "", 255);
          let contextSentence = "";
          const anchorNode = selection && selection.anchorNode;
          const element = anchorNode && anchorNode.nodeType === Node.TEXT_NODE
            ? anchorNode.parentElement
            : anchorNode;
          if (element && element.closest) {
            const container = element.closest("p, li, article, section, div");
            contextSentence = clamp((container && container.textContent) || term, 700);
          }
          return {
            term,
            contextSentence,
            pageUrl: window.location.href,
            pageTitle: document.title,
          };
        })();`,
      });
      return results?.[0] || null;
    } catch {
      return null;
    }
  }
}

async function loadSelection({ autoLookup = false } = {}) {
  const [fromTab, stored] = await Promise.all([
    getActiveTabSelection(),
    browser.storage.local.get("pendingSelection"),
  ]);
  const selection = fromTab?.term ? fromTab : stored.pendingSelection;

  if (!selection?.term) {
    setStatus("Select a word on a page, then open this popup.");
    return false;
  }

  elements.term.value = selection.term || "";
  elements.meaning.value = "";
  elements.exampleSentence.value = selection.contextSentence || "";
  resetLookupUi();
  currentPronunciationText = selection.term || "";
  await browser.storage.local.set({ pendingSelection: selection });
  await browser.browserAction.setBadgeText({ text: "" });
  setStatus("Selection loaded.");
  if (autoLookup) {
    await lookupWord();
  }
  return true;
}

async function lookupWord() {
  if (lookupInFlight) {
    return;
  }
  const term = cleanText(elements.term.value);
  if (!term) {
    setStatus("No word selected.");
    return;
  }

  lookupInFlight = true;
  elements.lookupWord.disabled = true;
  setStatus("Looking up...");
  try {
    const result = await directLookup(term, elements.exampleSentence.value);
    const localEntry = await getLocalVocabularyEntry(term);
    renderLookupResult(
      localEntry
        ? {
            ...result,
            already_saved: true,
            saved_vocab_id: localEntry.vocab_id,
            saved_status: "local_only",
          }
        : result,
      term,
    );
    setStatus(localEntry ? "Already saved locally." : "Lookup ready.");
  } catch (error) {
    setStatus(error.message || "Lookup failed.");
  } finally {
    lookupInFlight = false;
    elements.lookupWord.disabled = false;
  }
}

async function saveWord() {
  const term = cleanText(elements.term.value);
  if (!term) {
    setStatus("No word selected.");
    return;
  }

  elements.saveWord.disabled = true;
  setStatus("Saving locally...");
  try {
    const localEntry = await saveLocalVocabularyEntry(
      currentLookupResult || {
        term,
        normalized_term: normalizeLocalTerm(term),
        meaning: elements.meaning.value,
        example_sentence: elements.exampleSentence.value,
      },
      term,
    );
    currentLookupResult = {
      ...(currentLookupResult || {}),
      ...localEntry,
      already_saved: true,
      saved_vocab_id: localEntry.vocab_id,
      saved_status: "local_only",
    };
    renderLookupResult(currentLookupResult, localEntry.term);
    setStatus(`Saved locally: ${localEntry.term}`);
  } catch (error) {
    setStatus(error.message || "Local save failed.");
  } finally {
    elements.saveWord.disabled = false;
  }
}

async function playPronunciation() {
  const textToSpeak = currentPronunciationText || cleanText(elements.term.value);
  if (!currentAudioUrl && !textToSpeak) {
    return;
  }
  if (currentAudio) {
    currentAudio.pause();
  }
  window.speechSynthesis?.cancel();
  if (currentAudioUrl) {
    currentAudio = new Audio(currentAudioUrl);
    await currentAudio.play();
    return;
  }

  if ("SpeechSynthesisUtterance" in window && window.speechSynthesis) {
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = "en-US";
    utterance.rate = 0.85;
    window.speechSynthesis.speak(utterance);
  }
}

elements.refreshSelection.addEventListener("click", () =>
  loadSelection({ autoLookup: true }),
);
elements.lookupWord.addEventListener("click", lookupWord);
elements.saveWord.addEventListener("click", saveWord);
elements.playAudio.addEventListener("click", playPronunciation);
elements.playSelectedAudio.addEventListener("click", playPronunciation);
elements.term.addEventListener("input", () => {
  currentPronunciationText = cleanText(elements.term.value);
  currentAudioUrl = "";
});

setStatus("Local mode ready.");
loadSelection({ autoLookup: true }).catch(() =>
  setStatus("Extension could not initialize."),
);
