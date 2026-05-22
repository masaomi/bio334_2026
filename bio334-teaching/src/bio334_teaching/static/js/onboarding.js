/**
 * BIO334 Teaching App - Onboarding Module
 *
 * Three-step first-visit onboarding:
 *   1. Welcome + course token input
 *   2. Animated demo of chat interaction
 *   3. Ready to start
 */

(function () {
  "use strict";

  var overlay = null;
  var contentDiv = null;
  var currentStep = 0;
  var totalSteps = 3;

  /* ---- Demo Messages ---- */
  var demoMessages = [
    { role: "user", text: "What is population genetics?" },
    { role: "ai", text: "Population genetics studies how allele frequencies change in populations over time. It combines genetics with evolutionary biology. Ready to explore this with Python?" },
    { role: "user", text: "Yes! How do I start?" },
    { role: "ai", text: "Let's begin with Hardy-Weinberg equilibrium. I'll give you a simple Python script to calculate expected genotype frequencies. Try running it in the code editor!" },
  ];

  /* ---- Step Rendering ---- */
  function renderStep(step) {
    currentStep = step;
    contentDiv.innerHTML = "";

    // Dots
    var dotsDiv = document.createElement("div");
    dotsDiv.className = "onboarding-dots";
    dotsDiv.setAttribute("aria-label", "Step " + (step + 1) + " of " + totalSteps);
    for (var i = 0; i < totalSteps; i++) {
      var dot = document.createElement("div");
      dot.className = "onboarding-dot" + (i === step ? " active" : "");
      dotsDiv.appendChild(dot);
    }
    contentDiv.appendChild(dotsDiv);

    var stepDiv = document.createElement("div");
    stepDiv.className = "onboarding-step";

    if (step === 0) {
      renderStepWelcome(stepDiv);
    } else if (step === 1) {
      renderStepDemo(stepDiv);
    } else if (step === 2) {
      renderStepReady(stepDiv);
    }

    contentDiv.appendChild(stepDiv);
  }

  /* ---- Step 1: Welcome ---- */
  function renderStepWelcome(container) {
    container.innerHTML =
      "<h2>Welcome to BIO334</h2>" +
      "<p>Learn Python programming for population genetics, guided by an AI teaching assistant. " +
      "No prior programming experience needed.</p>" +
      '<div class="form-group">' +
        '<label for="onboarding-token">Course Token</label>' +
        '<input type="text" id="onboarding-token" class="form-input" ' +
          'placeholder="Enter the token provided by your instructor" ' +
          'aria-describedby="token-help">' +
        '<p id="token-help" style="font-size: 13px; color: var(--color-text-secondary); margin-top: 4px;">' +
          "Your instructor will provide this token in class. You can also add it later in Settings.</p>" +
      "</div>" +
      '<div class="onboarding-nav">' +
        '<button class="btn btn-primary" id="btn-onboarding-next-0">Next</button>' +
      "</div>";

    // Pre-fill if token exists
    setTimeout(function () {
      var input = document.getElementById("onboarding-token");
      if (input && Bio334.token) {
        input.value = Bio334.token;
      }

      document.getElementById("btn-onboarding-next-0").addEventListener("click", function () {
        var token = document.getElementById("onboarding-token").value.trim();
        if (token) {
          Bio334.saveToken(token);
        }
        renderStep(1);
      });
    }, 0);
  }

  /* ---- Step 2: Demo ---- */
  function renderStepDemo(container) {
    container.innerHTML =
      "<h2>How It Works</h2>" +
      "<p>Chat with the teaching assistant, and it will guide you through the course. " +
      "When it's time to write code, the editor will appear automatically.</p>" +
      '<div class="onboarding-demo" id="onboarding-demo-area" aria-label="Demo conversation"></div>' +
      '<div class="onboarding-nav">' +
        '<button class="btn btn-secondary" id="btn-onboarding-back-1">Back</button>' +
        '<button class="btn btn-primary" id="btn-onboarding-next-1">Next</button>' +
      "</div>";

    setTimeout(function () {
      document.getElementById("btn-onboarding-back-1").addEventListener("click", function () {
        renderStep(0);
      });
      document.getElementById("btn-onboarding-next-1").addEventListener("click", function () {
        renderStep(2);
      });

      // Animate demo messages
      animateDemoMessages();
    }, 0);
  }

  function animateDemoMessages() {
    var area = document.getElementById("onboarding-demo-area");
    if (!area) return;

    // Create all messages first (hidden)
    demoMessages.forEach(function (msg) {
      var div = document.createElement("div");
      div.className = "demo-msg demo-" + msg.role;
      div.textContent = msg.text;
      area.appendChild(div);
    });

    // Reveal them one by one
    var msgs = area.querySelectorAll(".demo-msg");
    msgs.forEach(function (msg, index) {
      setTimeout(function () {
        msg.classList.add("visible");
      }, 600 * (index + 1));
    });
  }

  /* ---- Step 3: Ready ---- */
  function renderStepReady(container) {
    container.innerHTML =
      "<h2>You're All Set!</h2>" +
      "<p>The teaching assistant will greet you and guide you through today's lesson. " +
      "Feel free to ask questions at any time. There are no silly questions here.</p>" +
      "<p style='margin-top: 16px; font-size: 14px; color: var(--color-text-secondary);'>" +
        "<strong>Tips:</strong><br>" +
        "- Use <kbd>Ctrl+Enter</kbd> (or <kbd>Cmd+Enter</kbd> on Mac) to run code<br>" +
        "- Click on the timeline to jump to different topics<br>" +
        "- If you get an error, click \"Ask AI about this error\" for help" +
      "</p>" +
      '<div class="onboarding-nav">' +
        '<button class="btn btn-secondary" id="btn-onboarding-back-2">Back</button>' +
        '<button class="btn btn-primary" id="btn-onboarding-start" style="font-size: 16px; padding: 10px 32px;">Start Learning</button>' +
      "</div>";

    setTimeout(function () {
      document.getElementById("btn-onboarding-back-2").addEventListener("click", function () {
        renderStep(1);
      });
      document.getElementById("btn-onboarding-start").addEventListener("click", function () {
        completeOnboarding();
      });
    }, 0);
  }

  /* ---- Complete Onboarding ---- */
  function completeOnboarding() {
    localStorage.setItem(Bio334.STORAGE_KEY_ONBOARDED, "true");
    overlay.hidden = true;

    // Load timeline and trigger greeting
    if (typeof window.loadTimeline === "function") {
      window.loadTimeline();
    }
    if (typeof window.sendInitialGreeting === "function") {
      window.sendInitialGreeting();
    }
  }

  /* ---- Public API ---- */
  window.startOnboarding = function () {
    overlay = document.getElementById("onboarding-overlay");
    contentDiv = overlay.querySelector(".overlay-content");
    overlay.hidden = false;
    renderStep(0);

    // Focus the first input after render
    setTimeout(function () {
      var input = document.getElementById("onboarding-token");
      if (input) input.focus();
    }, 100);
  };

  /* Allow re-running onboarding from settings or console */
  window.resetOnboarding = function () {
    localStorage.removeItem(Bio334.STORAGE_KEY_ONBOARDED);
    window.startOnboarding();
  };
})();
