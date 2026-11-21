let socket;
let partnerId;
let currentUserId;
let typingTimer;

function initChat(partnerIdParam, currentUserIdParam) {
  partnerId = partnerIdParam;
  currentUserId = currentUserIdParam;

  socket = io();

  socket.on('connect', () => {
  socket.emit('join_chat', { partner_id: partnerId });
  });

  socket.on('new_message', (msg) => {
    appendMessage(msg);
    scrollToBottom();
  });

  socket.on('partner_typing', (data) => {
    const indicator = document.getElementById('typing-indicator');
    if (data.is_typing) {
      indicator.style.display = 'block';
    } else {
      indicator.style.display = 'none';
    }
  });

  socket.on('user_status_changed', (data) => {
    if (data.user_id === partnerId) {
      const statusEl = document.querySelector('.chat-header div div:last-child');
      if (statusEl) {
        statusEl.textContent = data.is_online ? '● Online' : 'Offline';
        statusEl.style.color = data.is_online ? 'var(--green)' : 'var(--text-muted)';
      }
    }
  });

  socket.on('error', (data) => {
    console.error('Socket error:', data.message);
  });

  scrollToBottom();
}

function sendMessage() {
  const input = document.getElementById('chat-input');
  const content = input.value.trim();
  if (!content) return;

  socket.emit('send_message', {
  receiver_id: partnerId,
  content: content
  });

  input.value = '';
  input.style.height = 'auto';

  socket.emit('typing', { partner_id: partnerId, is_typing: false });
}

function handleKey(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function handleTyping() {
  const input = document.getElementById('chat-input');
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 120) + 'px';

  socket.emit('typing', { partner_id: partnerId, is_typing: true });

  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => {
  socket.emit('typing', { partner_id: partnerId, is_typing: false });
  }, 2000);
}

function appendMessage(msg) {
  const container = document.getElementById('chat-messages');

  // Remove the empty state placeholder if present
  const emptyState = container.querySelector('.empty-state');
  if (emptyState) emptyState.remove();

  const isOwn = msg.sender_id === currentUserId;
  const time = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const div = document.createElement('div');
  div.className = `chat-message ${isOwn ? 'chat-message--own' : ''}`;
  div.id = `msg-${msg.id}`;
  div.innerHTML = `
    ${!isOwn ? `<img src="${msg.sender_avatar || '/static/images/default_avatar.svg'}"
         alt="avatar"
         style="width:28px;height:28px;border-radius:50%;object-fit:cover;flex-shrink:0;"
         onerror="this.onerror=null;this.src='/static/images/default_avatar.svg'">` : ''}
    <div>
      <div class="chat-bubble">${escapeHtml(msg.content)}</div>
      <div class="chat-bubble__time">${time}</div>
    </div>
  `;
  container.appendChild(div);
}

function scrollToBottom() {
  const container = document.getElementById('chat-messages');
  if (container) {
  container.scrollTop = container.scrollHeight;
  }
}

