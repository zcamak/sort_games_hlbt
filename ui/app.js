// Interactive Game Sorter Application Logic

(function () {
  let allGames = [];
  let currentSort = {
    column: "main_extra",
    direction: "asc", // Shortest to longest by default
  };
  let searchQuery = "";

  // DOM Elements
  const loadBtn = document.getElementById("load-btn");
  const exportBtn = document.getElementById("export-btn");
  const fileInput = document.getElementById("file-input");
  const searchInput = document.getElementById("search-input");
  const statsCounter = document.getElementById("stats-counter");
  const progressCard = document.getElementById("progress-card");
  const progressStatus = document.getElementById("progress-status");
  const progressCount = document.getElementById("progress-count");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const tableBody = document.getElementById("games-table-body");
  const emptyState = document.getElementById("empty-state");
  const tableCard = document.getElementById("table-card");

  // Format HTML safety
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Sorting Comparator
  function compareGames(a, b) {
    const col = currentSort.column;
    const isAsc = currentSort.direction === "asc";

    if (col === "title") {
      const nameA = (a.game_name || a.user_title || "").toLowerCase();
      const nameB = (b.game_name || b.user_title || "").toLowerCase();
      return isAsc ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
    }

    // Time Columns: 'main_story', 'main_extra', 'completionist'
    const timeA = a[col] ? a[col].minutes : -1;
    const timeB = b[col] ? b[col].minutes : -1;

    // Both missing -> fallback to title sort
    if (timeA <= 0 && timeB <= 0) {
      return (a.game_name || "").localeCompare(b.game_name || "");
    }

    // Always pin missing values (-- / -1) to the bottom regardless of sort direction
    if (timeA <= 0) return 1;
    if (timeB <= 0) return -1;

    return isAsc ? timeA - timeB : timeB - timeA;
  }

  // Render Table
  function renderTable() {
    if (!allGames || allGames.length === 0) {
      tableCard.style.display = "none";
      emptyState.style.display = "block";
      statsCounter.innerHTML = "No games loaded";
      return;
    }

    // Filter by search query
    const filtered = allGames.filter((g) => {
      if (!searchQuery) return true;
      const q = searchQuery.toLowerCase();
      const title = (g.game_name || g.user_title || "").toLowerCase();
      const year = g.release_year ? String(g.release_year) : "";
      return title.includes(q) || year.includes(q);
    });

    // Sort
    filtered.sort(compareGames);

    tableCard.style.display = "block";
    emptyState.style.display = "none";
    statsCounter.innerHTML = `Showing <strong>${filtered.length}</strong> of <strong>${allGames.length}</strong> games`;

    // Build rows
    const rowsHtml = filtered
      .map((g) => {
        const coverUrl = g.game_image_url;
        const gameName = escapeHtml(g.game_name || g.user_title || "Unknown");
        const releaseYear = g.release_year ? escapeHtml(g.release_year) : "—";
        const link = g.game_web_link ? escapeHtml(g.game_web_link) : "#";

        const mainStory = g.main_story || { display: "--", minutes: -1 };
        const mainExtra = g.main_extra || { display: "--", minutes: -1 };
        const comp = g.completionist || { display: "--", minutes: -1 };

        const coverHtml = coverUrl
          ? `<img class="game-cover-img" src="${escapeHtml(coverUrl)}" alt="${gameName}" loading="lazy" onerror="this.parentElement.innerHTML='<span class=\\'game-cover-placeholder\\'>🎮</span>';">`
          : `<span class="game-cover-placeholder">🎮</span>`;

        const titleCell = `
          <div class="game-title-cell">
            <div class="game-cover-wrap">${coverHtml}</div>
            <div class="game-info">
              <a href="${link}" target="_blank" rel="noopener noreferrer" class="game-name-link" title="View on HowLongToBeat">${gameName}</a>
              <span class="game-release-year">${releaseYear}</span>
            </div>
          </div>
        `;

        const mainBadge = `<span class="time-badge main ${mainStory.minutes > 0 ? "" : "empty"}">${escapeHtml(mainStory.display)}</span>`;
        const extraBadge = `<span class="time-badge extra ${mainExtra.minutes > 0 ? "" : "empty"}">${escapeHtml(mainExtra.display)}</span>`;
        const compBadge = `<span class="time-badge comp ${comp.minutes > 0 ? "" : "empty"}">${escapeHtml(comp.display)}</span>`;

        return `
          <tr>
            <td>${titleCell}</td>
            <td>${mainBadge}</td>
            <td>${extraBadge}</td>
            <td>${compBadge}</td>
          </tr>
        `;
      })
      .join("");

    tableBody.innerHTML = rowsHtml;
    updateHeaderIcons();
  }

  // Update Table Header Sort Indicators
  function updateHeaderIcons() {
    const headers = document.querySelectorAll(".games-table th[data-sort]");
    headers.forEach((th) => {
      const col = th.getAttribute("data-sort");
      const icon = th.querySelector(".sort-icon");

      th.classList.remove("sorted-asc", "sorted-desc");
      if (col === currentSort.column) {
        if (currentSort.direction === "asc") {
          th.classList.add("sorted-asc");
          if (icon) icon.textContent = "▲";
        } else {
          th.classList.add("sorted-desc");
          if (icon) icon.textContent = "▼";
        }
      } else {
        if (icon) icon.textContent = "↕";
      }
    });
  }

  // Handle Header Click
  function onHeaderClick(e) {
    const th = e.currentTarget;
    const col = th.getAttribute("data-sort");
    if (!col) return;

    if (currentSort.column === col) {
      // Toggle direction
      currentSort.direction = currentSort.direction === "asc" ? "desc" : "asc";
    } else {
      currentSort.column = col;
      currentSort.direction = "asc";
    }

    renderTable();
  }

  // Progress UI
  window.updateProgress = function (current, total, gameName) {
    progressCard.style.display = "block";
    const percent = Math.min(100, Math.round((current / total) * 100));
    progressBarFill.style.width = percent + "%";
    progressStatus.textContent = `Fetching: ${gameName || "..."}`;
    progressCount.textContent = `${current} / ${total} (${percent}%)`;

    if (current >= total) {
      setTimeout(() => {
        progressCard.style.display = "none";
      }, 800);
    }
  };

  // Called when games are loaded
  window.onGamesLoaded = function (games) {
    allGames = games || [];
    currentSort = { column: "main_extra", direction: "asc" };
    renderTable();
  };

  // File Loading
  async function handleLoadClick() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.select_file) {
      try {
        progressCard.style.display = "block";
        progressBarFill.style.width = "0%";
        progressStatus.textContent = "Selecting file...";
        progressCount.textContent = "";

        const result = await window.pywebview.api.select_file();
        if (result && result.games) {
          window.onGamesLoaded(result.games);
        } else if (result && result.cancelled) {
          progressCard.style.display = "none";
        }
      } catch (err) {
        console.error("Error loading file via pywebview:", err);
        progressCard.style.display = "none";
        alert("Failed to load file: " + err);
      }
    } else {
      // Browser fallback via file input
      fileInput.click();
    }
  }

  // Browser Fallback for File Input
  fileInput.addEventListener("change", function (e) {
    const file = e.target.files[0];
    if (!file) return;

    alert(
      "To query HowLongToBeat directly from a local text file, please run this app via the Python desktop launcher: `python main.py`"
    );
  });

  // Export HTML Action
  async function handleExportClick() {
    if (!allGames || allGames.length === 0) {
      alert("Please load a games list before exporting.");
      return;
    }

    if (window.pywebview && window.pywebview.api && window.pywebview.api.export_html) {
      try {
        const resp = await window.pywebview.api.export_html(allGames);
        if (resp && resp.success) {
          alert("Successfully exported HTML report to:\n" + resp.path);
        }
      } catch (err) {
        console.error("Export error:", err);
        alert("Failed to export HTML: " + err);
      }
    } else {
      // Browser standalone download
      const htmlContent = document.documentElement.outerHTML;
      const blob = new Blob([htmlContent], { type: "text/html" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "games_report.html";
      a.click();
    }
  }

  // Setup Event Listeners
  loadBtn.addEventListener("click", handleLoadClick);
  exportBtn.addEventListener("click", handleExportClick);

  searchInput.addEventListener("input", function (e) {
    searchQuery = e.target.value.trim();
    renderTable();
  });

  document.querySelectorAll(".games-table th[data-sort]").forEach((th) => {
    th.addEventListener("click", onHeaderClick);
  });

  // Check for preloaded data (used in standalone exported HTML files)
  if (window.PRELOADED_GAMES && Array.isArray(window.PRELOADED_GAMES)) {
    window.onGamesLoaded(window.PRELOADED_GAMES);
  }
})();
