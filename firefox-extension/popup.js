const NATIVE_HOST = "com.fdmrealdebrid.magnet";
const picks = {};
const folds = {};
const fileCache = {};
let lastJobs = [];
let configOpen = false;

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
  const checks = [
    ["native", nativeOk, "ok", "missing", true],
    ["FDM", !!config.fdmFound, "ok", "missing", true],
    ["add-on", !!config.addonFound, "ok", "missing", true],
    ["token", !!config.tokenSet, "set", "missing", true],
    ["remote", true, config.useRemoteTraffic ? "on" : "off", "", false],
    ["poll", true, (config.torrentPollIntervalSec || 5) + "s / " + (config.torrentMaxWaitSec || 900) + "s", "", false],
    ["delete", true, config.deleteTorrentAfter ? "on" : "off", "", false],
  ];
  const problems = [];
  if (!nativeOk) {
    problems.push("native host");
  }
  if (!config.fdmFound) {
    problems.push("FDM");
  }
  if (!config.addonFound) {
    problems.push("add-on");
  }
  if (!config.tokenSet) {
    problems.push("token");
  }

  $("config").innerHTML = checks
    .map(function (row) {
      return (
        "<dt>" +
        row[0] +
        '</dt><dd class="' +
        (row[4] && !row[1] ? "bad" : "ok") +
        '">' +
        (row[1] ? row[2] : row[3]) +
        "</dd>"
      );
    })
    .join("");

  $("config-sum").textContent = problems.length
    ? problems.join(" · ")
    : "all set";
  $("config-sum").className = "count" + (problems.length ? " bad" : " ok");
  $("config-sheet").classList.toggle("collapsed", !configOpen);
  $("config-fold").setAttribute("aria-expanded", configOpen ? "true" : "false");

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
      const fileList = fileCache[job.id] || [];
      const files = fileList
        .map(function (file) {
          const stamp = file.cached ? '<span class="stamp">cached</span>' : "";
          const checked = !picking || fileChecked(job.id, file.id);
          const box = picking
            ? '<input type="checkbox" data-job="' +
              job.id +
              '" value="' +
              file.id +
              '"' +
              (checked ? " checked" : "") +
              " />"
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

      const allOn = picking && fileList.length > 0 && fileList.every(function (file) {
        return fileChecked(job.id, file.id);
      });
      const actions = picking
        ? '<div class="actions"><button type="button" data-all="' +
          job.id +
          '">' +
          (allOn ? "Deselect all" : "Select all") +
          '</button><button class="primary" type="button" data-send="' +
          job.id +
          '">Send to FDM</button></div>'
        : "";
      const collapsed = isCollapsed(job);
      const fileCount = job.fileCount || fileList.length;

      return (
        '<article class="waybill' +
        (collapsed ? " collapsed" : "") +
        '">' +
        '<button type="button" class="fold" data-fold="' +
        job.id +
        '" aria-expanded="' +
        (collapsed ? "false" : "true") +
        '"><div class="waybill-top"><span class="wb-id">WB-' +
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
        '<p class="cargo-n">' +
        (fileCount ? fileCount + " files · " : "") +
        (collapsed ? "expand" : "collapse") +
        "</p></button>" +
        '<div class="waybill-body">' +
        actions +
        (files ? '<ul class="files">' + files + "</ul>" : "") +
        (job.error ? '<p class="error">' + escapeHtml(job.error) + "</p>" : "") +
        "</div></article>"
      );
    })
    .join("");
}

function isCollapsed(job) {
  if (folds[job.id] !== undefined) {
    return folds[job.id];
  }
  return (job.fileCount || 0) > 8;
}

async function ensureFiles(job) {
  const count = job.fileCount || 0;
  if (!count) {
    fileCache[job.id] = [];
    return;
  }
  if (fileCache[job.id] && fileCache[job.id].length === count) {
    return;
  }
  const all = [];
  let offset = 0;
  const limit = 1500;
  while (true) {
    const response = await native({
      cmd: "files",
      jobId: job.id,
      offset: offset,
      limit: limit,
    });
    if (!response || response.ok === false) {
      throw new Error((response && response.error) || "Could not load files");
    }
    all.push.apply(all, response.files || []);
    if (!response.more) {
      break;
    }
    offset += limit;
  }
  fileCache[job.id] = all;
}

function fileChecked(jobId, fileId) {
  if (!picks[jobId] || picks[jobId][fileId] === undefined) {
    return true;
  }
  return picks[jobId][fileId];
}

function rememberPicks(jobId) {
  picks[jobId] = {};
  $("jobs")
    .querySelectorAll('input[data-job="' + jobId + '"]')
    .forEach(function (box) {
      picks[jobId][box.value] = box.checked;
    });
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
    lastJobs = response.jobs || [];
    renderJobs(lastJobs);
    const needed = lastJobs.filter(function (job) {
      return !isCollapsed(job) && (job.fileCount || 0) > 0;
    });
    for (let i = 0; i < needed.length; i++) {
      await ensureFiles(needed[i]);
    }
    if (needed.length) {
      renderJobs(lastJobs);
    }
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

$("config-fold").addEventListener("click", function () {
  configOpen = !configOpen;
  $("config-sheet").classList.toggle("collapsed", !configOpen);
  $("config-fold").setAttribute("aria-expanded", configOpen ? "true" : "false");
});

$("capture").addEventListener("change", function () {
  browser.storage.local.set({ enabled: $("capture").checked });
  refresh();
});

$("jobs").addEventListener("change", function (event) {
  const jobId = event.target.getAttribute && event.target.getAttribute("data-job");
  if (jobId) {
    rememberPicks(jobId);
  }
});

$("jobs").addEventListener("click", function (event) {
  const fold = event.target.closest && event.target.closest("[data-fold]");
  if (fold && !event.target.closest("input, .actions")) {
    const jobId = fold.getAttribute("data-fold");
    folds[jobId] = !fold.closest(".waybill").classList.contains("collapsed")
      ? true
      : false;
    fold.closest(".waybill").classList.toggle("collapsed", folds[jobId]);
    fold.setAttribute("aria-expanded", folds[jobId] ? "false" : "true");
    const hint = fold.querySelector(".cargo-n");
    if (hint) {
      hint.textContent = hint.textContent.replace(
        /expand|collapse/,
        folds[jobId] ? "expand" : "collapse",
      );
    }
    if (!folds[jobId]) {
      const job = lastJobs.find(function (item) {
        return item.id === jobId;
      });
      if (job) {
        ensureFiles(job).then(function () {
          renderJobs(lastJobs);
        });
      }
    }
    return;
  }
  const send = event.target.getAttribute("data-send");
  const all = event.target.getAttribute("data-all");
  if (all) {
    const boxes = $("jobs").querySelectorAll('input[data-job="' + all + '"]');
    const select = !Array.from(boxes).every(function (box) {
      return box.checked;
    });
    boxes.forEach(function (box) {
      box.checked = select;
    });
    rememberPicks(all);
    event.target.textContent = select ? "Deselect all" : "Select all";
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
