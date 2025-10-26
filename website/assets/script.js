// Alkinson's Newsletter JavaScript

document.addEventListener('DOMContentLoaded', function() {
    loadCurrentWeek();
    loadArchive();
    setupSubscriptionForm();
});

async function loadCurrentWeek() {
    try {
        const response = await fetch('/data/current-week.json');
        const data = await response.json();
        displayWeeklyContent(data);
    } catch (error) {
        document.getElementById('content-loading').innerHTML = 
            '<p>Unable to load current content. Please try again later.</p>';
    }
}

function displayWeeklyContent(data) {
    const contentDiv = document.getElementById('content-loading');
    contentDiv.innerHTML = `
        <div class="weekly-content">
            <h3>Week of ${new Date(data.generated_date).toLocaleDateString()}</h3>
            
            <div class="disease-section">
                <h4>Alzheimer's Disease Updates</h4>
                <p>${data.alzheimers.summary}</p>
                <div class="articles">
                    ${data.alzheimers.articles.map(article => `
                        <div class="article">
                            <h5><a href="${article.url}" target="_blank">${article.title}</a></h5>
                            <p class="source">Source: ${article.source}</p>
                            <p>${article.summary}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="disease-section">
                <h4>Parkinson's Disease Updates</h4>
                <p>${data.parkinsons.summary}</p>
                <div class="articles">
                    ${data.parkinsons.articles.map(article => `
                        <div class="article">
                            <h5><a href="${article.url}" target="_blank">${article.title}</a></h5>
                            <p class="source">Source: ${article.source}</p>
                            <p>${article.summary}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
}

async function loadArchive() {
    // Placeholder for archive loading
    document.getElementById('archive-list').innerHTML = 
        '<p>Archive will be populated as weekly summaries are generated.</p>';
}

function setupSubscriptionForm() {
    const form = document.getElementById('subscribe-form');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const messageDiv = document.getElementById('subscription-message');
        
        try {
            const response = await fetch('/api/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email: email })
            });
            
            if (response.ok) {
                messageDiv.innerHTML = '<p style="color: green;">Successfully subscribed! Check your email for confirmation.</p>';
                form.reset();
            } else {
                messageDiv.innerHTML = '<p style="color: red;">Subscription failed. Please try again.</p>';
            }
        } catch (error) {
            messageDiv.innerHTML = '<p style="color: red;">Network error. Please try again.</p>';
        }
    });
}