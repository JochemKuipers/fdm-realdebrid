const NATIVE_HOST = "com.fdmrealdebrid.magnet";

let enabled = true;
let pollTimer = null;

browser.storage.local.get("enabled").then(function (stored) {
  if (typeof stored.enabled === "boolean") {
    enabled = stored.enabled;
  }
  refreshBadge();
  startPoll(false);
});

browser.storage.onChanged.addListener(function (changes) {
  if (changes.enabled) {
    enabled = changes.enabled.newValue !== false;
  }
});

function native(message) {
  return browser.runtime.sendNativeMessage(NATIVE_HOST, message);
}

function activeJobs(jobs) {
  return (jobs || []).filter(function (job) {
    return job.status !== "done" && job.status !== "error";
  });
}

function refreshBadge() {
  return native({ cmd: "status" })
    .then(function (response) {
      const jobs = (response && response.jobs) || [];
      const live = activeJobs(jobs);
      const needs = live.some(function (job) {
        return job.status === "needs_selection";
      });
      browser.action.setBadgeBackgroundColor({
        color: needs ? "#D9772C" : "#3D6B5A",
      });
      browser.action.setBadgeText({
        text: needs ? "!" : live.length ? String(live.length) : "",
      });
      startPoll(live.length > 0);
    })
    .catch(function () {
      browser.action.setBadgeBackgroundColor({ color: "#D9772C" });
      browser.action.setBadgeText({ text: "?" });
      startPoll(false);
    });
}

function startPoll(fast) {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
  pollTimer = setInterval(refreshBadge, fast ? 2000 : 15000);
}

function sendMagnet(magnetUrl) {
  return native({ cmd: "enqueue", url: magnetUrl }).then(function (response) {
    if (!response || response.ok === false) {
      throw new Error((response && response.error) || "Native host failed");
    }
    refreshBadge();
    return response;
  });
}

browser.runtime.onMessage.addListener(function (message, sender, sendResponse) {
  if (message.type !== "magnet" || !message.url) {
    return false;
  }

  if (!enabled && !message.force) {
    sendResponse({ success: false, skipped: true });
    return false;
  }

  sendMagnet(message.url)
    .then(function () {
      sendResponse({ success: true });
    })
    .catch(function (error) {
      sendResponse({ success: false, error: error.message });
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
    sendMagnet(info.linkUrl).catch(function () {
      refreshBadge();
    });
  }
});
