const STORAGE_DEFAULTS = {
  language: "pt",
  history: [],
  reports: []
};

const MAX_HISTORY = 50;
const RECORD_MS = 8500;

const DEFAULT_CORRECTIONS = [
  {
    match: {
      artist: "Spacetoon TV",
      contains: ["gaara"]
    },
    replace: {
      title: "Gaara",
      artist: "7 Minutoz",
      album: ""
    }
  }
];

const TEXT = {
  pt: {
    language_button: "EN",
    ready: "Pronto para ouvir",
    listening: "Ouvindo a aba...",
    identifying: "Identificando...",
    loading_engine: "Preparando reconhecimento...",
    recognized: "Música encontrada",
    engine_error: "Não consegui iniciar o reconhecimento.",
    capture_error: "Não consegui capturar o áudio dessa aba.",
    no_music: "Música não reconhecida.",
    network_error: "Não consegui consultar o Shazam.",
    recognize_tab: "Ouvir Música",
    stop: "Parar gravação",
    result: "Resultado",
    history: "Histórico",
    close_history: "Fechar histórico",
    clear_result: "Limpar resultado",
    clear_history: "Limpar histórico",
    history_count_one: "música salva",
    history_count_many: "músicas salvas",
    no_history: "Nenhuma música reconhecida ainda.",
    title: "Título",
    artist: "Artista",
    album: "Álbum",
    release: "Lançamento",
    unknown: "Desconhecido",
    report: "Reportar",
    report_saved: "Report salvo."
  },
  en: {
    language_button: "PT",
    ready: "Ready to listen",
    listening: "Listening to this tab...",
    identifying: "Identifying...",
    loading_engine: "Preparing recognition...",
    recognized: "Song found",
    engine_error: "Could not initialize recognition.",
    capture_error: "I could not capture audio from this tab.",
    no_music: "Song not recognized.",
    network_error: "Could not reach Shazam.",
    recognize_tab: "Listen",
    stop: "Stop recording",
    result: "Result",
    history: "History",
    close_history: "Close history",
    clear_result: "Clear result",
    clear_history: "Clear history",
    history_count_one: "song saved",
    history_count_many: "songs saved",
    no_history: "No recognized songs yet.",
    title: "Title",
    artist: "Artist",
    album: "Album",
    release: "Release",
    unknown: "Unknown",
    report: "Report",
    report_saved: "Report saved."
  }
};

const state = {
  language: "pt",
  history: [],
  reports: [],
  lastResult: null,
  lastQuery: "",
  mediaStream: null,
  audioContext: null,
  audioSource: null,
  audioProcessor: null,
  audioChunks: [],
  captureResolve: null,
  stopTimer: null,
  historyVisible: false,
  engineReady: false
};

const els = {};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  bindElements();
  bindEvents();
  const stored = await storageGet(STORAGE_DEFAULTS);
  Object.assign(state, stored);
  applyLanguage();
  renderHistory();
  setStatus(tr("loading_engine"));
  try {
    await globalThis.IchthusShazam.ready();
    state.engineReady = true;
    setStatus(tr("ready"));
  } catch (_error) {
    setStatus(tr("engine_error"));
  }
}

function bindElements() {
  [
    "languageBtn",
    "bars",
    "statusText",
    "recognizeBtn",
    "stopBtn",
    "resultLabel",
    "resultCard",
    "coverBox",
    "songTitle",
    "songArtist",
    "platformLinks",
    "youtubeBtn",
    "spotifyBtn",
    "historyToggleBtn",
    "clearResultBtn",
    "historyPanel",
    "historyTitle",
    "historyCount",
    "clearHistoryBtn",
    "historyList"
  ].forEach((id) => {
    els[id] = document.getElementById(id);
  });
}

function bindEvents() {
  els.languageBtn.addEventListener("click", toggleLanguage);
  els.recognizeBtn.addEventListener("click", recognizeCurrentTab);
  els.stopBtn.addEventListener("click", stopRecording);
  els.clearResultBtn.addEventListener("click", clearResult);
  els.clearHistoryBtn.addEventListener("click", clearHistory);
  els.historyToggleBtn.addEventListener("click", toggleHistory);
  els.youtubeBtn.addEventListener("click", () => openPlatform("youtube"));
  els.spotifyBtn.addEventListener("click", () => openPlatform("spotify"));
}

function tr(key) {
  return (TEXT[state.language] || TEXT.pt)[key] || key;
}

