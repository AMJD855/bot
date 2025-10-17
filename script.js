document.addEventListener('DOMContentLoaded', () => {
    // --- تهيئة Firebase ---
    const firebaseConfig = {
        apiKey: "AIzaSyDls7qCYoGj5L37w1nkSkAaaAFe-O1HR_s", // استخدم مفتاحك الحقيقي
        authDomain: "chat-amjd.firebaseapp.com",
        projectId: "chat-amjd",
        storageBucket: "chat-amjd.appspot.com",
        messagingSenderId: "317055926652",
        appId: "1:317055926652:web:a00dbe19443dd201d3e4f9",
        measurementId: "G-3BHG4GGRBW",
        databaseURL: "https://chat-amjd-default-rtdb.firebaseio.com/", // مهم لقواعد بيانات Realtime القديمة
    };

    // تهيئة Firebase
    const app = firebase.initializeApp(firebaseConfig);
    const analytics = firebase.analytics(app); // اختياري للتحليلات
    const database = firebase.database(); // الحصول على مرجع قاعدة البيانات

    // --- عناصر DOM ---
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatContainer = document.getElementById('chat-container');
    const usernameInput = document.getElementById('username-input');
    const joinButton = document.getElementById('join-button');
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const messagesContainer = document.getElementById('messages');
    const chatList = document.getElementById('chats'); // قائمة المحادثات
    const currentUsernameDisplay = document.getElementById('current-username');
    const logoutButton = document.getElementById('logout-button');
    const chatTitle = document.getElementById('chat-title');

    // عناصر الصوت (اختياري)
    const sendSound = document.getElementById('send-sound');
    const receiveSound = document.getElementById('receive-sound');

    // --- متغيرات الحالة ---
    let currentUser = null;
    let currentChatId = 'general'; // المحادثة الافتراضية
    let messagesRef = null; // مرجع رسائل المحادثة الحالية

    // --- الدوال المساعدة ---

    // دالة تنسيق التاريخ والوقت
    function formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const days = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
        const months = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];

        const dayName = days[date.getDay()];
        const dayOfMonth = date.getDate();
        const monthName = months[date.getMonth()];
        const year = date.getFullYear();
        let hours = date.getHours();
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'مساءً' : 'صباحًا';
        hours = hours % 12;
        hours = hours ? hours : 12; // الساعة 0 تصبح 12

        // مثال: "الاثنين - 3:25 مساءً - 10 أبريل 2025"
        // تعديل بسيط للصيغة المطلوبة:
        // return `${dayName} - ${hours}:${minutes} ${ampm} - ${dayOfMonth} ${monthName} ${year}`;
        // الصيغة الأقرب للمثال في الوصف:
        return `${dayName} - ${hours}:${minutes} ${ampm} - ${dayOfMonth} ${monthName} ${year}`; // بناءً على التنسيق المطلوب
    }

    // دالة عرض الرسالة في الواجهة
    function displayMessage(msgData, msgId) {
        if (!msgData || !msgData.text || !msgData.username || !msgData.timestamp) {
            console.warn("رسالة غير مكتملة أو تالفة:", msgId, msgData);
            return; // تجاهل الرسائل غير الصالحة
        }

        const messageElement = document.createElement('div');
        messageElement.classList.add('message');
        messageElement.dataset.id = msgId; // يمكن استخدامه لاحقًا للحذف/التعديل

        // تحديد إذا كانت الرسالة مرسلة أم مستلمة
        const isSent = msgData.username === currentUser;
        messageElement.classList.add(isSent ? 'sent' : 'received');

        // إضافة اسم المرسل (إذا لم تكن مرسلة من المستخدم الحالي)
        if (!isSent) {
            const senderElement = document.createElement('span');
            senderElement.classList.add('sender');
            senderElement.textContent = msgData.username;
            messageElement.appendChild(senderElement);
        }

        // إضافة نص الرسالة
        const textElement = document.createElement('p');
        textElement.classList.add('text');
        // تحويل النص العادي إلى HTML آمن (لمنع XSS بسيط)
        textElement.textContent = msgData.text; // استخدام textContent أكثر أمانًا
        messageElement.appendChild(textElement);

        // إضافة الوقت والتاريخ
        const timestampElement = document.createElement('span');
        timestampElement.classList.add('timestamp');
        timestampElement.textContent = formatTimestamp(msgData.timestamp);
        messageElement.appendChild(timestampElement);

        // إضافة الرسالة إلى الحاوية
        messagesContainer.appendChild(messageElement);

        // التمرير للأسفل تلقائيًا لرؤية الرسالة الجديدة
        scrollToBottom();

        // تشغيل صوت الاستلام (إذا لم تكن مرسلة من المستخدم الحالي)
        if (!isSent && receiveSound) {
            receiveSound.play().catch(e => console.log("لم يتم تشغيل صوت الاستلام:", e));
        }
    }

    // دالة التمرير لأسفل حاوية الرسائل
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // دالة تحميل وتحديث الرسائل لمحادثة معينة
    function loadMessages(chatId) {
        // إزالة المستمع القديم إذا كان موجودًا
        if (messagesRef) {
            messagesRef.off();
        }

        // مسح الرسائل القديمة من الواجهة
        messagesContainer.innerHTML = '';

        // الحصول على مرجع الرسائل للمحادثة الجديدة
        // نفترض بنية بسيطة: /chats/{chatId}/messages
        messagesRef = database.ref(`chats/${chatId}/messages`);

        // الاستماع لإضافة رسائل جديدة (limitToLast لتحميل آخر N رسائل فقط لتجنب تحميل كل شيء)
        messagesRef.limitToLast(50).on('child_added', (snapshot) => {
            const msgData = snapshot.val();
            const msgId = snapshot.key;
            displayMessage(msgData, msgId);
        });

        // يمكنك إضافة 'child_changed' و 'child_removed' إذا أردت دعم التعديل والحذف
    }

    // دالة تحديث واجهة قائمة المحادثات
    function updateChatListUI(activeChatId) {
        currentChatId = activeChatId; // تحديث المحادثة الحالية
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.chatId === activeChatId) {
                item.classList.add('active');
                // تحديث عنوان الدردشة في الهيدر
                chatTitle.textContent = item.textContent.replace(item.querySelector('.chat-icon').textContent, '').trim();
            }
        });
    }

    // --- المنطق الرئيسي ---

    // 1. التحقق من وجود اسم مستخدم محفوظ
    const savedUsername = localStorage.getItem('chatAMJD_username');
    if (savedUsername) {
        currentUser = savedUsername;
        welcomeScreen.classList.add('hidden');
        chatContainer.classList.remove('hidden');
        currentUsernameDisplay.textContent = currentUser;
        loadMessages(currentChatId); // تحميل رسائل المحادثة الافتراضية
        updateChatListUI(currentChatId); // تحديد المحادثة النشطة في القائمة
    } else {
        welcomeScreen.classList.remove('hidden');
        chatContainer.classList.add('hidden');
    }

    // 2. التعامل مع إدخال اسم المستخدم
    joinButton.addEventListener('click', () => {
        const username = usernameInput.value.trim();
        if (username && username.length > 2) {
            currentUser = username;
            localStorage.setItem('chatAMJD_username', currentUser); // حفظ الاسم
            welcomeScreen.classList.add('hidden'); // إخفاء شاشة الترحيب
             // تأخير بسيط لإظهار تأثير الانتقال
            setTimeout(() => {
               chatContainer.classList.remove('hidden'); // إظهار واجهة الدردشة
               currentUsernameDisplay.textContent = currentUser;
               loadMessages(currentChatId); // تحميل رسائل المحادثة الافتراضية
               updateChatListUI(currentChatId);
            }, 100); // تأخير بسيط جدًا

        } else {
            alert("الرجاء إدخال اسم صحيح (3 أحرف على الأقل).");
            usernameInput.focus();
        }
    });
    // السماح بالدخول عند الضغط على Enter في حقل الإسم
    usernameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            joinButton.click();
        }
    });


    // 3. التعامل مع إرسال الرسائل
    messageForm.addEventListener('submit', (e) => {
        e.preventDefault(); // منع إعادة تحميل الصفحة
        const messageText = messageInput.value.trim();

        if (messageText && currentUser && messagesRef) {
            const newMessage = {
                username: currentUser,
                text: messageText,
                timestamp: firebase.database.ServerValue.TIMESTAMP // استخدام وقت الخادم
            };

            // إرسال الرسالة إلى Firebase
            messagesRef.push(newMessage)
                .then(() => {
                    // تم الإرسال بنجاح
                    messageInput.value = ''; // مسح حقل الإدخال
                    scrollToBottom();
                    if (sendSound) {
                       sendSound.play().catch(e => console.log("لم يتم تشغيل صوت الإرسال:", e));
                    }
                })
                .catch((error) => {
                    console.error("خطأ في إرسال الرسالة:", error);
                    alert("حدث خطأ أثناء محاولة إرسال الرسالة.");
                });
        }
    });

    // 4. التعامل مع تغيير المحادثة (النقر على عنصر في القائمة)
    chatList.addEventListener('click', (e) => {
        const chatItem = e.target.closest('.chat-item');
        if (chatItem && chatItem.dataset.chatId !== currentChatId) {
            const newChatId = chatItem.dataset.chatId;
            updateChatListUI(newChatId); // تحديث الواجهة
            loadMessages(newChatId);    // تحميل رسائل المحادثة الجديدة
        }
    });

    // 5. التعامل مع زر "تغيير الاسم" (تسجيل الخروج البسيط)
    logoutButton.addEventListener('click', () => {
        if (confirm("هل أنت متأكد أنك تريد تغيير اسمك؟ سيتم مسح الاسم الحالي.")) {
            localStorage.removeItem('chatAMJD_username');
            currentUser = null;
            // إخفاء الدردشة وإظهار شاشة الترحيب
             chatContainer.classList.add('hidden');
             // تأخير بسيط لإظهار تأثير الانتقال
             setTimeout(() => {
                 welcomeScreen.classList.remove('hidden');
                 usernameInput.value = ''; // مسح حقل الإدخال القديم
                 messagesContainer.innerHTML = ''; // مسح الرسائل المعروضة
                 if (messagesRef) {
                     messagesRef.off(); // إيقاف الاستماع للرسائل القديمة
                     messagesRef = null;
                 }
             }, 100);
        }
    });

}); // نهاية DOMContentLoaded