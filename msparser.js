var msParser = (function () {
  var HOSTS_API = "https://api.real-debrid.com/rest/1.0/hosts/domains";
  var DOMAIN_CACHE_TTL_MS = 24 * 60 * 60 * 1000;
  var PRIORITY = 65000;

  var cachedDomains = null;
  var cacheLoadedAt = 0;
  var cachePromise = null;

  var CONTAINER_PATTERN = /\.(dlc|ccf|ccfz|rsdf)(\?|$)/i;
  var TORRENT_PATTERN = /\.torrent(\?|$)/i;
  var MAGNET_PATTERN = /^magnet:/i;
  var RD_CDN_PATTERN = /(^|\.)rdeb\.io$/i;

  var FOLDER_MARKERS = [
    "/folder/",
    "/folders/",
    "#f!",
    "folder=",
    "/dir/",
    "/collection/",
  ];

  function embeddedDomains() {
    if (
      typeof RD_EMBEDDED_DOMAINS !== "undefined" &&
      RD_EMBEDDED_DOMAINS.length
    ) {
      return RD_EMBEDDED_DOMAINS;
    }
    return [];
  }

  function activeDomains() {
    return cachedDomains || embeddedDomains();
  }

  function hostnameFromUrl(url) {
    var match = /^https?:\/\/([^\/?#]+)/i.exec(url);
    if (!match) {
      return "";
    }
    return match[1].replace(/:\d+$/, "").toLowerCase();
  }

  function domainMatches(hostname, domain) {
    if (!hostname || !domain) {
      return false;
    }

    domain = domain.toLowerCase();
    return hostname === domain || hostname.endsWith("." + domain);
  }

  function urlMatchesDomains(url, domains) {
    var hostname = hostnameFromUrl(url);
    if (!hostname || !domains || !domains.length) {
      return false;
    }

    for (var i = 0; i < domains.length; i++) {
      if (domainMatches(hostname, domains[i])) {
        return true;
      }
    }

    return false;
  }

  function looksLikeFolder(url) {
    var lowered = url.toLowerCase();
    for (var i = 0; i < FOLDER_MARKERS.length; i++) {
      if (lowered.indexOf(FOLDER_MARKERS[i]) !== -1) {
        return true;
      }
    }
    return false;
  }

  function ensureDomainsLoaded() {
    var now = Date.now();
    if (cachedDomains && now - cacheLoadedAt < DOMAIN_CACHE_TTL_MS) {
      return Promise.resolve(cachedDomains);
    }

    if (cachePromise) {
      return cachePromise;
    }

    cachePromise = downloadUrlAsUtf8Text(HOSTS_API, "", [], "")
      .then(function (response) {
        var domains = JSON.parse(response.body);
        if (!Array.isArray(domains)) {
          throw new Error("Unexpected Real-Debrid hosts response");
        }
        cachedDomains = domains;
        cacheLoadedAt = Date.now();
        cachePromise = null;
        return domains;
      })
      .catch(function (error) {
        cachePromise = null;
        if (cachedDomains) {
          return cachedDomains;
        }
        throw error;
      });

    return cachePromise;
  }

  function isRdDirectUrl(url) {
    var hostname = hostnameFromUrl(url);
    if (!hostname) {
      return false;
    }
    return (
      RD_CDN_PATTERN.test(hostname) ||
      hostname.indexOf("real-debrid.com") !== -1
    );
  }

  function isMagnetUrl(url) {
    return MAGNET_PATTERN.test(url);
  }

  function isTorrentFileUrl(url) {
    return /^https?:\/\//i.test(url) && TORRENT_PATTERN.test(url);
  }

  function isSupportedUrl(url) {
    if (!url) {
      return false;
    }

    if (isMagnetUrl(url) || isTorrentFileUrl(url)) {
      return true;
    }

    if (isRdDirectUrl(url)) {
      return true;
    }

    if (CONTAINER_PATTERN.test(url) && /^https?:\/\//i.test(url)) {
      return true;
    }

    if (!/^https?:\/\//i.test(url)) {
      return false;
    }

    if (looksLikeFolder(url)) {
      return false;
    }

    return urlMatchesDomains(url, activeDomains());
  }

  function launchParser(scriptPath) {
    return function (obj) {
      var args = [obj.url];
      if (obj.cookie) {
        args.push(obj.cookie);
      }

      return launchPythonScript(
        obj.requestId,
        obj.interactive,
        scriptPath,
        args,
      ).then(function (result) {
        if (result.exitCode !== 0) {
          return Promise.reject({
            error: result.output || "Real-Debrid parser failed",
            isParseError: true,
          });
        }

        try {
          return JSON.parse(result.output);
        } catch (parseError) {
          return Promise.reject({
            error: "Invalid parser output: " + parseError.message,
            isParseError: true,
          });
        }
      });
    };
  }

  ensureDomainsLoaded().catch(function (error) {
    console.warn(
      "Failed to refresh Real-Debrid host list:",
      error.error || error.message || error,
    );
  });

  return {
    parse: launchParser("python/parse.py"),

    isSupportedSource: function (url) {
      return isSupportedUrl(url);
    },

    supportedSourceCheckPriority: function () {
      return PRIORITY;
    },

    isPossiblySupportedSource: function (obj) {
      if (!obj || !obj.url) {
        return false;
      }

      return isSupportedUrl(obj.url);
    },

    minIntevalBetweenQueryInfoDownloads: function () {
      return 14400000;
    },

    overrideUrlPolicy: function (url) {
      return isRdDirectUrl(url) || isMagnetUrl(url);
    },
  };
})();
