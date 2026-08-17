(function () {
  var params = new URLSearchParams(window.location.search);
  var raw = params.get("url") || "";
  var magnet = "";
  try {
    magnet = decodeURIComponent(raw);
  } catch (error) {
    magnet = raw;
  }

  var status = document.getElementById("status");
  if (!magnet.toLowerCase().startsWith("magnet:")) {
    status.textContent = "Not a magnet link.";
    return;
  }

  browser.runtime
    .sendMessage({ type: "magnet", url: magnet, force: true })
    .then(function (response) {
      if (response && response.success) {
        status.textContent = "Queued. Open the toolbar popup to pick files.";
        window.close();
        return;
      }
      status.textContent = (response && response.error) || "Could not queue this magnet.";
    })
    .catch(function (error) {
      status.textContent = error.message || String(error);
    });
})();
