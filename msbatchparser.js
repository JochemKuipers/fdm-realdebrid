var msBatchVideoParser = (function () {
    var PRIORITY = 65000;

    var FOLDER_MARKERS = [
        "/folder/",
        "/folders/",
        "#f!",
        "folder=",
        "/dir/",
        "/collection/"
    ];

    function hostnameFromUrl(url) {
        var match = /^https?:\/\/([^\/?#]+)/i.exec(url);
        if (!match) {
            return "";
        }
        return match[1].replace(/:\d+$/, "").toLowerCase();
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

    function launchFolderParser(obj) {
        return launchPythonScript(obj.requestId, obj.interactive, "python/parse_folder.py", [obj.url])
            .then(function (result) {
                if (result.exitCode !== 0) {
                    return Promise.reject({
                        error: result.output || "Real-Debrid folder parser failed",
                        isParseError: true
                    });
                }

                try {
                    return JSON.parse(result.output);
                } catch (parseError) {
                    return Promise.reject({
                        error: "Invalid folder parser output: " + parseError.message,
                        isParseError: true
                    });
                }
            });
    }

    return {
        parse: launchFolderParser,

        isSupportedSource: function (url) {
            if (!/^https?:\/\//i.test(url)) {
                return false;
            }

            if (!looksLikeFolder(url)) {
                return false;
            }

            return hostnameFromUrl(url).length > 0;
        },

        supportedSourceCheckPriority: function () {
            return PRIORITY;
        },

        isPossiblySupportedSource: function () {
            return false;
        },

        minIntevalBetweenQueryInfoDownloads: function () {
            return 14400000;
        },

        overrideUrlPolicy: function (url) {
            var hostname = hostnameFromUrl(url);
            return hostname.indexOf("real-debrid.com") !== -1 || /\.rdeb\.io$/i.test(hostname);
        }
    };
}());
