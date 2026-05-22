/**
 * BIO334 Teaching App - Chat Module
 *
 * Handles message sending, SSE streaming responses,
 * markdown rendering, and code insertion into the editor.
 */

(function () {
  "use strict";

  var messagesContainer = null;
  var chatForm = null;
  var chatInput = null;
  var btnSend = null;
  var isStreaming = false;
  var abortController = null;
  var chatMessages = []; // {role, content} array for persistence

  /* ---- Markdown Rendering (lightweight) ---- */
  function renderMarkdown(text) {
    // Escape HTML first
    var html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Code blocks: ```lang\n...\n```
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function (match, lang, code) {
      var id = "code-" + Math.random().toString(36).substr(2, 8);
      return (
        '<div class="code-block-wrapper">' +
        '<button class="btn-copy-code" onclick="window.copyCode(\'' + id + '\')" aria-label="Copy code">Copy</button>' +
        '<button class="btn-insert-code" onclick="window.insertCode(\'' + id + '\')" aria-label="Insert code into editor">Insert into editor</button>' +
        '<pre><code id="' + id + '">' + code.trim() + "</code></pre>" +
        "</div>"
      );
    });

    // Inline code: `code`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold: **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italic: *text*
    html = html.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");

    // Headers: # ## ### etc.
    html = html.replace(/^#{3}\s+(.+)$/gm, "<h4>$1</h4>");
    html = html.replace(/^#{2}\s+(.+)$/gm, "<h3>$1</h3>");
    html = html.replace(/^#{1}\s+(.+)$/gm, "<h3>$1</h3>");

    // Horizontal rule: ---
    html = html.replace(/^---+$/gm, "<hr>");

    // Tables: detect and convert markdown tables
    html = html.replace(/((?:^[^\n]*\|[^\n]*\n)+)/gm, function (tableBlock) {
      var rows = tableBlock.trim().split("\n");
      if (rows.length < 2) return tableBlock;
      var tableHtml = '<table class="md-table">';
      var isHeader = true;
      for (var r = 0; r < rows.length; r++) {
        var row = rows[r].trim();
        if (!row) continue;
        // Skip separator rows (|---|---|)
        if (/^\|?[\s\-:|]+\|?$/.test(row)) {
          isHeader = false;
          continue;
        }
        var cells = row.split("|").filter(function (c, i, a) {
          // Remove empty first/last from leading/trailing pipes
          return !(i === 0 && c.trim() === "") && !(i === a.length - 1 && c.trim() === "");
        });
        var tag = isHeader ? "th" : "td";
        tableHtml += "<tr>";
        for (var c = 0; c < cells.length; c++) {
          tableHtml += "<" + tag + ">" + cells[c].trim() + "</" + tag + ">";
        }
        tableHtml += "</tr>";
        if (isHeader) isHeader = false;
      }
      tableHtml += "</table>";
      return tableHtml;
    });

    // Unordered lists
    html = html.replace(/^[\s]*[-*]\s+(.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>(\n)?)+/g, "<ul>$&</ul>");

    // Ordered lists
    html = html.replace(/^[\s]*\d+\.\s+(.+)$/gm, "<li>$1</li>");
    html = html.replace(/(?<!<\/ul>)(<li>.*?<\/li>(\n)?)+/g, function (match) {
      if (match.indexOf("<ul>") === -1) {
        return "<ol>" + match + "</ol>";
      }
      return match;
    });

    // Paragraphs: double newlines
    html = html.replace(/\n\n+/g, "</p><p>");
    html = "<p>" + html + "</p>";

    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, "");
    // Don't wrap block elements in <p>
    html = html.replace(/<p>(<div|<ul|<ol|<pre|<h[1-6]|<table|<hr)/g, "$1");
    html = html.replace(/(<\/div>|<\/ul>|<\/ol>|<\/pre>|<\/h[1-6]>|<\/table>|<hr>)<\/p>/g, "$1");

    return html;
  }

  /* ---- Interactive Choices ---- */

  /**
   * Detect multiple-choice patterns in a rendered message element
   * and convert them to clickable buttons.
   *
   * Supported patterns (in the raw markdown, pre-render):
   *   A) text  /  B) text      (letter + paren)
   *   A. text  /  B. text      (letter + dot)
   *   1) text  /  2) text      (number + paren)
   *   1. text  /  2. text      (number + dot — rendered as <ol>)
   *
   * The function works on the rendered DOM: it finds <li> items inside
   * <ol> or <ul> that look like choices, or <p>/<br>-separated lines
   * starting with a choice label.
   */
  function makeChoicesClickable(msgDiv) {
    if (!msgDiv) return;

    // Only convert lists where ALL items have explicit choice labels:
    //   A) / B) / C)   or   a) / b) / c)   or   A. / B. / C.
    var labelPattern = /^[A-Da-d][\).:\]]\s/;

    // Strategy 1: Find <li> elements that ALL start with a choice label
    var lists = msgDiv.querySelectorAll("ul, ol");
    for (var li = 0; li < lists.length; li++) {
      var listEl = lists[li];
      var items = listEl.querySelectorAll("li");
      if (items.length < 2 || items.length > 6) continue;

      // ALL items must start with a choice label and be short
      var allLabeled = true;
      for (var j = 0; j < items.length; j++) {
        var txt = items[j].textContent.trim();
        if (!labelPattern.test(txt) || txt.length > 150) {
          allLabeled = false;
          break;
        }
        if (items[j].querySelector("pre, .code-block-wrapper")) {
          allLabeled = false;
          break;
        }
      }
      if (!allLabeled) continue;

      // Convert to choice buttons
      var choiceGroup = document.createElement("div");
      choiceGroup.className = "choice-group";
      choiceGroup.setAttribute("role", "group");
      choiceGroup.setAttribute("aria-label", "Select your answer");

      for (var m = 0; m < items.length; m++) {
        var text = items[m].textContent.trim();
        var btn = document.createElement("button");
        btn.className = "choice-btn";
        btn.innerHTML = items[m].innerHTML;
        btn.setAttribute("data-choice", text);
        btn.setAttribute("aria-label", "Choose: " + text);
        choiceGroup.appendChild(btn);
      }

      listEl.parentNode.replaceChild(choiceGroup, listEl);
    }

    // Strategy 2: Find paragraph lines with A)/B)/C)/D) patterns
    var paragraphs = msgDiv.querySelectorAll("p");
    for (var pi = 0; pi < paragraphs.length; pi++) {
      var p = paragraphs[pi];
      var pHtml = p.innerHTML;
      var lines = pHtml.split(/<br\s*\/?>/i);
      if (lines.length < 2 || lines.length > 6) continue;

      // ALL lines must match the label pattern
      var choiceLines = [];
      var allMatch = true;
      for (var cl = 0; cl < lines.length; cl++) {
        var stripped = lines[cl].replace(/<[^>]+>/g, "").trim();
        if (!stripped) continue; // skip empty lines
        if (labelPattern.test(stripped) && stripped.length <= 150) {
          choiceLines.push({ html: lines[cl].trim(), text: stripped });
        } else {
          allMatch = false;
          break;
        }
      }

      if (!allMatch || choiceLines.length < 2) continue;

      var group = document.createElement("div");
      group.className = "choice-group";
      group.setAttribute("role", "group");
      group.setAttribute("aria-label", "Select your answer");

      for (var cb = 0; cb < choiceLines.length; cb++) {
        var cBtn = document.createElement("button");
        cBtn.className = "choice-btn";
        cBtn.innerHTML = choiceLines[cb].html;
        cBtn.setAttribute("data-choice", choiceLines[cb].text);
        group.appendChild(cBtn);
      }

      p.parentNode.replaceChild(group, p);
    }

    // Attach click handlers to all choice buttons in this message
    var allBtns = msgDiv.querySelectorAll(".choice-btn");
    if (allBtns.length > 0) {
      allBtns.forEach(function (btn) {
        btn.addEventListener("click", function () {
          var choice = this.getAttribute("data-choice");
          // Highlight selected
          var siblings = this.parentNode.querySelectorAll(".choice-btn");
          siblings.forEach(function (s) { s.classList.remove("selected"); s.disabled = true; });
          this.classList.add("selected");
          // Send as message
          sendMessage(choice);
        });
      });
    }
  }

  /* ---- Code Actions ---- */
  window.copyCode = function (id) {
    var el = document.getElementById(id);
    if (el) {
      navigator.clipboard.writeText(el.textContent).then(function () {
        var btn = el.closest(".code-block-wrapper").querySelector(".btn-copy-code");
        var orig = btn.textContent;
        btn.textContent = "Copied!";
        setTimeout(function () { btn.textContent = orig; }, 1500);
      });
    }
  };

  window.insertCode = function (id) {
    var el = document.getElementById(id);
    if (el) {
      Bio334.showEditor();
      if (typeof window.setEditorCode === "function") {
        window.setEditorCode(el.textContent);
      }
      if (Bio334.isMobile) {
        Bio334.switchMobilePanel("editor");
      }
    }
  };

  /* ---- Auto-Insert Code into Editor ---- */

  // Minimum lines for auto-insert (skip short snippets like `print("hello")`)
  var AUTO_INSERT_MIN_LINES = 3;

  /**
   * Extract Python code blocks from the raw markdown response and
   * auto-insert the best candidate into the editor.
   *
   * Selection logic:
   * - Only ```python or ``` blocks (not inline code)
   * - Must be >= AUTO_INSERT_MIN_LINES lines
   * - Pick the longest qualifying block (most complete code)
   * - Show a visual indicator on the message
   */
  function autoInsertCode(fullText, msgDiv) {
    if (typeof window.setEditorCode !== "function") return;

    // Extract all fenced code blocks: ```lang\n...\n```
    var pattern = /```(\w*)\n([\s\S]*?)```/g;
    var match;
    var bestCode = null;
    var bestLines = 0;

    while ((match = pattern.exec(fullText)) !== null) {
      var lang = match[1].toLowerCase();
      var code = match[2].trim();
      // Accept python, py, or unspecified language
      if (lang && lang !== "python" && lang !== "py") continue;
      var lineCount = code.split("\n").length;
      if (lineCount >= AUTO_INSERT_MIN_LINES && lineCount > bestLines) {
        bestCode = code;
        bestLines = lineCount;
      }
    }

    if (!bestCode) return;

    // Insert into editor
    window.setEditorCode(bestCode);

    // Show a toast-like indicator on the message
    if (msgDiv) {
      var badge = document.createElement("div");
      badge.className = "auto-insert-badge";
      badge.innerHTML = '<span class="auto-insert-icon" aria-hidden="true">&#10148;</span> Code sent to editor (' + bestLines + ' lines)';
      msgDiv.appendChild(badge);
    }

    // On mobile, don't auto-switch — let them read the explanation first
  }

  /* ---- Message Rendering ---- */
  function addMessage(role, content, skipScroll, skipTracking) {
    var div = document.createElement("div");
    div.className = "chat-msg " + role;
    div.setAttribute("role", "article");
    div.setAttribute("aria-label", role === "user" ? "Your message" : "Teaching assistant message");

    if (role === "assistant" || role === "system") {
      div.innerHTML = renderMarkdown(content);
      makeChoicesClickable(div);
    } else {
      div.textContent = content;
    }

    messagesContainer.appendChild(div);
    if (!skipScroll) {
      scrollToBottom();
    }
    // Track message for persistence (skip system messages and restored ones)
    if (!skipTracking && (role === "user" || role === "assistant") && content) {
      chatMessages.push({ role: role, content: content });
    }
    return div;
  }

  function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  /* ---- Model Indicator ---- */
  var modelIndicatorEl = null;
  var slowResponseTimer = null;

  function ensureModelIndicator() {
    if (modelIndicatorEl) return modelIndicatorEl;
    modelIndicatorEl = document.getElementById("model-indicator");
    if (!modelIndicatorEl) {
      // Create it above the chat input
      modelIndicatorEl = document.createElement("div");
      modelIndicatorEl.id = "model-indicator";
      modelIndicatorEl.className = "model-indicator";
      var formParent = chatForm ? chatForm.parentElement : null;
      if (formParent) {
        formParent.insertBefore(modelIndicatorEl, chatForm);
      }
    }
    return modelIndicatorEl;
  }

  function formatModelName(model) {
    // "claude-opus-4-6" -> "Opus 4.6"
    // "claude-sonnet-4-6" -> "Sonnet 4.6"
    // "claude-haiku-4-5-20251001" -> "Haiku 4.5"
    var m = model.replace("claude-", "");
    if (m.indexOf("opus") >= 0) return "Opus " + extractVersion(m);
    if (m.indexOf("sonnet") >= 0) return "Sonnet " + extractVersion(m);
    if (m.indexOf("haiku") >= 0) return "Haiku " + extractVersion(m);
    return model;
  }

  function extractVersion(s) {
    // "opus-4-6" -> "4.6", "sonnet-4-6" -> "4.6", "haiku-4-5-20251001" -> "4.5"
    var match = s.match(/(\d+)-(\d+)/);
    return match ? match[1] + "." + match[2] : "";
  }

  function updateModelIndicator(model, backend) {
    var el = ensureModelIndicator();
    var name = formatModelName(model);
    var backendLabel = backend === "claude-code" ? "Claude Code" : "API";
    el.innerHTML = '<span class="model-name" title="' + model + '">' + name + '</span>'
      + ' <span class="model-backend">via ' + backendLabel + '</span>';
    el.style.display = "block";
  }

  function updateResponseStats(durationMs, costUsd) {
    var el = ensureModelIndicator();
    var sec = (durationMs / 1000).toFixed(1);
    var statsSpan = el.querySelector(".model-stats");
    if (!statsSpan) {
      statsSpan = document.createElement("span");
      statsSpan.className = "model-stats";
      el.appendChild(statsSpan);
    }
    var costStr = costUsd ? " ($" + costUsd.toFixed(4) + ")" : "";
    statsSpan.textContent = " | " + sec + "s" + costStr;
  }

  function showSlowResponseTip() {
    var el = ensureModelIndicator();
    var tipSpan = el.querySelector(".slow-tip");
    if (!tipSpan) {
      tipSpan = document.createElement("span");
      tipSpan.className = "slow-tip";
      el.appendChild(tipSpan);
    }
    tipSpan.innerHTML = ' | <span title="Opus is more capable but slower. '
      + 'You can switch to Sonnet in Claude Code settings for faster responses.'
      + '">Slow? Try a faster model</span>';
  }

  function clearSlowResponseTip() {
    if (slowResponseTimer) {
      clearTimeout(slowResponseTimer);
      slowResponseTimer = null;
    }
    if (modelIndicatorEl) {
      var tip = modelIndicatorEl.querySelector(".slow-tip");
      if (tip) tip.remove();
    }
  }

  /* ---- Typing Indicator ---- */
  function showTypingIndicator() {
    var indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.id = "typing-indicator";
    indicator.setAttribute("role", "status");
    indicator.setAttribute("aria-label", "Teaching assistant is typing");
    indicator.innerHTML = "<span></span><span></span><span></span>";
    messagesContainer.appendChild(indicator);
    scrollToBottom();
  }

  function removeTypingIndicator() {
    var indicator = document.getElementById("typing-indicator");
    if (indicator) indicator.remove();
  }

  /* ---- Send / Stop Button Toggle ---- */
  function setSendMode() {
    if (!btnSend) return;
    btnSend.disabled = false;
    btnSend.classList.remove("btn-stop");
    btnSend.innerHTML = '<span aria-hidden="true">&#10148;</span> Send';
    btnSend.setAttribute("aria-label", "Send message");
  }

  function setStopMode() {
    if (!btnSend) return;
    btnSend.disabled = false;
    btnSend.classList.add("btn-stop");
    btnSend.innerHTML = '<span aria-hidden="true">&#9632;</span> Stop';
    btnSend.setAttribute("aria-label", "Stop response");
  }

  function cancelStreaming() {
    if (!isStreaming) return;
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
  }

  /* ---- SSE Streaming ---- */
  function sendMessage(message) {
    if (!message.trim()) return;

    // If currently streaming, cancel instead of sending
    if (isStreaming) {
      cancelStreaming();
      return;
    }

    addMessage("user", message);
    chatInput.value = "";
    chatInput.style.height = "auto";
    isStreaming = true;
    setStopMode();

    showTypingIndicator();
    clearSlowResponseTip();
    // Show slow-response tip after 10 seconds
    slowResponseTimer = setTimeout(showSlowResponseTip, 10000);

    var payload = {
      message: message,
      session_id: Bio334.sessionId,
    };

    // Use fetch with SSE (with AbortController for cancellation)
    abortController = new AbortController();
    Bio334.apiRequest("POST", "/api/chat", payload, abortController.signal)
      .then(function (response) {
        if (!response.ok) {
          removeTypingIndicator();
          throw new Error("Server error: " + response.status);
        }

        var contentType = response.headers.get("content-type") || "";

        if (contentType.includes("text/event-stream")) {
          // SSE streaming — keep typing indicator until first text chunk
          var reader = response.body.getReader();
          var decoder = new TextDecoder();
          var buffer = "";
          var msgDiv = null;
          var fullText = "";
          var typingRemoved = false;

          function processChunk() {
            return reader.read().then(function (result) {
              if (result.done) {
                finishStream(fullText, msgDiv);
                return;
              }

              buffer += decoder.decode(result.value, { stream: true });
              var lines = buffer.split("\n");
              buffer = lines.pop(); // Keep incomplete line

              for (var i = 0; i < lines.length; i++) {
                var line = lines[i].trim();
                if (line.startsWith("data: ")) {
                  var data = line.substring(6);
                  if (data === "[DONE]") {
                    finishStream(fullText, msgDiv);
                    return;
                  }

                  try {
                    var parsed = JSON.parse(data);

                    if (parsed.type === "meta") {
                      // Model info or completion stats
                      if (parsed.model) {
                        updateModelIndicator(parsed.model, parsed.backend);
                      }
                      if (parsed.duration_ms) {
                        updateResponseStats(parsed.duration_ms, parsed.cost_usd);
                      }
                    } else if (parsed.type === "text" || parsed.type === "content_block_delta") {
                      var chunk = parsed.text || parsed.delta || "";
                      fullText += chunk;

                      if (!typingRemoved) {
                        removeTypingIndicator();
                        typingRemoved = true;
                      }
                      if (!msgDiv) {
                        msgDiv = addMessage("assistant", "");
                      }
                      msgDiv.innerHTML = renderMarkdown(fullText);
                      scrollToBottom();
                    } else if (parsed.type === "show_editor") {
                      Bio334.showEditor();
                    } else if (parsed.type === "code") {
                      Bio334.showEditor();
                      if (typeof window.setEditorCode === "function") {
                        window.setEditorCode(parsed.code);
                      }
                    } else if (parsed.type === "status") {
                      Bio334.updateStatusBar(parsed.day, parsed.phase, parsed.topic);
                    } else if (parsed.type === "error") {
                      addMessage("system", "Error: " + (parsed.message || "Unknown error"));
                    }
                  } catch (e) {
                    // Plain text chunk
                    fullText += data;
                    if (!msgDiv) {
                      msgDiv = addMessage("assistant", "");
                    }
                    msgDiv.innerHTML = renderMarkdown(fullText);
                    scrollToBottom();
                  }
                }
              }

              return processChunk();
            });
          }

          return processChunk();
        } else {
          // Non-streaming JSON response
          return response.json().then(function (data) {
            var text = data.response || data.message || data.text || JSON.stringify(data);
            addMessage("assistant", text);

            if (data.show_editor) {
              Bio334.showEditor();
            }

            if (data.code) {
              Bio334.showEditor();
              if (typeof window.setEditorCode === "function") {
                window.setEditorCode(data.code);
              }
            }

            if (data.day || data.phase || data.topic) {
              Bio334.updateStatusBar(data.day, data.phase, data.topic);
            }

            finishStream(text);
          });
        }
      })
      .catch(function (err) {
        removeTypingIndicator();
        clearSlowResponseTip();
        isStreaming = false;
        abortController = null;
        setSendMode();

        if (err.name === "AbortError") {
          // User cancelled — show a note on the last assistant message or add one
          var lastMsg = messagesContainer.querySelector(".chat-msg.assistant:last-of-type");
          if (lastMsg && lastMsg.textContent.trim()) {
            var badge = document.createElement("div");
            badge.className = "cancelled-badge";
            badge.textContent = "[Stopped]";
            lastMsg.appendChild(badge);
          } else {
            addMessage("system", "Response cancelled.");
          }
          chatInput.focus();
          return;
        }

        console.error("Chat error:", err);
        addMessage("system", "Connection error. Please check that the server is running and try again.");
      });
  }

  function finishStream(fullText, msgDiv) {
    isStreaming = false;
    abortController = null;
    setSendMode();
    clearSlowResponseTip();
    removeTypingIndicator(); // Ensure removed even if no text chunks arrived

    // Track the complete assistant message
    if (fullText) {
      chatMessages.push({ role: "assistant", content: fullText });
    }

    // Auto-insert code into editor (agentic coding experience)
    if (fullText && fullText.indexOf("```") !== -1) {
      Bio334.showEditor();
      autoInsertCode(fullText, msgDiv);
    }

    // Make any multiple-choice options clickable
    if (msgDiv) {
      makeChoicesClickable(msgDiv);
    }

    chatInput.focus();
  }

  /* ---- Error Forwarding ---- */
  window.askAboutError = function (errorText) {
    var message = "I got this error when running my code. Can you help me understand and fix it?\n\n```\n" + errorText + "\n```";
    chatInput.value = message;
    sendMessage(message);
    if (Bio334.isMobile) {
      Bio334.switchMobilePanel("chat");
    }
  };

  /* ---- Initial Greeting ---- */
  window.sendInitialGreeting = function () {
    // Ensure chat module is initialized (may be called before chat.js init)
    if (!messagesContainer) {
      messagesContainer = document.getElementById("chat-messages");
      chatForm = document.getElementById("chat-form");
      chatInput = document.getElementById("chat-input");
      btnSend = document.getElementById("btn-send");
    }
    if (!messagesContainer || messagesContainer.children.length > 0) return;

    // Try to load progress to show a context-aware welcome
    Bio334.apiRequest("GET", "/api/progress/" + Bio334.sessionId)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        var topics = data && data.topics ? Object.keys(data.topics) : [];
        var day = data ? data.current_day || 1 : 1;

        if (topics.length > 0) {
          // Returning student — show resume message
          var resumeDiv = addMessage("assistant",
            "**Welcome back to BIO334!**\n\n" +
            "You've been working on **" + topics.length + " topic(s)** so far (Day " + day + ").\n\n" +
            "What would you like to do?"
          );
          appendQuickActions(resumeDiv, [
            "Let's continue where I left off",
            "Show my progress",
            "Start a new topic",
          ]);
        } else {
          // New student — show welcome
          var welcomeDiv = addMessage("assistant",
            "**Welcome to BIO334 -- Python for Population Genetics!**\n\n" +
            "I'm your AI teaching assistant. I'll adapt to your pace -- " +
            "no prior programming experience needed.\n\n" +
            "When I show you code, click **Insert into editor** to try it. " +
            "Use **Ctrl+Enter** (or **Cmd+Enter**) to run code.\n\n" +
            "How would you like to start?"
          );
          appendQuickActions(welcomeDiv, [
            "Let's start today's lesson",
            "What is nucleotide diversity?",
            "I'm new to Python -- teach me the basics",
          ]);
        }
      })
      .catch(function () {
        // Fallback if progress API fails
        var fallbackDiv = addMessage("assistant",
          "**Welcome to BIO334 -- Python for Population Genetics!**\n\n" +
          "I'm your AI teaching assistant. How would you like to start?"
        );
        appendQuickActions(fallbackDiv, [
          "Let's start today's lesson",
          "What is nucleotide diversity?",
          "I'm new to Python -- teach me the basics",
        ]);
      });
  };

  /**
   * Append quick-action buttons to a message div.
   * Clicking a button sends it as a chat message.
   */
  function appendQuickActions(msgDiv, actions) {
    var group = document.createElement("div");
    group.className = "quick-actions";

    for (var i = 0; i < actions.length; i++) {
      var btn = document.createElement("button");
      btn.className = "quick-action-btn";
      btn.textContent = actions[i];
      btn.setAttribute("data-action", actions[i]);
      btn.addEventListener("click", function () {
        var text = this.getAttribute("data-action");
        // Disable all quick action buttons in this group
        var siblings = this.parentNode.querySelectorAll(".quick-action-btn");
        siblings.forEach(function (s) { s.disabled = true; s.classList.add("used"); });
        this.classList.add("selected");
        sendMessage(text);
      });
      group.appendChild(btn);
    }

    msgDiv.appendChild(group);
    scrollToBottom();
  }

  /* ---- Session Save / Resume / Progress Buttons ---- */

  function ensureChatReady() {
    if (!messagesContainer) messagesContainer = document.getElementById("chat-messages");
    if (!chatInput) chatInput = document.getElementById("chat-input");
    if (!btnSend) btnSend = document.getElementById("btn-send");
    if (!chatForm) chatForm = document.getElementById("chat-form");
  }

  function saveSession() {
    ensureChatReady();
    if (isStreaming) {
      alert("Please wait for the current response to finish before saving.");
      return;
    }

    if (chatMessages.length === 0) {
      addMessage("system", "Nothing to save yet -- start chatting first!");
      return;
    }

    // Auto-suggest a label from the last user message
    var suggestion = "";
    for (var i = chatMessages.length - 1; i >= 0; i--) {
      if (chatMessages[i].role === "user") {
        suggestion = chatMessages[i].content.substring(0, 60).replace(/\n/g, " ");
        break;
      }
    }

    var label = prompt("Save point label (optional):", suggestion);
    if (label === null) return; // cancelled

    // Save chat history + create a save point on the server
    Bio334.apiRequest("POST", "/api/session/" + Bio334.sessionId + "/save", {
      chat_history: chatMessages,
      label: label || suggestion || "Save point",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var msgCount = chatMessages.length;
        var saveCount = data.total_save_points || 1;
        addMessage("system",
          "Session saved (" + msgCount + " messages, save point #" + saveCount + ")."
        );
      })
      .catch(function (err) {
        addMessage("system", "Could not save session: " + err.message);
      });
  }

  function resumeSession() {
    ensureChatReady();
    if (isStreaming) {
      alert("Please wait for the current response to finish.");
      return;
    }

    addMessage("system", "Restoring previous session...");

    Bio334.apiRequest("GET", "/api/session/" + Bio334.sessionId + "/load")
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        var history = data.chat_history || [];
        if (history.length === 0) {
          addMessage("system", "No saved session found.");
          return;
        }

        // Clear current messages and restore
        messagesContainer.innerHTML = "";
        chatMessages = [];

        for (var i = 0; i < history.length; i++) {
          var msg = history[i];
          addMessage(msg.role, msg.content, true, false);
        }
        scrollToBottom();

        var savePoints = data.save_points || [];
        var lastSave = savePoints.length > 0
          ? new Date(savePoints[savePoints.length - 1].timestamp).toLocaleString()
          : "unknown";
        addMessage("system",
          "Restored " + history.length + " messages (last saved: " + lastSave + ")."
        );

        // Ask LLM to continue
        sendMessage("I've restored my previous session. Please review my progress and suggest what to work on next.");
      })
      .catch(function (err) {
        addMessage("system", "Could not restore session: " + err.message);
      });
  }

  function openProgressFromChat() {
    // Open progress modal directly
    var modal = document.getElementById("progress-modal");
    var body = document.getElementById("progress-body");
    if (!modal || !body) return;

    modal.hidden = false;
    body.innerHTML = '<p class="progress-loading">Loading progress...</p>';

    Bio334.apiRequest("GET", "/api/progress/" + Bio334.sessionId)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        // Re-use the renderProgress from progress.js if available,
        // otherwise show a simple summary
        if (typeof window._renderProgress === "function") {
          window._renderProgress(data, body);
        } else {
          var topics = data.topics ? Object.keys(data.topics) : [];
          if (topics.length === 0) {
            body.innerHTML =
              '<div class="progress-empty">' +
              '<p>No progress recorded yet.</p>' +
              '<p class="progress-hint">As you work through exercises, your understanding will be tracked here.</p>' +
              '</div>';
          } else {
            var html = '<div class="progress-summary"><div class="progress-stat">' +
              '<span class="stat-number">' + topics.length + '</span>' +
              '<span class="stat-label">Topics</span></div></div>';
            topics.forEach(function (key) {
              var tp = data.topics[key];
              var name = key.replace(/_/g, " ");
              html += '<div class="progress-card"><div class="progress-card-title">' + name + '</div>';
              ["conceptual", "instruction", "implementation", "verification"].forEach(function (dim) {
                var val = tp[dim] || "not_assessed";
                html += '<div class="progress-dim-row"><span class="dim-label">' + dim + '</span>' +
                  '<span class="dim-level">' + val + '</span></div>';
              });
              html += '</div>';
            });
            body.innerHTML = html;
          }
        }
      })
      .catch(function (err) {
        body.innerHTML = '<p class="progress-loading">Could not load progress. (' + err.message + ')</p>';
      });
  }

  /* ---- Export Functions ---- */

  function exportChatLog() {
    if (chatMessages.length === 0) {
      alert("No messages to export.");
      return;
    }
    var md = "# BIO334 Chat Log\n\n";
    md += "Session: " + Bio334.sessionId + "\n";
    md += "Exported: " + new Date().toLocaleString() + "\n\n---\n\n";
    for (var i = 0; i < chatMessages.length; i++) {
      var msg = chatMessages[i];
      var label = msg.role === "user" ? "**Student**" : "**Teaching Assistant**";
      md += label + ":\n\n" + msg.content + "\n\n---\n\n";
    }
    downloadFile("bio334-chat-log.md", md);
  }

  function exportSummary(savePointIndex) {
    // Get chat history up to a specific save point, or all if no index
    Bio334.apiRequest("GET", "/api/session/" + Bio334.sessionId + "/load")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !data.chat_history || data.chat_history.length === 0) {
          alert("No saved session data to summarize.");
          return;
        }

        var history = data.chat_history;
        var savePoints = data.save_points || [];

        // If a save point index is specified, trim history to that point
        if (typeof savePointIndex === "number" && savePointIndex < savePoints.length) {
          var msgCount = savePoints[savePointIndex].message_count || history.length;
          history = history.slice(0, msgCount);
        }

        // Build a prompt with the conversation excerpt
        var excerpt = "";
        for (var i = 0; i < history.length; i++) {
          var msg = history[i];
          excerpt += (msg.role === "user" ? "Student: " : "Assistant: ") + msg.content + "\n\n";
        }

        // Ask LLM to generate summary (shown in chat, user can copy)
        var prompt = "Based on this conversation log, provide a concise learning summary " +
          "covering: (1) topics studied, (2) key concepts learned, (3) exercises completed, " +
          "(4) areas needing more practice. Format as markdown.\n\n" +
          "--- Conversation (" + history.length + " messages) ---\n\n" + excerpt;
        sendMessage(prompt);
      });
  }

  function downloadFile(filename, content) {
    var blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function toggleExportMenu() {
    var existing = document.getElementById("export-dropdown");
    if (existing) {
      existing.remove();
      return;
    }

    var btn = document.getElementById("btn-export");
    if (!btn) return;

    var rect = btn.getBoundingClientRect();
    var menu = document.createElement("div");
    menu.id = "export-dropdown";
    menu.className = "export-dropdown";
    menu.style.position = "fixed";
    menu.style.top = (rect.bottom + 4) + "px";
    menu.style.left = rect.left + "px";

    // Show loading state while fetching save points
    menu.innerHTML = '<div class="export-dropdown-item" style="color:#999">Loading...</div>';
    document.body.appendChild(menu);

    // Fetch save points from server
    Bio334.apiRequest("GET", "/api/session/" + Bio334.sessionId + "/load")
      .then(function (r) { return r.ok ? r.json() : { save_points: [], chat_history: [] }; })
      .then(function (data) {
        menu.innerHTML = "";
        var savePoints = data.save_points || [];

        // Current session chat log (from browser memory)
        var headerCurrent = document.createElement("div");
        headerCurrent.className = "export-dropdown-header";
        headerCurrent.textContent = "CURRENT SESSION";
        menu.appendChild(headerCurrent);

        var itemLog = document.createElement("button");
        itemLog.className = "export-dropdown-item";
        itemLog.textContent = "Chat Log (.md)";
        itemLog.addEventListener("click", function () { menu.remove(); exportChatLog(); });
        menu.appendChild(itemLog);

        var itemSummary = document.createElement("button");
        itemSummary.className = "export-dropdown-item";
        itemSummary.textContent = "Generate Summary";
        itemSummary.addEventListener("click", function () { menu.remove(); exportSummary(); });
        menu.appendChild(itemSummary);

        // Save points section
        if (savePoints.length > 0) {
          var headerSaves = document.createElement("div");
          headerSaves.className = "export-dropdown-header";
          headerSaves.textContent = "SAVE POINTS";
          menu.appendChild(headerSaves);

          for (var i = 0; i < savePoints.length; i++) {
            var sp = savePoints[i];
            var label = sp.label || "Save #" + (i + 1);
            var ts = new Date(sp.timestamp).toLocaleDateString();
            var msgCount = sp.message_count || 0;

            var spItem = document.createElement("div");
            spItem.className = "export-dropdown-savepoint";

            var spLabel = document.createElement("div");
            spLabel.className = "export-sp-label";
            spLabel.textContent = "#" + (i + 1) + " " + label;
            spItem.appendChild(spLabel);

            var spMeta = document.createElement("div");
            spMeta.className = "export-sp-meta";
            spMeta.textContent = ts + " (" + msgCount + " msgs)";
            spItem.appendChild(spMeta);

            var spActions = document.createElement("div");
            spActions.className = "export-sp-actions";

            var btnLog = document.createElement("button");
            btnLog.className = "export-sp-btn";
            btnLog.textContent = "Chat Log";
            btnLog.setAttribute("data-index", i);
            btnLog.addEventListener("click", function () {
              var idx = parseInt(this.getAttribute("data-index"), 10);
              menu.remove();
              exportChatLogForSavePoint(data.chat_history, data.save_points, idx);
            });
            spActions.appendChild(btnLog);

            var btnSum = document.createElement("button");
            btnSum.className = "export-sp-btn";
            btnSum.textContent = "Summary";
            btnSum.setAttribute("data-index", i);
            btnSum.addEventListener("click", function () {
              var idx = parseInt(this.getAttribute("data-index"), 10);
              menu.remove();
              exportSummary(idx);
            });
            spActions.appendChild(btnSum);

            spItem.appendChild(spActions);
            menu.appendChild(spItem);
          }
        }
      });

    // Close on outside click
    setTimeout(function () {
      document.addEventListener("click", function closeMenu(e) {
        if (!menu.contains(e.target) && e.target !== btn) {
          menu.remove();
          document.removeEventListener("click", closeMenu);
        }
      });
    }, 0);
  }

  function exportChatLogForSavePoint(fullHistory, savePoints, index) {
    var sp = savePoints[index];
    var msgCount = sp.message_count || fullHistory.length;
    var history = fullHistory.slice(0, msgCount);
    var label = sp.label || "Save #" + (index + 1);
    var ts = new Date(sp.timestamp).toLocaleString();

    var md = "# BIO334 Chat Log\n\n";
    md += "Save point: #" + (index + 1) + " - " + label + "\n";
    md += "Date: " + ts + "\n";
    md += "Messages: " + history.length + "\n\n---\n\n";
    for (var i = 0; i < history.length; i++) {
      var msg = history[i];
      var roleLabel = msg.role === "user" ? "**Student**" : "**Teaching Assistant**";
      md += roleLabel + ":\n\n" + msg.content + "\n\n---\n\n";
    }
    downloadFile("bio334-chat-sp" + (index + 1) + ".md", md);
  }

  /* ---- Init ---- */
  function init() {
    messagesContainer = document.getElementById("chat-messages");
    chatForm = document.getElementById("chat-form");
    chatInput = document.getElementById("chat-input");
    btnSend = document.getElementById("btn-send");

    // Submit handler — send or stop
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (isStreaming) {
        cancelStreaming();
      } else {
        sendMessage(chatInput.value);
      }
    });

    // Enter to send (Shift+Enter for newline), Escape to stop
    chatInput.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isStreaming) {
        e.preventDefault();
        cancelStreaming();
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (isStreaming) {
          cancelStreaming();
        } else {
          sendMessage(chatInput.value);
        }
      }
    });

    // Auto-resize textarea
    chatInput.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 120) + "px";
    });

    // Session management buttons
    var btnSaveSession = document.getElementById("btn-save-session");
    var btnResumeSession = document.getElementById("btn-resume-session");
    var btnProgressInline = document.getElementById("btn-progress-inline");
    var btnExport = document.getElementById("btn-export");
    if (btnSaveSession) btnSaveSession.addEventListener("click", saveSession);
    if (btnResumeSession) btnResumeSession.addEventListener("click", resumeSession);
    if (btnProgressInline) btnProgressInline.addEventListener("click", openProgressFromChat);
    if (btnExport) btnExport.addEventListener("click", toggleExportMenu);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