function applyLanguage() {
  els.languageBtn.textContent = tr("language_button");
  els.recognizeBtn.textContent = tr("recognize_tab");
  els.stopBtn.textContent = tr("stop");
  els.resultLabel.textContent = tr("result");
  els.historyToggleBtn.textContent = state.historyVisible ? tr("close_history") : tr("history");
  els.clearResultBtn.textContent = tr("clear_result");
  els.clearHistoryBtn.textContent = tr("clear_history");
  els.historyTitle.textContent = tr("history");
  renderHistory();
  if (!state.lastResult) {
    setStatus(state.engineReady ? tr("ready") : tr("loading_engine"));
  }
}

async function toggleLanguage() {
  state.language = state.language === "pt" ? "en" : "pt";
  await storageSet({ language: state.language });
  applyLanguage();
}

async function recognizeCurrentTab() {
  clearResult(false);
  setBusy(true);

  try {
    if (!state.engineReady) {
      setStatus(tr("loading_engine"));
      await globalThis.IchthusShazam.ready();
      state.engineReady = true;
    }
    setStatus(tr("listening"));
    const blob = await captureAudioBlob();
    setStatus(tr("identifying"));
    const result = await globalThis.IchthusShazam.recognizeWav(blob, {
      language: state.language,
      country: "BR"
    });
    const corrected = applyKnownCorrections(result);
    await showRecognition(corrected);
  } catch (error) {
    const message = recognitionErrorMessage(error);
    showError(message);
  } finally {
    cleanupCapture();
    setBusy(false);
  }
}

function captureAudioBlob() {
  return new Promise((resolve, reject) => {
    chrome.tabCapture.capture({ audio: true, video: false }, (stream) => {
      const chromeError = chrome.runtime.lastError;
      if (chromeError || !stream) {
        reject(new Error(chromeError?.message || tr("capture_error")));
        return;
      }

      state.mediaStream = stream;
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      state.audioContext = new AudioContextClass();
      state.audioSource = state.audioContext.createMediaStreamSource(stream);
      state.audioProcessor = state.audioContext.createScriptProcessor(4096, 1, 1);
      state.audioChunks = [];
      state.captureResolve = resolve;

      state.audioProcessor.onaudioprocess = (event) => {
        state.audioChunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };
      state.audioSource.connect(state.audioProcessor);
      state.audioProcessor.connect(state.audioContext.destination);
      state.audioSource.connect(state.audioContext.destination);
      state.stopTimer = setTimeout(stopRecording, RECORD_MS);
    });
  });
}

function stopRecording() {
  clearTimeout(state.stopTimer);
  state.stopTimer = null;
  if (state.captureResolve && state.audioContext) {
    const resolve = state.captureResolve;
    state.captureResolve = null;
    resolve(encodeWavBlob(state.audioChunks, state.audioContext.sampleRate));
  }
}

function cleanupCapture() {
  clearTimeout(state.stopTimer);
  state.stopTimer = null;
  if (state.mediaStream) {
    state.mediaStream.getTracks().forEach((track) => track.stop());
    state.mediaStream = null;
  }
  if (state.audioProcessor) {
    state.audioProcessor.disconnect();
    state.audioProcessor = null;
  }
  if (state.audioSource) {
    state.audioSource.disconnect();
    state.audioSource = null;
  }
  if (state.audioContext) {
    state.audioContext.close().catch(() => {});
    state.audioContext = null;
  }
  state.audioChunks = [];
  state.captureResolve = null;
}

function encodeWavBlob(chunks, sampleRate) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + length * 2);
  const view = new DataView(buffer);
  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + length * 2, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, length * 2, true);

  let offset = 44;
  chunks.forEach((chunk) => {
    chunk.forEach((sample) => {
      const clamped = Math.max(-1, Math.min(1, sample));
      view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
      offset += 2;
    });
  });
  return new Blob([buffer], { type: "audio/wav" });
}

function writeAscii(view, offset, text) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}

function applyKnownCorrections(result) {
  if (!result?.ok) {
    return result;
  }

  for (const rule of DEFAULT_CORRECTIONS) {
    if (!ruleMatches(result, rule)) {
      continue;
    }
    return {
      ...result,
      ...rule.replace,
      corrected: true,
      corrected_from: result.title || result.artist || "Shazam"
    };
  }

  return result;
}

function ruleMatches(result, rule) {
  const match = rule.match || {};
  const haystack = normalizeText(`${result.title} ${result.artist} ${result.album}`);

  return Object.entries(match).every(([key, value]) => {
    if (key === "contains") {
      const values = Array.isArray(value) ? value : [value];
      return values.every((item) => haystack.includes(normalizeText(item)));
    }
    return normalizeText(result[key]) === normalizeText(value);
  });
}

