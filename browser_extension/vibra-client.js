(() => {
  const RUNTIME_TIMEOUT_MS = 15000;
  let runtimePromise = null;

  function isRuntimeReady() {
    return typeof Module !== "undefined"
      && Module.HEAPU8
      && Module._malloc
      && Module._free
      && Module.ccall;
  }

  function ready() {
    if (isRuntimeReady()) {
      return Promise.resolve();
    }
    if (runtimePromise) {
      return runtimePromise;
    }

    runtimePromise = new Promise((resolve, reject) => {
      if (typeof Module === "undefined") {
        reject(new Error("Vibra WebAssembly did not load."));
        return;
      }

      const previousReady = Module.onRuntimeInitialized;
      const previousAbort = Module.onAbort;
      const timeout = setTimeout(() => {
        reject(new Error("Vibra WebAssembly initialization timed out."));
      }, RUNTIME_TIMEOUT_MS);

      Module.onRuntimeInitialized = () => {
        clearTimeout(timeout);
        previousReady?.();
        resolve();
      };
      Module.onAbort = (reason) => {
        clearTimeout(timeout);
        previousAbort?.(reason);
        reject(new Error(`Vibra WebAssembly stopped: ${reason || "unknown error"}`));
      };
    });

    return runtimePromise;
  }

  async function createSignature(wavBlob) {
    await ready();
    const wavBytes = new Uint8Array(await wavBlob.arrayBuffer());
    if (!wavBytes.length) {
      throw new Error("Empty audio recording.");
    }

    const dataPointer = Module._malloc(wavBytes.length);
    let signaturePointer = 0;
    try {
      Module.HEAPU8.set(wavBytes, dataPointer);
      signaturePointer = Module.ccall(
        "GetWavSignature",
        "number",
        ["number", "number"],
        [dataPointer, wavBytes.length]
      );
      if (!signaturePointer) {
        throw new Error("Could not create an audio fingerprint.");
      }

      return {
        uri: Module.ccall("GetFingerprint", "string", ["number"], [signaturePointer]),
        samplems: Module.ccall("GetSampleMs", "number", ["number"], [signaturePointer])
      };
    } finally {
      // The published global WASM build does not export FreeFingerprint.
      // Closing the popup releases its short-lived WASM instance.
      Module._free(dataPointer);
    }
  }

  function metadataValue(track, ...wantedNames) {
    const wanted = new Set(wantedNames.map((name) => name.toLocaleLowerCase()));
    for (const section of track.sections || []) {
      for (const item of section?.metadata || []) {
        if (wanted.has(String(item?.title || "").toLocaleLowerCase())) {
          return String(item?.text || "");
        }
      }
    }
    return "";
  }

  function youtubeUrl(track) {
    for (const section of track.sections || []) {
      if (section?.youtubeurl) {
        return String(section.youtubeurl);
      }
    }
    return "";
  }

  function normalizeResponse(data) {
    const track = data?.track;
    if (!track) {
      return {
        ok: false,
        provider: "Shazam",
        error: "Song not recognized.",
        raw: data
      };
    }

    const images = track.images || {};
    return {
      ok: true,
      provider: "Shazam",
      title: String(track.title || "Unknown"),
      artist: String(track.subtitle || "Unknown"),
      album: metadataValue(track, "album"),
      release_date: metadataValue(track, "released", "release date", "lancamento"),
      label: metadataValue(track, "label", "gravadora"),
      cover_url: String(images.coverarthq || images.coverart || images.background || ""),
      youtube_url: youtubeUrl(track),
      shazam_url: String(track.url || ""),
      raw: track
    };
  }

  async function recognizeWav(wavBlob, options = {}) {
    const signature = await createSignature(wavBlob);
    const language = options.language === "en" ? "en-US" : "pt-BR";
    const country = options.country || "BR";
    const now = Date.now();
    const uuid1 = crypto.randomUUID().toUpperCase();
    const uuid2 = crypto.randomUUID().toUpperCase();
    const endpoint = `https://amp.shazam.com/discovery/v5/${language}/${country}/web/-/tag/`
      + `${uuid1}/${uuid2}?sync=true&webv3=true&sampling=true&connected=`
      + "&shazamapiversion=v3&sharehub=true&hubv5minorversion=v5.1&hidelb=true&video=v3";
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Sao_Paulo";

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Language": language,
        "X-Shazam-Platform": "WEB",
        "X-Shazam-AppVersion": "14.1.0"
      },
      body: JSON.stringify({
        timezone,
        signature,
        timestamp: now,
        context: {},
        geolocation: {}
      })
    });

    if (!response.ok) {
      throw new Error(`Shazam request failed (${response.status}).`);
    }
    return normalizeResponse(await response.json());
  }

  globalThis.IchthusShazam = { ready, recognizeWav };
})();
