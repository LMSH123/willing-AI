/**
 * 乐意AI - Web前端交互
 * 支持流式输出、文档上传、对话管理
 */

let currentSessionId = null;
let isStreaming = false;
let abortController = null;

// 页面加载完成
document.addEventListener('DOMContentLoaded', () => {
    loadModelInfo();
    loadConversations();
    loadKnowledgeStatus();
    loadToolInfo();

    // 文件上传
    setupFileUpload();
});

// ========================
// 对话管理
// ========================

async function newConversation() {
    try {
        const res = await fetch('/api/conversations/new', { method: 'POST' });
        const data = await res.json();
        currentSessionId = data.session_id;
        document.getElementById('messages').innerHTML = '';
        document.getElementById('welcomeMessage')?.style.removeProperty('display');
        document.getElementById('inputBox').value = '';
        document.getElementById('inputBox').focus();
        loadConversations();
    } catch (e) {
        console.error('创建新对话失败:', e);
    }
}

async function loadConversations() {
    try {
        const res = await fetch('/api/conversations');
        const data = await res.json();
        const list = document.getElementById('conversation-list');

        if (!data.conversations || data.conversations.length === 0) {
            list.innerHTML = '<div class="conversation-item" style="color:var(--text-muted);cursor:default;">暂无对话</div>';
            return;
        }

        list.innerHTML = data.conversations.map(s => `
            <div class="conversation-item" onclick="loadConversation('${s.session_id}')">
                <span>${escapeHtml(s.title)}</span>
                <button class="delete-btn" onclick="event.stopPropagation();deleteConversation('${s.session_id}')">✕</button>
            </div>
        `).join('');
    } catch (e) {
        console.error('加载对话列表失败:', e);
    }
}

async function loadConversation(sessionId) {
    try {
        const res = await fetch(`/api/conversations/${sessionId}`);
        if (!res.ok) return;
        const data = await res.json();

        currentSessionId = sessionId;
        const messagesDiv = document.getElementById('messages');
        messagesDiv.innerHTML = '';

        // 显示欢迎消息
        document.getElementById('welcomeMessage')?.style.setProperty('display', 'none');

        // 加载历史消息
        for (const msg of data.messages) {
            addMessage(msg.role, msg.content);
        }

        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    } catch (e) {
        console.error('加载对话失败:', e);
    }
}

async function deleteConversation(sessionId) {
    if (!confirm('确定删除此对话？')) return;
    try {
        await fetch(`/api/conversations/${sessionId}`, { method: 'DELETE' });
        if (currentSessionId === sessionId) {
            currentSessionId = null;
            document.getElementById('messages').innerHTML = '';
            document.getElementById('welcomeMessage')?.style.removeProperty('display');
        }
        loadConversations();
    } catch (e) {
        console.error('删除对话失败:', e);
    }
}

// ========================
// 发送消息
// ========================

async function sendMessage() {
    const inputBox = document.getElementById('inputBox');
    const text = inputBox.value.trim();
    if (!text || isStreaming) return;

    // 隐藏欢迎消息
    document.getElementById('welcomeMessage')?.style.setProperty('display', 'none');

    // 清空输入
    inputBox.value = '';
    autoResize(inputBox);

    // 显示用户消息
    addMessage('user', text);

    // 禁用发送按钮
    setStreaming(true);

    // 显示AI消息占位
    const assistantDiv = addMessage('assistant', '', true);
    const bubble = assistantDiv.querySelector('.bubble');

    // 准备消息
    const messages = [{ role: 'user', content: text }];
    if (currentSessionId) {
        currentSessionId = null; // 让后端创建新会话或使用已有会话
    }

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, session_id: currentSessionId }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullResponse = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data.type === 'session_id') {
                            currentSessionId = data.session_id;
                        } else if (data.type === 'chunk') {
                            fullResponse += data.content;
                            bubble.textContent = fullResponse;
                            scrollToBottom();
                        } else if (data.type === 'done') {
                            fullResponse = data.content;
                            bubble.textContent = fullResponse;
                            renderMarkdown(bubble, fullResponse);
                            scrollToBottom();
                        } else if (data.type === 'error') {
                            bubble.textContent = '出错了: ' + data.content;
                            bubble.style.color = 'var(--text-muted)';
                        }
                    } catch (e) {
                        // 忽略解析错误
                    }
                }
            }
        }
    } catch (e) {
        bubble.textContent = '网络错误，请检查连接后重试';
        bubble.style.color = 'var(--text-muted)';
    }

    setStreaming(false);
    loadConversations();
}

