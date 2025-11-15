// firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging.js');

firebase.initializeApp({
    apiKey: "tvoj_api_kljuc",
    authDomain: "tvoj_projekat.firebaseapp.com",
    projectId: "tvoj_projekat",
    storageBucket: "tvoj_projekat.appspot.com",
    messagingSenderId: "tvoj_sender_id",
    appId: "tvoj_app_id",
    measurementId: "tvoj_measurement_id"
});

const messaging = firebase.messaging();