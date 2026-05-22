/**
 * BIO334 Teaching App - Main Application Logic
 *
 * Manages session state, panel visibility, settings, and
 * coordinates between chat, editor, and timeline modules.
 */

(function () {
  "use strict";

  /* ---- Constants ---- */
  var STORAGE_KEY_TOKEN = "bio334_token";
  var STORAGE_KEY_SESSION = "bio334_session_id";
  var STORAGE_KEY_ONBOARDED = "bio334_onboarded";

  /* ---- State ---- */
  window.Bio334 = {
    sessionId: null,
    token: null,
    editorVisible: false,
    timelineCollapsed: false,
    isMobile: false,
    activePanel: "chat",
  };

  /* ---- Utilities ---- */
  function generateSessionId() {
    var chars = "abcdefghijklmnopqrstuvwxyz0123456789";
    var id = "s_";
    for (var i = 0; i < 12; i++) {
      id += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return id;
  }

  function $(selector) {
    return document.querySelector(selector);
  }

  function $$(selector) {
    return document.querySelectorAll(selector);
  }

  /* ---- Session Management ---- */
  function initSession() {
    // Prefer server-injected token (CSRF), fall back to localStorage (course token)
    Bio334.token = window.__BIO334_TOKEN || localStorage.getItem(STORAGE_KEY_TOKEN) || "";
    Bio334.sessionId = localStorage.getItem(STORAGE_KEY_SESSION);

    if (!Bio334.sessionId) {
      Bio334.sessionId = generateSessionId();
      localStorage.setItem(STORAGE_KEY_SESSION, Bio334.sessionId);
    }
  }

  function saveToken(token) {
    Bio334.token = token;
    localStorage.setItem(STORAGE_KEY_TOKEN, token);
  }

  /* ---- Panel Management ---- */
  function showEditor() {
    if (Bio334.editorVisible) return;
    Bio334.editorVisible = true;
    var editorPanel = $("#panel-editor");
    editorPanel.hidden = false;

    var layout = $(".app-layout");
    layout.classList.remove("editor-hidden");
    layout.classList.add("editor-visible");

    // On desktop, adjust grid to show all three panels + resize handle
    if (!Bio334.isMobile) {
      updateDesktopGrid();
    }

    // Initialize editor if not already done
    if (typeof window.initCodeEditor === "function") {
      window.initCodeEditor();
    }
  }

  function hideEditor() {
    if (!Bio334.editorVisible) return;
    Bio334.editorVisible = false;
    var editorPanel = $("#panel-editor");
    editorPanel.hidden = true;

    var layout = $(".app-layout");
    layout.classList.add("editor-hidden");
    layout.classList.remove("editor-visible");

    if (!Bio334.isMobile) {
      updateDesktopGrid();
    }
  }

  function toggleTimeline() {
    Bio334.timelineCollapsed = !Bio334.timelineCollapsed;
    var layout = $(".app-layout");
    layout.classList.toggle("timeline-collapsed", Bio334.timelineCollapsed);
    updateDesktopGrid();
  }

  function updateDesktopGrid() {
    if (Bio334.isMobile) return;
    var layout = $(".app-layout");
    var sidebar = Bio334.timelineCollapsed ? "0" : "var(--sidebar-width)";
    // Grid: sidebar | editor (or empty space) | resize handle | chat
    layout.style.gridTemplateColumns = sidebar + " 1fr 6px var(--chat-width)";
  }

  /* ---- Mobile Tab Switching ---- */
  function switchMobilePanel(panelName) {
    Bio334.activePanel = panelName;

    $$(".tab-btn").forEach(function (btn) {
      var isActive = btn.getAttribute("data-panel") === panelName;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    $$(".panel").forEach(function (panel) {
      panel.classList.remove("panel-active");
    });

    var targetId = "panel-" + panelName;
    var target = document.getElementById(targetId);
    if (target) {
      target.classList.add("panel-active");
      target.hidden = false;
    }

    // Show editor when code tab is selected
    if (panelName === "editor" && !Bio334.editorVisible) {
      Bio334.editorVisible = true;
      if (typeof window.initCodeEditor === "function") {
        window.initCodeEditor();
      }
    }
  }

  /* ---- Responsive ---- */
  function checkMobile() {
    var wasMobile = Bio334.isMobile;
    Bio334.isMobile = window.innerWidth <= 768;

    if (Bio334.isMobile !== wasMobile) {
      if (Bio334.isMobile) {
        // Switch to mobile: show active panel
        switchMobilePanel(Bio334.activePanel);
      } else {
        // Switch to desktop: reset panels
        $$(".panel").forEach(function (p) {
          p.classList.remove("panel-active");
        });
        updateDesktopGrid();
      }
    }
  }

  /* ---- Settings Modal ---- */
  function openSettings() {
    var modal = $("#settings-modal");
    modal.hidden = false;
    $("#settings-token").value = Bio334.token || "";
    $("#settings-session").value = Bio334.sessionId;
    $("#settings-token").focus();
  }

  function closeSettings() {
    $("#settings-modal").hidden = true;
  }

  function saveSettings() {
    var token = $("#settings-token").value.trim();
    saveToken(token);
    closeSettings();
  }

  /* ---- Status Bar ---- */
  function updateStatusBar(day, phase, topic) {
    if (day !== undefined) $("#status-day").textContent = "Day: " + day;
    if (phase !== undefined) $("#status-phase").textContent = "Phase: " + phase;
    if (topic !== undefined) $("#status-topic").textContent = "Topic: " + topic;
  }

  /* ---- API Helper ---- */
  function apiRequest(method, path, body, signal) {
    var opts = {
      method: method,
      headers: {
        "Content-Type": "application/json",
      },
    };
    if (Bio334.token) {
      opts.headers["X-Course-Token"] = Bio334.token;
    }
    if (body) {
      opts.body = JSON.stringify(body);
    }
    if (signal) {
      opts.signal = signal;
    }
    return fetch(path, opts);
  }

  /* ---- Initialization ---- */
  function init() {
    initSession();
    checkMobile();

    // Start with editor hidden (progressive disclosure)
    hideEditor();

    // Event listeners
    $("#btn-toggle-timeline").addEventListener("click", toggleTimeline);
    $("#btn-settings").addEventListener("click", openSettings);
    $("#btn-close-settings").addEventListener("click", closeSettings);
    $("#btn-save-settings").addEventListener("click", saveSettings);

    // Close settings on overlay click
    $("#settings-modal").addEventListener("click", function (e) {
      if (e.target === this) closeSettings();
    });

    // Mobile tabs
    $$(".tab-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        switchMobilePanel(this.getAttribute("data-panel"));
      });
    });

    // Keyboard: Escape closes modals
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (!$("#settings-modal").hidden) closeSettings();
        if (!$("#onboarding-overlay").hidden) {
          // Don't close onboarding with Escape - they need to complete it
        }
      }
    });

    // Responsive handler
    window.addEventListener("resize", checkMobile);

    // Chat panel resize handle
    initChatResize();

    // Check if onboarding needed
    var isOnboarded = localStorage.getItem(STORAGE_KEY_ONBOARDED);
    if (!isOnboarded) {
      if (typeof window.startOnboarding === "function") {
        window.startOnboarding();
      }
    } else {
      // Load timeline and send initial greeting
      if (typeof window.loadTimeline === "function") {
        window.loadTimeline();
      }
      if (typeof window.sendInitialGreeting === "function") {
        window.sendInitialGreeting();
      }
    }
  }

  /* ---- Chat Panel Resize ---- */
  function initChatResize() {
    var handle = document.getElementById("chat-resize-handle");
    if (!handle) return;

    var layout = $(".app-layout");
    var chatPanel = $("#panel-chat");
    var isDragging = false;

    handle.addEventListener("mousedown", function (e) {
      e.preventDefault();
      isDragging = true;
      handle.classList.add("dragging");
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    });

    document.addEventListener("mousemove", function (e) {
      if (!isDragging) return;
      var layoutRect = layout.getBoundingClientRect();
      var chatWidth = layoutRect.right - e.clientX;
      // Clamp: min 280px, max depends on whether editor is visible
      var sidebarW = Bio334.timelineCollapsed ? 0 : 280;
      var minW = 280;
      var minOtherCol = Bio334.editorVisible ? 200 : 50; // editor min or just a small gap
      var maxW = layoutRect.width - sidebarW - minOtherCol - 6;
      chatWidth = Math.max(minW, Math.min(maxW, chatWidth));
      document.documentElement.style.setProperty("--chat-width", chatWidth + "px");
      updateDesktopGrid();
    });

    document.addEventListener("mouseup", function () {
      if (isDragging) {
        isDragging = false;
        handle.classList.remove("dragging");
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    });
  }

  /* ---- Exports ---- */
  window.Bio334.showEditor = showEditor;
  window.Bio334.hideEditor = hideEditor;
  window.Bio334.updateStatusBar = updateStatusBar;
  window.Bio334.apiRequest = apiRequest;
  window.Bio334.saveToken = saveToken;
  window.Bio334.switchMobilePanel = switchMobilePanel;
  window.Bio334.$ = $;
  window.Bio334.$$ = $$;
  window.Bio334.STORAGE_KEY_ONBOARDED = STORAGE_KEY_ONBOARDED;

  // Start when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
