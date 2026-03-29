import { initializeApp } from "https://www.gstatic.com/firebasejs/11.3.1/firebase-app.js";
import { getFirestore, doc, onSnapshot, setDoc, getDoc, collection, query, orderBy, limit } from "https://www.gstatic.com/firebasejs/11.3.1/firebase-firestore.js";

// Firebase Configuration
const firebaseConfig = {
  apiKey: "AIzaSyDGd3KAo45UuqmeGFALziz_oKm3htEASHY",
  projectId: "mywebtools-f8d53",
  messagingSenderId: "979594414301",
  appId: "1:979594414301:web:7048c995e56e331a85f334"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

const SYNC_APP_ID = "617849c704870f43d0f04c7b"; // আপনার অ্যাপ আইডি
let myMobile = localStorage.getItem('myMobile');
let myName = localStorage.getItem('myName') || "User";
let allUsers = [];
let isDataLoading = true;

// ১. সার্ভিস ওয়ার্কার রেজিস্ট্রেশন (ক্যাশিং এর জন্য)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js')
      .then(reg => console.log('SW registered!'))
      .catch(err => console.error('SW failed:', err));
  });
}

// ২. অ্যাপ শুরু করার মেইন ফাংশন
async function startApp() {
  if (!myMobile) {
    window.location.href = "login.html"; // মোবাইল নম্বর না থাকলে লগইন এ পাঠাবে
    return;
  }

  // স্পিনার লজিক: ক্যাশে ডেটা থাকলে দেখাবে, ফাঁকা থাকলে স্পিনার ঘুরবে
  const cachedUsers = localStorage.getItem('cached_users');
  if (cachedUsers) {
    const parsedUsers = JSON.parse(cachedUsers);
    if (parsedUsers.length > 0) {
      allUsers = parsedUsers;
      isDataLoading = false;
      renderChatList();
    }
  }

  // OneSignal ID হ্যান্ডেল করা (Modular Syntax)
  window.OneSignalDeferred = window.OneSignalDeferred || [];
  OneSignalDeferred.push(async function(OneSignal) {
    OneSignal.User.PushSubscription.addEventListener("change", async (event) => {
      const oneSignalUserId = event.current.id;
      if (oneSignalUserId) saveOneSignalId(oneSignalUserId);
    });

    const currentId = OneSignal.User.PushSubscription.id;
    if (currentId) saveOneSignalId(currentId);
  });

  // ফায়ারবেস থেকে রিয়েলটাইম চ্যাট লিস্ট আনা
  const usersQuery = query(collection(db, 'artifacts', SYNC_APP_ID, 'public', 'data', 'chat_users'));
  
  onSnapshot(usersQuery, (snapshot) => {
    allUsers = [];
    snapshot.forEach(doc => {
      if (doc.id !== myMobile) {
        allUsers.push({ id: doc.id, ...doc.data() });
      }
    });

    // ডেটা আসার পর ক্যাশ আপডেট এবং স্পিনার বন্ধ
    localStorage.setItem('cached_users', JSON.stringify(allUsers));
    isDataLoading = false;
    renderChatList();
  }, (error) => {
    console.error("Firestore Error:", error);
    isDataLoading = false;
    renderChatList();
  });
}

// ৩. OneSignal ID ফায়ারস্টোরে সেভ করা
async function saveOneSignalId(playerId) {
  if (myMobile && playerId) {
    try {
      await setDoc(doc(db, 'artifacts', SYNC_APP_ID, 'public', 'data', 'chat_users', myMobile), {
        onesignal_id: playerId,
        lastActive: new Date().toISOString()
      }, { merge: true });
      console.log("OneSignal ID synced:", playerId);
    } catch (e) {
      console.error("Error saving OneSignal ID:", e);
    }
  }
}

// ৪. চ্যাট লিস্ট রেন্ডার করা (UI)
function renderChatList() {
  const chatContainer = document.getElementById('chat-list-container');
  const loader = document.getElementById('loading-spinner');

  if (isDataLoading) {
    loader.classList.remove('hidden');
    chatContainer.innerHTML = '';
    return;
  }

  loader.classList.add('hidden');

  if (allUsers.length === 0) {
    chatContainer.innerHTML = `
      <div class="flex flex-col items-center justify-center h-64 text-gray-500">
        <i class="fa-solid fa-message text-4xl mb-2 opacity-20"></i>
        <p>No chats found yet</p>
      </div>`;
    return;
  }

  chatContainer.innerHTML = allUsers.map(user => `
    <div onclick="openChat('${user.id}', '${user.name}')" class="flex items-center p-4 border-b border-gray-100 active:bg-gray-50 cursor-pointer transition">
      <img src="https://ui-avatars.com/api/?name=${user.name}&background=random" class="w-12 h-12 rounded-full shadow-sm">
      <div class="ml-4 flex-1">
        <div class="flex justify-between items-center">
          <h3 class="font-bold text-gray-800">${user.name}</h3>
          <span class="text-xs text-gray-400">Just now</span>
        </div>
        <p class="text-sm text-gray-500 truncate">Tap to start conversation</p>
      </div>
    </div>
  `).join('');
}

// ৫. চ্যাট ওপেন করা
window.openChat = function(id, name) {
  localStorage.setItem('chattingWithId', id);
  localStorage.setItem('chattingWithName', name);
  window.location.href = 'chat_indivisual.html';
};

// ৬. পুশ নোটিফিকেশন ট্রিগার (যাকে মেসেজ পাঠাবেন তার ID দিয়ে কল করবেন)
window.triggerPush = async function(targetMobile, messageText) {
  try {
    const userDoc = await getDoc(doc(db, 'artifacts', SYNC_APP_ID, 'public', 'data', 'chat_users', targetMobile));
    if (userDoc.exists() && userDoc.data().onesignal_id) {
      const restApiKey = "os_v2_app_kivtcnwbnvg6xbbdotnmhvsffzag6wdfng7ufmfb7dtdwn2k4nr43uy5xgi6zvzqfyttgujh3yhn4eghuttyixea2o7dopgljwgq3uq";
      
      await fetch("https://onesignal.com/api/v1/notifications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Authorization": "Basic " + restApiKey
        },
        body: JSON.stringify({
          app_id: "522b3136-c16d-4deb-8423-74dac3d6452e",
          include_player_ids: [userDoc.data().onesignal_id],
          contents: {"en": messageText},
          headings: {"en": myName + " sends a message"},
          priority: 10
        })
      });
    }
  } catch (e) {
    console.error("Push notification failed:", e);
  }
};

// অ্যাপ রান করা
startApp();
