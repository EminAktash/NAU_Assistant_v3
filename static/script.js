// Detect environment and set appropriate API URL
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const API_URL = isLocalhost ? 'http://localhost:5000/api' : 'https://nau-assistant-v3.vercel.app/api';

// State variables
let currentFollowUpId = null; // Track the current follow-up question
let userHasScrolled = false; // Track if user has manually scrolled up

// DOM Elements
const messagesContainer = document.getElementById('messages');
const welcomeContainer = document.getElementById('welcome-container');
const welcomeTemplate = document.getElementById('welcome-template');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const chatContainer = document.getElementById('chat-container');

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    showWelcomeScreen();
    
    // Add scroll event listener to detect when user manually scrolls
    chatContainer.addEventListener('scroll', () => {
        const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 100;
        
        if (isNearBottom) {
            userHasScrolled = false;
        } else {
            userHasScrolled = true;
        }
    });
});

// Add window event listeners for better scroll handling
window.addEventListener('resize', enhancedScrollToBottom);
window.addEventListener('orientationchange', () => {
    // Wait for orientation change to complete
    setTimeout(enhancedScrollToBottom, 500);
});

// Handle keyboard appearing on mobile
userInput.addEventListener('focus', () => {
    // Wait for keyboard to appear
    setTimeout(enhancedScrollToBottom, 600);
});

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Enhanced scrolling function for better reliability across devices
function enhancedScrollToBottom() {
    // Only auto-scroll if user hasn't manually scrolled up or if explicit force scroll
    if (!userHasScrolled) {
        // Get the height of the viewport
        const viewportHeight = window.innerHeight;
        
        // Primary method: Scroll the messages container
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        // Method for mobile devices: Scroll the whole document
        window.scrollTo({
            top: document.body.scrollHeight,
            behavior: 'smooth'
        });
        
        // Backup method: Use requestAnimationFrame to ensure the DOM is fully updated
        requestAnimationFrame(() => {
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
            
            // Secondary scroll to handle issues on some mobile browsers
            window.scrollTo({
                top: document.body.scrollHeight,
                behavior: 'smooth'
            });
        });
        
        // Force scroll after a short delay to handle slow rendering
        setTimeout(() => {
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight + 1000; // Extra padding to ensure we go all the way down
            }
            
            // Final attempt to scroll the window with extra padding
            window.scrollTo(0, document.body.scrollHeight + 1000);
            
            // Make sure chat container is also scrolled
            if (chatContainer) {
                chatContainer.scrollTop = chatContainer.scrollHeight + 1000;
            }
        }, 300);
    }
}

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
    
    // Reset current follow-up ID and scroll state
    currentFollowUpId = null;
    userHasScrolled = false;
    
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
    
    // Reset user scroll state when sending a new message
    userHasScrolled = false;
    
    // Ensure scroll after user message
    enhancedScrollToBottom();

    // Add loading indicator with more descriptive text for web search
    const loadingId = 'loading-' + Date.now();
    const loadingHTML = `
        <div class="message assistant-message" id="${loadingId}">
            <div class="message-content">
                <p><i class="bi bi-search"></i> Thinking...</p>
            </div>
        </div>
    `;
    messagesContainer.insertAdjacentHTML('beforeend', loadingHTML);
    
    // Scroll to see the loading indicator
    enhancedScrollToBottom();

    try {
        // Prepare the request payload
        const payload = {
            chat_id: 'default', // Use a default chat ID since we don't track chats
            query: message
        };

        // If this is a response to a follow-up question, include that info
        if (currentFollowUpId) {
            payload.follow_up_to = currentFollowUpId;
            payload.original_question = message;
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
        
        // Ensure scroll after assistant message
        enhancedScrollToBottom();

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
                
                // Store the original question for context if needed
                if (data.original_question) {
                    followUpMessage.original_question = data.original_question;
                }
                
                // Ensure scrolling after the follow-up appears
                enhancedScrollToBottom();
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
        
        // Scroll to error message
        enhancedScrollToBottom();
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

    // Format the message content, properly handling citation brackets if any
    let formattedContent = message.content;
    
    // Check for OpenAI-style citation syntax like [1], [2], etc. and make them superscript
    // This makes citations stand out in the UI
    formattedContent = formattedContent.replace(/\[(\d+)\]/g, '<sup class="citation-marker">[<a href="#citation-$1" class="citation-link">$1</a>]</sup>');
    
    const paragraph = document.createElement('p');
    paragraph.innerHTML = formattedContent.replace(/\n/g, '<br>');
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
        sourcesList.className = 'source-list';
        
        message.sources.forEach((source, index) => {
            const sourceItem = document.createElement('li');
            sourceItem.id = `citation-${index + 1}`; // Used for citation links
            
            const sourceLink = document.createElement('a');
            sourceLink.href = source;
            sourceLink.target = '_blank';
            sourceLink.className = 'source-link';
            
            // Add source number for reference with citations
            sourceLink.textContent = `[${index + 1}] ${source}`;
            
            sourceItem.appendChild(sourceLink);
            sourcesList.appendChild(sourceItem);
        });

        sourcesDiv.appendChild(sourcesList);
        contentDiv.appendChild(sourcesDiv);
    }

    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom after rendering message
    enhancedScrollToBottom();
}

// Function to ask a question from the FAQ buttons
function askQuestion(question) {
    // Set the input value to the question
    userInput.value = question;
    // Send the message
    sendMessage();
}

// Fix for mobile viewport height issues
function setAppHeight() {
    const doc = document.documentElement;
    doc.style.setProperty('--app-height', `${window.innerHeight}px`);
}
window.addEventListener('resize', setAppHeight);
window.addEventListener('orientationchange', setAppHeight);
setAppHeight();

// Scroll indicator functionality
const scrollIndicator = document.getElementById('scroll-indicator');

// Show/hide scroll indicator based on scroll position
chatContainer.addEventListener('scroll', () => {
    const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 100;
    
    if (isNearBottom) {
        userHasScrolled = false;
        scrollIndicator.classList.remove('visible');
    } else {
        userHasScrolled = true;
        scrollIndicator.classList.add('visible');
    }
});

// Click on scroll indicator to scroll to bottom
scrollIndicator.addEventListener('click', () => {
    userHasScrolled = false;
    enhancedScrollToBottom();
    scrollIndicator.classList.remove('visible');
});

// Modify enhancedScrollToBottom to update scroll indicator
function updateScrollIndicator() {
    const isNearBottom = chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight < 100;
    
    if (isNearBottom) {
        scrollIndicator.classList.remove('visible');
    } else if (userHasScrolled) {
        scrollIndicator.classList.add('visible');
    }
}

// Call this after each scroll operation
const originalEnhancedScrollToBottom = enhancedScrollToBottom;
enhancedScrollToBottom = function() {
    originalEnhancedScrollToBottom();
    setTimeout(updateScrollIndicator, 400);
};

// Additional improvement: detect when keyboard appears on mobile
let originalWindowHeight = window.innerHeight;
window.addEventListener('resize', () => {
    // If window height decreases significantly, keyboard probably appeared
    if (window.innerHeight < originalWindowHeight * 0.8) {
        setTimeout(enhancedScrollToBottom, 300);
    } else {
        originalWindowHeight = window.innerHeight;
    }
});

// Fix for iOS devices where keyboard handling is different
if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
    document.body.addEventListener('focusin', () => {
        // Element received focus, keyboard might be shown
        setTimeout(enhancedScrollToBottom, 500);
    });
    
    document.body.addEventListener('focusout', () => {
        // Element lost focus, keyboard might be hidden
        setTimeout(enhancedScrollToBottom, 500);
    });
}