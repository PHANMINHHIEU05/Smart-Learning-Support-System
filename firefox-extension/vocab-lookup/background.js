const DICTIONARY_API_BASE = "https://api.dictionaryapi.dev";
const TRANSLATION_API_BASE = "https://api.mymemory.translated.net";
const SPRING_API_BASE = "http://localhost:8080";
const MENU_PREPARE_ID = "slss-prepare-selection";
const MENU_SAVE_ID = "slss-save-selection";

function cleanText(value) {
  return (value || "").replace(/\s+/g, " ").trim();
}

function normalizeLocalTerm(value) {
  return cleanText(value).toLowerCase();
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
  };
}

async function getLocalVocabulary() {
  const data = await browser.storage.local.get("localVocabulary");
  return data.localVocabulary && typeof data.localVocabulary === "object"
    ? data.localVocabulary
    : {};
}

async function saveLocalVocabularyEntry(payload, lookupResult = null) {
  const now = new Date().toISOString();
  const term = cleanText(
    lookupResult?.normalized_term || lookupResult?.term || payload.term,
  );
  const normalizedTerm = normalizeLocalTerm(term);
  if (!normalizedTerm) {
    throw new Error("No selected word found.");
  }

  const localVocabulary = await getLocalVocabulary();
  const existing = localVocabulary[normalizedTerm] || {};
  const entry = {
    ...existing,
    vocab_id: existing.vocab_id || `local-${Date.now()}`,
    term,
    normalized_term: normalizedTerm,
    meaning: cleanText(lookupResult?.meaning) || "",
    translation_vi: cleanText(lookupResult?.translation_vi) || "",
    definition_en: cleanText(lookupResult?.definition_en) || "",
    example_sentence:
      cleanText(lookupResult?.example_sentence) ||
      cleanText(payload.contextSentence) ||
      "",
    part_of_speech: cleanText(lookupResult?.part_of_speech) || "",
    phonetic: cleanText(lookupResult?.phonetic) || "",
    audio_url: cleanText(lookupResult?.audio_url) || "",
    dictionary_provider: cleanText(lookupResult?.dictionary_provider) || "",
    translation_provider: cleanText(lookupResult?.translation_provider) || "",
    source_type: "firefox_local",
    source_ref: cleanText(payload.pageUrl || payload.pageTitle) || "",
    saved_status: "local_only",
    created_at: existing.created_at || now,
    updated_at: now,
  };
  localVocabulary[normalizedTerm] = entry;
  await browser.storage.local.set({ localVocabulary });
  return entry;
}

async function savePersonalWebVocabularyEntry(payload, lookupResult = null) {
  const term = cleanText(
    lookupResult?.normalized_term || lookupResult?.term || payload.term,
  );
  if (!term) {
    throw new Error("No selected word found.");
  }

  const response = await fetch(`${SPRING_API_BASE}/api/v1/vocab/personal/capture`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      term,
      meaning: cleanText(lookupResult?.meaning) || "",
      translation_vi: cleanText(lookupResult?.translation_vi) || "",
      definition_en: cleanText(lookupResult?.definition_en) || "",
      example_sentence:
        cleanText(lookupResult?.example_sentence) ||
        cleanText(payload.contextSentence) ||
        "",
      part_of_speech: cleanText(lookupResult?.part_of_speech) || "",
      phonetic: cleanText(lookupResult?.phonetic) || "",
      audio_url: cleanText(lookupResult?.audio_url) || "",
      dictionary_provider: cleanText(lookupResult?.dictionary_provider) || "",
      translation_provider: cleanText(lookupResult?.translation_provider) || "",
      context_sentence: cleanText(payload.contextSentence) || "",
      page_url: cleanText(payload.pageUrl) || "",
      page_title: cleanText(payload.pageTitle) || "Firefox Vocabulary Extension",
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Spring save failed with ${response.status}`);
  }

  return response.json();
}

async function setBadge(text, color = "#0891b2", clearAfterMs = 0) {
  await browser.browserAction.setBadgeText({ text });
  await browser.browserAction.setBadgeBackgroundColor({ color });
  if (clearAfterMs > 0) {
    setTimeout(() => {
      browser.browserAction.setBadgeText({ text: "" });
    }, clearAfterMs);
  }
}

async function setLastStatus(message, type = "info") {
  await browser.storage.local.set({
    lastBackgroundStatus: {
      message,
      type,
      updatedAt: new Date().toISOString(),
    },
  });
}

async function getSelectionFromTab(tab) {
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
      return {
        term: "",
        contextSentence: "",
        pageUrl: tab.url ?? "",
        pageTitle: tab.title ?? "",
      };
    }
  }
}

async function getSelectionPayload(info, tab) {
  const fromTab = await getSelectionFromTab(tab);
  const selectedText = (info.selectionText || fromTab?.term || "").trim();
  return {
    term: selectedText,
    contextSentence: fromTab?.contextSentence || "",
    pageUrl: tab?.url || fromTab?.pageUrl || "",
    pageTitle: tab?.title || fromTab?.pageTitle || "",
    capturedAt: new Date().toISOString(),
  };
}

async function prepareSelection(info, tab) {
  const payload = await getSelectionPayload(info, tab);
  await browser.storage.local.set({ pendingSelection: payload });
  await setBadge(payload.term ? "1" : "", "#0891b2");
  await setLastStatus(
    payload.term
      ? `Loaded "${payload.term}" into the popup.`
      : "No selected word found.",
    payload.term ? "info" : "error",
  );
}

async function saveSelectionNow(info, tab) {
  const payload = await getSelectionPayload(info, tab);
  await browser.storage.local.set({ pendingSelection: payload });
  if (!payload.term) {
    await setBadge("!", "#e11d48", 3500);
    await setLastStatus("No selected word found.", "error");
    return;
  }

  await setBadge("...", "#0891b2");
  await setLastStatus(`Saving "${payload.term}" to web...`, "info");

  try {
    const lookupResult = await directLookup(payload.term, payload.contextSentence);
    try {
      const entry = await savePersonalWebVocabularyEntry(payload, lookupResult);
      await saveLocalVocabularyEntry(payload, {
        ...lookupResult,
        ...entry,
        normalized_term: entry.term,
        saved_status: entry.status,
      });
      await setBadge("WEB", "#16a34a", 4500);
      await setLastStatus(`Saved to web "${entry.term}".`, "success");
    } catch {
      const entry = await saveLocalVocabularyEntry(payload, lookupResult);
      await setBadge("LOCAL", "#16a34a", 4500);
      await setLastStatus(`Spring unavailable, saved locally "${entry.term}".`, "success");
    }
  } catch (error) {
    await setBadge("!", "#e11d48", 6000);
    await setLastStatus(error.message || "Local save failed.", "error");
  }
}

async function createContextMenus() {
  await browser.contextMenus.removeAll();
  browser.contextMenus.create({
    id: MENU_PREPARE_ID,
    title: "SLSS: Open selected word in popup",
    contexts: ["selection"],
  });
  browser.contextMenus.create({
    id: MENU_SAVE_ID,
    title: "SLSS: Save selected word",
    contexts: ["selection"],
  });
}

browser.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === MENU_PREPARE_ID) {
    await prepareSelection(info, tab);
  }
  if (info.menuItemId === MENU_SAVE_ID) {
    await saveSelectionNow(info, tab);
  }
});

createContextMenus().catch(() => undefined);
