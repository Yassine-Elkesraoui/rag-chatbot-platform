"""chat_ui.py

HTTP route serving the browser chat frontend.

Exposes one endpoint:

    GET /chat/ui    A self-contained HTML page that lets a user ask a
                    question and see the answer, its grounding status,
                    the retrieved sources with their similarity scores,
                    and the model that generated it.

The page talks to the API same-origin via fetch, calling POST /chat/rag
by default and POST /chat when the baseline toggle is on. Because both
calls are relative, the page works unchanged on localhost and on the
Hugging Face Space with no configuration.

Unlike /eval/dashboard, this page loads NOTHING from a CDN: all CSS and
JS are inline. The deployment therefore has zero third-party runtime
dependencies, which matters more here than consistency with the older
page, since this is the entry point a Space visitor actually lands on.

This module is a thin presentation boundary, consistent with the
project's four-tier architecture: it holds no chat logic at all. The
browser calls the existing endpoints directly; this route only serves
the document.
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from api.utils.logger import logger


router = APIRouter(tags=["Chat"])


@router.get(
    "/chat/ui",
    response_class=HTMLResponse,
    summary="Browser chat interface",
    description=(
        "Serves a self-contained HTML page for asking questions "
        "interactively. The page calls POST /chat/rag (retrieval-"
        "augmented) or POST /chat (baseline) same-origin and renders "
        "the answer, its grounded/ungrounded status, the retrieved "
        "sources with similarity scores, and the reported model."
    ),
)
def chat_ui() -> HTMLResponse:
    """Serve the self-contained chat frontend."""
    logger.info("GET /chat/ui | serving chat page")
    return HTMLResponse(content=_CHAT_HTML)


# ──────────────────────────────────────────────────────────────────────
# Static HTML for the chat frontend.
# Kept as a module-level constant so the route stays a thin boundary,
# matching the approach in eval_dashboard.py: no template engine and no
# static-file mount, which keeps the Docker / Hugging Face Spaces
# deployment simple and dependency-light.
#
# NOTE: this is a plain (non-f) string and is never passed through
# .format(), so the braces in the inline CSS and JS need no escaping.
# ──────────────────────────────────────────────────────────────────────
_CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RAG Chatbot</title>
  <style>
    :root { --bg:#0f1117; --card:#1a1d27; --ink:#e6e8ee; --muted:#9aa0b0;
            --rag:#4f8cff; --base:#ff7a59; --line:#2a2e3c;
            --ok:#3fb950; --warn:#e0b341; --err:#ff7a7a; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--ink);
           font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }
    header { padding:28px 32px 8px; }
    h1 { margin:0 0 4px; font-size:22px; }
    .sub { color:var(--muted); font-size:14px; }
    .sub a { color:var(--rag); text-decoration:none; }
    .sub a:hover { text-decoration:underline; }
    .wrap { max-width:900px; padding:20px 32px 60px; }
    .card { background:var(--card); border:1px solid var(--line);
            border-radius:14px; padding:20px; margin-bottom:20px; }

    /* ── mode toggle ─────────────────────────────────────────── */
    .modes { display:flex; gap:8px; margin-bottom:14px; }
    .mode { flex:0 0 auto; padding:7px 16px; border-radius:999px;
            border:1px solid var(--line); background:#222637;
            color:var(--muted); font-size:13px; cursor:pointer;
            font-family:inherit; }
    .mode[aria-pressed="true"] { color:#fff; border-color:transparent; }
    #mode-rag[aria-pressed="true"] { background:var(--rag); }
    #mode-base[aria-pressed="true"] { background:var(--base); }
    .mode-hint { color:var(--muted); font-size:13px; margin:0 0 14px; }

    /* ── input ───────────────────────────────────────────────── */
    textarea { width:100%; min-height:92px; resize:vertical;
               background:var(--bg); color:var(--ink);
               border:1px solid var(--line); border-radius:10px;
               padding:12px 14px; font-size:15px; font-family:inherit;
               line-height:1.5; }
    textarea:focus { outline:none; border-color:var(--rag); }
    .row { display:flex; align-items:center; gap:14px; margin-top:12px;
           flex-wrap:wrap; }
    button.ask { padding:9px 22px; border:none; border-radius:10px;
                 background:var(--rag); color:#fff; font-size:14px;
                 font-weight:600; cursor:pointer; font-family:inherit; }
    button.ask:disabled { opacity:.5; cursor:not-allowed; }
    .counter { color:var(--muted); font-size:12px; margin-left:auto; }
    .kbd { color:var(--muted); font-size:12px; }

    /* ── loading ─────────────────────────────────────────────── */
    .loading { display:none; align-items:center; gap:12px;
               color:var(--muted); font-size:14px; }
    .loading.on { display:flex; }
    .spinner { width:16px; height:16px; flex:0 0 16px; border-radius:50%;
               border:2px solid var(--line); border-top-color:var(--rag);
               animation:spin .8s linear infinite; }
    @keyframes spin { to { transform:rotate(360deg); } }
    .elapsed { font-variant-numeric:tabular-nums; color:var(--ink); }

    /* ── result ──────────────────────────────────────────────── */
    #result { display:none; }
    .badges { display:flex; gap:8px; align-items:center; flex-wrap:wrap;
              margin-bottom:14px; }
    .badge { display:inline-block; padding:3px 12px; border-radius:999px;
             font-size:12px; font-weight:600; letter-spacing:.02em; }
    .badge.grounded { background:rgba(63,185,80,.15); color:var(--ok);
                      border:1px solid rgba(63,185,80,.35); }
    .badge.ungrounded { background:rgba(224,179,65,.15); color:var(--warn);
                        border:1px solid rgba(224,179,65,.35); }
    .badge.baseline { background:rgba(255,122,89,.15); color:var(--base);
                      border:1px solid rgba(255,122,89,.35); }
    .badge.meta { background:#222637; color:var(--muted);
                  border:1px solid var(--line); font-weight:400; }
    .answer { white-space:pre-wrap; line-height:1.65; font-size:15px; }
    .note { color:var(--muted); font-size:13px; margin-top:14px;
            padding-top:14px; border-top:1px solid var(--line); }

    /* ── sources ─────────────────────────────────────────────── */
    h2 { font-size:15px; margin:0 0 4px; }
    .hint { color:var(--muted); font-size:13px; margin:0 0 14px; }
    .src { border:1px solid var(--line); border-radius:10px; padding:14px;
           margin-bottom:12px; background:var(--bg); }
    .src-head { display:flex; align-items:center; gap:10px;
                margin-bottom:10px; flex-wrap:wrap; }
    .src-rank { flex:0 0 auto; width:22px; height:22px; border-radius:6px;
                background:var(--rag); color:#fff; font-size:12px;
                font-weight:700; display:flex; align-items:center;
                justify-content:center; }
    .src-id { color:var(--muted); font-size:12px; word-break:break-all; }
    .src-score { margin-left:auto; font-size:12px; color:var(--ink);
                 font-variant-numeric:tabular-nums; }
    .bar { height:4px; background:var(--line); border-radius:999px;
           overflow:hidden; margin-bottom:10px; }
    .bar i { display:block; height:100%; background:var(--rag); }
    .src-body { white-space:pre-wrap; font-size:13px; line-height:1.6;
                color:var(--muted); max-height:190px; overflow-y:auto; }

    /* ── error ───────────────────────────────────────────────── */
    #error { display:none; color:var(--err); font-size:14px;
             border:1px solid rgba(255,122,122,.35);
             background:rgba(255,122,122,.08); }
  </style>
</head>
<body>
  <header>
    <h1>RAG Chatbot</h1>
    <div class="sub">
      Trilingual retrieval-augmented chat (EN / FR / PT) &middot;
      Master's Thesis, ISLA Gaia &middot;
      <a href="/eval/dashboard">evaluation dashboard</a>
    </div>
  </header>

  <div class="wrap">
    <div class="card">
      <div class="modes">
        <button type="button" class="mode" id="mode-rag" aria-pressed="true">RAG</button>
        <button type="button" class="mode" id="mode-base" aria-pressed="false">Baseline</button>
      </div>
      <p class="mode-hint" id="mode-hint"></p>

      <textarea id="q" placeholder="Ask a question about the indexed corpus..."
                maxlength="2000" autofocus></textarea>
      <div class="row">
        <button type="button" class="ask" id="ask">Ask</button>
        <span class="kbd">Ctrl + Enter</span>
        <span class="counter" id="counter">0 / 2000</span>
      </div>
      <div class="row loading" id="loading">
        <span class="spinner"></span>
        <span id="loading-text"></span>
        <span class="elapsed" id="elapsed">0s</span>
      </div>
    </div>

    <div class="card" id="error"></div>

    <div id="result">
      <div class="card">
        <div class="badges" id="badges"></div>
        <div class="answer" id="answer"></div>
        <div class="note" id="note"></div>
      </div>
      <div class="card" id="sources-card">
        <h2>Sources</h2>
        <p class="hint" id="sources-hint"></p>
        <div id="sources"></div>
      </div>
    </div>
  </div>

  <script>
    // Same-origin endpoints. Relative paths keep the page working
    // unchanged on localhost and on the Hugging Face Space.
    var RAG_URL = "/chat/rag";
    var BASE_URL = "/chat";

    // Generation on local Ollama can take ~45s; allow generous headroom
    // before giving up so a slow-but-alive request is not killed.
    var TIMEOUT_MS = 120000;

    // POST /chat enforces min_length=3 on the question and POST /chat/rag
    // enforces min_length=1. We apply the stricter bound in both modes so
    // toggling to baseline can never produce a surprise 422.
    var MIN_CHARS = 3;

    var mode = "rag";
    var busy = false;
    var timer = null;

    var els = {
      q: document.getElementById("q"),
      ask: document.getElementById("ask"),
      counter: document.getElementById("counter"),
      modeRag: document.getElementById("mode-rag"),
      modeBase: document.getElementById("mode-base"),
      modeHint: document.getElementById("mode-hint"),
      loading: document.getElementById("loading"),
      loadingText: document.getElementById("loading-text"),
      elapsed: document.getElementById("elapsed"),
      result: document.getElementById("result"),
      badges: document.getElementById("badges"),
      answer: document.getElementById("answer"),
      note: document.getElementById("note"),
      sourcesCard: document.getElementById("sources-card"),
      sourcesHint: document.getElementById("sources-hint"),
      sources: document.getElementById("sources"),
      error: document.getElementById("error")
    };

    // ── mode ──────────────────────────────────────────────────
    function setMode(next) {
      if (busy) return;
      mode = next;
      var isRag = mode === "rag";
      els.modeRag.setAttribute("aria-pressed", isRag ? "true" : "false");
      els.modeBase.setAttribute("aria-pressed", isRag ? "false" : "true");
      els.ask.style.background = isRag ? "var(--rag)" : "var(--base)";
      els.modeHint.textContent = isRag
        ? "POST /chat/rag - retrieves context from the vector store, then answers from it."
        : "POST /chat - baseline: the same question goes straight to the model, with no retrieval.";
    }
    els.modeRag.addEventListener("click", function () { setMode("rag"); });
    els.modeBase.addEventListener("click", function () { setMode("baseline"); });

    // ── helpers ───────────────────────────────────────────────
    function badge(cls, text) {
      var b = document.createElement("span");
      b.className = "badge " + cls;
      b.textContent = text;
      return b;
    }

    function clear(node) {
      while (node.firstChild) node.removeChild(node.firstChild);
    }

    function showError(message) {
      els.error.textContent = message;
      els.error.style.display = "block";
    }

    function setBusy(on) {
      busy = on;
      els.ask.disabled = on;
      els.q.disabled = on;
      els.loading.className = on ? "row loading on" : "row loading";
      if (on) {
        els.loadingText.textContent = mode === "rag"
          ? "Embedding question, searching the store, generating..."
          : "Generating without retrieval...";
        var started = Date.now();
        els.elapsed.textContent = "0s";
        timer = setInterval(function () {
          els.elapsed.textContent =
            Math.round((Date.now() - started) / 1000) + "s";
        }, 250);
      } else if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }

    els.q.addEventListener("input", function () {
      els.counter.textContent = els.q.value.length + " / 2000";
    });

    els.q.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) ask();
    });
    els.ask.addEventListener("click", ask);

    // ── rendering ─────────────────────────────────────────────
    function renderSources(sources) {
      clear(els.sources);
      sources.forEach(function (s, i) {
        var card = document.createElement("div");
        card.className = "src";

        var head = document.createElement("div");
        head.className = "src-head";

        var rank = document.createElement("span");
        rank.className = "src-rank";
        rank.textContent = String(i + 1);
        head.appendChild(rank);

        var id = document.createElement("span");
        id.className = "src-id";
        id.textContent = "chunk " + s.chunk_id + "  (index " + s.index + ")";
        head.appendChild(id);

        var score = document.createElement("span");
        score.className = "src-score";
        score.textContent = "similarity " + Number(s.score).toFixed(4);
        head.appendChild(score);

        card.appendChild(head);

        // Score bar. Cosine similarity is in [0, 1] for the normalized
        // embeddings this project uses, so the score maps to width directly.
        var bar = document.createElement("div");
        bar.className = "bar";
        var fill = document.createElement("i");
        var pct = Math.max(0, Math.min(1, Number(s.score))) * 100;
        fill.style.width = pct + "%";
        bar.appendChild(fill);
        card.appendChild(bar);

        // textContent, never innerHTML: chunk content is user-uploaded
        // document text and must never be interpreted as markup.
        var body = document.createElement("div");
        body.className = "src-body";
        body.textContent = s.content;
        card.appendChild(body);

        els.sources.appendChild(card);
      });
    }

    function renderRag(data) {
      clear(els.badges);
      var sources = data.sources || [];
      if (data.grounded) {
        els.badges.appendChild(badge("grounded",
          "GROUNDED - " + sources.length +
          (sources.length === 1 ? " source" : " sources")));
      } else {
        els.badges.appendChild(badge("ungrounded",
          "UNGROUNDED - answered from model knowledge"));
      }
      els.badges.appendChild(badge("meta", "model: " + data.model));
      // Client-side, not an API field: RAGChatResponse carries no status.
      // renderRag() is only reached after res.ok, so reaching here means
      // the request returned 200.
      els.badges.appendChild(badge("meta", "status: success"));

      els.answer.textContent = data.answer;
      els.note.textContent = data.grounded
        ? "Answer generated from the retrieved context below."
        : "No stored chunk cleared the relevance threshold, so the model " +
          "answered from its own knowledge. This is the documented fallback, " +
          "not an error.";

      if (sources.length) {
        els.sourcesCard.style.display = "block";
        els.sourcesHint.textContent =
          "Chunks retrieved above the relevance threshold, ordered by similarity.";
        renderSources(sources);
      } else {
        els.sourcesCard.style.display = "none";
      }
    }

    function renderBaseline(data) {
      clear(els.badges);
      els.badges.appendChild(badge("baseline", "BASELINE - no retrieval"));
      // POST /chat returns ChatResponse (question, answer, status) and
      // carries no model field: its contract is frozen as the comparison
      // arm of the thesis evaluation. Both endpoints resolve their LLM
      // through get_llm_service(), so the provider is the one /chat/rag
      // names -- we can say that much without inventing a field.
      els.badges.appendChild(badge("meta", "model: same provider as RAG"));
      if (data.status) {
        els.badges.appendChild(badge("meta", "status: " + data.status));
      }
      els.answer.textContent = data.answer;
      els.note.textContent =
        "Baseline answer: the question went straight to the model with no " +
        "retrieval, so there are no sources and no grounding flag.";
      els.sourcesCard.style.display = "none";
    }

    // ── request ───────────────────────────────────────────────
    async function ask() {
      if (busy) return;
      var question = els.q.value.trim();

      els.error.style.display = "none";
      if (question.length < MIN_CHARS) {
        showError("Please enter a question of at least " + MIN_CHARS +
                  " characters.");
        return;
      }

      setBusy(true);
      var controller = new AbortController();
      var abortTimer = setTimeout(function () { controller.abort(); },
                                  TIMEOUT_MS);

      try {
        var res = await fetch(mode === "rag" ? RAG_URL : BASE_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: question }),
          signal: controller.signal
        });

        var data = null;
        try { data = await res.json(); } catch (e) { data = null; }

        if (!res.ok) {
          var detail = data && data.detail ? data.detail : "HTTP " + res.status;
          if (typeof detail !== "string") detail = JSON.stringify(detail);
          showError(detail);
          els.result.style.display = "none";
          return;
        }

        if (mode === "rag") renderRag(data);
        else renderBaseline(data);
        els.result.style.display = "block";
      } catch (e) {
        els.result.style.display = "none";
        if (e.name === "AbortError") {
          showError("The request timed out after " + (TIMEOUT_MS / 1000) +
                    "s. Local generation is slow; the model may still be " +
                    "loading. Try again.");
        } else {
          showError("Request failed: " + e.message);
        }
      } finally {
        clearTimeout(abortTimer);
        setBusy(false);
      }
    }

    setMode("rag");
  </script>
</body>
</html>"""
