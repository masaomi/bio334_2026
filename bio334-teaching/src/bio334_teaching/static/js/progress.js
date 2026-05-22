/**
 * BIO334 Teaching App - Progress Module
 *
 * Displays learning progress dashboard with per-topic
 * 4-dimension assessments (conceptual, instruction, implementation, verification).
 */

(function () {
  "use strict";

  var modal = null;
  var body = null;
  var btnOpen = null;
  var btnClose = null;

  /* ---- Level Definitions ---- */
  var LEVELS = {
    not_assessed: { label: "Not assessed", value: 0, color: "#cbd5e1" },
    low:          { label: "Low",          value: 1, color: "#f87171" },
    medium:       { label: "Medium",       value: 2, color: "#fbbf24" },
    high:         { label: "High",         value: 3, color: "#34d399" },
  };

  var DIMENSIONS = [
    { key: "conceptual",     label: "Understanding",     icon: "\uD83E\uDDE0" },
    { key: "instruction",    label: "Instruction",       icon: "\uD83D\uDDE3" },
    { key: "implementation", label: "Implementation",    icon: "\uD83D\uDD27" },
    { key: "verification",   label: "Verification",      icon: "\uD83D\uDD2C" },
  ];

  /* ---- Topic Display Names ---- */
  var TOPIC_NAMES = {
    python_basics_for_bio:       "Python Basics",
    python_file_io_parsing:      "File I/O & Parsing",
    python_functions_modules:    "Functions & Modules",
    python_batch_processing:     "Batch Processing",
    popgen_nucleotide_diversity: "Nucleotide Diversity (\u03C0)",
    popgen_segregating_sites:    "Segregating Sites (\u03B8w)",
    popgen_tajimas_d:            "Tajima's D",
    popgen_wright_fisher:        "Wright-Fisher Model",
    akamchatica_biology:         "A. kamchatica Biology",
    bioinformatics_file_formats: "File Formats (FASTA/VCF)",
  };

  function topicDisplayName(key) {
    return TOPIC_NAMES[key] || key.replace(/_/g, " ");
  }

  /* ---- Render Progress ---- */
  // Expose for reuse from chat.js
  window._renderProgress = function (data, targetEl) {
    var origBody = body;
    body = targetEl || body;
    renderProgress(data);
    body = origBody;
  };

  function renderProgress(data) {
    body.innerHTML = "";

    var topics = data.topics || {};
    var topicKeys = Object.keys(topics);

    if (topicKeys.length === 0) {
      body.innerHTML =
        '<div class="progress-empty">' +
        '<p>No progress recorded yet.</p>' +
        '<p class="progress-hint">As you work through exercises and checkpoints, ' +
        'your understanding will be tracked here across four dimensions:</p>' +
        '<ul>' +
        '<li><strong>Understanding</strong> \u2014 Can you explain the concept?</li>' +
        '<li><strong>Instruction</strong> \u2014 Can you instruct AI to write correct code?</li>' +
        '<li><strong>Implementation</strong> \u2014 Can you read and debug the code?</li>' +
        '<li><strong>Verification</strong> \u2014 Can you interpret results biologically?</li>' +
        '</ul>' +
        '</div>';
      return;
    }

    // Summary stats
    var totalDims = topicKeys.length * DIMENSIONS.length;
    var assessed = 0;
    var highCount = 0;
    topicKeys.forEach(function (key) {
      var tp = topics[key];
      DIMENSIONS.forEach(function (dim) {
        var val = tp[dim.key] || "not_assessed";
        if (val !== "not_assessed") assessed++;
        if (val === "high") highCount++;
      });
    });

    var summaryDiv = document.createElement("div");
    summaryDiv.className = "progress-summary";
    summaryDiv.innerHTML =
      '<div class="progress-stat">' +
      '<span class="stat-number">' + topicKeys.length + '</span>' +
      '<span class="stat-label">Topics</span>' +
      '</div>' +
      '<div class="progress-stat">' +
      '<span class="stat-number">' + assessed + '/' + totalDims + '</span>' +
      '<span class="stat-label">Assessed</span>' +
      '</div>' +
      '<div class="progress-stat">' +
      '<span class="stat-number">' + highCount + '</span>' +
      '<span class="stat-label">Mastered</span>' +
      '</div>';
    body.appendChild(summaryDiv);

    // Per-topic details
    topicKeys.forEach(function (key) {
      var tp = topics[key];
      var card = document.createElement("div");
      card.className = "progress-card";

      var title = document.createElement("div");
      title.className = "progress-card-title";
      title.textContent = topicDisplayName(key);

      // Phase indicator
      var phase = inferPhase(tp);
      var phaseSpan = document.createElement("span");
      phaseSpan.className = "progress-phase phase-" + phase;
      phaseSpan.textContent = "Phase " + phase;
      phaseSpan.title = phase === 1 ? "Guided" : phase === 2 ? "Partially guided" : "Autonomous";
      title.appendChild(phaseSpan);

      card.appendChild(title);

      // Dimension bars
      DIMENSIONS.forEach(function (dim) {
        var val = tp[dim.key] || "not_assessed";
        var level = LEVELS[val] || LEVELS.not_assessed;

        var row = document.createElement("div");
        row.className = "progress-dim-row";

        row.innerHTML =
          '<span class="dim-icon" title="' + dim.label + '">' + dim.icon + '</span>' +
          '<span class="dim-label">' + dim.label + '</span>' +
          '<div class="dim-bar">' +
          '<div class="dim-bar-fill" style="width:' + (level.value / 3 * 100) + '%;background:' + level.color + '"></div>' +
          '</div>' +
          '<span class="dim-level" style="color:' + level.color + '">' + level.label + '</span>';

        card.appendChild(row);
      });

      body.appendChild(card);
    });

    // Save history section
    var savePoints = data.save_points || [];
    if (savePoints.length > 0) {
      var saveSection = document.createElement("div");
      saveSection.className = "progress-save-history";

      var saveTitle = document.createElement("h3");
      saveTitle.className = "progress-section-title";
      saveTitle.textContent = "Save History";
      saveSection.appendChild(saveTitle);

      for (var si = 0; si < savePoints.length; si++) {
        var sp = savePoints[si];
        var spRow = document.createElement("div");
        spRow.className = "save-point-row";

        var ts = new Date(sp.timestamp).toLocaleString();
        var msgCount = sp.message_count || 0;
        var label = sp.label || "Save point";

        var infoSpan = document.createElement("span");
        infoSpan.className = "save-point-info";
        infoSpan.innerHTML =
          '<span class="save-point-number">#' + (si + 1) + '</span> ' +
          '<span class="save-point-label">' + label.replace(/</g, "&lt;") + '</span>' +
          '<span class="save-point-meta">' + ts + ' (' + msgCount + ' msgs)</span>';
        spRow.appendChild(infoSpan);

        saveSection.appendChild(spRow);
      }

      body.appendChild(saveSection);
    }

    // Session info
    var infoDiv = document.createElement("div");
    infoDiv.className = "progress-info";
    var lastActive = data.last_active ? new Date(data.last_active).toLocaleString() : "N/A";
    infoDiv.innerHTML =
      '<small>Session: ' + (data.session_id || "N/A") +
      ' | Day: ' + (data.current_day || "--") +
      ' | Last active: ' + lastActive + '</small>';
    body.appendChild(infoDiv);
  }

  function inferPhase(tp) {
    var order = { not_assessed: 0, low: 1, medium: 2, high: 3 };
    var c = order[tp.conceptual] || 0;
    var i = order[tp.instruction] || 0;
    var m = order[tp.implementation] || 0;
    var v = order[tp.verification] || 0;
    if (c >= 2 && i >= 2 && m >= 2 && v >= 1) return 3;
    if (c >= 2) return 2;
    return 1;
  }

  /* ---- Load Progress ---- */
  function loadProgress() {
    body.innerHTML = '<p class="progress-loading">Loading progress...</p>';

    Bio334.apiRequest("GET", "/api/progress/" + Bio334.sessionId)
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        renderProgress(data);
      })
      .catch(function (err) {
        console.warn("Failed to load progress:", err);
        body.innerHTML = '<p class="progress-loading">Could not load progress data.</p>';
      });
  }

  /* ---- Modal Control ---- */
  function openProgress() {
    modal.hidden = false;
    loadProgress();
  }

  function closeProgress() {
    modal.hidden = true;
  }

  /* ---- Init ---- */
  function init() {
    modal = document.getElementById("progress-modal");
    body = document.getElementById("progress-body");
    btnOpen = document.getElementById("btn-progress");
    btnClose = document.getElementById("btn-close-progress");

    if (btnOpen) btnOpen.addEventListener("click", openProgress);
    if (btnClose) btnClose.addEventListener("click", closeProgress);

    // Close on overlay click
    if (modal) {
      modal.addEventListener("click", function (e) {
        if (e.target === modal) closeProgress();
      });
    }

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal && !modal.hidden) {
        closeProgress();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
