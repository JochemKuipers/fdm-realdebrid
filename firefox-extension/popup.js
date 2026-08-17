const NATIVE_HOST = "com.fdmrealdebrid.magnet";

const STATUS_LABEL = {
  queued: "queued",
  magnet_conversion: "converting magnet",
  waiting_files_selection: "pick files",
  needs_selection: "pick files",
  downloading: "loading",
  compressing: "packing",
  uploading: "handing off",
  downloaded: "unpacking",
  done: "sent to FDM",
  error: "failed",
};

function $(id) {
  return document.getElementById(id);
}

function bytes(value) {
  const n = Number(value) || 0;
  if (n <= 0) {
    return "";
  }
  if (n < 1024) {
    return n + " B";
  }
  if (n < 1048576) {
    return (n / 1024).toFixed(1) + " KB";
  }
  if (n < 1073741824) {
    return (n / 1048576).toFixed(1) + " MB";
  }
  return (n / 1073741824).toFixed(1) + " GB";
}

function native(message) {
  return browser.runtime.sendNativeMessage(NATIVE_HOST, message);
}

function renderConfig(config, nativeOk) {
  const rows = [
    ["capture", $("capture").checked ? "on" : "off"],
    ["native host", nativeOk ? "reachable" : "missing — run the install script, then restart Firefox"],
    ["FDM", config.fdmFound ? "found" : "not found"],
    ["add-on", config.addonFound ? "found" : "install fdm-realdebrid in FDM"],
    ["token", config.tokenSet ? "set" : "edit config.json"],
    ["remote traffic", config.useRemoteTraffic ? "on" : "off"],
    ["poll / wait", (config.torrentPollIntervalSec || 5) + "s / " + (config.torrentMaxWaitSec || 900) + "s"],
    ["delete after", config.deleteTorrentAfter ? "on" : "off"],
  ];

  $("config").innerHTML = rows
    .map(function (row) {
      const bad =
        (row[0] === "native host" && !nativeOk) ||
        (row[0] === "FDM" && !config.fdmFound) ||
        (row[0] === "add-on" && !config.addonFound) ||
        (row[0] === "token" && !config.tokenSet);
      return "<dt>" + row[0] + "</dt><dd class=\"" + (bad ? "bad" : "ok") + "\">" + row[1] + "</dd>";
    })
    .join("");

  if (config.error) {
    $("banner").hidden = false;
    $("banner").textContent = config.error;
  }
}

function renderJobs(jobs) {
  const live = (jobs || []).filter(function (job) {
    return job.status !== "done" && job.status !== "error";
  }).length;
  $("lane-count").textContent = live ? live + " live" : "idle";

  if (!jobs || !jobs.length) {
    $("jobs").innerHTML =
      '<p class="empty">No waybills. Click a magnet or paste one in FDM.</p>';
    return;
  }

  $("jobs").innerHTML = jobs
    .map(function (job) {
      const picking = job.status === "needs_selection";
      const files = (job.files || [])
        .map(function (file) {
          const stamp = file.cached ? '<span class="stamp">cached</span>' : "";
          const box = picking
            ? '<input type="checkbox" data-job="' +
              job.id +
              '" value="' +
              file.id +
              '" checked />'
            : "";
          return (
            "<li>" +
            box +
            '<span class="file-path">' +
            escapeHtml(file.path || file.id) +
            stamp +
            "</span>" +
            '<span class="size">' +
            bytes(file.bytes) +
            "</span></li>"
          );
        })
        .join("");

      const actions = picking
        ? '<div class="actions"><button type="button" data-all="' +
          job.id +
          '">Select all</button><button class="primary" type="button" data-send="' +
          job.id +
          '">Send to FDM</button></div>'
        : "";

      return (
        '<article class="waybill">' +
        '<div class="waybill-top"><span class="wb-id">WB-' +
        escapeHtml((job.id || "").slice(0, 6).toUpperCase()) +
        '</span><span class="status">' +
        escapeHtml(STATUS_LABEL[job.status] || job.status || "") +
        "</span></div>" +
        '<div class="name">' +
        escapeHtml(job.filename || job.hash || "torrent") +
        "</div>" +
        '<div class="bar" aria-hidden="true"><span style="width:' +
        Math.max(0, Math.min(100, Number(job.progress) || 0)) +
        '%"></span></div>' +
        (files ? '<ul class="files">' + files + "</ul>" : "") +
        actions +
        (job.error ? '<p class="error">' + escapeHtml(job.error) + "</p>" : "") +
        "</article>"
      );
    })
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function refresh() {
  $("banner").hidden = true;
  try {
    const response = await native({ cmd: "status" });
    if (!response || response.ok === false) {
      throw new Error((response && response.error) || "Native host failed");
    }
    renderConfig(response.config || {}, true);
    renderJobs(response.jobs || []);
  } catch (error) {
    renderConfig({}, false);
    $("banner").hidden = false;
    $("banner").textContent = error.message || String(error);
    $("jobs").innerHTML = "";
    $("lane-count").textContent = "";
  }
}

async function sendSelection(jobId, files) {
  $("banner").hidden = true;
  try {
    const response = await native({ cmd: "selectFiles", jobId: jobId, files: files });
    if (!response || response.ok === false) {
      throw new Error((response && response.error) || "Could not send selection");
    }
    await refresh();
  } catch (error) {
    $("banner").hidden = false;
    $("banner").textContent = error.message || String(error);
  }
}

$("capture").addEventListener("change", function () {
  browser.storage.local.set({ enabled: $("capture").checked });
  refresh();
});

$("jobs").addEventListener("click", function (event) {
  const send = event.target.getAttribute("data-send");
  const all = event.target.getAttribute("data-all");
  if (all) {
    $("jobs")
      .querySelectorAll('input[data-job="' + all + '"]')
      .forEach(function (box) {
        box.checked = true;
      });
    return;
  }
  if (!send) {
    return;
  }
  const selected = Array.from(
    $("jobs").querySelectorAll('input[data-job="' + send + '"]:checked'),
  ).map(function (box) {
    return box.value;
  });
  sendSelection(send, selected.length ? selected : ["all"]);
});

browser.storage.local.get("enabled").then(function (stored) {
  $("capture").checked = stored.enabled !== false;
  refresh();
  setInterval(refresh, 1000);
});
