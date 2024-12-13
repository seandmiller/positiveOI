// DOM Elements
const tickerInput = document.getElementById("tickerInput");
const searchButton = document.getElementById("searchButton");
const loadingState = document.getElementById("loadingState");
const statusDisplay = document.getElementById("statusDisplay");
const statusText = document.getElementById("statusText");
const resultsDisplay = document.getElementById("resultsDisplay");

// Metrics Elements
const revenue = document.getElementById("revenue");
const grossMargin = document.getElementById("grossMargin");
const operatingExpenses = document.getElementById("operatingExpenses");
const growthRate = document.getElementById("growthRate");
const timeToProfit = document.getElementById("timeToProfit");
const timeToYears = document.getElementById("timeToYears");
const projectedRevenue = document.getElementById("projectedRevenue");
const projectedExpenses = document.getElementById("projectedExpenses");
const projectedProfit = document.getElementById("projectedProfit");

// Event Listeners
searchButton.addEventListener("click", handleSearch);
tickerInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    handleSearch();
  }
});

async function handleSearch() {
  const ticker = tickerInput.value.trim().toUpperCase();

  if (!ticker) {
    showStatus("Please enter a ticker symbol", "error");
    return;
  }

  // Clear previous states
  hideStatus();
  hideResults();
  showLoading();

  try {
    const response = await fetch(`/api/metrics/${ticker}`);
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = await response.json();
    displayResults(data);
    showStatus("Data fetched successfully", "success");
  } catch (err) {
    showStatus(err.message, "error");
  } finally {
    hideLoading();
  }
}

function displayResults(data) {
  const { inputMetrics, profitability } = data;

  // Display input metrics
  revenue.textContent = `Revenue: $${inputMetrics.quarterlyRevenue}M`;
  grossMargin.textContent = `Gross Margin: ${inputMetrics.grossMargin}%`;
  operatingExpenses.textContent = `Operating Expenses: $${inputMetrics.operatingExpenses}M`;
  growthRate.textContent = `Growth Rate: ${inputMetrics.revenueGrowthRate}%`;

  // Display profitability metrics
  timeToProfit.textContent =
    typeof profitability.quartersToProfitability === "number"
      ? `${profitability.quartersToProfitability} Quarters`
      : profitability.quartersToProfitability;

  timeToYears.textContent =
    profitability.yearsToProfit === "N/A"
      ? ""
      : `(${profitability.yearsToProfit} years)`;

  projectedRevenue.textContent = `$${profitability.projectedRevenue}M`;
  projectedExpenses.textContent = `$${profitability.projectedExpenses}M`;
  projectedProfit.textContent = `$${profitability.projectedProfit}M`;

  showResults();
}

function showLoading() {
  searchButton.disabled = true;
  loadingState.classList.remove("hidden");
}

function hideLoading() {
  searchButton.disabled = false;
  loadingState.classList.add("hidden");
}

function showStatus(message, type) {
  statusText.textContent = message;
  statusDisplay.classList.remove("hidden", "success", "error");
  statusDisplay.classList.add("visible", type);
}

function hideStatus() {
  statusDisplay.classList.remove("visible", "success", "error");
  statusDisplay.classList.add("hidden");
  statusText.textContent = "";
}

function showResults() {
  resultsDisplay.classList.remove("hidden");
}

function hideResults() {
  resultsDisplay.classList.add("hidden");
}
