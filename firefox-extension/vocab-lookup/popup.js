const DEFAULT_API_BASE = "http://localhost:8080";

const elements = {
  apiBase: document.getElementById("apiBase"),
  accessToken: document.getElementById("accessToken"),
  term: document.getElementById("term"),
  meaning: document.getElementById("meaning"),
  exampleSentence: document.getElementById("exampleSentence"),
  lexicalDetails: document.getElementById("lexicalDetails"),
  partOfSpeech: document.getElementById("partOfSpeech"),
  phonetic: document.getElementById("phonetic"),
  definitionEnglish: document.getElementById("definitionEnglish"),
  playAudio: document.getElementById("playAudio"),
  status: document.getElementById("status"),
  saveSettings: document.getElementById("saveSettings"),
  refreshSelection: document.getElementById("refreshSelection"),
  lookupWord: document.getElementById("lookupWord"),
  saveWord: document.getElementById("saveWord"),
};

let currentAudioUrl = "";

function setStatus(message) {
  elements.status.textContent = message;
}

function normalizeApiBase(value) {
  const trimmed = (value || DEFAULT_API_BASE).trim();
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

async function loadSettings() {
  const data = await browser.storage.local.get(["apiBase", "accessToken"]);
  elements.apiBase.value = data.apiBase || DEFAULT_API_BASE;
  elements.accessToken.value = data.accessToken || "";
}

async function saveSettings() {
  const apiBase = normalizeApiBase(elements.apiBase.value);
  const accessToken = elements.accessToken.value.trim();
  await browser.storage.local.set({ apiBase, accessToken });
  elements.apiBase.value = apiBase;
  setStatus("Settings saved.");
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
    return null;
  }
}

async function loadSelection() {
  const [fromTab, stored] = await Promise.all([
    getActiveTabSelection(),
    browser.storage.local.get("pendingSelection"),
  ]);
  const selection = fromTab?.term ? fromTab : stored.pendingSelection;

  if (!selection?.term) {
    setStatus("Select a word on the page, then open this popup again.");
    return;
  }

  elements.term.value = selection.term || "";
  elements.exampleSentence.value = selection.contextSentence || "";
  await browser.storage.local.set({ pendingSelection: selection });
  await browser.browserAction.setBadgeText({ text: "" });
  setStatus("Selection loaded.");
}

async function apiFetch(path, body) {
  const { apiBase, accessToken } = await browser.storage.local.get([
    "apiBase",
    "accessToken",
  ]);
  const token = accessToken || elements.accessToken.value.trim();
  if (!token) {
    throw new Error("Paste your web app access token first.");
  }

  const response = await fetch(`${normalizeApiBase(apiBase)}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }

  return response.json();
}

async function lookupWord() {
  const term = elements.term.value.trim();
  if (!term) {
    setStatus("No word selected.");
    return;
  }

  elements.lookupWord.disabled = true;
  setStatus("Looking up...");
  try {
    const stored = await browser.storage.local.get("pendingSelection");
    const result = await apiFetch("/api/v1/vocab/lookup", {
      term,
      context_sentence: elements.exampleSentence.value.trim(),
      page_url: stored.pendingSelection?.pageUrl || "",
      page_title: stored.pendingSelection?.pageTitle || "",
    });

    elements.term.value = result.normalized_term || result.term || term;
    if (result.meaning) {
      elements.meaning.value = result.meaning;
    }
    if (result.example_sentence) {
      elements.exampleSentence.value = result.example_sentence;
    }
    elements.partOfSpeech.textContent = result.part_of_speech || "";
    elements.partOfSpeech.hidden = !result.part_of_speech;
    elements.phonetic.textContent = result.phonetic || "";
    elements.definitionEnglish.textContent = result.definition_en || "";
    currentAudioUrl = result.audio_url || "";
    elements.playAudio.hidden = !currentAudioUrl;
    elements.lexicalDetails.hidden = !(
      result.part_of_speech ||
      result.phonetic ||
      result.definition_en ||
      currentAudioUrl
    );
    setStatus(result.already_saved ? "Already saved." : "Lookup ready.");
  } catch (error) {
    setStatus(error.message || "Lookup failed.");
  } finally {
    elements.lookupWord.disabled = false;
  }
}

async function saveWord() {
  const term = elements.term.value.trim();
  if (!term) {
    setStatus("No word selected.");
    return;
  }

  elements.saveWord.disabled = true;
  setStatus("Saving...");
  try {
    const stored = await browser.storage.local.get("pendingSelection");
    const entry = await apiFetch("/api/v1/vocab/capture", {
      term,
      meaning: elements.meaning.value.trim(),
      example_sentence: elements.exampleSentence.value.trim(),
      context_sentence: stored.pendingSelection?.contextSentence || "",
      page_url: stored.pendingSelection?.pageUrl || "",
      page_title: stored.pendingSelection?.pageTitle || "",
    });
    setStatus(`Saved: ${entry.term}`);
  } catch (error) {
    setStatus(error.message || "Save failed.");
  } finally {
    elements.saveWord.disabled = false;
  }
}

async function playPronunciation() {
  if (!currentAudioUrl) {
    return;
  }
  await browser.tabs.create({ url: currentAudioUrl, active: false });
}

elements.saveSettings.addEventListener("click", saveSettings);
elements.refreshSelection.addEventListener("click", loadSelection);
elements.lookupWord.addEventListener("click", lookupWord);
elements.saveWord.addEventListener("click", saveWord);
elements.playAudio.addEventListener("click", playPronunciation);

loadSettings()
  .then(loadSelection)
  .catch(() => setStatus("Extension could not initialize."));
