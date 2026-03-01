// === AUTHENTICATION STATE ===
let authToken = null;
let currentUser = null;
let currentConversationId = null;

// === AUTH UI FUNCTIONS ===
function showLogin() {
    document.getElementById('login-tab').classList.add('active');
    document.getElementById('register-tab').classList.remove('active');
    document.getElementById('login-form').style.display = 'flex';
    document.getElementById('register-form').style.display = 'none';
    document.getElementById('login-error').textContent = '';
    document.getElementById('register-error').textContent = '';
}

function showRegister() {
    document.getElementById('register-tab').classList.add('active');
    document.getElementById('login-tab').classList.remove('active');
    document.getElementById('register-form').style.display = 'flex';
    document.getElementById('login-form').style.display = 'none';
    document.getElementById('login-error').textContent = '';
    document.getElementById('register-error').textContent = '';
}

function showMainInterface() {
     console.log('showMainInterface called'); // ← ADD THIS
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('main-container').style.display = 'block';
    document.getElementById('username-display').textContent = `Welcome, ${currentUser}! 👋`;
    loadConversations();
}

// === LOAD CONVERSATIONS ===
async function loadConversations() {
    console.log('loadConversations called, currentConversationId:', currentConversationId); // ← ADD THIS
    try {
        const response = await fetch('http://127.0.0.1:5000/conversations', {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const data = await response.json();
        console.log('Conversations loaded:', data.conversations.length); // ← ADD THIS
        displayConversations(data.conversations);
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}
// === DISPLAY CONVERSATIONS ===
function displayConversations(conversations) {
    const listContainer = document.getElementById('conversations-list');
    listContainer.innerHTML = '';
    
    if (!conversations || conversations.length === 0) {
        listContainer.innerHTML = '<p style="text-align:center;color:#999;padding:20px;">No conversations yet</p>';
        return;
    }
    
    const groups = {
        today: [],
        yesterday: [],
        last7days: [],
        older: []
    };
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    
    conversations.forEach(conv => {
        const convDate = new Date(conv.updated_at);
        const convDay = new Date(convDate.getFullYear(), convDate.getMonth(), convDate.getDate());
        
        if (convDay.getTime() === today.getTime()) {
            groups.today.push(conv);
        } else if (convDay.getTime() === yesterday.getTime()) {
            groups.yesterday.push(conv);
        } else if (convDay >= sevenDaysAgo) {
            groups.last7days.push(conv);
        } else {
            groups.older.push(conv);
        }
    });
    
    if (groups.today.length > 0) {
        listContainer.appendChild(createConversationGroup('Today', groups.today));
    }
    if (groups.yesterday.length > 0) {
        listContainer.appendChild(createConversationGroup('Yesterday', groups.yesterday));
    }
    if (groups.last7days.length > 0) {
        listContainer.appendChild(createConversationGroup('Last 7 Days', groups.last7days));
    }
    if (groups.older.length > 0) {
        listContainer.appendChild(createConversationGroup('Older', groups.older));
    }
}

// === CREATE CONVERSATION GROUP ===
function createConversationGroup(title, conversations) {
    const groupDiv = document.createElement('div');
    groupDiv.className = 'conversation-group';
    
    const titleDiv = document.createElement('div');
    titleDiv.className = 'conversation-group-title';
    titleDiv.textContent = title;
    groupDiv.appendChild(titleDiv);
    
    conversations.forEach(conv => {
        const convItem = document.createElement('div');
        convItem.className = 'conversation-item';
        convItem.dataset.convId = conv.id;
        
        if (conv.id === currentConversationId) {
            convItem.classList.add('active');
        }
        
        const titleSpan = document.createElement('span');
        titleSpan.className = 'conversation-title';
        titleSpan.textContent = conv.title;
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-conversation';
        deleteBtn.textContent = 'Delete';
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        };
        
        convItem.appendChild(titleSpan);
        convItem.appendChild(deleteBtn);
        convItem.onclick = () => loadConversation(conv.id);
        
        groupDiv.appendChild(convItem);
    });
    
    return groupDiv;
}

// === LOAD CONVERSATION ===
async function loadConversation(convId) {
    try {
        const response = await fetch(`http://127.0.0.1:5000/conversations/${convId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        const conversation = await response.json();
        currentConversationId = convId;
        
        const chatWindow = document.getElementById('chatwindow');
        chatWindow.innerHTML = '';
        
        conversation.messages.forEach(msg => {
            if (msg.role === 'user') {
                addMessageToUI('You', msg.content, 'user-message');
            } else {
                addMessageToUI('Bot', msg.content, 'bot-message');
            }
        });
        
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.convId === convId) {
                item.classList.add('active');
            }
        });
        
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

// === DELETE CONVERSATION ===
async function deleteConversation(convId) {
    if (!confirm('Delete this conversation?')) return;
    
    try {
        const response = await fetch(`http://127.0.0.1:5000/conversations/${convId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            if (convId === currentConversationId) {
                currentConversationId = null;
                document.getElementById('chatwindow').innerHTML = '';
            }
            loadConversations();
        }
    } catch (error) {
        console.error('Error deleting conversation:', error);
    }
}

// === ADD MESSAGE TO UI ===
function addMessageToUI(sender, text, className) {
    const chatwindow = document.getElementById('chatwindow');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${className}`;

    const senderSpan = document.createElement('strong');
    senderSpan.textContent = sender + ": ";

    const textSpan = document.createElement('span');
    textSpan.textContent = text;

    messageDiv.appendChild(senderSpan);
    messageDiv.appendChild(textSpan);
    
    chatwindow.appendChild(messageDiv);
    chatwindow.scrollTop = chatwindow.scrollHeight;
}

// === SEND MESSAGE ===
async function sendMessage() {
    const userInput = document.getElementById('userinput');
    const message = userInput.value.trim();
    
    if (!message) {
        return;
    }
    
    if (!authToken) {
        alert('Please login first');
        return;
    }
    
    addMessageToUI("You", message, "user-message");
    userInput.value = "";

    try {
        const response = await fetch('http://127.0.0.1:5000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ 
                message: message,
                conversation_id: currentConversationId
            })
        });
        
        const data = await response.json();

        if (response.ok) {
            if (data.response) {
                addMessageToUI("Bot", data.response, "bot-message");
                
                if (data.conversation_id) {
                    const wasNewConversation = !currentConversationId;
                    currentConversationId = data.conversation_id;
                    
                    if (wasNewConversation) {
                        setTimeout(() => {
                            loadConversations();
                        }, 100);
                    }
                }
            }
        } else {
            if (response.status === 401) {
                addMessageToUI("System", "Session expired. Please login again.", "error-message");
                setTimeout(() => {
                    document.getElementById('logout-button').click();
                }, 2000);
            } else {
                addMessageToUI("System", "Error: " + (data.detail || JSON.stringify(data)), "error-message");
            }
        }
    } catch (error) {
        console.error('Send message error:', error);
        addMessageToUI("System", "Server connection failed.", "error-message");
    }
}

// === DOM CONTENT LOADED ===
document.addEventListener("DOMContentLoaded", () => {
    // Check if user is already logged in
    authToken = localStorage.getItem('auth_token');
    currentUser = localStorage.getItem('username');
    
    if (authToken && currentUser) {
        showMainInterface();
    }

    // === LOGIN HANDLER ===
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        const errorElement = document.getElementById('login-error');
        
        errorElement.textContent = 'Logging in...';
        errorElement.style.color = '#3498db';
        
        try {
            const response = await fetch('http://127.0.0.1:5000/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                authToken = data.token;
                currentUser = data.username;
                
                localStorage.setItem('auth_token', authToken);
                localStorage.setItem('username', currentUser);
                localStorage.setItem('user_id', data.user_id);
                
                showMainInterface();
            } else {
                errorElement.style.color = '#e74c3c';
                errorElement.textContent = data.detail || 'Login failed';
            }
        } catch (error) {
            errorElement.style.color = '#e74c3c';
            errorElement.textContent = 'Connection error. Is the server running?';
            console.error('Login error:', error);
        }
    });

    // === REGISTER HANDLER ===
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        const errorElement = document.getElementById('register-error');
        
        errorElement.textContent = 'Creating account...';
        errorElement.style.color = '#3498db';
        
        try {
            const response = await fetch('http://127.0.0.1:5000/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                errorElement.style.color = '#27ae60';
                errorElement.textContent = 'Account created! Please login.';
                
                setTimeout(() => {
                    showLogin();
                    document.getElementById('login-username').value = username;
                }, 1500);
            } else {
                errorElement.style.color = '#e74c3c';
                errorElement.textContent = data.detail || 'Registration failed';
            }
        } catch (error) {
            errorElement.style.color = '#e74c3c';
            errorElement.textContent = 'Connection error. Is the server running?';
            console.error('Register error:', error);
        }
    });

    // === LOGOUT HANDLER ===
    document.getElementById('logout-button').addEventListener('click', () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('username');
        localStorage.removeItem('user_id');
        
        document.getElementById('chatwindow').innerHTML = '';
        
        authToken = null;
        currentUser = null;
        currentConversationId = null;
        
        document.getElementById('main-container').style.display = 'none';
        document.getElementById('auth-container').style.display = 'flex';
        
        document.getElementById('login-username').value = '';
        document.getElementById('login-password').value = '';
    });

    // === NEW CHAT BUTTON ===
    document.getElementById('new-chat-button').addEventListener('click', () => {
        currentConversationId = null;
        document.getElementById('chatwindow').innerHTML = '';
        
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.classList.remove('active');
        });
    });

    // === CHAT EVENT LISTENERS ===
   const sendButton = document.getElementById('sendbutton');
    const userInput = document.getElementById('userinput');

    sendButton.addEventListener('click', (e) => {
        e.preventDefault(); // Stops any accidental button-click refreshes
        sendMessage();
    });
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault(); // THE MAGIC FIX: Stops the browser from refreshing!
            sendMessage();
        }
    });
});

async function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const statusDiv = document.getElementById('uploadStatus');
    const file = fileInput.files[0];

    if (!file) return;

    // 1. UI Feedback
    statusDiv.innerText = "⏳ Reading & Learning...";
    statusDiv.style.color = "#FFD700"; // Gold

    const formData = new FormData();
    formData.append('file', file);

    try {
        // 2. Send to Backend (NOW WITH AUTHENTICATION!)
        const response = await fetch('http://127.0.0.1:5000/upload-doc', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}` // <-- Added the VIP Pass!
            },
            body: formData
        });

        const data = await response.json();
        
        // 3. Handle Result
        if (response.ok && data.status === "success") {
            statusDiv.innerText = "✅ Knowledge Added!";
            statusDiv.style.color = "#4caf50"; // Green
            fileInput.value = ""; // Reset input
            
            // Optional: clear message after 3 seconds
            setTimeout(() => { statusDiv.innerText = ""; }, 3000);
        } else {
            statusDiv.innerText = "❌ Error: " + (data.detail || data.message || "Upload failed");
            statusDiv.style.color = "#f44336"; // Red
        }
    } catch (error) {
        statusDiv.innerText = "❌ Server Error";
        statusDiv.style.color = "#f44336";
        console.error('Upload error:', error);
    }
}