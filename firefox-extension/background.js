const NATIVE_HOST = "com.fdmrealdebrid.magnet";
const DOCK_URL = browser.runtime.getURL("popup.html");

let enabled = true;
let pollTimer = null;
let dockTabId = null;
const watchIds = new Set();

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
      maybeCloseDock(jobs);
      startPoll(live.length > 0 || watchIds.size > 0);
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

function createDock() {
  return browser.tabs.create({ url: DOCK_URL, active: true }).then(function (tab) {
    dockTabId = tab.id;
    return tab;
  });
}

function openDock() {
  if (!dockTabId) {
    return createDock();
  }
  return browser.tabs
    .get(dockTabId)
    .then(function (tab) {
      return browser.tabs.update(tab.id, { active: true });
    })
    .catch(function () {
      dockTabId = null;
      return createDock();
    });
}

function leaveHandlerTab(tabId) {
  browser.tabs.goBack(tabId).catch(function () {
    browser.tabs.get(tabId).then(function (tab) {
      if (tab.url && tab.url.indexOf("handler.html") !== -1) {
        browser.tabs.remove(tabId);
      }
    });
  });
}

function maybeCloseDock(jobs) {
  if (!dockTabId || !watchIds.size) {
    return;
  }
  const byId = {};
  (jobs || []).forEach(function (job) {
    byId[job.id] = job;
  });
  let allDone = true;
  watchIds.forEach(function (id) {
    const job = byId[id];
    if (!job || job.status !== "done") {
      allDone = false;
    }
  });
  if (!allDone) {
    return;
  }
  const tabId = dockTabId;
  dockTabId = null;
  watchIds.clear();
  setTimeout(function () {
    browser.tabs.remove(tabId).catch(function () {});
  }, 1500);
}

function sendMagnet(magnetUrl) {
  return native({ cmd: "enqueue", url: magnetUrl }).then(function (response) {
    if (!response || response.ok === false) {
      throw new Error((response && response.error) || "Native host failed");
    }
    if (response.jobId) {
      watchIds.add(response.jobId);
    }
    refreshBadge();
    return response;
  });
}

browser.tabs.onRemoved.addListener(function (tabId) {
  if (tabId === dockTabId) {
    dockTabId = null;
  }
});

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
      openDock();
      if (sender.tab && sender.tab.url && sender.tab.url.indexOf("handler.html") !== -1) {
        leaveHandlerTab(sender.tab.id);
      }
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
    sendMagnet(info.linkUrl)
      .then(function () {
        openDock();
      })
      .catch(function () {
        refreshBadge();
      });
  }
});
