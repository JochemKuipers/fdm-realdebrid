const NATIVE_HOST = "com.fdmrealdebrid.magnet";
const DOCK_URL = chrome.runtime.getURL("popup.html");
const ALARM_BADGE = "badge-poll";

let enabled = true;

chrome.storage.local.get("enabled").then(function (stored) {
  if (typeof stored.enabled === "boolean") {
    enabled = stored.enabled;
  }
  refreshBadge();
  startPoll(false);
});

chrome.storage.onChanged.addListener(function (changes) {
  if (changes.enabled) {
    enabled = changes.enabled.newValue !== false;
  }
});

function native(message) {
  return chrome.runtime.sendNativeMessage(NATIVE_HOST, message);
}

function activeJobs(jobs) {
  return (jobs || []).filter(function (job) {
    return job.status !== "done" && job.status !== "error";
  });
}

async function getSession() {
  const data = await chrome.storage.session.get({
    watchIds: [],
    dockTabId: null,
  });
  return {
    watchIds: data.watchIds || [],
    dockTabId: data.dockTabId == null ? null : data.dockTabId,
  };
}

async function setSession(patch) {
  await chrome.storage.session.set(patch);
}

function refreshBadge() {
  return native({ cmd: "status" })
    .then(async function (response) {
      const jobs = (response && response.jobs) || [];
      const live = activeJobs(jobs);
      const needs = live.some(function (job) {
        return job.status === "needs_selection";
      });
      const session = await getSession();
      chrome.action.setBadgeBackgroundColor({
        color: needs ? "#D9772C" : "#3D6B5A",
      });
      chrome.action.setBadgeText({
        text: needs ? "!" : live.length ? String(live.length) : "",
      });
      await maybeCloseDock(jobs, session);
      startPoll(live.length > 0 || session.watchIds.length > 0);
    })
    .catch(function () {
      chrome.action.setBadgeBackgroundColor({ color: "#D9772C" });
      chrome.action.setBadgeText({ text: "?" });
      startPoll(false);
    });
}

function startPoll(fast) {
  chrome.alarms.clear(ALARM_BADGE).then(function () {
    if (fast) {
      // One-shot under 1 minute is allowed; chain from refreshBadge while jobs are live.
      chrome.alarms.create(ALARM_BADGE, { delayInMinutes: 2 / 60 });
    } else {
      chrome.alarms.create(ALARM_BADGE, { periodInMinutes: 1 });
    }
  });
}

chrome.alarms.onAlarm.addListener(function (alarm) {
  if (alarm.name === ALARM_BADGE) {
    refreshBadge();
  }
});

function createDock() {
  return chrome.tabs.create({ url: DOCK_URL, active: true }).then(async function (tab) {
    await setSession({ dockTabId: tab.id });
    return tab;
  });
}

async function openDock() {
  const session = await getSession();
  if (!session.dockTabId) {
    return createDock();
  }
  return chrome.tabs
    .get(session.dockTabId)
    .then(function (tab) {
      return chrome.tabs.update(tab.id, { active: true });
    })
    .catch(function () {
      return setSession({ dockTabId: null }).then(createDock);
    });
}

async function maybeCloseDock(jobs, session) {
  if (!session.dockTabId || !session.watchIds.length) {
    return;
  }
  const byId = {};
  (jobs || []).forEach(function (job) {
    byId[job.id] = job;
  });
  const allDone = session.watchIds.every(function (id) {
    const job = byId[id];
    return job && job.status === "done";
  });
  if (!allDone) {
    return;
  }
  const tabId = session.dockTabId;
  await setSession({ dockTabId: null, watchIds: [] });
  setTimeout(function () {
    chrome.tabs.remove(tabId).catch(function () {});
  }, 1500);
}

function sendMagnet(magnetUrl) {
  return native({ cmd: "enqueue", url: magnetUrl }).then(async function (response) {
    if (!response || response.ok === false) {
      throw new Error((response && response.error) || "Native host failed");
    }
    if (response.jobId) {
      const session = await getSession();
      if (session.watchIds.indexOf(response.jobId) === -1) {
        session.watchIds.push(response.jobId);
        await setSession({ watchIds: session.watchIds });
      }
    }
    refreshBadge();
    return response;
  });
}

chrome.tabs.onRemoved.addListener(async function (tabId) {
  const session = await getSession();
  if (tabId === session.dockTabId) {
    await setSession({ dockTabId: null });
  }
});

chrome.runtime.onMessage.addListener(function (message, _sender, sendResponse) {
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
      sendResponse({ success: true });
    })
    .catch(function (error) {
      sendResponse({ success: false, error: error.message });
    });

  return true;
});

function ensureContextMenu() {
  chrome.contextMenus.removeAll(function () {
    chrome.contextMenus.create({
      id: "send-magnet-fdm",
      title: "Send magnet to FDM (Real-Debrid)",
      contexts: ["link"],
      targetUrlPatterns: ["magnet:*"],
    });
  });
}

chrome.runtime.onInstalled.addListener(ensureContextMenu);
chrome.runtime.onStartup.addListener(function () {
  ensureContextMenu();
  refreshBadge();
  startPoll(false);
});

ensureContextMenu();
