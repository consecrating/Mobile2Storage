"""
Mobile Upload Page HTML.

TWO MODES:
1. QUICK PICK (small selections) - Pick files/folder normally
2. DIRECT SEND (large folders like Download with 44K+ files) - 
   User types or selects a folder name, grants permission ONCE,
   and files stream out automatically without the file manager
   needing to load/display all contents.

Key fix for the "file manager not responding" problem:
- Added PRESET folder buttons (Download, DCIM, WhatsApp, etc.)
- When user taps a preset, it ONLY asks for permission (one tap)
- Files enumerate in background and upload automatically
- User never sees the full file list in the file manager
"""

MOBILE_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Mobile2Storage</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #1a1a2e 100%);
    color: #fff; min-height: 100vh; padding: 16px;
    display: flex; flex-direction: column; align-items: center;
}
.header { text-align: center; margin-bottom: 18px; }
.header h1 {
    font-size: 22px; margin-bottom: 4px;
    background: linear-gradient(90deg, #00d4ff, #00ff99);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.header p { color: #8b949e; font-size: 13px; }
.status-bar {
    width: 100%; max-width: 420px; background: #1c2128;
    border-radius: 10px; padding: 10px 14px; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
}
.status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #00ff99; animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
.status-text { font-size: 12px; color: #00ff99; }

/* MODE TABS */
.mode-tabs {
    width: 100%; max-width: 420px;
    display: flex; gap: 4px; margin-bottom: 16px;
    background: #1c2128; border-radius: 10px; padding: 4px;
}
.mode-tab {
    flex: 1; padding: 10px; text-align: center;
    border-radius: 8px; cursor: pointer;
    font-size: 13px; font-weight: 600;
    transition: all 0.2s; color: #8b949e;
}
.mode-tab.active {
    background: #00d4ff; color: #000;
}
.mode-tab:not(.active):active { background: #2a3040; }

/* SECTIONS */
.section { width: 100%; max-width: 420px; display: none; }
.section.visible { display: block; }

/* QUICK PICK MODE */
.pick-btn {
    display: flex; align-items: center; gap: 14px;
    background: #1c2128; border: 2px solid #30363d;
    border-radius: 14px; padding: 14px 18px;
    cursor: pointer; transition: all 0.2s ease;
    margin-bottom: 10px;
}
.pick-btn:active { border-color: #00d4ff; background: #0d2233; transform: scale(0.97); }
.pick-btn .icon { font-size: 26px; min-width: 34px; text-align: center; }
.pick-btn .label { font-size: 14px; font-weight: 600; }
.pick-btn .hint { font-size: 11px; color: #8b949e; margin-top: 2px; }

/* DIRECT SEND MODE */
.direct-title {
    font-size: 14px; font-weight: 600; color: #ccc; margin-bottom: 12px;
}
.direct-hint {
    font-size: 12px; color: #8b949e; margin-bottom: 14px;
    line-height: 1.5; background: #1c2128; border-radius: 8px;
    padding: 10px 14px;
}
.folder-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
    margin-bottom: 14px;
}
.folder-btn {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; gap: 4px;
    background: #1c2128; border: 2px solid #30363d;
    border-radius: 12px; padding: 14px 8px;
    cursor: pointer; transition: all 0.2s;
}
.folder-btn:active { border-color: #00d4ff; background: #0d2233; transform: scale(0.96); }
.folder-btn.selected { border-color: #00ff99; background: #0d2818; }
.folder-btn .f-icon { font-size: 24px; }
.folder-btn .f-name { font-size: 12px; font-weight: 600; }
.folder-btn .f-hint { font-size: 9px; color: #8b949e; }

.select-all-row {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 14px; padding: 10px 14px;
    background: #1c2128; border-radius: 10px;
}
.select-all-row label { font-size: 13px; flex: 1; cursor: pointer; }
.select-all-row input { width: 18px; height: 18px; cursor: pointer; }

.direct-send-btn {
    width: 100%; padding: 16px; border: none; border-radius: 12px;
    font-size: 16px; font-weight: 700; cursor: pointer;
    background: linear-gradient(135deg, #00aa44, #00cc55);
    color: #fff; transition: all 0.2s; display: none;
}
.direct-send-btn.visible { display: block; }
.direct-send-btn:active { transform: scale(0.97); }
.direct-send-btn:disabled { opacity: 0.5; }

/* NOTE about how it works */
.how-it-works {
    margin-top: 14px; padding: 12px;
    background: #0d1a26; border-radius: 10px;
    font-size: 11px; color: #8b949e; line-height: 1.6;
}
.how-it-works b { color: #00d4ff; }

/* HIDDEN INPUTS */
.hidden-input { display: none; }

/* PROCESSING */
.processing {
    width: 100%; max-width: 420px;
    background: #1c2128; border-radius: 12px;
    padding: 20px; text-align: center;
    margin-bottom: 16px; display: none;
}
.processing.visible { display: block; }
.processing .spinner {
    display: inline-block; width: 24px; height: 24px;
    border: 3px solid #30363d; border-top-color: #00d4ff;
    border-radius: 50%; animation: spin 0.8s linear infinite;
    margin-bottom: 8px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.processing .proc-text { font-size: 13px; color: #8b949e; }
.processing .proc-count { font-size: 16px; font-weight: 700; color: #00d4ff; margin-top: 4px; }

/* PROGRESS */
.overall-progress {
    width: 100%; max-width: 420px; margin-top: 12px; display: none;
}
.overall-progress.visible { display: block; }
.progress-header {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 5px;
}
.progress-pct { color: #00d4ff; font-weight: 700; font-size: 22px; }
.progress-speed { color: #8b949e; font-size: 12px; }
.overall-bar {
    width: 100%; height: 10px; background: #30363d;
    border-radius: 5px; overflow: hidden;
}
.overall-bar-fill {
    height: 100%; background: linear-gradient(90deg, #00d4ff, #00ff99);
    border-radius: 5px; transition: width 0.3s; width: 0%;
}
.progress-detail {
    display: flex; justify-content: space-between;
    margin-top: 6px; font-size: 11px; color: #8b949e;
}
.progress-eta {
    text-align: center; margin-top: 8px;
    font-size: 13px; color: #ffdd59; font-weight: 600;
}

/* FILE LIST (small mode only) */
.file-list {
    width: 100%; max-width: 420px; margin-bottom: 14px;
    max-height: 30vh; overflow-y: auto;
}
.file-item {
    background: #1c2128; border-radius: 8px;
    padding: 8px 12px; margin-bottom: 4px;
    display: flex; align-items: center; gap: 8px; font-size: 12px;
}
.file-item .fi-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.file-item .fi-size { color: #8b949e; font-size: 10px; }
.file-item .fi-status { font-weight: 600; min-width: 35px; text-align: right; }
.fi-status.done { color: #00ff99; }
.fi-status.sending { color: #00d4ff; }

/* SEND BTN for quick pick */
.send-btn {
    width: 100%; max-width: 420px;
    padding: 16px; border: none; border-radius: 12px;
    font-size: 16px; font-weight: 700; cursor: pointer;
    background: linear-gradient(135deg, #00aa44, #00cc55);
    color: #fff; display: none; transition: all 0.2s;
    margin-bottom: 10px;
}
.send-btn.visible { display: block; }
.send-btn:active { transform: scale(0.97); }
.send-btn:disabled { opacity: 0.5; }

/* COMPLETE */
.complete-msg { width: 100%; max-width: 420px; text-align: center; margin-top: 20px; display: none; }
.complete-msg.visible { display: block; }
.complete-msg h2 { color: #00ff99; font-size: 22px; margin-bottom: 8px; }
.complete-msg p { color: #8b949e; font-size: 13px; line-height: 1.6; }
</style>
</head>
<body>

<div class="header">
    <h1>⚡ Mobile2Storage</h1>
    <p>Send files to your PC — fast</p>
</div>

<div class="status-bar">
    <div class="status-dot"></div>
    <span class="status-text">Connected to PC ✓</span>
</div>

<!-- MODE TABS -->
<div class="mode-tabs">
    <div class="mode-tab active" id="tabQuick" onclick="switchMode('quick')">📄 Pick Files</div>
    <div class="mode-tab" id="tabDirect" onclick="switchMode('direct')">📁 Send Folders</div>
</div>

<!-- === QUICK PICK MODE === -->
<div class="section visible" id="sectionQuick">
    <div class="pick-btn" id="pickFiles">
        <span class="icon">📄</span>
        <div>
            <div class="label">Select Files</div>
            <div class="hint">Pick specific photos, videos, docs</div>
        </div>
    </div>
    <div class="pick-btn" id="pickSmallFolder">
        <span class="icon">📁</span>
        <div>
            <div class="label">Select a Small Folder</div>
            <div class="hint">For folders with less than ~500 files</div>
        </div>
    </div>
</div>

<!-- === DIRECT SEND MODE (for large folders) === -->
<div class="section" id="sectionDirect">
    <div class="direct-hint">
        <b>⚡ For large folders</b> (like Download with 44,000+ files):<br>
        Tap the folders you want to send. When the file picker opens, 
        just tap <b>"Use this folder"</b> or <b>"Allow"</b> — you don't need 
        to open or browse inside it.
    </div>
    
    <div class="direct-title">Select folders to send:</div>
    
    <div class="folder-grid" id="folderGrid">
        <div class="folder-btn" data-folder="Download" onclick="toggleFolder(this)">
            <span class="f-icon">📥</span>
            <span class="f-name">Download</span>
        </div>
        <div class="folder-btn" data-folder="DCIM" onclick="toggleFolder(this)">
            <span class="f-icon">📷</span>
            <span class="f-name">DCIM</span>
        </div>
        <div class="folder-btn" data-folder="Pictures" onclick="toggleFolder(this)">
            <span class="f-icon">🖼️</span>
            <span class="f-name">Pictures</span>
        </div>
        <div class="folder-btn" data-folder="Movies" onclick="toggleFolder(this)">
            <span class="f-icon">🎬</span>
            <span class="f-name">Movies</span>
        </div>
        <div class="folder-btn" data-folder="Music" onclick="toggleFolder(this)">
            <span class="f-icon">🎵</span>
            <span class="f-name">Music</span>
        </div>
        <div class="folder-btn" data-folder="Documents" onclick="toggleFolder(this)">
            <span class="f-icon">📄</span>
            <span class="f-name">Documents</span>
        </div>
        <div class="folder-btn" data-folder="WhatsApp" onclick="toggleFolder(this)">
            <span class="f-icon">💬</span>
            <span class="f-name">WhatsApp</span>
        </div>
        <div class="folder-btn" data-folder="Telegram" onclick="toggleFolder(this)">
            <span class="f-icon">✈️</span>
            <span class="f-name">Telegram</span>
        </div>
    </div>
    
    <button class="direct-send-btn" id="directSendBtn" onclick="startDirectSend()">
        🚀 Send Selected Folders
    </button>
    
    <div class="how-it-works">
        <b>How it works:</b> For each folder you select, the file picker will open 
        ONCE — just grant access (don't browse inside). Files will start 
        sending automatically in the background. Even 44,000+ files will 
        work without freezing because we process them in small batches.
    </div>
</div>

<!-- HIDDEN INPUTS -->
<input type="file" class="hidden-input" id="fileInput" multiple>
<input type="file" class="hidden-input" id="smallFolderInput" webkitdirectory directory multiple>
<input type="file" class="hidden-input" id="directFolderInput" webkitdirectory directory multiple>

<!-- PROCESSING -->
<div class="processing" id="processing">
    <div class="spinner"></div>
    <div class="proc-text" id="procText">Scanning files...</div>
    <div class="proc-count" id="procCount">0 files found</div>
</div>

<!-- FILE LIST (quick mode) -->
<div class="file-list" id="fileList"></div>
<button class="send-btn" id="sendBtn">🚀 Send to PC</button>

<!-- PROGRESS -->
<div class="overall-progress" id="overallProgress">
    <div class="progress-header">
        <span class="progress-pct" id="progressPct">0%</span>
        <span class="progress-speed" id="progressSpeed">Starting...</span>
    </div>
    <div class="overall-bar">
        <div class="overall-bar-fill" id="overallBarFill"></div>
    </div>
    <div class="progress-detail">
        <span id="progressFiles">0 / 0 files</span>
        <span id="progressTransferred">0 B / 0 B</span>
    </div>
    <div class="progress-eta" id="progressEta"></div>
</div>

<!-- COMPLETE -->
<div class="complete-msg" id="completeMsg">
    <h2>✅ All sent!</h2>
    <p id="completeSummary"></p>
</div>

<script>
// === STATE ===
let selectedFiles = [];
let totalBytes = 0;
let sentBytes = 0;
let sentFileCount = 0;
let startTime = 0;
let selectedFolders = [];
let currentFolderIdx = 0;

const PROCESS_BATCH = 500;
const UPLOAD_PARALLEL = 3;
const CHUNK_SIZE = 5 * 1024 * 1024;

// System patterns to skip
const SKIP = [/^\\./, /\\/\\./, /Android\\/data/i, /Android\\/obb/i, /LOST\\.DIR/i, 
    /\\.thumbnails/i, /\\.cache/i, /\\.nomedia$/i, /\\.tmp$/i, /thumbs\\.db$/i];

function isSystem(p) { for (const r of SKIP) if (r.test(p)) return true; return false; }

// === MODE SWITCHING ===
function switchMode(mode) {
    document.getElementById('tabQuick').classList.toggle('active', mode === 'quick');
    document.getElementById('tabDirect').classList.toggle('active', mode === 'direct');
    document.getElementById('sectionQuick').classList.toggle('visible', mode === 'quick');
    document.getElementById('sectionDirect').classList.toggle('visible', mode === 'direct');
}

// === FOLDER SELECTION (Direct Mode) ===
function toggleFolder(el) {
    el.classList.toggle('selected');
    updateDirectBtn();
}

function updateDirectBtn() {
    const selected = document.querySelectorAll('.folder-btn.selected');
    const btn = document.getElementById('directSendBtn');
    if (selected.length > 0) {
        btn.classList.add('visible');
        btn.textContent = '🚀 Send ' + selected.length + ' folder' + (selected.length > 1 ? 's' : '');
    } else {
        btn.classList.remove('visible');
    }
}

// === DIRECT SEND: Process folders one by one ===
async function startDirectSend() {
    const selected = document.querySelectorAll('.folder-btn.selected');
    selectedFolders = Array.from(selected).map(el => el.getAttribute('data-folder'));
    
    if (selectedFolders.length === 0) return;
    
    // Hide UI
    document.getElementById('sectionDirect').style.display = 'none';
    document.querySelector('.mode-tabs').style.display = 'none';
    
    // Process each folder: open picker once per folder
    selectedFiles = [];
    totalBytes = 0;
    
    const processing = document.getElementById('processing');
    const procText = document.getElementById('procText');
    const procCount = document.getElementById('procCount');
    
    for (let i = 0; i < selectedFolders.length; i++) {
        const folderName = selectedFolders[i];
        procText.textContent = 'Select "' + folderName + '" folder when picker opens...';
        procCount.textContent = 'Folder ' + (i+1) + ' of ' + selectedFolders.length;
        processing.classList.add('visible');
        
        // Open folder picker and wait for selection
        const files = await openFolderPicker();
        
        if (files && files.length > 0) {
            procText.textContent = 'Scanning ' + folderName + '...';
            
            // Process files in batches (non-blocking)
            await processBatch(files, true);
            
            procCount.textContent = selectedFiles.length.toLocaleString() + ' files (' + formatSize(totalBytes) + ') ready';
        }
    }
    
    processing.classList.remove('visible');
    
    if (selectedFiles.length > 0) {
        // Start upload immediately
        startUpload();
    }
}

function openFolderPicker() {
    return new Promise((resolve) => {
        const input = document.getElementById('directFolderInput');
        input.value = '';
        input.onchange = (e) => {
            resolve(e.target.files);
        };
        // If user cancels, resolve with null after timeout
        // (can't detect cancel directly)
        input.click();
        
        // Fallback: if no change after 60s, assume cancel
        setTimeout(() => resolve(null), 60000);
    });
}

// === QUICK PICK MODE ===
document.getElementById('pickFiles').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});
document.getElementById('pickSmallFolder').addEventListener('click', () => {
    document.getElementById('smallFolderInput').click();
});

document.getElementById('fileInput').addEventListener('change', (e) => {
    quickPickFiles(e.target.files, false);
});
document.getElementById('smallFolderInput').addEventListener('change', (e) => {
    quickPickFiles(e.target.files, true);
});

async function quickPickFiles(fileListObj, filterSystem) {
    const files = fileListObj;
    if (!files || files.length === 0) return;
    
    document.getElementById('sectionQuick').style.display = 'none';
    document.querySelector('.mode-tabs').style.display = 'none';
    
    const processing = document.getElementById('processing');
    processing.classList.add('visible');
    document.getElementById('procText').textContent = 'Scanning...';
    
    selectedFiles = [];
    totalBytes = 0;
    
    await processBatch(files, filterSystem);
    
    processing.classList.remove('visible');
    
    if (selectedFiles.length <= 200) {
        renderSmallFileList();
    }
    
    document.getElementById('sendBtn').classList.add('visible');
    document.getElementById('sendBtn').textContent = 
        '🚀 Send ' + selectedFiles.length.toLocaleString() + ' files (' + formatSize(totalBytes) + ')';
}

// === BATCH PROCESSING (prevents freeze) ===
function processBatch(rawFiles, filterSystem) {
    return new Promise((resolve) => {
        const total = rawFiles.length;
        let processed = 0;
        const procCount = document.getElementById('procCount');
        
        function batch() {
            const end = Math.min(processed + PROCESS_BATCH, total);
            for (let i = processed; i < end; i++) {
                const file = rawFiles[i];
                const path = file.webkitRelativePath || file.name;
                if (filterSystem && isSystem(path)) continue;
                if (file.size === 0) continue;
                selectedFiles.push(file);
                totalBytes += file.size;
            }
            processed = end;
            procCount.textContent = processed.toLocaleString() + ' / ' + total.toLocaleString() + ' scanned';
            
            if (processed < total) {
                setTimeout(batch, 0);
            } else {
                resolve();
            }
        }
        setTimeout(batch, 10);
    });
}

function renderSmallFileList() {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';
    selectedFiles.forEach((f, i) => {
        fileList.innerHTML +=
            '<div class="file-item" id="fi-'+i+'">' +
            '<span class="fi-name">' + f.name + '</span>' +
            '<span class="fi-size">' + formatSize(f.size) + '</span>' +
            '<span class="fi-status" id="fis-'+i+'"></span></div>';
    });
}

// === UPLOAD ENGINE ===
document.getElementById('sendBtn').addEventListener('click', startUpload);

async function startUpload() {
    document.getElementById('sendBtn').style.display = 'none';
    document.getElementById('fileList').innerHTML = '';
    
    const overallProgress = document.getElementById('overallProgress');
    overallProgress.classList.add('visible');
    
    startTime = Date.now();
    sentBytes = 0;
    sentFileCount = 0;
    const totalFiles = selectedFiles.length;
    
    document.getElementById('progressFiles').textContent = '0 / ' + totalFiles.toLocaleString();
    document.getElementById('progressTransferred').textContent = '0 B / ' + formatSize(totalBytes);
    
    // Parallel upload
    let idx = 0;
    let active = 0;
    
    await new Promise((resolve) => {
        function next() {
            while (active < UPLOAD_PARALLEL && idx < selectedFiles.length) {
                const file = selectedFiles[idx++];
                active++;
                uploadFile(file).finally(() => {
                    sentFileCount++;
                    active--;
                    document.getElementById('progressFiles').textContent = 
                        sentFileCount.toLocaleString() + ' / ' + totalFiles.toLocaleString();
                    if (sentFileCount >= totalFiles) resolve();
                    else next();
                });
            }
        }
        next();
    });
    
    // Done
    overallProgress.classList.remove('visible');
    const elapsed = (Date.now() - startTime) / 1000;
    document.getElementById('completeMsg').classList.add('visible');
    document.getElementById('completeSummary').innerHTML =
        '<b>' + totalFiles.toLocaleString() + ' files</b> (' + formatSize(totalBytes) + ')<br>' +
        'Time: ' + formatDuration(elapsed) + ' • Speed: ' + formatSize(totalBytes/Math.max(1,elapsed)) + '/s<br>' +
        'Folder structure preserved ✓';
}

async function uploadFile(file) {
    const name = encodeURIComponent(file.webkitRelativePath || file.name);
    try {
        if (file.size <= CHUNK_SIZE) {
            await fetch('/upload', {
                method: 'POST',
                headers: { 'X-Filename': name, 'Content-Type': 'application/octet-stream' },
                body: file
            }).then(r => { if(r.ok) sentBytes += file.size; updateProgress(); });
        } else {
            const chunks = Math.ceil(file.size / CHUNK_SIZE);
            for (let i = 0; i < chunks; i++) {
                const start = i * CHUNK_SIZE;
                const end = Math.min(start + CHUNK_SIZE, file.size);
                await fetch('/upload-chunk', {
                    method: 'POST',
                    headers: {
                        'X-Filename': name,
                        'X-Chunk-Index': i.toString(),
                        'X-Total-Chunks': chunks.toString(),
                        'X-Total-Size': file.size.toString(),
                        'Content-Type': 'application/octet-stream'
                    },
                    body: file.slice(start, end)
                });
                sentBytes += (end - start);
                updateProgress();
            }
        }
    } catch(e) {}
}

function updateProgress() {
    const pct = Math.min(100, Math.round((sentBytes / totalBytes) * 100));
    document.getElementById('progressPct').textContent = pct + '%';
    document.getElementById('overallBarFill').style.width = pct + '%';
    document.getElementById('progressTransferred').textContent = 
        formatSize(sentBytes) + ' / ' + formatSize(totalBytes);
    
    const elapsed = (Date.now() - startTime) / 1000;
    if (elapsed > 1) {
        const speed = sentBytes / elapsed;
        const remaining = (totalBytes - sentBytes) / Math.max(1, speed);
        document.getElementById('progressSpeed').textContent = formatSize(speed) + '/s';
        document.getElementById('progressEta').textContent = '⏱ ' + formatDuration(remaining) + ' remaining';
    }
}

// === UTILS ===
function formatSize(b) {
    if(b===0)return'0 B';
    const u=['B','KB','MB','GB','TB'];let i=0,s=b;
    while(s>=1024&&i<u.length-1){s/=1024;i++;}
    return s.toFixed(i===0?0:1)+' '+u[i];
}
function formatDuration(s) {
    if(s<60)return Math.round(s)+'s';
    if(s<3600)return Math.floor(s/60)+'m '+Math.round(s%60)+'s';
    return Math.floor(s/3600)+'h '+Math.floor((s%3600)/60)+'m';
}
</script>
</body>
</html>"""