function setStreaming(streaming) {
    isStreaming = streaming;
    document.getElementById('sendBtn').disabled = streaming;
    const inputBox = document.getElementById('inputBox');
    inputBox.disabled = streaming;
    if (!streaming) inputBox.focus();
}

// ========================
// 消息渲染
// ========================

function addMessage(role, content, isLoading = false) {
    const messagesDiv = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    if (isLoading) {
        div.innerHTML = `
            <span class="role-label">乐意AI</span>
            <div class="bubble">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
    } else {
        const label = role === 'user' ? '你' : '乐意AI';
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.textContent = content;
        renderMarkdown(bubble, content);

        div.innerHTML = `<span class="role-label">${label}</span>`;
        div.appendChild(bubble);
    }

    messagesDiv.appendChild(div);
    scrollToBottom();
    return div;
}

function renderMarkdown(element, text) {
    // 简单渲染：代码块、粗体、列表
    let html = escapeHtml(text);

    // 代码块 (``` )
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

    // 行内代码 (`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 粗体
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 换行
    html = html.replace(/\n/g, '<br>');

    element.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========================
// 文件上传
// ========================

function setupFileUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            uploadFile(fileInput.files[0]);
            fileInput.value = '';
        }
    });
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const uploadArea = document.getElementById('uploadArea');
    const originalText = uploadArea.innerHTML;
    uploadArea.innerHTML = `⏳ 正在上传 ${file.name}...`;

    try {
        const res = await fetch('/api/documents/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            uploadArea.innerHTML = `✅ ${data.source} (${data.chunks} 块)`;
            loadKnowledgeStatus();
        } else {
            uploadArea.innerHTML = `❌ 上传失败: ${data.error || '未知错误'}`;
        }
    } catch (e) {
        uploadArea.innerHTML = `❌ 上传出错`;
    }

    setTimeout(() => {
        uploadArea.innerHTML = originalText;
    }, 3000);
}

// ========================
// 信息加载
// ========================

async function loadModelInfo() {
    try {
        const res = await fetch('/api/model');
        const data = await res.json();
        document.getElementById('modelInfo').textContent = `${data.backend}: ${data.model}`;
    } catch (e) {
        document.getElementById('modelInfo').textContent = '未连接';
    }
}

async function loadKnowledgeStatus() {
    try {
        const res = await fetch('/api/knowledge');
        const data = await res.json();
        if (data.enabled && data.total_chunks > 0) {
            document.getElementById('knowledge-status').textContent = `📚 ${data.total_chunks} 文档块 · ${data.sources.length} 来源`;
        } else {
            document.getElementById('knowledge-status').textContent = '📭 暂无文档';
        }
    } catch (e) {
        document.getElementById('knowledge-status').textContent = '加载失败';
    }
}

async function loadToolInfo() {
    try {
        const res = await fetch('/api/tools');
        const data = await res.json();
        if (data.tools.length > 0) {
            document.getElementById('toolBadge').textContent = `🔧 ${data.tools.map(t => t.name).join(', ')}`;
        }
    } catch (e) {
        // 忽略
    }
}

// ========================
// 工具函数
// ========================

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function scrollToBottom() {
    const messages = document.getElementById('messages');
    messages.scrollTop = messages.scrollHeight;
}