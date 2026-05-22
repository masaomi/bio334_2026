/**
 * BIO334 Teaching App - Code Editor Module
 *
 * Manages the code editor (CodeMirror 6 with textarea fallback),
 * code execution, output display, and error line highlighting.
 */

(function () {
  "use strict";

  var editorView = null; // CodeMirror EditorView (if loaded)
  var textarea = null;
  var outputContent = null;
  var executionTime = null;
  var btnRun = null;
  var btnClear = null;
  var btnReset = null;
  var isRunning = false;
  var editorInitialized = false;
  var defaultCode = "# Write your Python code here\nprint(\"Hello, BIO334!\")\n";

  // CodeMirror error highlight state
  var errorEffect = null;   // StateEffect for setting error lines
  var clearErrorEffect = null; // StateEffect for clearing error lines
  var errorField = null;     // StateField holding error decorations

  /* ---- CodeMirror Initialization ---- */
  function initCodeMirror() {
    if (editorView || !window._CM) return;

    try {
      var CM = window._CM;
      var wrapper = document.getElementById("editor-wrapper");

      // Hide the textarea
      textarea.style.display = "none";

      // Set up error line highlight extensions
      if (CM.StateEffect && CM.StateField && CM.Decoration && CM.EditorView) {
        errorEffect = CM.StateEffect.define();
        clearErrorEffect = CM.StateEffect.define();

        errorField = CM.StateField.define({
          create: function () {
            return CM.Decoration.none;
          },
          update: function (decos, tr) {
            for (var i = 0; i < tr.effects.length; i++) {
              var effect = tr.effects[i];
              if (effect.is(clearErrorEffect)) {
                return CM.Decoration.none;
              }
              if (effect.is(errorEffect)) {
                return effect.value;
              }
            }
            return decos;
          },
          provide: function (field) {
            return CM.EditorView.decorations.from(field);
          },
        });
      }

      var extensions = [
        CM.basicSetup,
        CM.python(),
        CM.oneDark,
        CM.keymap.of([
          {
            key: "Mod-Enter",
            run: function () {
              runCode();
              return true;
            },
          },
        ]),
      ];

      // Add error field if available
      if (errorField) {
        extensions.push(errorField);
      }

      // Add error line gutter mark style
      if (CM.EditorView) {
        extensions.push(CM.EditorView.baseTheme({
          ".cm-error-line": {
            backgroundColor: "rgba(220, 38, 38, 0.15)",
          },
          ".cm-error-line .cm-gutterElement": {
            color: "#dc2626",
            fontWeight: "bold",
          },
        }));
      }

      editorView = new CM.EditorView({
        doc: textarea.value || defaultCode,
        extensions: extensions,
        parent: wrapper,
      });
    } catch (e) {
      console.warn("CodeMirror init failed, using textarea:", e);
      textarea.style.display = "";
      initTextareaLineNumbers();
    }
  }

  /* ---- Textarea Line Numbers (fallback) ---- */
  var lineGutter = null;

  function initTextareaLineNumbers() {
    if (lineGutter) return;
    var wrapper = document.getElementById("editor-wrapper");
    if (!wrapper || !textarea) return;

    // Create line gutter
    lineGutter = document.createElement("div");
    lineGutter.className = "line-gutter";
    lineGutter.setAttribute("aria-hidden", "true");
    wrapper.insertBefore(lineGutter, textarea);

    // Add class to wrapper for layout
    wrapper.classList.add("has-line-gutter");

    updateLineNumbers();
    textarea.addEventListener("input", updateLineNumbers);
    textarea.addEventListener("scroll", syncGutterScroll);
    textarea.addEventListener("keyup", updateLineNumbers);
  }

  function updateLineNumbers() {
    if (!lineGutter || !textarea) return;
    var lines = textarea.value.split("\n").length;
    var html = "";
    for (var i = 1; i <= lines; i++) {
      var cls = "line-num";
      if (currentErrorLines.indexOf(i) >= 0) {
        cls += " line-num-error";
      }
      html += '<div class="' + cls + '">' + i + "</div>";
    }
    lineGutter.innerHTML = html;
  }

  function syncGutterScroll() {
    if (lineGutter && textarea) {
      lineGutter.scrollTop = textarea.scrollTop;
    }
  }

  /* ---- Error Line Tracking ---- */
  var currentErrorLines = [];

  function parseErrorLines(stderr) {
    var lines = [];
    if (!stderr) return lines;

    // Match Python traceback: "  File "<string>", line X"
    // Also: "  File "/tmp/...", line X"
    var pattern = /File\s+["'].*?["'],\s+line\s+(\d+)/g;
    var match;
    while ((match = pattern.exec(stderr)) !== null) {
      var lineNum = parseInt(match[1], 10);
      if (lineNum > 0 && lines.indexOf(lineNum) < 0) {
        lines.push(lineNum);
      }
    }

    // Also match SyntaxError indicators: "    ^ \n SyntaxError:"
    // Look for "line X" anywhere
    var simplePattern = /line\s+(\d+)/gi;
    while ((match = simplePattern.exec(stderr)) !== null) {
      var num = parseInt(match[1], 10);
      if (num > 0 && lines.indexOf(num) < 0) {
        lines.push(num);
      }
    }

    return lines;
  }

  function highlightErrorLines(errorLines) {
    currentErrorLines = errorLines;

    if (editorView && errorEffect && window._CM) {
      var CM = window._CM;
      if (errorLines.length === 0) {
        // Clear errors
        editorView.dispatch({ effects: clearErrorEffect.of(null) });
        return;
      }

      var doc = editorView.state.doc;
      var decos = [];
      var lineDeco = CM.Decoration.line({ class: "cm-error-line" });

      for (var i = 0; i < errorLines.length; i++) {
        var lineNum = errorLines[i];
        if (lineNum >= 1 && lineNum <= doc.lines) {
          var line = doc.line(lineNum);
          decos.push(lineDeco.range(line.from));
        }
      }

      var decoSet = CM.Decoration.set(decos, true);
      editorView.dispatch({ effects: errorEffect.of(decoSet) });

      // Scroll to first error line
      if (errorLines.length > 0) {
        var firstLine = doc.line(Math.min(errorLines[0], doc.lines));
        editorView.dispatch({
          selection: { anchor: firstLine.from },
          scrollIntoView: true,
        });
      }
    } else if (textarea) {
      // Textarea fallback: update line gutter highlighting
      updateLineNumbers();

      // Scroll textarea to error line
      if (errorLines.length > 0) {
        var lineHeight = parseInt(getComputedStyle(textarea).lineHeight) || 21;
        textarea.scrollTop = (errorLines[0] - 3) * lineHeight;
      }
    }
  }

  function clearErrorHighlights() {
    currentErrorLines = [];
    if (editorView && clearErrorEffect) {
      editorView.dispatch({ effects: clearErrorEffect.of(null) });
    }
    if (lineGutter) {
      updateLineNumbers();
    }
  }

  /* ---- Editor API ---- */
  function getCode() {
    if (editorView) {
      return editorView.state.doc.toString();
    }
    return textarea.value;
  }

  window.setEditorCode = function (code) {
    clearErrorHighlights();
    if (editorView) {
      editorView.dispatch({
        changes: {
          from: 0,
          to: editorView.state.doc.length,
          insert: code,
        },
      });
    } else if (textarea) {
      textarea.value = code;
      updateLineNumbers();
    }
  };

  window.appendEditorCode = function (code) {
    var current = getCode();
    var separator = current.trim() ? "\n\n" : "";
    window.setEditorCode(current + separator + code);
  };

  /* ---- Code Execution ---- */
  var argsInput = null;

  function runCode() {
    if (isRunning) return;

    var code = getCode().trim();
    if (!code) {
      showOutput("", "Please write some code first.", 0);
      return;
    }

    isRunning = true;
    btnRun.disabled = true;
    btnRun.innerHTML = '<span aria-hidden="true">&#8987;</span> Running...';
    outputContent.innerHTML = '<span class="output-placeholder">Running your code...</span>';
    executionTime.hidden = true;
    clearErrorHighlights();

    var payload = { code: code };
    // Include command-line arguments if provided
    if (argsInput && argsInput.value.trim()) {
      payload.args = argsInput.value.trim();
    }

    Bio334.apiRequest("POST", "/api/run", payload)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Server error: " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        showOutput(data.stdout || "", data.stderr || "", data.execution_time_ms || 0);

        // Highlight error lines if there's stderr
        if (data.stderr) {
          var errorLines = parseErrorLines(data.stderr);
          if (errorLines.length > 0) {
            highlightErrorLines(errorLines);
          }
        }
      })
      .catch(function (err) {
        console.error("Run error:", err);
        showOutput("", "Failed to run code. Is the server running?\n" + err.message, 0);
      })
      .finally(function () {
        isRunning = false;
        btnRun.disabled = false;
        btnRun.innerHTML = '<span aria-hidden="true">&#9654;</span> Run';
      });
  }

  /* ---- Output Display ---- */
  function showOutput(stdout, stderr, timeMs) {
    outputContent.innerHTML = "";

    if (!stdout && !stderr) {
      outputContent.innerHTML = '<span class="output-placeholder">Code ran successfully with no output.</span>';
    }

    if (stdout) {
      var stdoutSpan = document.createElement("span");
      stdoutSpan.className = "output-stdout";
      stdoutSpan.textContent = stdout;
      outputContent.appendChild(stdoutSpan);
    }

    if (stderr) {
      if (stdout) {
        outputContent.appendChild(document.createTextNode("\n"));
      }
      var stderrSpan = document.createElement("span");
      stderrSpan.className = "output-stderr";

      // Format stderr with clickable line references
      var formatted = formatStderr(stderr);
      stderrSpan.innerHTML = formatted;
      outputContent.appendChild(stderrSpan);

      // Add "Ask AI about this error" button
      var askBtn = document.createElement("button");
      askBtn.className = "btn-ask-error";
      askBtn.textContent = "Ask AI about this error";
      askBtn.setAttribute("aria-label", "Ask the teaching assistant about this error");
      askBtn.addEventListener("click", function () {
        if (typeof window.askAboutError === "function") {
          window.askAboutError(stderr);
        }
      });
      outputContent.appendChild(askBtn);
    }

    if (timeMs > 0) {
      executionTime.textContent = timeMs + " ms";
      executionTime.hidden = false;
    } else {
      executionTime.hidden = true;
    }
  }

  function formatStderr(stderr) {
    // Escape HTML
    var html = stderr
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Make "line X" references clickable
    html = html.replace(/(line\s+)(\d+)/gi, function (match, prefix, num) {
      return prefix + '<a class="error-line-link" href="#" data-line="' + num + '" title="Go to line ' + num + '">' + num + "</a>";
    });

    return html;
  }

  function clearOutput() {
    outputContent.innerHTML = '<span class="output-placeholder">Output will appear here when you run your code.</span>';
    executionTime.hidden = true;
    clearErrorHighlights();
  }

  function resetCode() {
    window.setEditorCode(defaultCode);
    clearOutput();
  }

  /* ---- Save / Restore (workspace) ---- */
  var btnSaveWs = null;
  var btnRestoreWs = null;
  var restoreDropdown = null;

  /* ---- Download / Upload (file) ---- */
  function downloadCode() {
    var code = getCode();
    // Default filename with timestamp
    var now = new Date();
    var ts = now.getFullYear()
      + ("0" + (now.getMonth() + 1)).slice(-2)
      + ("0" + now.getDate()).slice(-2)
      + "_"
      + ("0" + now.getHours()).slice(-2)
      + ("0" + now.getMinutes()).slice(-2);
    var defaultName = "bio334_" + ts + ".py";

    var filename = prompt("Save as:", defaultName);
    if (!filename) return; // cancelled

    // Ensure .py extension
    if (!/\.\w+$/.test(filename)) filename += ".py";

    var blob = new Blob([code], { type: "text/x-python" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function uploadCode(file) {
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function (e) {
      window.setEditorCode(e.target.result);
      clearOutput();
    };
    reader.readAsText(file);
  }

  /* ---- Resize Handle ---- */
  function initResizeHandle() {
    var handle = document.querySelector(".resize-handle");
    var editorWrapper = document.getElementById("editor-wrapper");
    var outputPanel = document.getElementById("output-panel");
    var container = document.querySelector(".editor-container");

    if (!handle || !container) return;

    var startY, startEditorHeight, startOutputHeight;

    handle.addEventListener("mousedown", function (e) {
      e.preventDefault();
      startY = e.clientY;
      startEditorHeight = editorWrapper.offsetHeight;
      startOutputHeight = outputPanel.offsetHeight;

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "row-resize";
      document.body.style.userSelect = "none";
    });

    function onMouseMove(e) {
      var delta = e.clientY - startY;
      var newEditorHeight = Math.max(80, startEditorHeight + delta);
      var newOutputHeight = Math.max(60, startOutputHeight - delta);

      editorWrapper.style.flex = "0 0 " + newEditorHeight + "px";
      outputPanel.style.flex = "0 0 " + newOutputHeight + "px";
    }

    function onMouseUp() {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }
  }

  /* ---- File Browser (data + workspace) ---- */
  var cachedFileData = null;  // { data: [...], workspace: [...] }
  var fileDropdown = null;

  function loadDataFileHints() {
    var hintEl = document.getElementById("args-hint");
    if (!hintEl) return;

    refreshFileList(hintEl);
  }

  function refreshFileList(hintEl) {
    if (!hintEl) hintEl = document.getElementById("args-hint");
    if (!hintEl) return;

    Bio334.apiRequest("GET", "/api/data-files")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (resp) {
        if (!resp) { hintEl.textContent = ""; return; }
        cachedFileData = resp;

        var totalFiles = (resp.data ? resp.data.length : 0)
          + (resp.workspace ? resp.workspace.length : 0);

        if (totalFiles === 0) {
          hintEl.textContent = "";
          return;
        }

        hintEl.innerHTML = '<button class="args-browse-btn" aria-label="Browse available files">'
          + '&#128193; ' + totalFiles + ' file' + (totalFiles > 1 ? 's' : '')
          + '</button>';

        hintEl.querySelector(".args-browse-btn").addEventListener("click", function (e) {
          e.stopPropagation();
          toggleFileDropdown(hintEl);
        });

        // Set placeholder to first available file
        var firstFile = (resp.data && resp.data[0])
          ? resp.data[0].path
          : (resp.workspace && resp.workspace[0]) ? resp.workspace[0].name : "";
        if (argsInput && !argsInput.value && firstFile) {
          argsInput.placeholder = "e.g. " + firstFile;
        }
      })
      .catch(function () {});
  }

  function toggleFileDropdown(anchorEl) {
    if (fileDropdown) {
      fileDropdown.remove();
      fileDropdown = null;
      return;
    }
    if (!cachedFileData) return;

    fileDropdown = document.createElement("div");
    fileDropdown.className = "file-dropdown";

    var hasData = cachedFileData.data && cachedFileData.data.length > 0;
    var hasWorkspace = cachedFileData.workspace && cachedFileData.workspace.length > 0;

    // Workspace files (user's)
    if (hasWorkspace) {
      var wsHeader = document.createElement("div");
      wsHeader.className = "file-dropdown-section";
      wsHeader.textContent = "Your Files";
      fileDropdown.appendChild(wsHeader);

      cachedFileData.workspace.forEach(function (f) {
        var row = document.createElement("div");
        row.className = "file-dropdown-row";

        var item = document.createElement("button");
        item.className = "file-dropdown-item";
        item.textContent = f.name;
        item.title = f.name + " (" + formatSize(f.size) + ")";
        item.addEventListener("click", function () {
          insertFileArg(f.name);
          closeFileDropdown();
        });
        row.appendChild(item);

        var delBtn = document.createElement("button");
        delBtn.className = "file-dropdown-delete";
        delBtn.innerHTML = "&times;";
        delBtn.title = "Delete " + f.name;
        delBtn.addEventListener("click", function (e) {
          e.stopPropagation();
          deleteWorkspaceFile(f.name);
        });
        row.appendChild(delBtn);

        fileDropdown.appendChild(row);
      });
    }

    // Data files (read-only)
    if (hasData) {
      var dataHeader = document.createElement("div");
      dataHeader.className = "file-dropdown-section";
      dataHeader.textContent = "Course Data (read-only)";
      fileDropdown.appendChild(dataHeader);

      // Group by directory
      var groups = {};
      cachedFileData.data.forEach(function (f) {
        var parts = f.path.split("/");
        var dir = parts.length > 1 ? parts.slice(0, -1).join("/") : "";
        if (!groups[dir]) groups[dir] = [];
        groups[dir].push(f);
      });

      Object.keys(groups).sort().forEach(function (dir) {
        if (dir) {
          var dirLabel = document.createElement("div");
          dirLabel.className = "file-dropdown-dir";
          dirLabel.textContent = dir + "/";
          fileDropdown.appendChild(dirLabel);
        }
        groups[dir].forEach(function (f) {
          var item = document.createElement("button");
          item.className = "file-dropdown-item";
          item.textContent = f.name;
          item.title = f.path + " (" + formatSize(f.size) + ")";
          item.addEventListener("click", function () {
            insertFileArg(f.path);
            closeFileDropdown();
          });
          fileDropdown.appendChild(item);
        });
      });
    }

    // "Save current code" button at bottom
    var saveRow = document.createElement("div");
    saveRow.className = "file-dropdown-save";
    var saveBtn = document.createElement("button");
    saveBtn.className = "file-dropdown-save-btn";
    saveBtn.textContent = "+ Save current code to workspace";
    saveBtn.addEventListener("click", function () {
      closeFileDropdown();
      saveToWorkspace();
    });
    saveRow.appendChild(saveBtn);
    fileDropdown.appendChild(saveRow);

    // Position below the browse button using fixed positioning
    document.body.appendChild(fileDropdown);
    var browseBtn = anchorEl.querySelector(".args-browse-btn");
    var rect = browseBtn ? browseBtn.getBoundingClientRect() : anchorEl.getBoundingClientRect();
    var dropdownHeight = fileDropdown.offsetHeight;
    var viewportHeight = window.innerHeight;

    // Prefer opening downward; flip up if not enough space below
    var top = rect.bottom + 4;
    if (top + dropdownHeight > viewportHeight - 8) {
      top = rect.top - dropdownHeight - 4;
      if (top < 8) top = 8; // clamp to top edge
    }
    fileDropdown.style.top = top + "px";
    // Align right edge with button right edge
    var right = window.innerWidth - rect.right;
    fileDropdown.style.right = right + "px";

    // Close on outside click
    function closeOnOutside(e) {
      if (fileDropdown && !fileDropdown.contains(e.target)
          && !e.target.classList.contains("args-browse-btn")) {
        closeFileDropdown();
        document.removeEventListener("click", closeOnOutside);
      }
    }
    setTimeout(function () {
      document.addEventListener("click", closeOnOutside);
    }, 0);
  }

  function closeFileDropdown() {
    if (fileDropdown) {
      if (fileDropdown.parentNode) {
        fileDropdown.parentNode.removeChild(fileDropdown);
      }
      fileDropdown = null;
    }
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function insertFileArg(filePath) {
    // Insert into Teaching Assistant chat input (primary use case)
    var chatInput = document.getElementById("chat-input");
    if (chatInput) {
      var current = chatInput.value;
      // If empty, add a prompt template
      if (!current.trim()) {
        chatInput.value = filePath + " ";
      } else {
        // Insert at cursor position or append
        var start = chatInput.selectionStart;
        var end = chatInput.selectionEnd;
        chatInput.value = current.substring(0, start) + filePath + current.substring(end);
        chatInput.selectionStart = chatInput.selectionEnd = start + filePath.length;
      }
      chatInput.focus();
      // Auto-resize
      chatInput.style.height = "auto";
      chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
    }

    // Also set in Args field so the file is available for direct Run
    if (argsInput) {
      var argsVal = argsInput.value.trim();
      if (argsVal) {
        argsInput.value = argsVal + " " + filePath;
      } else {
        argsInput.value = filePath;
      }
    }
  }

  /* ---- Workspace Save / Delete ---- */
  function saveToWorkspace() {
    var code = getCode().trim();
    if (!code) {
      alert("Nothing to save — editor is empty.");
      return;
    }

    var now = new Date();
    var ts = now.getFullYear()
      + ("0" + (now.getMonth() + 1)).slice(-2)
      + ("0" + now.getDate()).slice(-2)
      + "_"
      + ("0" + now.getHours()).slice(-2)
      + ("0" + now.getMinutes()).slice(-2);
    var defaultName = "my_script_" + ts + ".py";
    var filename = prompt("Save to workspace as:", defaultName);
    if (!filename) return;

    Bio334.apiRequest("POST", "/api/workspace/save", {
      filename: filename,
      content: code,
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.status === "ok") {
          refreshFileList();
          // Show brief confirmation on the Save button
          if (btnSaveWs) {
            var orig = btnSaveWs.textContent;
            btnSaveWs.textContent = "Saved!";
            btnSaveWs.disabled = true;
            setTimeout(function () {
              btnSaveWs.textContent = orig;
              btnSaveWs.disabled = false;
            }, 1500);
          }
        } else {
          alert("Save failed: " + (data.detail || "Unknown error"));
        }
      })
      .catch(function (err) {
        alert("Save failed: " + err.message);
      });
  }

  function deleteWorkspaceFile(filename) {
    if (!confirm("Delete \"" + filename + "\" from workspace?")) return;

    Bio334.apiRequest("DELETE", "/api/workspace/" + encodeURIComponent(filename))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.status === "ok") {
          closeFileDropdown();
          refreshFileList();
        }
      })
      .catch(function () {});
  }

  /* ---- Restore from Workspace ---- */
  function showRestoreDropdown() {
    // Close if already open
    if (restoreDropdown) {
      restoreDropdown.remove();
      restoreDropdown = null;
      return;
    }

    // Fetch latest workspace file list
    Bio334.apiRequest("GET", "/api/data-files")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (resp) {
        if (!resp || !resp.workspace || resp.workspace.length === 0) {
          alert("No files in workspace yet. Use Save to create one first.");
          return;
        }

        restoreDropdown = document.createElement("div");
        restoreDropdown.className = "file-dropdown";

        var header = document.createElement("div");
        header.className = "file-dropdown-section";
        header.textContent = "Load into Editor";
        restoreDropdown.appendChild(header);

        resp.workspace.forEach(function (f) {
          var item = document.createElement("button");
          item.className = "file-dropdown-item";
          item.textContent = f.name + "  (" + formatSize(f.size) + ")";
          item.title = "Load " + f.name + " into the editor";
          item.addEventListener("click", function () {
            loadWorkspaceFile(f.name);
            restoreDropdown.remove();
            restoreDropdown = null;
          });
          restoreDropdown.appendChild(item);
        });

        // Position below the Restore button
        document.body.appendChild(restoreDropdown);
        var rect = btnRestoreWs.getBoundingClientRect();
        var dropH = restoreDropdown.offsetHeight;
        var viewH = window.innerHeight;

        var top = rect.bottom + 4;
        if (top + dropH > viewH - 8) {
          top = rect.top - dropH - 4;
          if (top < 8) top = 8;
        }
        restoreDropdown.style.top = top + "px";
        restoreDropdown.style.left = rect.left + "px";

        // Close on outside click
        function closeOnOutside(e) {
          if (restoreDropdown && !restoreDropdown.contains(e.target) && e.target !== btnRestoreWs) {
            restoreDropdown.remove();
            restoreDropdown = null;
            document.removeEventListener("click", closeOnOutside);
          }
        }
        setTimeout(function () {
          document.addEventListener("click", closeOnOutside);
        }, 0);
      })
      .catch(function () {
        alert("Could not load workspace file list.");
      });
  }

  function loadWorkspaceFile(filename) {
    Bio334.apiRequest("GET", "/api/workspace/" + encodeURIComponent(filename))
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        window.setEditorCode(data.content);
        clearOutput();
        // Also set filename in args if it's a data file (not .py)
        if (argsInput && !/\.py$/.test(filename)) {
          argsInput.value = filename;
        }
      })
      .catch(function (err) {
        alert("Could not load file: " + err.message);
      });
  }

  // Expose for use from other modules
  window.saveToWorkspace = saveToWorkspace;

  /* ---- Public Init ---- */
  window.initCodeEditor = function () {
    if (editorInitialized) return;
    editorInitialized = true;

    // Try to init CodeMirror if it's loaded
    if (window._CM) {
      initCodeMirror();
    } else {
      // Wait for CodeMirror to load
      window.addEventListener("codemirror-ready", function () {
        if (window._CM) {
          initCodeMirror();
        } else {
          // CodeMirror failed, init textarea line numbers
          initTextareaLineNumbers();
        }
      });
    }

    initResizeHandle();
  };

  /* ---- Init ---- */
  function init() {
    textarea = document.getElementById("code-input");
    outputContent = document.getElementById("output-content");
    executionTime = document.getElementById("execution-time");
    btnRun = document.getElementById("btn-run");
    btnClear = document.getElementById("btn-clear-output");
    btnReset = document.getElementById("btn-reset-code");
    btnSaveWs = document.getElementById("btn-stash");
    btnRestoreWs = document.getElementById("btn-stash-load");
    argsInput = document.getElementById("code-args");
    var btnDownload = document.getElementById("btn-download");
    var btnUpload = document.getElementById("btn-upload");
    var fileInput = document.getElementById("file-load-input");

    // Set default code
    textarea.value = defaultCode;

    // Detect platform and show shortcut hint
    var isMac = /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent);
    var runKey = isMac ? "\u2318\u23CE" : "Ctrl+Enter";
    var runKeyLong = isMac ? "Cmd+Enter" : "Ctrl+Enter";
    var hintEl = document.getElementById("shortcut-hint");
    var saveKey = isMac ? "\u2318S" : "Ctrl+S";
    var saveKeyLong = isMac ? "Cmd+S" : "Ctrl+S";
    if (hintEl) {
      hintEl.textContent = runKey + " Run  |  " + saveKey + " Save";
      hintEl.title = runKeyLong + " to run | " + saveKeyLong + " to save to workspace | Tab to indent";
    }
    if (btnRun) {
      btnRun.title = "Run code (" + runKeyLong + ")";
    }

    // Event listeners
    btnRun.addEventListener("click", runCode);
    btnClear.addEventListener("click", clearOutput);
    btnReset.addEventListener("click", resetCode);
    if (btnSaveWs) btnSaveWs.addEventListener("click", saveToWorkspace);
    if (btnRestoreWs) {
      btnRestoreWs.disabled = false;
      btnRestoreWs.addEventListener("click", showRestoreDropdown);
    }
    if (btnDownload) btnDownload.addEventListener("click", downloadCode);
    if (btnUpload) btnUpload.addEventListener("click", function () { fileInput.click(); });
    if (fileInput) fileInput.addEventListener("change", function () {
      if (this.files && this.files[0]) {
        uploadCode(this.files[0]);
        this.value = "";
      }
    });

    // Load available data files for the args hint
    loadDataFileHints();

    // Keyboard shortcuts
    document.addEventListener("keydown", function (e) {
      if (!Bio334.editorVisible) return;
      // Ctrl/Cmd+Enter to run
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        runCode();
      }
      // Ctrl/Cmd+S to save to workspace
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        saveToWorkspace();
      }
    });

    // Tab key in textarea inserts spaces instead of changing focus
    textarea.addEventListener("keydown", function (e) {
      if (e.key === "Tab") {
        e.preventDefault();
        var start = this.selectionStart;
        var end = this.selectionEnd;
        this.value = this.value.substring(0, start) + "    " + this.value.substring(end);
        this.selectionStart = this.selectionEnd = start + 4;
      }
    });

    // Click handler for error line links in output
    outputContent.addEventListener("click", function (e) {
      var link = e.target.closest(".error-line-link");
      if (link) {
        e.preventDefault();
        var lineNum = parseInt(link.getAttribute("data-line"), 10);
        if (lineNum > 0) {
          highlightErrorLines([lineNum]);
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
