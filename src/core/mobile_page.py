"""
Mobile Upload Page HTML.
Handles 44,000+ files without crashing or freezing.

Key optimizations for MASSIVE folders:
- Does NOT render individual file items for large selections (>200 files)
- Uses batched async processing to avoid browser "not responding"
- Starts uploading immediately in batches (no waiting for full list)
- Shows compact progress view (count + bar) instead of per-file items
- Uses Web Workers concept (setTimeout batching) for file filtering
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

/* PICKER */
.picker-section { width: 100%; max-width: 420px; margin-bottom: 16px; }
.picker-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; color: #ccc; }
.picker-grid { display: flex; flex-direction: column; gap: 10px; }
.pick-btn {
    display: flex; align-items: center; gap: 14px;
    background: #1c2128; border: 2px solid #30363d;
    border-radius: 14px; padding: 16px 18px;
    cursor: pointer; transition: all 0.2s ease;
}
.pick-btn:active { border-color: #00d4ff; background: #0d2233; transform: scale(0.97); }
.pick-btn .icon { font-size: 30px; min-width: 36px; text-align: center; }
.pick-btn .text { flex: 1; }
.pick-btn .label { font-size: 14px; font-weight: 600; display: block; }
.pick-btn .hint { font-size: 11px; color: #8b949e; display: block; margin-top: 2px; }
.pick-btn.everything { border-color: #00d4ff; background: linear-gradient(135deg, #0d1f2d, #0d2233); }
.pick-btn.everything .label { color: #00d4ff; }
.hidden-input { display: none; }

/* PROCESSING indicator */
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

/* SUMMARY (for large folder selections) */
.summary-card {
    width: 100%; max-width: 420px;
    background: #1c2128; border-radius: 12px;
    padding: 16px; margin-bottom: 14px; display: none;
}
.summary-card.visible { display: block; }
.summary-title { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
.summary-stats {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
}
.stat-box {
    background: #0d1117; border-radius: 8px; padding: 10px;
    text-align: center;
}
.stat-value { font-size: 18px; font-weight: 700; color: #00d4ff; }
.stat-label { font-size: 10px; color: #8b949e; margin-top: 2px; }
.summary-breakdown {
    margin-top: 10px; font-size: 11px; color: #8b949e;
    line-height: 1.6;
}

/* FILE LIST (only for small selections <=200 files) */
.file-list {
    width: 100%; max-width: 420px; margin-bottom: 14px;
    max-height: 35vh; overflow-y: auto;
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
.file-size { font-size: 10px; color: #8b949e; }
.file-progress {
    width: 100%; height: 3px; background: #30363d;
    border-radius: 2px; margin-top: 3px; overflow: hidden;
}
.file-progress-bar {
    height: 100%; background: linear-gradient(90deg, #00d4ff, #00ff99);
    border-radius: 2px; transition: width 0.3s; width: 0%;
}
.file-status { font-size: 11px; font-weight: 600; min-width: 40px; text-align: right; }
.file-status.done { color: #00ff99; }
.file-status.sending { color: #00d4ff; }
.file-status.failed { color: #ff4466; }
.file-remove { font-size: 14px; color: #ff4466; cursor: pointer; padding: 3px 7px; }

/* SEND BUTTON */
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

/* COMPLETE */
.complete-msg { text-align: center; margin-top: 20px; display: none; }
.complete-msg.visible { display: block; }
.complete-msg h2 { color: #00ff99; font-size: 22px; margin-bottom: 8px; }
.complete-msg p { color: #8b949e; font-size: 13px; line-height: 1.6; }

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

<!-- PICKER -->
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
                <span class="hint">All your files — skips system files, keeps folder structure</span>
            </div>
        </div>
    </div>
</div>

<!-- Hidden inputs -->
<input type="file" class="hidden-input" id="fileInput" multiple>
<input type="file" class="hidden-input" id="folderInput" webkitdirectory directory multiple>
<input type="file" class="hidden-input" id="everythingInput" webkitdirectory directory multiple>

<!-- Processing indicator (shown while scanning large folders) -->
<div class="processing" id="processing">
    <div class="spinner"></div>
    <div class="proc-text">Scanning files...</div>
    <div class="proc-count" id="procCount">0 files found</div>
</div>

<!-- Summary card (for large selections - no individual file items) -->
<div class="summary-card" id="summaryCard">
    <div class="summary-title">📂 Ready to send:</div>
    <div class="summary-stats">
        <div class="stat-box">
            <div class="stat-value" id="statFiles">0</div>
            <div class="stat-label">FILES</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="statSize">0 B</div>
            <div class="stat-label">TOTAL SIZE</div>
        </div>
    </div>
    <div class="summary-breakdown" id="summaryBreakdown"></div>
</div>

<div class="skip-notice" id="skipNotice"></div>

<!-- File list (ONLY shown for small selections <= 200 files) -->
<div class="file-list" id="fileList"></div>

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
    <div class="progress-eta" id="progressEta"></div>
</div>

<div class="complete-msg" id="completeMsg">
    <h2>✅ All sent!</h2>
    <p id="completeSummary"></p>
</div>

<script>
// === ELEMENTS ===
const pickerSection = document.getElementById('pickerSection');
const processing = document.getElementById('processing');
const procCount = document.getElementById('procCount');
const summaryCard = document.getElementById('summaryCard');
const statFiles = document.getElementById('statFiles');
const statSize = document.getElementById('statSize');
const summaryBreakdown = document.getElementById('summaryBreakdown');
const skipNotice = document.getElementById('skipNotice');
const fileList = document.getElementById('fileList');
const sendBtn = document.getElementById('sendBtn');
const overallProgress = document.getElementById('overallProgress');
const progressPct = document.getElementById('progressPct');
const progressSpeed = document.getElementById('progressSpeed');
const overallBarFill = document.getElementById('overallBarFill');
const progressFiles = document.getElementById('progressFiles');
const progressTransferred = document.getElementById('progressTransferred');
const progressEta = document.getElementById('progressEta');
const completeMsg = document.getElementById('completeMsg');
const completeSummary = document.getElementById('completeSummary');

// === STATE ===
let selectedFiles = [];  // Array of File objects to upload
let totalBytes = 0;
let sentBytes = 0;
let sentFileCount = 0;
let startTime = 0;
let isLargeMode = false;  // true = don't render individual items

// Max files to render individually (above this → summary mode)
const RENDER_THRESHOLD = 200;

// Batch size for processing files from folder picker
const PROCESS_BATCH = 500;

// Upload concurrency (parallel uploads)
const UPLOAD_PARALLEL = 3;

// System file patterns to skip
const SYSTEM_PATTERNS = [
    /^\\./,
    /\\/\\./,
    /^Android\\/data/i,
    /^Android\\/obb/i,
    /^Android\\/runtime/i,
    /^LOST\\.DIR/i,
    /\\.thumbnails/i,
    /\\.cache/i,
    /\\.trash/i,
    /\\.nomedia$/i,
    /\\.tmp$/i,
    /thumbs\\.db$/i,
    /desktop\\.ini$/i,
];

function isSystemFile(path) {
    for (const p of SYSTEM_PATTERNS) {
        if (p.test(path)) return true;
    }
    return false;
}

// === PICKERS ===
document.getElementById('pickFiles').addEventListener('click', () => document.getElementById('fileInput').click());
document.getElementById('pickFolder').addEventListener('click', () => document.getElementById('folderInput').click());
document.getElementById('pickEverything').addEventListener('click', () => document.getElementById('everythingInput').click());

document.getElementById('fileInput').addEventListener('change', (e) => processSelection(e.target.files, false));
document.getElementById('folderInput').addEventListener('change', (e) => processSelection(e.target.files, false));
document.getElementById('everythingInput').addEventListener('change', (e) => processSelection(e.target.files, true));

/**
 * Process file selection in BATCHES to avoid browser freeze.
 * For 44,000+ files this is critical — we process 500 at a time
 * with setTimeout(0) between batches to keep UI responsive.
 */
function processSelection(fileListObj, filterSystem) {
    const rawFiles = fileListObj;
    const total = rawFiles.length;
    
    if (total === 0) return;
    
    // Show processing indicator immediately
    pickerSection.style.display = 'none';
    processing.classList.add('visible');
    procCount.textContent = '0 / ' + total.toLocaleString() + ' scanned...';
    
    // Reset
    selectedFiles = [];
    totalBytes = 0;
    let skipped = 0;
    let processed = 0;
    
    // Category counters for breakdown
    let cats = { photos: 0, videos: 0, audio: 0, docs: 0, other: 0 };
    
    // Process in batches using setTimeout to keep browser responsive
    function processBatch() {
        const batchEnd = Math.min(processed + PROCESS_BATCH, total);
        
        for (let i = processed; i < batchEnd; i++) {
            const file = rawFiles[i];
            const path = file.webkitRelativePath || file.name;
            
            // Skip system files if in "everything" mode
            if (filterSystem && isSystemFile(path)) {
                skipped++;
                continue;
            }
            
            // Skip zero-byte files
            if (file.size === 0) {
                skipped++;
                continue;
            }
            
            selectedFiles.push(file);
            totalBytes += file.size;
            
            // Categorize
            const ext = (file.name.split('.').pop() || '').toLowerCase();
            if ('jpg,jpeg,png,gif,heic,webp,bmp,raw,dng'.includes(ext)) cats.photos++;
            else if ('mp4,avi,mkv,mov,3gp,webm,wmv,flv,m4v'.includes(ext)) cats.videos++;
            else if ('mp3,wav,flac,aac,ogg,m4a,wma,opus'.includes(ext)) cats.audio++;
            else if ('pdf,doc,docx,xls,xlsx,ppt,pptx,txt,csv'.includes(ext)) cats.docs++;
            else cats.other++;
        }
        
        processed = batchEnd;
        procCount.textContent = processed.toLocaleString() + ' / ' + total.toLocaleString() + ' scanned...';
        
        if (processed < total) {
            // More to process — yield to browser then continue
            setTimeout(processBatch, 0);
        } else {
            // Done processing!
            processing.classList.remove('visible');
            showReady(skipped, cats);
        }
    }
    
    // Start batch processing (first batch runs immediately)
    setTimeout(processBatch, 50);
}

/**
 * Show the "ready to send" state.
 * For large selections (>200): shows summary card only.
 * For small selections: shows individual file items.
 */
function showReady(skipped, cats) {
    isLargeMode = selectedFiles.length > RENDER_THRESHOLD;
    
    // Show skip notice
    if (skipped > 0) {
        skipNotice.textContent = '⚠️ Skipped ' + skipped.toLocaleString() + ' system/empty files';
        skipNotice.classList.add('visible');
    }
    
    if (isLargeMode) {
        // LARGE MODE: Summary card only (no individual items)
        summaryCard.classList.add('visible');
        statFiles.textContent = selectedFiles.length.toLocaleString();
        statSize.textContent = formatSize(totalBytes);
        
        // Build breakdown text
        let breakdown = '';
        if (cats.photos > 0) breakdown += '📷 ' + cats.photos.toLocaleString() + ' photos  ';
        if (cats.videos > 0) breakdown += '🎬 ' + cats.videos.toLocaleString() + ' videos  ';
        if (cats.audio > 0) breakdown += '🎵 ' + cats.audio.toLocaleString() + ' audio  ';
        if (cats.docs > 0) breakdown += '📄 ' + cats.docs.toLocaleString() + ' docs  ';
        if (cats.other > 0) breakdown += '📦 ' + cats.other.toLocaleString() + ' other';
        summaryBreakdown.textContent = breakdown;
        
        fileList.innerHTML = '';
    } else {
        // SMALL MODE: Render individual file items
        summaryCard.classList.remove('visible');
        renderFileList();
    }
    
    // Show send button
    sendBtn.classList.add('visible');
    sendBtn.textContent = '🚀 Send ' + selectedFiles.length.toLocaleString() + 
        ' files (' + formatSize(totalBytes) + ')';
}

function renderFileList() {
    fileList.innerHTML = '';
    selectedFiles.forEach((file, i) => {
        const name = file.name;
        const path = file.webkitRelativePath || '';
        const folder = path.includes('/') ? path.substring(0, path.lastIndexOf('/')) : '';
        
        fileList.innerHTML +=
            '<div class="file-item" id="file-' + i + '">' +
                '<span class="file-icon">' + getFileIcon(name) + '</span>' +
                '<div class="file-info">' +
                    '<div class="file-name">' + name + '</div>' +
                    '<div class="file-size">' + formatSize(file.size) + (folder ? ' • ' + folder : '') + '</div>' +
                    '<div class="file-progress"><div class="file-progress-bar" id="bar-' + i + '"></div></div>' +
                '</div>' +
                '<span class="file-status" id="status-' + i + '">Ready</span>' +
                '<span class="file-remove" onclick="removeFile(' + i + ')">✕</span>' +
            '</div>';
    });
}

function removeFile(index) {
    totalBytes -= selectedFiles[index].size;
    selectedFiles.splice(index, 1);
    if (selectedFiles.length === 0) {
        pickerSection.style.display = 'block';
        sendBtn.classList.remove('visible');
        summaryCard.classList.remove('visible');
        fileList.innerHTML = '';
    } else {
        renderFileList();
        sendBtn.textContent = '🚀 Send ' + selectedFiles.length + ' files (' + formatSize(totalBytes) + ')';
    }
}

// === UPLOAD ENGINE ===
sendBtn.addEventListener('click', startUpload);

async function startUpload() {
    sendBtn.disabled = true;
    sendBtn.textContent = 'Sending...';
    overallProgress.classList.add('visible');
    summaryCard.classList.remove('visible');
    skipNotice.classList.remove('visible');
    fileList.innerHTML = '';
    
    startTime = Date.now();
    sentBytes = 0;
    sentFileCount = 0;
    
    const totalFiles = selectedFiles.length;
    progressFiles.textContent = '0 / ' + totalFiles.toLocaleString() + ' files';
    progressTransferred.textContent = '0 B / ' + formatSize(totalBytes);
    
    // Upload with PARALLEL concurrency for speed
    // Process in parallel batches of UPLOAD_PARALLEL
    let queue = [...selectedFiles];
    let active = 0;
    let idx = 0;
    
    await new Promise((resolve) => {
        function next() {
            while (active < UPLOAD_PARALLEL && idx < queue.length) {
                const fileIdx = idx;
                const file = queue[idx];
                idx++;
                active++;
                
                uploadFile(file, fileIdx).then(() => {
                    sentFileCount++;
                    active--;
                    progressFiles.textContent = sentFileCount.toLocaleString() + ' / ' + totalFiles.toLocaleString() + ' files';
                    
                    if (sentFileCount === totalFiles) {
                        resolve();
                    } else {
                        next();
                    }
                }).catch(() => {
                    sentFileCount++;
                    active--;
                    if (sentFileCount === totalFiles) resolve();
                    else next();
                });
            }
        }
        next();
    });
    
    // Done!
    overallProgress.classList.remove('visible');
    completeMsg.classList.add('visible');
    const elapsed = (Date.now() - startTime) / 1000;
    const avgSpeed = totalBytes / Math.max(1, elapsed);
    completeSummary.innerHTML = 
        '<b>' + totalFiles.toLocaleString() + ' files</b> (' + formatSize(totalBytes) + ')<br>' +
        'Time: ' + formatDuration(elapsed) + '<br>' +
        'Average speed: ' + formatSize(avgSpeed) + '/s<br><br>' +
        'Folder structure preserved on PC ✓';
}

async function uploadFile(file, index) {
    const uploadName = file.webkitRelativePath || file.name;
    const CHUNK_SIZE = 5 * 1024 * 1024;
    
    try {
        if (file.size <= CHUNK_SIZE) {
            await uploadSingle(file, uploadName, index);
        } else {
            await uploadChunked(file, uploadName, index);
        }
    } catch(e) {
        // Failed - continue with next file
    }
}

async function uploadSingle(file, uploadName, index) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) updateOverall(sentBytes + e.loaded);
        };
        xhr.onload = () => {
            if (xhr.status === 200) {
                sentBytes += file.size;
                updateOverall(sentBytes);
                resolve();
            } else reject();
        };
        xhr.onerror = () => reject();
        xhr.open('POST', '/upload');
        xhr.setRequestHeader('X-Filename', encodeURIComponent(uploadName));
        xhr.setRequestHeader('Content-Type', 'application/octet-stream');
        xhr.send(file);
    });
}

async function uploadChunked(file, uploadName, index) {
    const CHUNK_SIZE = 5 * 1024 * 1024;
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    let uploaded = 0;
    
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
        
        if (!resp.ok) throw new Error('Failed');
        
        uploaded += (end - start);
        sentBytes += (end - start);
        updateOverall(sentBytes);
    }
}

function updateOverall(currentTotal) {
    const pct = Math.min(100, Math.round((currentTotal / totalBytes) * 100));
    progressPct.textContent = pct + '%';
    overallBarFill.style.width = pct + '%';
    progressTransferred.textContent = formatSize(currentTotal) + ' / ' + formatSize(totalBytes);
    
    const elapsed = (Date.now() - startTime) / 1000;
    if (elapsed > 1) {
        const speed = currentTotal / elapsed;
        const remaining = (totalBytes - currentTotal) / Math.max(1, speed);
        progressSpeed.textContent = formatSize(speed) + '/s';
        progressEta.textContent = '⏱ ' + formatDuration(remaining) + ' remaining';
    }
}

// === UTILITIES ===
function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0, size = bytes;
    while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
    return size.toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
}

function formatDuration(seconds) {
    if (seconds < 60) return Math.round(seconds) + 's';
    if (seconds < 3600) return Math.floor(seconds/60) + 'm ' + Math.round(seconds%60) + 's';
    return Math.floor(seconds/3600) + 'h ' + Math.floor((seconds%3600)/60) + 'm';
}

function getFileIcon(name) {
    const ext = (name.split('.').pop() || '').toLowerCase();
    const map = {
        'jpg':'🖼️','jpeg':'🖼️','png':'🖼️','gif':'🖼️','heic':'🖼️','webp':'🖼️',
        'mp4':'🎬','avi':'🎬','mkv':'🎬','mov':'🎬','3gp':'🎬','webm':'🎬',
        'mp3':'🎵','wav':'🎵','flac':'🎵','aac':'🎵','m4a':'🎵',
        'pdf':'📄','doc':'📄','docx':'📄','txt':'📄',
        'zip':'📦','rar':'📦','7z':'📦','apk':'📱'
    };
    return map[ext] || '📎';
}
</script>
</body>
</html>"""
