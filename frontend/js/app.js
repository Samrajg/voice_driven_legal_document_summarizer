const API_BASE = 'http://127.0.0.1:5000/api';
let token = localStorage.getItem('token');
let currentUser = JSON.parse(localStorage.getItem('user'));
let currentDocId = null;

// Translations Dictionary
const translations = {
    en: {
        app_title: "LegalDoc Verifier AI",
        app_title_large: "LegalDoc Verifier AI",
        nav_law_bot: "Law Bot",
        theme_dark: "🌙 Dark Mode",
        theme_light: "☀️ Light Mode",
        welcome: "Welcome, ",
        settings: "Settings",
        recent_docs: "Your Recent Documents",
        logout: "Logout",
        app_subtitle: "Extract, Analyze, and Simplify your Legal Documents",
        login: "Login",
        access_portal: "Access Portal",
        no_account: "No account?",
        register_here: "Register here",
        upload_new: "Upload New Document",
        record: "🎤 Record",
        recording_status: "🔴 Recording... (Click again to stop)",
        drag_drop: "Drag & Drop your legal document here, or ",
        click_browse: "click to browse",
        supported_formats: "Supported formats: PDF, JPG, PNG, TXT",
        process_doc: "🚀 Process Document",
        processing: "Processing...",
        req_summary: "📝 Your Requested Summary",
        loading_summary: "Loading summary...",
        law_bot_title: "⚖️ Law Bot (IPC Predictor)",
        law_bot_desc: "Describe a crime or situation to find relevant IPC sections.",
        find_ipc: "Find IPC Sections",
        suggested_laws: "Suggested IPC Sections:",
        // Placeholders
        p_username: "Username",
        p_password: "Password",
        p_type_command: "Type your command (e.g., Summarize easily in 50 words)",
        p_describe_incident: "Describe the incident here..."
    },
    ta: {
        app_title: "LegalDoc Verifier AI",
        app_title_large: "LegalDoc Verifier AI",
        nav_law_bot: "சட்ட ரோபோ (Law Bot)",
        theme_dark: "🌙 இருண்ட முறை",
        theme_light: "☀️ ஒளி முறை",
        welcome: "வரவேற்கிறோம், ",
        settings: "அமைப்புகள்",
        recent_docs: "உங்கள் ஆவணங்கள்",
        logout: "வெளியேறு",
        app_subtitle: "உங்கள் சட்ட ஆவணங்களை பிரித்தெடுக்கவும், பகுப்பாய்வு செய்யவும்",
        login: "உள்நுழைய",
        access_portal: "போர்ட்டலை அணுகவும்",
        no_account: "கணக்கு இல்லையா?",
        register_here: "இங்கே பதிவு செய்க",
        upload_new: "புதிய ஆவணத்தைப் பதிவேற்றவும்",
        record: "🎤 பதிவு செய்",
        recording_status: "🔴 பதிவு செய்யப்படுகிறது...",
        drag_drop: "ஆவணத்தை இங்கே இழுத்து விடவும், அல்லது ",
        click_browse: "உலாவ கிளிக் செய்யவும்",
        supported_formats: "ஆதரிக்கப்படும் வடிவங்கள்: PDF, JPG, PNG, TXT",
        process_doc: "🚀 ஆவணத்தை செயலாக்கு",
        processing: "செயலாக்கப்படுகிறது...",
        req_summary: "📝 சுருக்கம்",
        loading_summary: "சுருக்கம் ஏற்றப்படுகிறது...",
        law_bot_title: "⚖️ சட்ட ரோபோ (IPC கணிப்பான்)",
        law_bot_desc: "தொடர்புடைய IPC பிரிவுகளைக் கண்டறிய ஒரு சூழ்நிலையை விவரிக்கவும்.",
        find_ipc: "IPC பிரிவுகளைக் கண்டுபிடி",
        suggested_laws: "பரிந்துரைக்கப்பட்ட IPC பிரிவுகள்:",
        // Placeholders
        p_username: "பயனர்பெயர்",
        p_password: "கடவுச்சொல்",
        p_type_command: "உங்கள் கட்டளையை உள்ளிடவும்",
        p_describe_incident: "சம்பவத்தை இங்கே விவரிக்கவும்..."
    }
};

function applyTranslations(lang) {
    const dict = translations[lang] || translations['en'];
    
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) {
            if (key === 'welcome' && currentUser && currentUser.username) {
                el.innerHTML = `${dict[key]} <span id="user-greeting">${currentUser.username}</span>`;
            } else {
                el.innerText = dict[key];
            }
        }
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = 'p_' + el.getAttribute('data-i18n-placeholder');
        if (dict[key]) {
            el.placeholder = dict[key];
        }
    });
}

// Global Loader
const globalLoader = document.getElementById('global-loader');
const loaderText = document.getElementById('loader-text');
function showLoader(textKey = 'processing') {
    const lang = document.getElementById('language-selector').value;
    const dict = translations[lang] || translations['en'];
    loaderText.innerText = dict[textKey] || 'Processing...';
    globalLoader.classList.remove('hidden');
}
function hideLoader() {
    globalLoader.classList.add('hidden');
}

// DOM Elements
const authSection = document.getElementById('auth-section');
const dashboardSection = document.getElementById('dashboard-section');
const loginForm = document.getElementById('login-form');
const logoutBtn = document.getElementById('logout-btn');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const resultsPanel = document.getElementById('results-panel');

