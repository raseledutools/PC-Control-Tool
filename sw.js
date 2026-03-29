const CACHE_NAME = 'rasgram-offline-v5'; // ভার্সন আপডেট করা হলো নতুন কোড লোড করার জন্য

// এখানে ফাইলের নামগুলো একদম হুবহু আপনার GitHub এর নামের মতো দিয়েছি
const urlsToCache = [
  './',
  './index.html', // সরাসরি index.html দিয়ে রাখা ভালো
  './chat_indivisual.html', 
  './script.js',
  './webrtc_core.js', 
  './manifest.json',
  './developer.jpg',
  'https://unpkg.com/dexie/dist/dexie.js',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // একটি একটি করে ফাইল ক্যাশ করবে, যাতে কোনো একটি ফেইল করলেও পুরো প্রসেস ক্র্যাশ না করে
      for (let url of urlsToCache) {
        try {
          await cache.add(url);
          console.log('Successfully cached:', url);
        } catch (e) {
          console.error('Failed to cache:', url, e);
        }
      }
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName); // পুরনো ক্যাশ মুছে নতুনটা চালু করবে
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // ফায়ারবেস, ক্লাউডিনারি, OneSignal ক্যাশ করবো না এবং শুধুমাত্র GET রিকোয়েস্ট ক্যাশ করবো
  if (
    event.request.method !== 'GET' ||
    url.includes('firestore.googleapis.com') || 
    url.includes('identitytoolkit.googleapis.com') ||
    url.includes('api.cloudinary.com') ||
    url.includes('onesignal.com')
  ) {
    return; 
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      // ক্যাশে থাকলে সাথে সাথে দিয়ে দিবে (এটি ফ্লিকারিং কমাবে এবং স্পিড বাড়াবে)
      if (cachedResponse) {
        return cachedResponse;
      }

      // ক্যাশে না থাকলে নেটওয়ার্ক থেকে আনবে
      return fetch(event.request).then((networkResponse) => {
        return caches.open(CACHE_NAME).then((cache) => {
          // ডাইনামিক ক্যাশিং: ইউজারদের প্রোফাইল ছবি ও সাউন্ড একবার লোড হলে ক্যাশ করে রাখবে
          if (url.includes('ui-avatars.com') || url.includes('assets.mixkit.co')) {
              cache.put(event.request, networkResponse.clone());
          }
          return networkResponse;
        });
      }).catch(() => {
        console.log('Offline and resource not found in cache:', url);
      });
    })
  );
});