async function showRecognition(result) {
  if (!result?.ok) {
    throw new Error(tr("no_music"));
  }

  const query = makeQuery(result);
  state.lastResult = result;
  state.lastQuery = query;
  setStatus(tr("recognized"));
  els.songTitle.textContent = result.title || tr("unknown");
  els.songArtist.textContent = result.artist || tr("unknown");
  els.platformLinks.classList.remove("hidden");
  els.resultCard.classList.remove("hidden");
  const imageUrl = await setCover(result, query);
  await addHistory(result, query, imageUrl);
}

function makeQuery(result) {
  return [result.title, result.artist, result.album].filter(Boolean).join(" ");
}

async function setCover(result, query) {
  els.coverBox.innerHTML = "<span>♪</span>";
  const coverUrl = await findCoverUrl(result, query);
  if (!coverUrl) {
    return "";
  }

  const image = document.createElement("img");
  image.alt = "";
  image.referrerPolicy = "no-referrer";
  image.src = coverUrl;
  image.onload = () => {
    els.coverBox.textContent = "";
    els.coverBox.append(image);
  };
  return coverUrl;
}

async function findCoverUrl(result, query) {
  const direct = result.corrected ? "" : result.cover_url;
  if (direct && await canLoadImage(direct)) {
    return direct;
  }

  const queries = coverSearchQueries(result, query);
  for (const searchQuery of queries.slice(0, 3)) {
    const url = await findItunesArtwork(searchQuery);
    if (url && await canLoadImage(url)) {
      return url;
    }
  }

  for (const searchQuery of queries.slice(0, 3)) {
    const url = await findDeezerArtwork(searchQuery);
    if (url && await canLoadImage(url)) {
      return url;
    }
  }

  const youtubeUrl = await findYoutubeThumbnail(queries[0] || query);
  return youtubeUrl && await canLoadImage(youtubeUrl) ? youtubeUrl : "";
}

function canLoadImage(url) {
  return new Promise((resolve) => {
    if (!url) {
      resolve(false);
      return;
    }

    const image = new Image();
    let settled = false;
    const finish = (ok) => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      resolve(ok);
    };
    const timer = setTimeout(() => finish(false), 2800);
    image.onload = () => finish(true);
    image.onerror = () => finish(false);
    image.referrerPolicy = "no-referrer";
    image.src = url;
  });
}

