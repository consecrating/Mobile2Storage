"""
Mobile Upload Page HTML.
A beautiful, mobile-optimized file/folder picker and uploader.

3 Transfer Modes:
1. Pick Specific Files - Choose exactly which files to send
2. Pick Entire Folder - Select a folder, all contents transfer
3. Transfer Everything - All user files (skips system files), preserves full directory structure
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

/* === PICKER SECTION === */
.picker-section { width: 100%; max-width: 420px; margin-bottom: 16px; }
.picker-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; color: #ccc; }
.picker-grid { display: flex; flex-direction: column; gap: 10px; }

.pick-btn {
    display: flex; align-items: center; gap: 14px;
    background: #1c2128; border: 2px solid #30363d;
    border-radius: 14px; padding: 16px 18px;
    cursor: pointer; transition: all 0.2s ease;
}
.pick-btn:active {
    border-color: #00d4ff; background: #0d2233; transform: scale(0.97);
}
.pick-btn .icon { font-size: 30px; min-width: 36px; text-align: center; }
.pick-btn .text { flex: 1; }
.pick-btn .label { font-size: 14px; font-weight: 600; display: block; }
.pick-btn .hint { font-size: 11px; color: #8b949e; display: block; margin-top: 2px; }

/* Highlight the "Everything" button */
.pick-btn.everything {
    border-color: #00d4ff; background: linear-gradient(135deg, #0d1f2d, #0d2233);
}
.pick-btn.everything .label { color: #00d4ff; }

/* Hidden inputs */
.hidden-input { display: none; }

/* === FILE LIST === */
.file-list {
    width: 100%; max-width: 420px; margin-bottom: 14px;
    max-height: 38vh; overflow-y: auto;
}
.file-item {
    background: #1c2128; border-radius: 8px;
    padding: 10px 12px; margin-bottom: 5px;
    display: flex; align-items: center; gap: 8px;
}
.file-icon { font-size: 16px; }
.file-info { flex: 1; min-width: 0; }
.file-name {
    font-size: 11px; font-weight: 500;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.file-path {
    font-size: 9px; color: #586069;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.file-size { font-size: 10px; color: #8b949e; }
.file-progress {
    width: 100%; height: 3px; background: #30363d;
    border-radius: 2px; margin-top: 3px; overflow: hidden;
}
.file-progress-bar {
    height: 100%; background: linear-gradient(90deg, #00d4ff, #00ff99);
    border-radius: 2px; transition: width 0.3s; width: 0%;
}
.file-status {
    font-size: 11px; font-weight: 600; min-width: 40px; text-align: right;
}
.file-status.done { color: #00ff99; }
.file-status.sending { color: #00d4ff; }
.file-status.failed { color: #ff4466; }
.file-remove {
    font-size: 14px; color: #ff4466; cursor: pointer;
    padding: 3px 7px; border-radius: 6px;
}
.file-remove:active { background: #2a1520; }

/* === SUMMARY BAR === */
.summary-bar {
    width: 100%; max-width: 420px;
    background: #1c2128; border-radius: 10px;
    padding: 10px 14px; margin-bottom: 12px;
    display: none; font-size: 12px;
}
.summary-bar.visible { display: flex; justify-content: space-between; }
.summary-count { color: #00d4ff; font-weight: 600; }
.summary-size { color: #8b949e; }

/* === SEND BUTTON === */
.send-btn {
    width: 100%; max-width: 420px;
    padding: 16px; border: none; border-radius: 12px;
    font-size: 16px; font-weight: 700; cursor: pointer;
    background: linear-gradient(135deg, #00aa44, #00cc55);
    color: #fff; display: none; transition: all 0.2s;
}
.send-btn:active { transform: scale(0.97); }
.send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.send-btn.visible { display: block; }

/* === PROGRESS === */
.overall-progress {
    width: 100%; max-width: 420px; margin-top: 12px; display: none;
}
.overall-progress.visible { display: block; }
.progress-header {
    display: flex; justify-content: space-between;
    margin-bottom: 5px; font-size: 12px;
}
.progress-pct { color: #00d4ff; font-weight: 700; font-size: 15px; }
.progress-speed { color: #8b949e; }
.overall-bar {
    width: 100%; height: 8px; background: #30363d;
    border-radius: 4px; overflow: hidden;
}
.overall-bar-fill {
    height: 100%; background: linear-gradient(90deg, #00d4ff, #00ff99);
    border-radius: 4px; transition: width 0.3s; width: 0%;
}
.progress-detail {
    display: flex; justify-content: space-between;
    margin-top: 5px; font-size: 11px; color: #8b949e;
}

/* === COMPLETE === */
.complete-msg { text-align: center; margin-top: 20px; display: none; }
.complete-msg.visible { display: block; }
.complete-msg h2 { color: #00ff99; font-size: 20px; margin-bottom: 5px; }
.complete-msg p { color: #8b949e; font-size: 13px; line-height: 1.5; }

/* Add more */
.add-more {
    display: none; margin-top: 8px; margin-bottom: 8px;
    font-size: 12px; color: #00d4ff; cursor: pointer; text-decoration: underline;
}
.add-more.visible { display: block; }

/* Skipped files notice */
.skip-notice {
    width: 100%; max-width: 420px;
    background: #1a1a00; border-radius: 8px;
    padding: 8px 12px; margin-bottom: 10px;
    font-size: 11px; color: #ffdd59; display: none;
}
.skip-notice.visible { display: block; }
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

<!-- === PICKER === -->
<div class="picker-section" id="pickerSection">
    <div class="picker-title">Choose what to send:</div>
    <div class="picker-grid">
        <div class="pick-btn" id="pickFiles">
            <span class="icon">📄</span>
            <div class="text">
                <span class="label">Pick Specific Files</span>
                <span class="hint">Choose exactly which files to send</span>
            </div>
        </div>
        <div class="pick-btn" id="pickFolder">
            <span class="icon">📁</span>
            <div class="text">
                <span class="label">Pick a Folder</span>
                <span class="hint">Send everything inside a folder (keeps structure)</span>
            </div>
        </div>
        <div class="pick-btn everything" id="pickEverything">
            <span class="icon">🗂️</span>
            <div class="text">
                <span class="label">Transfer Everything</span>
                <span class="hint">All your files (photos, videos, docs, music) — skips system files. Keeps exact same folder names & structure.</span>
            </div>
        </div>
    </div>
</div>

<!-- Hidden inputs -->
<input type="file" class="hidden-input" id="fileInput" multiple>
<input type="file" class="hidden-input" id="folderInput" webkitdirectory directory multiple>
<input type="file" class="hidden-input" id="everythingInput" webkitdirectory directory multiple>

<div class="skip-notice" id="skipNotice"></div>
<div class="summary-bar" id="summaryBar">
    <span class="summary-count" id="summaryCount">0 files</span>
    <span class="summary-size" id="summarySize">0 B</span>
</div>

<div class="file-list" id="fileList"></div>
<span class="add-more" id="addMore">+ Add more files</span>
<button class="send-btn" id="sendBtn">🚀 Send to PC</button>

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
</div>

<div class="complete-msg" id="completeMsg">
    <h2>✅ All sent!</h2>
    <p id="completeSummary"></p>
</div>

<script>
// === ELEMENTS ===
const pickerSection = document.getElementById('pickerSection');
const pickFiles = document.getElementById('pickFiles');
const pickFolder = document.getElementById('pickFolder');
const pickEverything = document.getElementById('pickEverything');
const fileInput = document.getElementById('fileInput');
const folderInput = document.getElementById('folderInput');
const everythingInput = document.getElementById('everythingInput');
const fileList = document.getElementById('fileList');
const sendBtn = document.getElementById('sendBtn');
const addMore = document.getElementById('addMore');
const summaryBar = document.getElementById('summaryBar');
const summaryCount = document.getElementById('summaryCount');
const summarySize = document.getElementById('summarySize');
const skipNotice = document.getElementById('skipNotice');
const overallProgress = document.getElementById('overallProgress');
const progressPct = document.getElementById('progressPct');
const progressSpeed = document.getElementById('progressSpeed');
const overallBarFill = document.getElementById('overallBarFill');
const progressFiles = document.getElementById('progressFiles');
const progressTransferred = document.getElementById('progressTransferred');
const completeMsg = document.getElementById('completeMsg');
const completeSummary = document.getElementById('completeSummary');

let selectedFiles = [];
let totalBytes = 0;
let sentBytes = 0;
let sentFileCount = 0;
let startTime = 0;
let skippedCount = 0;

// System file/folder patterns to skip in "Transfer Everything" mode
const SYSTEM_PATTERNS = [
    /^\./, // hidden files/folders
    /^Android\/data/i,
    /^Android\/obb/i,
    /^Android\/runtime/i,
    /^LOST\.DIR/i,
    /\.thumbnails/i,
    /\.cache/i,
    /\.trash/i,
    /^data\//i,
    /^system\//i,
    /\.nomedia$/i,
    /\.tmp$/i,
    /thumbs\.db$/i,
    /desktop\.ini$/i,
];

function isSystemFile(relativePath) {
    const path = relativePath.replace(/\\\\/g, '/');
    for (const pattern of SYSTEM_PATTERNS) {
        if (pattern.test(path)) return true;
    }
    // Skip zero-byte files
    return false;
}

// === PICKER EVENTS ===
pickFiles.addEventListener('click', () => fileInput.click());
pickFolder.addEventListener('click', () => folderInput.click());
pickEverything.addEventListener('click', () => {
    // For "everything", we use folder picker pointed at root
    // On Android Chrome, this opens the storage picker
    everythingInput.click();
});
addMore.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => addFiles(e.target.files, false));
folderInput.addEventListener('change', (e) => addFiles(e.target.files, true));
everythingInput.addEventListener('change', (e) => addFiles(e.target.files, true, true));

function addFiles(fileListObj, preserveStructure, filterSystem) {
    const newFiles = Array.from(fileListObj);
    if (newFiles.length === 0) return;
    
    skippedCount = 0;
    
    for (const f of newFiles) {
        // Get relative path (preserves folder structure)
        const relativePath = f.webkitRelativePath || f.name;
        
        // In "everything" mode, skip system files
        if (filterSystem && isSystemFile(relativePath)) {
            skippedCount++;
            continue;
        }
        
        // Skip zero-byte files
        if (f.size === 0) {
            skippedCount++;
            continue;
        }
        
        // Avoid duplicates
        const exists = selectedFiles.some(
            sf => (sf.webkitRelativePath || sf.name) === relativePath && sf.size === f.size
        );
        if (!exists) selectedFiles.push(f);
    }
    
    if (skippedCount > 0) {
        skipNotice.textContent = '⚠️ Skipped ' + skippedCount + ' system/empty files (Android system, cache, thumbnails)';
        skipNotice.classList.add('visible');
    } else {
        skipNotice.classList.remove('visible');
    }
    
    renderFileList();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
}

function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0, size = bytes;
    while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
    return size.toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
}

function getFileIcon(name) {
    const ext = (name.split('.').pop() || '').toLowerCase();
    const map = {
        'jpg':'🖼️','jpeg':'🖼️','png':'🖼️','gif':'🖼️','heic':'🖼️','webp':'🖼️',
        'mp4':'🎬','avi':'🎬','mkv':'🎬','mov':'🎬','3gp':'🎬','webm':'🎬',
        'mp3':'🎵','wav':'🎵','flac':'🎵','aac':'🎵','m4a':'🎵','ogg':'🎵',
        'pdf':'📄','doc':'📄','docx':'📄','txt':'📄',
        'xls':'📊','xlsx':'📊','ppt':'📊','pptx':'📊',
        'zip':'📦','rar':'📦','7z':'📦','apk':'📱'
    };
    return map[ext] || '📎';
}

function renderFileList() {
    fileList.innerHTML = '';
    totalBytes = 0;

    selectedFiles.forEach((file, i) => {
        totalBytes += file.size;
        const relativePath = file.webkitRelativePath || file.name;
        const fileName = file.name;
        // Show folder path separately
        const folderPath = relativePath.includes('/') 
            ? relativePath.substring(0, relativePath.lastIndexOf('/'))
            : '';
        
        fileList.innerHTML += 
            '<div class="file-item" id="file-' + i + '">' +
                '<span class="file-icon">' + getFileIcon(fileName) + '</span>' +
                '<div class="file-info">' +
                    '<div class="file-name">' + fileName + '</div>' +
                    (folderPath ? '<div class="file-path">📁 ' + folderPath + '</div>' : '') +
                    '<div class="file-size">' + formatSize(file.size) + '</div>' +
                    '<div class="file-progress"><div class="file-progress-bar" id="bar-' + i + '"></div></div>' +
                '</div>' +
                '<span class="file-status" id="status-' + i + '">Ready</span>' +
                '<span class="file-remove" onclick="removeFile(' + i + ')">✕</span>' +
            '</div>';
    });

    // Update summary
    if (selectedFiles.length > 0) {
        sendBtn.classList.add('visible');
        sendBtn.textContent = '🚀 Send ' + selectedFiles.length + 
            ' file' + (selectedFiles.length > 1 ? 's' : '') + 
            ' (' + formatSize(totalBytes) + ')';
        addMore.classList.add('visible');
        summaryBar.classList.add('visible');
        summaryCount.textContent = selectedFiles.length + ' files selected';
        summarySize.textContent = formatSize(totalBytes);
        pickerSection.style.display = 'none';
    } else {
        sendBtn.classList.remove('visible');
        addMore.classList.remove('visible');
        summaryBar.classList.remove('visible');
        pickerSection.style.display = 'block';
    }
}

// === UPLOAD ===
sendBtn.addEventListener('click', startUpload);

async function startUpload() {
    sendBtn.disabled = true;
    sendBtn.textContent = 'Sending...';
    addMore.classList.remove('visible');
    overallProgress.classList.add('visible');
    startTime = Date.now();
    sentBytes = 0;
    sentFileCount = 0;

    document.querySelectorAll('.file-remove').forEach(el => el.style.display = 'none');

    for (let i = 0; i < selectedFiles.length; i++) {
        await uploadFile(selectedFiles[i], i);
        sentFileCount++;
        progressFiles.textContent = sentFileCount + ' / ' + selectedFiles.length + ' files';
    }

    // Done!
    completeMsg.classList.add('visible');
    overallProgress.classList.remove('visible');
    sendBtn.style.display = 'none';
    summaryBar.classList.remove('visible');
    const elapsed = (Date.now() - startTime) / 1000;
    const avgSpeed = totalBytes / Math.max(1, elapsed);
    completeSummary.textContent = 
        selectedFiles.length + ' files (' + formatSize(totalBytes) + ')\\n' +
        'Time: ' + (elapsed > 60 ? Math.round(elapsed/60) + 'm ' + Math.round(elapsed%60) + 's' : Math.round(elapsed) + 's') +
        ' • Avg speed: ' + formatSize(avgSpeed) + '/s\\n' +
        'Folder structure preserved on PC ✓';
}

async function uploadFile(file, index) {
    const statusEl = document.getElementById('status-' + index);
    const barEl = document.getElementById('bar-' + index);
    if (!statusEl || !barEl) return;
    
    statusEl.textContent = '0%';
    statusEl.className = 'file-status sending';

    // Use relative path to preserve folder structure on PC
    const uploadName = file.webkitRelativePath || file.name;
    const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB for speed

    if (file.size <= CHUNK_SIZE) {
        await uploadSingle(file, uploadName, index, statusEl, barEl);
    } else {
        await uploadChunked(file, uploadName, index, statusEl, barEl);
    }
}

async function uploadSingle(file, uploadName, index, statusEl, barEl) {
    try {
        const xhr = new XMLHttpRequest();
        const promise = new Promise((resolve, reject) => {
            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    barEl.style.width = pct + '%';
                    statusEl.textContent = pct + '%';
                    updateOverall(sentBytes + e.loaded);
                }
            };
            xhr.onload = () => {
                if (xhr.status === 200) {
                    sentBytes += file.size;
                    barEl.style.width = '100%';
                    statusEl.textContent = '✓';
                    statusEl.className = 'file-status done';
                    resolve();
                } else reject(new Error('Failed'));
            };
            xhr.onerror = () => reject(new Error('Network'));
        });
        xhr.open('POST', '/upload');
        xhr.setRequestHeader('X-Filename', encodeURIComponent(uploadName));
        xhr.setRequestHeader('Content-Type', 'application/octet-stream');
        xhr.send(file);
        await promise;
    } catch (e) {
        statusEl.textContent = '✗';
        statusEl.className = 'file-status failed';
    }
}

async function uploadChunked(file, uploadName, index, statusEl, barEl) {
    const CHUNK_SIZE = 5 * 1024 * 1024;
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    let uploaded = 0;

    try {
        for (let i = 0; i < totalChunks; i++) {
            const start = i * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const chunk = file.slice(start, end);

            const resp = await fetch('/upload-chunk', {
                method: 'POST',
                headers: {
                    'X-Filename': encodeURIComponent(uploadName),
                    'X-Chunk-Index': i.toString(),
                    'X-Total-Chunks': totalChunks.toString(),
                    'X-Total-Size': file.size.toString(),
                    'Content-Type': 'application/octet-stream'
                },
                body: chunk
            });
            if (!resp.ok) throw new Error('Chunk failed');

            uploaded += (end - start);
            const pct = Math.round((uploaded / file.size) * 100);
            barEl.style.width = pct + '%';
            statusEl.textContent = pct + '%';
            updateOverall(sentBytes + uploaded);
        }
        sentBytes += file.size;
        statusEl.textContent = '✓';
        statusEl.className = 'file-status done';
    } catch (e) {
        statusEl.textContent = '✗';
        statusEl.className = 'file-status failed';
    }
}

function updateOverall(currentTotal) {
    const pct = Math.round((currentTotal / totalBytes) * 100);
    progressPct.textContent = pct + '%';
    overallBarFill.style.width = pct + '%';
    progressTransferred.textContent = formatSize(currentTotal) + ' / ' + formatSize(totalBytes);

    const elapsed = (Date.now() - startTime) / 1000;
    if (elapsed > 0.5) {
        const speed = currentTotal / elapsed;
        const remaining = (totalBytes - currentTotal) / Math.max(1, speed);
        progressSpeed.textContent = formatSize(speed) + '/s • ' +
            (remaining > 60 ? Math.round(remaining/60) + 'm left' : Math.round(remaining) + 's left');
    }
}
</script>
</body>
</html>"""
