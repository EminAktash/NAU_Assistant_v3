// Detect environment and set appropriate API URL
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_URL = isLocalhost ? 'http://localhost:5000/api' : 'https://nau-assistant-v3.vercel.app/api';

// State variables
let currentFollowUpId = null; // Track the current follow-up question

// DOM Elements
const messagesContainer = document.getElementById('messages');
const welcomeContainer = document.getElementById('welcome-container');
const welcomeTemplate = document.getElementById('welcome-template');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    showWelcomeScreen();
    
    // Note: We no longer need to create the nav button here
    // as it's now included directly in the HTML
});

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Function to show welcome screen
function showWelcomeScreen() {
    // Clear welcome container
    welcomeContainer.innerHTML = '';

    // Clone the template content
    const welcomeContent = welcomeTemplate.content.cloneNode(true);

    // Add it to the welcome container
    welcomeContainer.appendChild(welcomeContent);

    // Show welcome, hide messages
    welcomeContainer.style.display = 'block';
    messagesContainer.classList.add('d-none');
    messagesContainer.innerHTML = ''; // Clear any existing messages
    
    // Reset current follow-up ID
    currentFollowUpId = null;
    
    // Optionally update URL without refreshing the page
    if (window.history && window.history.pushState) {
        window.history.pushState({}, document.title, window.location.pathname);
    }
}

async function sendMessage() {
    const message = userInput.value.trim();

    if (!message) return;

    // Hide welcome screen, show messages
    welcomeContainer.style.display = 'none';
    messagesContainer.classList.remove('d-none');

    // Clear input
    userInput.value = '';

    // Add user message to UI
    const userMessage = {
        role: 'user',
        content: message
    };
    renderMessage(userMessage);
    
    // Ensure scroll after user message
    scrollToBottom();

    // Add loading 
    const loadingId = 'loading-' + Date.now();
    const loadingHTML = `
        <div class="message assistant-message" id="${loadingId}">
            <div class="message-content">
                <p><i class="bi bi-three-dots"></i> Thinking</p>
            </div>
        </div>
    `;
    messagesContainer.insertAdjacentHTML('beforeend', loadingHTML);
    
    // Scroll to see the loading indicator
    scrollToBottom();

    try {
        // Prepare the request payload
        const payload = {
            chat_id: 'default', // Use a default chat ID since we don't track chats
            query: message
        };

        // If this is a response to a follow-up question, include that info
        if (currentFollowUpId) {
            payload.follow_up_to = currentFollowUpId;
            // Reset follow up ID after using it
            currentFollowUpId = null;
        }

        console.log(`Sending request to: ${API_URL}/chat`);
        
        // Send message to API
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        // Remove loading message
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) loadingElement.remove();

        const data = await response.json();
        console.log('Response data:', data);

        // Add assistant message to UI
        const assistantMessage = {
            role: 'assistant',
            content: data.answer,
            sources: data.sources
        };
        renderMessage(assistantMessage);

        // Check if there's a follow-up question
        if (data.follow_up) {
            // Wait a moment before showing the follow-up
            setTimeout(() => {
                const followUpMessage = {
                    role: 'assistant',
                    content: data.follow_up,
                    follow_up: true,
                    follow_up_id: data.follow_up_id
                };
                renderMessage(followUpMessage);

                // Set the current follow-up ID
                currentFollowUpId = data.follow_up_id;
                
                // Ensure scrolling after the follow-up appears
                scrollToBottom();
            }, 1000);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        // Remove loading message
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) loadingElement.remove();

        // Add error message
        const errorHTML = `
            <div class="message assistant-message">
                <div class="message-content">
                    <p class="text-danger">Error: Could not get a response. Please try again.</p>
                </div>
            </div>
        `;
        messagesContainer.insertAdjacentHTML('beforeend', errorHTML);
    }
}

function renderMessage(message) {
    const messageDiv = document.createElement('div');

    // Add special class for follow-up questions
    if (message.follow_up) {
        messageDiv.className = `message follow-up-message`;
    } else {
        messageDiv.className = `message ${message.role}-message`;
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const paragraph = document.createElement('p');
    paragraph.innerHTML = message.content.replace(/\n/g, '<br>');
    contentDiv.appendChild(paragraph);

    // Add follow-up ID as data attribute if it exists
    if (message.follow_up_id) {
        messageDiv.dataset.followUpId = message.follow_up_id;
    }

    // Add sources if they exist and not a follow-up question
    if (message.sources && message.sources.length > 0 && !message.follow_up) {
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'sources';

        const sourcesText = document.createElement('p');
        sourcesText.textContent = 'Sources:';
        sourcesDiv.appendChild(sourcesText);

        const sourcesList = document.createElement('ul');
        message.sources.forEach(source => {
            const sourceItem = document.createElement('li');
            const sourceLink = document.createElement('a');
            sourceLink.href = source;
            sourceLink.target = '_blank';
            sourceLink.className = 'source-link';
            sourceLink.textContent = source;
            sourceItem.appendChild(sourceLink);
            sourcesList.appendChild(sourceItem);
        });

        sourcesDiv.appendChild(sourcesList);
        contentDiv.appendChild(sourcesDiv);
    }

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom - enhanced for multiple approaches
    scrollToBottom();
}

// Function to ensure scrolling to the bottom
function scrollToBottom() {
    // Method 1: Scroll the messages container
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Method 2: Scroll the whole window to ensure mobile compatibility
    window.scrollTo(0, document.body.scrollHeight);
    
    // Method 3: Use smooth scrolling for better UX
    messagesContainer.scrollIntoView({ behavior: 'smooth', block: 'end' });
    
    // Method 4: Delayed scroll to handle content rendering
    setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        window.scrollTo(0, document.body.scrollHeight);
    }, 100);
}

// Function to ask a question from the FAQ buttons
function askQuestion(question) {
    // Set the input value to the question
    userInput.value = question;
    // Send the message
    sendMessage();
}