const MENU_ID = "slss-capture-selection";

async function getSelectionFromTab(tab) {
  if (!tab?.id) {
    return null;
  }

  try {
    return await browser.tabs.sendMessage(tab.id, {
      type: "SLSS_GET_SELECTION",
    });
  } catch {
    return {
      term: "",
      contextSentence: "",
      pageUrl: tab.url ?? "",
      pageTitle: tab.title ?? "",
    };
  }
}

browser.runtime.onInstalled.addListener(() => {
  browser.contextMenus.create({
    id: MENU_ID,
    title: "Capture word in SLSS",
    contexts: ["selection"],
  });
});

browser.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID) {
    return;
  }

  const fromTab = await getSelectionFromTab(tab);
  const selectedText = (info.selectionText || fromTab?.term || "").trim();
  const payload = {
    term: selectedText,
    contextSentence: fromTab?.contextSentence || "",
    pageUrl: tab?.url || fromTab?.pageUrl || "",
    pageTitle: tab?.title || fromTab?.pageTitle || "",
    capturedAt: new Date().toISOString(),
  };

  await browser.storage.local.set({ pendingSelection: payload });
  await browser.browserAction.setBadgeText({ text: selectedText ? "1" : "" });
  await browser.browserAction.setBadgeBackgroundColor({ color: "#0891b2" });
});
