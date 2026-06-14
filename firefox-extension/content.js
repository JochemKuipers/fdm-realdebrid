(function () {
  function magnetFromEvent(target) {
    if (!target || !target.closest) {
      return null;
    }

    var anchor = target.closest("a[href^='magnet:'], a[href^='MAGNET:']");
    return anchor ? anchor.href : null;
  }

  document.addEventListener(
    "click",
    function (event) {
      var magnet = magnetFromEvent(event.target);
      if (!magnet) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      browser.runtime.sendMessage({ type: "magnet", url: magnet }).then(function (response) {
        if (response && response.skipped) {
          window.location.href = magnet;
        }
      });
    },
    true
  );
})();
