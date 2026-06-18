function clampText(value, maxLength) {
  const normalized = (value || "").replace(/\s+/g, " ").trim();
  return normalized.length > maxLength
    ? `${normalized.slice(0, maxLength - 1)}...`
    : normalized;
}

function getContextSentence(selection) {
  const anchorNode = selection.anchorNode;
  const element =
    anchorNode?.nodeType === Node.TEXT_NODE
      ? anchorNode.parentElement
      : anchorNode;

  if (!element || !("closest" in element)) {
    return "";
  }

  const container = element.closest("p, li, article, section, div");
  return clampText(container?.textContent || selection.toString(), 700);
}

function getSelectionPayload() {
  const selection = window.getSelection();
  const selectedText = clampText(selection?.toString() || "", 255);

  return {
    term: selectedText,
    contextSentence: selection && selectedText ? getContextSentence(selection) : "",
    pageUrl: window.location.href,
    pageTitle: document.title,
  };
}

browser.runtime.onMessage.addListener((message) => {
  if (message?.type !== "SLSS_GET_SELECTION") {
    return undefined;
  }

  return Promise.resolve(getSelectionPayload());
});