function coverSearchQueries(result, query) {
  const candidates = [
    [result.title, result.artist, result.album].filter(Boolean).join(" "),
    [result.title, result.artist].filter(Boolean).join(" "),
    [result.artist, result.title].filter(Boolean).join(" "),
    [result.title, result.album].filter(Boolean).join(" "),
    query
  ];
  const seen = new Set();
  return candidates.filter((candidate) => {
    const key = normalizeText(candidate);
    if (!key || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

async function findItunesArtwork(query) {
  try {
    const url = new URL("https://itunes.apple.com/search");
    url.search = new URLSearchParams({
      term: query,
      media: "music",
      entity: "song",
      country: "BR",
      limit: "5"
    }).toString();
    const response = await fetch(url);
    const data = await response.json();
    const item = data.results?.find((entry) => entry.artworkUrl100);
    return item?.artworkUrl100
      ?.replace("100x100bb", "600x600bb")
      ?.replace("100x100cc", "600x600cc");
  } catch (_error) {
    return "";
  }
}

async function findDeezerArtwork(query) {
  try {
    const url = new URL("https://api.deezer.com/search");
    url.search = new URLSearchParams({ q: query, limit: "5" }).toString();
    const response = await fetch(url);
    const data = await response.json();
    const item = data.data?.find((entry) => entry.album);
    return item?.album?.cover_xl || item?.album?.cover_big || item?.album?.cover_medium || "";
  } catch (_error) {
    return "";
  }
}

async function findYoutubeThumbnail(query) {
  try {
    const url = `https://www.youtube.com/results?search_query=${encodeURIComponent(query)}`;
    const response = await fetch(url);
    const html = await response.text();
    const match = html.match(/"videoId":"([A-Za-z0-9_-]{11})"/);
    return match ? `https://img.youtube.com/vi/${match[1]}/hqdefault.jpg` : "";
  } catch (_error) {
    return "";
  }
}

async function addHistory(result, query, imageUrl = "") {
  const entry = {
    when: new Date().toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    }),
    title: result.title || tr("unknown"),
    artist: result.artist || tr("unknown"),
    album: result.album || "",
    release_date: result.release_date || "",
    cover_url: result.cover_url || "",
    image_url: imageUrl || result.cover_url || "",
    query,
    corrected: Boolean(result.corrected),
    corrected_from: result.corrected_from || ""
  };

  state.history = [entry, ...state.history].slice(0, MAX_HISTORY);
  await storageSet({ history: state.history });
  renderHistory();
}

function renderHistory() {
  const total = state.history.length;
  const countKey = total === 1 ? "history_count_one" : "history_count_many";
  els.historyCount.textContent = `${total} ${tr(countKey)}`;
  els.historyList.textContent = "";

  if (!total) {
    const empty = document.createElement("p");
    empty.className = "history-date";
    empty.textContent = tr("no_history");
    els.historyList.append(empty);
    return;
  }

  state.history.forEach((entry, index) => {
    const item = document.createElement("article");
    item.className = "history-item";

    const thumb = document.createElement("div");
    thumb.className = "history-thumb";
    const imageUrl = entry.image_url || (entry.corrected ? "" : entry.cover_url) || "";
    if (imageUrl) {
      const image = document.createElement("img");
      image.alt = "";
      image.referrerPolicy = "no-referrer";
      image.src = imageUrl;
      image.onerror = () => {
        image.remove();
        if (!thumb.querySelector(".history-placeholder")) {
          const placeholder = document.createElement("span");
          placeholder.className = "history-placeholder";
          placeholder.textContent = "♪";
          thumb.prepend(placeholder);
        }
      };
      thumb.append(image);
    } else {
      const placeholder = document.createElement("span");
      placeholder.className = "history-placeholder";
      placeholder.textContent = "♪";
      thumb.append(placeholder);
    }

    const badge = document.createElement("span");
    badge.className = "history-index";
    badge.textContent = String(index + 1).padStart(2, "0");
    thumb.append(badge);

    const text = document.createElement("div");
    text.className = "history-text";
    text.innerHTML = `
      <p class="history-title"></p>
      <p class="history-artist"></p>
      <p class="history-album"></p>
      <p class="history-date"></p>
    `;
    text.querySelector(".history-title").textContent = entry.title || tr("unknown");
    text.querySelector(".history-artist").textContent = entry.artist || tr("unknown");
    text.querySelector(".history-album").textContent = entry.album || "";
    text.querySelector(".history-date").textContent = entry.when || "";

    const report = document.createElement("button");
    report.className = "report-button";
    report.type = "button";
    report.textContent = tr("report");
    report.addEventListener("click", () => reportHistoryItem(entry));

    item.append(thumb, text, report);
    els.historyList.append(item);
  });
}

async function reportHistoryItem(entry) {
  const report = {
    reported_at: new Date().toLocaleString("pt-BR"),
    status: "pending",
    entry
  };
  state.reports = [report, ...state.reports].slice(0, MAX_HISTORY);
  await storageSet({ reports: state.reports });
  setStatus(tr("report_saved"));
}

function toggleHistory() {
  state.historyVisible = !state.historyVisible;
  els.historyPanel.classList.toggle("hidden", !state.historyVisible);
  els.historyToggleBtn.textContent = state.historyVisible ? tr("close_history") : tr("history");
}

async function clearHistory() {
  state.history = [];
  await storageSet({ history: [] });
  renderHistory();
}

function clearResult(resetStatus = true) {
  state.lastResult = null;
  state.lastQuery = "";
  els.resultCard.classList.add("hidden");
  els.platformLinks.classList.add("hidden");
  els.coverBox.innerHTML = "<span>♪</span>";
  els.songTitle.textContent = "-";
  els.songArtist.textContent = "-";
  if (resetStatus) {
    setStatus(state.engineReady ? tr("ready") : tr("loading_engine"));
  }
}

function recognitionErrorMessage(error) {
  const message = String(error?.message || error || "");
  if (/not recognized|não reconhecida/i.test(message)) {
    return tr("no_music");
  }
  if (/fetch|network|shazam request/i.test(message)) {
    return tr("network_error");
  }
  if (/vibra|webassembly|fingerprint/i.test(message)) {
    return tr("engine_error");
  }
  return message || tr("no_music");
}

function showError(message) {
  setStatus(message || tr("no_music"));
}

function setBusy(isBusy) {
  els.bars.classList.toggle("active", isBusy);
  els.recognizeBtn.disabled = isBusy;
  els.stopBtn.disabled = !isBusy;
}

function setStatus(text) {
  els.statusText.textContent = text;
}

function openPlatform(platform) {
  if (!state.lastQuery) {
    return;
  }
  const encoded = encodeURIComponent(state.lastQuery);
  const url = platform === "spotify"
    ? `https://open.spotify.com/search/${encoded}`
    : `https://www.youtube.com/results?search_query=${encoded}`;
  chrome.tabs.create({ url });
}

function normalizeText(value) {
  return String(value || "").toLocaleLowerCase().trim().replace(/\s+/g, " ");
}

function storageGet(defaults) {
  return new Promise((resolve) => {
    chrome.storage.local.get(defaults, resolve);
  });
}

function storageSet(values) {
  return new Promise((resolve) => {
    chrome.storage.local.set(values, resolve);
  });
}
