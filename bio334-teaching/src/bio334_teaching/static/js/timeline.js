/**
 * BIO334 Teaching App - Timeline Module
 *
 * Fetches the course timetable and renders a vertical timeline
 * in the sidebar. Highlights the current activity block.
 */

(function () {
  "use strict";

  var container = null;
  var timetableData = null;

  /* ---- Activity Type Icons ---- */
  var ICONS = {
    lecture: "\uD83D\uDCD6",       // open book
    hands_on: "\uD83D\uDCBB",     // laptop
    checkpoint: "\u2705",          // check mark
    discussion: "\uD83D\uDCAC",   // speech bubbles
    break: "\u2615",               // coffee
    review: "\uD83D\uDD04",       // arrows cycle
    demo: "\uD83C\uDFAC",         // clapperboard
  };

  function getIcon(type) {
    return ICONS[type] || "\uD83D\uDCD6";
  }

  /* ---- Render Timeline ---- */
  function renderTimeline(data) {
    container.innerHTML = "";
    timetableData = data;

    if (!data || !data.days || data.days.length === 0) {
      container.innerHTML = '<p class="timeline-loading">No schedule available yet.</p>';
      return;
    }

    var currentDay = data.current_day || null;
    var currentBlock = data.current_block || null;

    data.days.forEach(function (day) {
      // Day header
      var dayHeader = document.createElement("div");
      dayHeader.className = "timeline-day-header";
      dayHeader.textContent = day.label || ("Day " + day.number);
      if (day.date) {
        dayHeader.textContent += " - " + day.date;
      }
      container.appendChild(dayHeader);

      if (!day.blocks || day.blocks.length === 0) {
        var emptyMsg = document.createElement("p");
        emptyMsg.className = "timeline-loading";
        emptyMsg.textContent = "No activities scheduled.";
        container.appendChild(emptyMsg);
        return;
      }

      day.blocks.forEach(function (block) {
        var blockDiv = document.createElement("div");
        blockDiv.className = "timeline-block";
        blockDiv.setAttribute("role", "button");
        blockDiv.setAttribute("tabindex", "0");
        blockDiv.setAttribute("aria-label", block.title + " (" + (block.type || "activity") + ")");

        // Mark active / completed
        if (currentDay === day.number && currentBlock === block.id) {
          blockDiv.classList.add("active");
        }
        if (block.completed) {
          blockDiv.classList.add("completed");
        }

        // Icon
        var icon = document.createElement("span");
        icon.className = "timeline-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = getIcon(block.type);

        // Title
        var title = document.createTextNode(" " + block.title);

        // Time
        var time = document.createElement("span");
        time.className = "timeline-time";
        if (block.time) {
          time.textContent = block.time;
        } else if (block.duration_min) {
          time.textContent = block.duration_min + " min";
        }

        blockDiv.appendChild(icon);
        blockDiv.appendChild(title);
        blockDiv.appendChild(time);

        // Click to navigate
        blockDiv.addEventListener("click", function () {
          navigateToBlock(block, day);
        });

        blockDiv.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            navigateToBlock(block, day);
          }
        });

        container.appendChild(blockDiv);
      });
    });

    // Update status bar with current info
    if (data.current_day) {
      var dayInfo = data.days.find(function (d) { return d.number === data.current_day; });
      var dayLabel = dayInfo ? (dayInfo.label || "Day " + dayInfo.number) : "Day " + data.current_day;
      Bio334.updateStatusBar(dayLabel, data.current_phase || "--", data.current_topic || "--");
    }
  }

  /* ---- Navigation ---- */
  function navigateToBlock(block, day) {
    // Highlight this block
    var allBlocks = container.querySelectorAll(".timeline-block");
    allBlocks.forEach(function (b) { b.classList.remove("active"); });
    event.currentTarget.classList.add("active");

    // Send a chat message to navigate
    var chatInput = document.getElementById("chat-input");
    if (chatInput) {
      var message = "Let's move to: " + block.title;
      chatInput.value = message;

      // Trigger send
      var submitEvent = new Event("submit", { cancelable: true });
      document.getElementById("chat-form").dispatchEvent(submitEvent);
    }

    // On mobile, switch to chat panel
    if (Bio334.isMobile) {
      Bio334.switchMobilePanel("chat");
    }
  }

  /* ---- Load Timetable ---- */
  window.loadTimeline = function () {
    Bio334.apiRequest("GET", "/api/timetable")
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        renderTimeline(data);
      })
      .catch(function (err) {
        console.warn("Failed to load timetable:", err);
        container.innerHTML =
          '<p class="timeline-loading">Could not load schedule. The server may still be starting up.</p>';
      });
  };

  /* ---- Init ---- */
  function init() {
    container = document.getElementById("timeline-content");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
