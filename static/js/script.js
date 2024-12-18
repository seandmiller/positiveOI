const tickerInput = document.getElementById("tickerInput");
const searchButton = document.getElementById("searchButton");
const loadingState = document.getElementById("loadingState");
const statusDisplay = document.getElementById("statusDisplay");
const statusText = document.getElementById("statusText");
const resultsDisplay = document.getElementById("resultsDisplay");

const revenue = document.getElementById("revenue");
const grossMargin = document.getElementById("grossMargin");
const operatingExpenses = document.getElementById("operatingExpenses");
const growthRate = document.getElementById("growthRate");
const timeToProfit = document.getElementById("timeToProfit");
const timeToYears = document.getElementById("timeToYears");
const projectedRevenue = document.getElementById("projectedRevenue");
const projectedExpenses = document.getElementById("projectedExpenses");
const projectedProfit = document.getElementById("projectedProfit");
const projectedGrossProfit = document.getElementById("projectedGrossProfit");

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

  revenue.textContent = `Revenue: $${inputMetrics.quarterlyRevenue}M`;
  grossMargin.textContent = `Gross Margin: ${inputMetrics.grossMargin}%`;
  operatingExpenses.textContent = `Operating Expenses: $${inputMetrics.operatingExpenses}M`;
  growthRate.textContent = `Growth Rate: ${inputMetrics.revenueGrowthRate}%`;

  timeToProfit.textContent =
    typeof profitability.quartersToProfitability === "number"
      ? `${profitability.quartersToProfitability} Quarters`
      : profitability.quartersToProfitability;

  timeToYears.textContent =
    profitability.yearsToProfit === "N/A"
      ? ""
      : `(${profitability.yearsToProfit} years)`;

  projectedRevenue.textContent = `$${profitability.projectedRevenue}M`;
  projectedGrossProfit.textContent = `$${profitability.projectedGrossProfit}M`;
  projectedExpenses.textContent = `$${profitability.projectedExpenses}M`;
  projectedProfit.textContent = `$${profitability.projectedProfit}M`;

  showResults();

  if (data.sentiment) {
    document.getElementById("avgSentiment").textContent =
      data.sentiment.averageSentiment.toFixed(2);
    document.getElementById("sentimentCategory").textContent =
      data.sentiment.sentimentCategory;
    document.getElementById("newsCount").textContent = data.sentiment.newsCount;

    const handle = document.getElementById("sentimentHandle");
    const scoreDisplay = document.getElementById("sentimentScore");

    // Convert sentiment from -1:1 range to percentage for positioning
    const position = ((data.sentiment.averageSentiment + 1) / 2) * 100;
    handle.style.left = `${position}%`;

    // Update score display
    scoreDisplay.textContent = `${
      data.sentiment.sentimentCategory
    } (${data.sentiment.averageSentiment.toFixed(2)})`;

    // Display recent news
    const newsList = document.getElementById("newsList");
    newsList.innerHTML = ""; // Clear existing news

    data.sentiment.recentNews.forEach((news) => {
      const newsItem = document.createElement("div");
      newsItem.className = "news-item";
      const sentimentClass = getSentimentClass(news.sentiment);

      newsItem.innerHTML = `
        <p>${news.title}</p>
        <p class="news-date">
          ${news.date} - Sentiment: 
          <span class="${sentimentClass}">
            ${news.sentiment.toFixed(2)}
          </span>
        </p>
      `;
      newsList.appendChild(newsItem);
    });
  }
}

function getSentimentClass(sentiment) {
  if (sentiment >= 0.1) return "sentiment-positive";
  if (sentiment <= -0.1) return "sentiment-negative";
  return "sentiment-neutral";
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
