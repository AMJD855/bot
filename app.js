// إعداد Firebase
const firebaseConfig = {
  apiKey: "AIzaSyASfXHC8_3eHMnWiK8XK23IGIi0ILxorx4",
  authDomain: "chat-314de.firebaseapp.com",
  databaseURL: "https://chat-314de-default-rtdb.firebaseio.com",
  projectId: "chat-314de",
  storageBucket: "chat-314de.appspot.com",
  messagingSenderId: "315729375055",
  appId: "1:315729375055:web:624d9197c9645d7af21f3a"
};

// تهيئة Firebase
firebase.initializeApp(firebaseConfig);
const db = firebase.database();
const auth = firebase.auth();

const messagesEl = document.getElementById('messages');
const msgInput = document.getElementById('msg');
const senderInput = document.getElementById('sender');
const sendBtn = document.getElementById('send');
const typingStatus = document.getElementById('typing-status');

let currentUser = null;

// 🔹 تسجيل الدخول بحساب Google
async function signInWithGoogle() {
  const provider = new firebase.auth.GoogleAuthProvider();
  try {
    const result = await auth.signInWithPopup(provider);
    currentUser = result.user;
    senderInput.value = currentUser.displayName;
    senderInput.disabled = true;
    loadMessages();
  } catch (error) {
    alert("حدث خطأ أثناء تسجيل الدخول!");
    console.error(error);
  }
}

// 🔹 مراقبة حالة تسجيل الدخول
auth.onAuthStateChanged(user => {
  if (user) {
    currentUser = user;
    senderInput.value = currentUser.displayName;
    senderInput.disabled = true;
    loadMessages();
  } else {
    signInWithGoogle();
  }
});

// 🔹 إرسال رسالة
sendBtn.addEventListener('click', async () => {
  const message = msgInput.value.trim();
  if (!message || !currentUser) return;

  sendBtn.style.transform = 'scale(0.9)';
  setTimeout(() => sendBtn.style.transform = '', 150);

  const newMsg = {
    sender: currentUser.displayName,
    message,
    time: Date.now()
  };

  await db.ref('messages').push(newMsg);
  msgInput.value = '';
});

// 🔹 تحميل الرسائل
function loadMessages() {
  db.ref('messages').on('value', snapshot => {
    messagesEl.innerHTML = '';
    const data = snapshot.val() || {};
    const messages = Object.values(data);

    messages.sort((a, b) => a.time - b.time);

    for (const m of messages) {
      const div = document.createElement('div');
      div.className = 'msg ' + (m.sender === currentUser.displayName ? 'me' : '');
      div.innerHTML = `
        <div class="meta">${escapeHtml(m.sender)} · ${new Date(m.time).toLocaleTimeString()}</div>
        <div class="body">${escapeHtml(m.message)}</div>
      `;
      messagesEl.appendChild(div);
    }
    messagesEl.scrollTop = messagesEl.scrollHeight;
  });
}

// 🔹 حالة الكتابة
msgInput.addEventListener('input', () => {
  if (!currentUser) return;
  typingStatus.textContent = `${currentUser.displayName} يكتب الآن...`;
  typingStatus.classList.add('typing');
  clearTimeout(msgInput._timeout);
  msgInput._timeout = setTimeout(() => {
    typingStatus.textContent = '';
    typingStatus.classList.remove('typing');
  }, 1500);
});

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}