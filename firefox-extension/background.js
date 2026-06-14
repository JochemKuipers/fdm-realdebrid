const NATIVE_HOST = "com.fdmrealdebrid.magnet";
const ICON = "icons/icon-48.png";

let enabled = true;

browser.storage.local.get("enabled").then(function (stored) {
  if (typeof stored.enabled === "boolean") {
    enabled = stored.enabled;
  }
  updateActionTitle();
});

browser.action.onClicked.addListener(function () {
  enabled = !enabled;
  browser.storage.local.set({ enabled: enabled });
  updateActionTitle();
  notify(
    enabled ? "Magnet capture enabled" : "Magnet capture disabled",
    enabled
      ? "Magnet links will be sent to FDM."
      : "Magnet links will use the browser default handler.",
  );
});

function updateActionTitle() {
  browser.action.setTitle({
    title: enabled
      ? "Real-Debrid magnets for FDM (enabled)"
      : "Real-Debrid magnets for FDM (disabled)",
  });
}

function notify(title, message) {
  browser.notifications.create({
    type: "basic",
    iconUrl: ICON,
    title: title,
    message: message,
  });
}

function showError(error) {
  notify(
    "FDM magnet handoff failed",
    String(error && error.message ? error.message : error),
  );
}

function sendMagnetToFdm(magnetUrl) {
  return browser.runtime
    .sendNativeMessage(NATIVE_HOST, { url: magnetUrl })
    .then(function (response) {
      if (!response || !response.success) {
        throw new Error((response && response.error) || "Native host failed");
      }
      notify(
        "Sent to Real-Debrid",
        response.message ||
          "FDM will add the download(s) when Real-Debrid finishes (this can take several minutes).",
      );
      return response;
    });
}

browser.runtime.onMessage.addListener(function (message, sender, sendResponse) {
  if (message.type !== "magnet" || !message.url) {
    return false;
  }

  if (!enabled) {
    sendResponse({ success: false, skipped: true });
    return false;
  }

  sendMagnetToFdm(message.url)
    .then(function () {
      sendResponse({ success: true });
    })
    .catch(function (error) {
      sendResponse({ success: false, error: error.message });
      showError(error);
    });

  return true;
});

browser.contextMenus.create({
  id: "send-magnet-fdm",
  title: "Send magnet to FDM (Real-Debrid)",
  contexts: ["link"],
  targetUrlPatterns: ["magnet:*"],
});

browser.contextMenus.onClicked.addListener(function (info) {
  if (info.menuItemId === "send-magnet-fdm" && info.linkUrl) {
    sendMagnetToFdm(info.linkUrl).catch(showError);
  }
});
