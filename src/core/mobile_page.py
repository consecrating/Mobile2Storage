"""
Mobile Page - Acts as a FILE SERVER on the phone.

The phone page does almost nothing visible — it just:
1. Shows "Connected to PC ✓"
2. Grants access to storage (one-time folder picker)
3. Serves file listings and file data to the PC over HTTP

The PC does ALL the browsing, selecting, and transferring.
The phone never has to display or process 44K+ files.
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
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    color: #fff; min-height: 100vh;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 20px;
}
.card {
    background: #161b22; border-radius: 20px;
    padding: 30px; text-align: center;
    width: 100%; max-width: 380px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.4);
}
h1 {
    font-size: 22px; margin-bottom: 6px;
    background: linear-gradient(90deg, #00d4ff, #00ff99);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.subtitle { color: #8b949e; font-size: 13px; margin-bottom: 24px; }
.status {
    display: flex; align-items: center; justify-content: center;
    gap: 8px; margin-bottom: 20px;
}
.dot {
    width: 10px; height: 10px; border-radius: 50%;
    animation: pulse 2s infinite;
}
.dot.green { background: #00ff99; }
.dot.orange { background: #ffaa44; }
.dot.blue { background: #00d4ff; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
.status-text { font-size: 14px; font-weight: 600; }

.grant-btn {
    width: 100%; padding: 16px; border: none; border-radius: 12px;
    font-size: 15px; font-weight: 700; cursor: pointer;
    background: linear-gradient(135deg, #00aa44, #00cc55);
    color: #fff; margin-bottom: 12px; transition: transform 0.2s;
}
.grant-btn:active { transform: scale(0.97); }
.grant-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.info {
    font-size: 12px; color: #8b949e; line-height: 1.6;
    margin-top: 16px; padding: 12px;
    background: #0d1117; border-radius: 10px;
}
.info b { color: #00d4ff; }

.transfer-status {
    margin-top: 20px; padding: 14px;
    background: #0d2233; border-radius: 10px;
    display: none;
}
.transfer-status.visible { display: block; }
.ts-text { font-size: 13px; color: #00d4ff; font-weight: 600; }
.ts-count { font-size: 11px; color: #8b949e; margin-top: 4px; }

.keep-open {
    margin-top: 16px; font-size: 11px; color: #ffdd59;
    padding: 8px; background: #1a1a00; border-radius: 8px;
}

input[type="file"] { display: none; }
</style>
</head>
<body>

<div class="card">
    <h1>⚡ Mobile2Storage</h1>
    <p class="subtitle">Your PC is connected</p>
    
    <div class="status" id="statusArea">
        <span class="dot orange" id="statusDot"></span>
        <span class="status-text" id="statusText">Grant storage access to start</span>
    </div>
    
    <button class="grant-btn" id="grantBtn" onclick="grantAccess()">
        📂 Grant Storage Access
    </button>
    
    <div class="info">
        <b>How it works:</b><br>
        1. Tap the button above → select your main storage folder<br>
        2. Your PC will show all your phone files<br>
        3. Select what you want from the PC<br>
        4. Files transfer automatically<br><br>
        <b>You never need to browse your files here.</b><br>
        Everything is done from the PC.
    </div>
    
    <div class="transfer-status" id="transferStatus">
        <div class="ts-text" id="tsText">Sending files to PC...</div>
        <div class="ts-count" id="tsCount">0 files sent</div>
    </div>
    
    <div class="keep-open">
        ⚠️ Keep this page open while transferring
    </div>
</div>

<input type="file" id="folderInput" webkitdirectory directory multiple>

<script>
let rootHandle = null;  // Directory handle for File System Access API
let fileMap = new Map(); // path -> File object
let granted = false;
let filesSent = 0;

const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const grantBtn = document.getElementById('grantBtn');
const transferStatus = document.getElementById('transferStatus');
const tsText = document.getElementById('tsText');
const tsCount = document.getElementById('tsCount');

// === GRANT ACCESS ===
async function grantAccess() {
    // Try modern File System Access API first (Chrome 86+)
    if ('showDirectoryPicker' in window) {
        try {
            rootHandle = await window.showDirectoryPicker({ mode: 'read' });
            onAccessGranted();
            return;
        } catch(e) {
            // User cancelled or API not available
            if (e.name === 'AbortError') return;
        }
    }
    
    // Fallback: use webkitdirectory input
    document.getElementById('folderInput').click();
}

// Fallback handler
document.getElementById('folderInput').addEventListener('change', async (e) => {
    const files = e.target.files;
    if (files.length === 0) return;
    
    // Index files by their relative path
    statusText.textContent = 'Indexing files...';
    statusDot.className = 'dot blue';
    
    // Process in batches to avoid freeze
    let processed = 0;
    const total = files.length;
    
    function batch() {
        const end = Math.min(processed + 1000, total);
        for (let i = processed; i < end; i++) {
            const f = files[i];
            const path = f.webkitRelativePath || f.name;
            fileMap.set(path, f);
        }
        processed = end;
        statusText.textContent = 'Indexing... ' + processed.toLocaleString() + '/' + total.toLocaleString();
        
        if (processed < total) {
            setTimeout(batch, 0);
        } else {
            onAccessGranted();
        }
    }
    setTimeout(batch, 10);
});

function onAccessGranted() {
    granted = true;
    statusDot.className = 'dot green';
    statusText.textContent = 'Connected ✓ — Browse files from your PC';
    grantBtn.disabled = true;
    grantBtn.textContent = '✓ Access Granted';
    
    // Notify PC that we're ready
    notifyPC();
}

// === SERVE FILE LISTINGS TO PC ===
// The PC polls this page for file listings via fetch requests
// We respond with directory contents

// Register service: PC will call /api/list?path=xxx and /api/file?path=xxx
// Since we can't run a real server from a webpage, we use a polling mechanism:
// PC sends requests → this page intercepts and responds via a shared state

// Method: Use BroadcastChannel or simple polling endpoint
// Actually: The PC already runs the HTTP server. We'll POST our file list TO the PC.

async function notifyPC() {
    // Send initial signal that we're ready
    try {
        await fetch('/phone-ready', { method: 'POST', body: JSON.stringify({ ready: true }) });
    } catch(e) {}
    
    // Start listening for commands from PC
    pollCommands();
}

async function pollCommands() {
    while (granted) {
        try {
            const resp = await fetch('/phone-command');
            if (resp.ok) {
                const cmd = await resp.json();
                await handleCommand(cmd);
            }
        } catch(e) {}
        
        // Poll every 500ms
        await new Promise(r => setTimeout(r, 500));
    }
}

async function handleCommand(cmd) {
    if (cmd.action === 'list') {
        // List directory contents
        const listing = await listDirectory(cmd.path || '');
        await fetch('/phone-response', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: cmd.id, data: listing })
        });
    } else if (cmd.action === 'send') {
        // Send a specific file to PC
        const file = await getFile(cmd.path);
        if (file) {
            transferStatus.classList.add('visible');
            tsText.textContent = 'Sending: ' + cmd.path.split('/').pop();
            
            await uploadFileToPc(file, cmd.path);
            
            filesSent++;
            tsCount.textContent = filesSent + ' files sent';
        }
        // Acknowledge
        await fetch('/phone-response', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: cmd.id, data: { success: true } })
        });
    }
}

async function listDirectory(path) {
    // If using File System Access API
    if (rootHandle) {
        return await listFromHandle(rootHandle, path);
    }
    
    // If using fallback (fileMap from webkitdirectory)
    return listFromFileMap(path);
}

async function listFromHandle(dirHandle, path) {
    try {
        // Navigate to the target directory
        let current = dirHandle;
        if (path) {
            const parts = path.split('/').filter(p => p);
            for (const part of parts) {
                current = await current.getDirectoryHandle(part);
            }
        }
        
        const entries = [];
        for await (const [name, handle] of current.entries()) {
            if (name.startsWith('.')) continue; // skip hidden
            
            if (handle.kind === 'directory') {
                entries.push({ name, type: 'dir', size: 0 });
            } else {
                try {
                    const file = await handle.getFile();
                    entries.push({ name, type: 'file', size: file.size });
                } catch(e) {
                    entries.push({ name, type: 'file', size: 0 });
                }
            }
        }
        
        // Sort: folders first, then files
        entries.sort((a, b) => {
            if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
            return a.name.localeCompare(b.name);
        });
        
        return { entries, path };
    } catch(e) {
        return { entries: [], path, error: e.message };
    }
}

function listFromFileMap(path) {
    // Build directory listing from the flat file map
    const prefix = path ? path + '/' : '';
    const dirs = new Set();
    const files = [];
    
    for (const [filePath, file] of fileMap) {
        if (!filePath.startsWith(prefix) && prefix) continue;
        
        const relative = prefix ? filePath.slice(prefix.length) : filePath;
        const slashIdx = relative.indexOf('/');
        
        if (slashIdx > 0) {
            // It's in a subdirectory
            dirs.add(relative.substring(0, slashIdx));
        } else if (slashIdx === -1 && relative) {
            // It's a file in current directory
            files.push({ name: relative, type: 'file', size: file.size });
        }
    }
    
    const entries = [
        ...Array.from(dirs).sort().map(d => ({ name: d, type: 'dir', size: 0 })),
        ...files.sort((a,b) => a.name.localeCompare(b.name))
    ];
    
    return { entries, path };
}

async function getFile(path) {
    // File System Access API
    if (rootHandle) {
        try {
            const parts = path.split('/').filter(p => p);
            let current = rootHandle;
            for (let i = 0; i < parts.length - 1; i++) {
                current = await current.getDirectoryHandle(parts[i]);
            }
            const fileHandle = await current.getFileHandle(parts[parts.length - 1]);
            return await fileHandle.getFile();
        } catch(e) {
            return null;
        }
    }
    
    // Fallback
    return fileMap.get(path) || null;
}

async function uploadFileToPc(file, path) {
    const CHUNK = 5 * 1024 * 1024;
    const name = encodeURIComponent(path);
    
    if (file.size <= CHUNK) {
        await fetch('/upload', {
            method: 'POST',
            headers: { 'X-Filename': name, 'Content-Type': 'application/octet-stream' },
            body: file
        });
    } else {
        const chunks = Math.ceil(file.size / CHUNK);
        for (let i = 0; i < chunks; i++) {
            const start = i * CHUNK;
            const end = Math.min(start + CHUNK, file.size);
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
        }
    }
}
</script>
</body>
</html>"""
