const API_BASE = 'http://127.0.0.1:5000/api';
let token = localStorage.getItem('token');
let currentUser = JSON.parse(localStorage.getItem('user'));
let currentDocId = null;

// DOM Elements
const authSection = document.getElementById('auth-section');
const dashboardSection = document.getElementById('dashboard-section');
const loginForm = document.getElementById('login-form');
const logoutBtn = document.getElementById('logout-btn');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadStatus = document.getElementById('upload-status');
const resultsPanel = document.getElementById('results-panel');

// Check Auth State
function checkAuth() {
    if (token) {
        authSection.classList.add('hidden');
        dashboardSection.classList.remove('hidden');
        document.getElementById('user-greeting').innerText = currentUser.username;
        loadHistory();
    } else {
        authSection.classList.remove('hidden');
        dashboardSection.classList.add('hidden');
    }
}

// Authentication
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    // Auto-decide login vs register for MVP simplicity
    try {
        let res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        
        if (res.status === 401) {
            // Try to register if login fails (MVP auto-register)
            res = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username, email: username+'@test.com', password})
            });
            if(res.ok) {
                 res = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
            }
        }
        
        if (res.ok) {
            const data = await res.json();
            token = data.access_token;
            currentUser = data.user;
            localStorage.setItem('token', token);
            localStorage.setItem('user', JSON.stringify(currentUser));
            checkAuth();
        } else {
            alert('Authentication failed.');
        }
    } catch(err) {
        alert('Server error. Is the Flask backend running?');
    }
});

logoutBtn.addEventListener('click', () => {
    token = null;
    currentUser = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    checkAuth();
});

// File Upload & Voice state
let selectedFile = null;
let audioBlob = null;
let mediaRecorder = null;
let audioChunks = [];

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

function attachFile(file) {
    selectedFile = file;
    document.getElementById('selected-file-name').innerText = file.name;
    document.getElementById('process-btn').style.display = 'inline-block';
}

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        attachFile(e.dataTransfer.files[0]);
    }
});
fileInput.addEventListener('change', () => {
    if (fileInput.files.length) attachFile(fileInput.files[0]);
});

// Voice Recording Logic
const recordBtn = document.getElementById('record-btn');
const recordingStatus = document.getElementById('recording-status');

recordBtn.addEventListener('click', async () => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.start();
            audioChunks = [];
            
            recordingStatus.classList.remove('hidden');
            recordBtn.innerText = '⏹️ Stop';
            
            mediaRecorder.ondataavailable = e => {
                audioChunks.push(e.data);
            };
            
            mediaRecorder.onstop = () => {
                audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                recordingStatus.classList.add('hidden');
                recordBtn.innerText = '🎤 Voice Saved';
                document.getElementById('command-input').placeholder = "Voice command captured. Ready to process.";
            };
        } catch (err) {
            alert('Microphone access denied or unavailable.');
        }
    } else if (mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
});

document.getElementById('process-btn').addEventListener('click', () => {
    if (!selectedFile) {
        alert("Please select a document first.");
        return;
    }
    handleUpload();
});

async function handleUpload() {
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    // Add command and/or voice directly to payload
    const command = document.getElementById('command-input').value;
    formData.append('command', command);
    if (audioBlob) {
        formData.append('audio_cmd', audioBlob, 'command.wav');
    }
    
    uploadStatus.classList.remove('hidden');
    resultsPanel.classList.add('hidden');
    
    try {
        let res = await fetch(`${API_BASE}/documents/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        
        const data = await res.json();
        
        if (res.ok) {
            currentDocId = data.document_id;
            fetchResults(currentDocId);
            loadHistory();
            // Reset chat history
            document.getElementById('chat-history').innerHTML = '<div style="color: var(--text-muted); text-align: center; margin-top: 20px;">Ask anything about the document you just uploaded!</div>';
        } else {
            alert(data.message || 'Upload failed');
        }
    } catch (err) {
        alert('Upload failed. Check connection.');
    } finally {
        uploadStatus.classList.add('hidden');
    }
}

async function fetchResults(docId, lang='en') {
    try {
        let res = await fetch(`${API_BASE}/documents/${docId}?lang=${lang}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (res.ok) renderResults(data.analysis);
    } catch(err) {
        console.error(err);
    }
}

function renderResults(analysis) {
    if (!analysis) return;
    resultsPanel.classList.remove('hidden');
    
    // Summary
    document.getElementById('result-summary').innerText = analysis.summary || "No summary available.";
}

// History
async function loadHistory() {
    try {
        let res = await fetch(`${API_BASE}/documents/history`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        const list = document.getElementById('history-list');
        list.innerHTML = '';
        if (data.length) {
            data.forEach(d => {
                const li = document.createElement('li');
                li.style.padding = '10px 0';
                li.style.borderBottom = '1px solid var(--glass-border)';
                li.innerHTML = `<a href="#" onclick="fetchResults(${d.id})" style="color: var(--secondary-color); text-decoration: none;">${d.filename}</a> - <small class="text-muted">${new Date(d.created_at).toLocaleDateString()}</small>`;
                list.appendChild(li);
            });
        }
    } catch(err) { }
}

// Tabs Logic
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
        
        e.target.classList.add('active');
        document.getElementById(`tab-${e.target.dataset.tab}`).classList.remove('hidden');
    });
});

// QA Logic
const qaBtn = document.getElementById('qa-send-btn');
const qaInput = document.getElementById('qa-input');
const chatHistory = document.getElementById('chat-history');

async function sendQA() {
    const question = qaInput.value;
    if (!question || !currentDocId) return;
    
    qaInput.value = '';
    
    // Append User message
    const uMsg = document.createElement('div');
    uMsg.style.textAlign = 'right';
    uMsg.innerHTML = `<span style="background: var(--primary-color); display: inline-block; padding: 8px 12px; border-radius: 12px; margin-bottom: 8px;">${question}</span>`;
    chatHistory.appendChild(uMsg);
    
    try {
        let res = await fetch(`${API_BASE}/documents/${currentDocId}/qa`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({question})
        });
        const data = await res.json();
        
        // Append Bot message
        const bMsg = document.createElement('div');
        bMsg.style.textAlign = 'left';
        bMsg.innerHTML = `<span style="background: rgba(255,255,255,0.1); display: inline-block; padding: 8px 12px; border-radius: 12px; margin-bottom: 8px; border: 1px solid var(--secondary-color);">${data.answer || data.message}</span>`;
        chatHistory.appendChild(bMsg);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        
    } catch(err) {
        console.error(err);
    }
}

qaBtn.addEventListener('click', sendQA);
qaInput.addEventListener('keypress', (e) => {
    if(e.key === 'Enter') sendQA();
});

// Localization Trigger
document.getElementById('language-selector').addEventListener('change', (e) => {
    if (currentDocId) {
        document.getElementById('result-summary').innerText = "Translating...";
        fetchResults(currentDocId, e.target.value);
    }
});

// Init
checkAuth();