// Sidebar Elements
const hamburgerBtn = document.getElementById('hamburger-btn');
const closeSidebarBtn = document.getElementById('close-sidebar');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebar-overlay');

function toggleSidebar() {
    sidebar.classList.toggle('open');
    sidebarOverlay.classList.toggle('hidden');
}

hamburgerBtn.addEventListener('click', toggleSidebar);
closeSidebarBtn.addEventListener('click', toggleSidebar);
sidebarOverlay.addEventListener('click', toggleSidebar);

// Check Auth State
function checkAuth() {
    if (token && currentUser) {
        authSection.classList.add('hidden');
        dashboardSection.classList.remove('hidden');
        const greeting = document.getElementById('user-greeting');
        if(greeting) greeting.innerText = currentUser.username;
        loadHistory();
    } else {
        authSection.classList.remove('hidden');
        dashboardSection.classList.add('hidden');
        if(sidebar.classList.contains('open')) toggleSidebar();
    }
}

// Authentication
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    showLoader('processing');
    try {
        let res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password})
        });
        
        if (res.status === 401) {
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
            applyTranslations(document.getElementById('language-selector').value);
        } else {
            alert('Authentication failed.');
        }
    } catch(err) {
        alert('Server error. Is the Flask backend running?');
    } finally {
        hideLoader();
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
    document.getElementById('process-btn').style.display = 'block';
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
    
    const command = document.getElementById('command-input').value;
    formData.append('command', command);
    if (audioBlob) {
        formData.append('audio_cmd', audioBlob, 'command.wav');
    }
    
    showLoader('processing');
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
            fetchResults(currentDocId, document.getElementById('language-selector').value);
            loadHistory();
        } else {
            alert(data.message || 'Upload failed');
        }
    } catch (err) {
        alert('Upload failed. Check connection.');
    } finally {
        hideLoader();
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
                li.innerHTML = `<a href="#" onclick="fetchResults(${d.id}, document.getElementById('language-selector').value); toggleSidebar();" style="color: var(--secondary-color); text-decoration: none; font-weight: 600;">${d.filename}</a> - <small class="text-muted">${new Date(d.created_at).toLocaleDateString()}</small>`;
                list.appendChild(li);
            });
        }
    } catch(err) { }
}

// Law Bot Logic
const predictLawsBtn = document.getElementById('predict-laws-btn');
const crimeInput = document.getElementById('crime-input');
const lawBotResults = document.getElementById('law-bot-results');
const lawBotOutput = document.getElementById('law-bot-output');

predictLawsBtn.addEventListener('click', async () => {
    const crimeText = crimeInput.value;
    if (!crimeText.trim()) {
        alert('Please enter a description.');
        return;
    }
    
    showLoader('processing');
    predictLawsBtn.disabled = true;
    
    try {
        let res = await fetch(`${API_BASE}/documents/law-bot`, {
            method: 'POST',
            headers: { 
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ crime_text: crimeText })
        });
        
        const data = await res.json();
        
        lawBotResults.classList.remove('hidden');
        lawBotOutput.innerHTML = '';
        
        if (res.ok && data.results) {
            data.results.forEach(r => {
                lawBotOutput.innerHTML += `
                    <div style="margin-bottom: 15px; border-bottom: 1px dashed var(--glass-border); padding-bottom: 10px;">
                        <strong style="color: var(--primary-color);">IPC Section: ${r.section}</strong><br>
                        <span class="text-muted">${r.description}</span><br>
                        <small style="color: var(--success); font-weight: bold;">Confidence: ${r.confidence}</small>
                    </div>
                `;
            });
        } else {
            lawBotOutput.innerHTML = `<div class="text-danger" style="color: var(--danger);">${data.message || 'Prediction failed. Is the model loaded?'}</div>`;
        }
    } catch (err) {
        lawBotOutput.innerHTML = `<div class="text-danger" style="color: var(--danger);">Failed to reach Law Bot API. Check backend.</div>`;
    } finally {
        hideLoader();
        predictLawsBtn.disabled = false;
    }
});


// Localization Trigger
document.getElementById('language-selector').addEventListener('change', (e) => {
    const lang = e.target.value;
    applyTranslations(lang);
    if (currentDocId) {
        const loadingText = translations[lang] ? translations[lang]['loading_summary'] : "Translating...";
        document.getElementById('result-summary').innerText = loadingText;
        fetchResults(currentDocId, lang);
    }
});

// Theme Toggle Logic
const themeToggleBtn = document.getElementById('theme-toggle');
if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
        const lang = document.getElementById('language-selector').value;
        const dict = translations[lang] || translations['en'];
        
        if (document.body.classList.contains('dark-theme')) {
            themeToggleBtn.innerText = dict['theme_light'] || '☀️ Light Mode';
            localStorage.setItem('theme', 'dark');
        } else {
            themeToggleBtn.innerText = dict['theme_dark'] || '🌙 Dark Mode';
            localStorage.setItem('theme', 'light');
        }
    });

    // Load saved theme
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-theme');
    }
}

// Init
checkAuth();
applyTranslations(document.getElementById('language-selector').value);
if (localStorage.getItem('theme') === 'dark') {
    const lang = document.getElementById('language-selector').value;
    const dict = translations[lang] || translations['en'];
    if(themeToggleBtn) themeToggleBtn.innerText = dict['theme_light'] || '☀️ Light Mode';
}
