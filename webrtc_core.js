// webrtc_core.js - Dedicated Calling Engine for Nexus Messenger
import { collection, doc, setDoc, updateDoc, onSnapshot, addDoc } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-firestore.js";

export function setupWebRTC(db, SYNC_APP_ID, getMyMobile, getActiveContact, getAllUsers) {
    // 100% Reliable Google STUN Servers
    const servers = {
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ]
    };

    let pc = null;
    let localStream = null;
    let incomingCallData = null;
    let currentCallId = null;
    let remoteDescriptionSet = false;
    let iceCandidateQueue = [];

    function getAvatarUrl(name, customUrl) {
        return customUrl ? customUrl : `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=ec4899&color=fff&bold=true`;
    }

    function initializePeerConnection() {
        if (pc) pc.close();
        pc = new RTCPeerConnection(servers);
        remoteDescriptionSet = false;
        iceCandidateQueue = [];

        const remoteVideo = document.getElementById('remote-video');
        const remoteAudio = document.getElementById('remote-audio');
        
        remoteVideo.srcObject = new MediaStream();
        remoteAudio.srcObject = new MediaStream();
        remoteVideo.muted = false;
        remoteAudio.muted = false;

        pc.ontrack = event => {
            const track = event.track;
            if (track.kind === 'video') {
                remoteVideo.srcObject.addTrack(track);
                remoteVideo.classList.remove('hidden');
                setTimeout(() => remoteVideo.play().catch(e => console.warn("Video blocked", e)), 100);
            } else if (track.kind === 'audio') {
                remoteAudio.srcObject.addTrack(track);
                setTimeout(() => remoteAudio.play().catch(e => console.warn("Audio blocked", e)), 100);
            }
        };
        return pc;
    }

    async function processIceCandidate(candidateData) {
        if (remoteDescriptionSet && pc) {
            await pc.addIceCandidate(new RTCIceCandidate(candidateData)).catch(e => {});
        } else { 
            iceCandidateQueue.push(candidateData); 
        }
    }

    // Expose listen function to window
    window.listenForIncomingCallsWebRTC = () => {
        const myMobile = getMyMobile();
        if (!myMobile) return;

        const callsRef = collection(db, 'artifacts', SYNC_APP_ID, 'public', 'data', 'calls');
        onSnapshot(callsRef, (snapshot) => {
            snapshot.docChanges().forEach(change => {
                const callData = change.doc.data();
                const callId = change.doc.id;

                if (change.type === 'added' || change.type === 'modified') {
                    if (callData.callee === myMobile && callData.status === 'calling') {
                        incomingCallData = { id: callId, ...callData };

                        document.getElementById('call-modal').classList.remove('hidden');
                        document.getElementById('call-modal').classList.add('flex');
                        document.getElementById('call-name').innerText = "Incoming Call";

                        const allUsers = getAllUsers();
                        const caller = allUsers.find(u => u.mobile === callData.caller);
                        document.getElementById('call-avatar').src = caller ? getAvatarUrl(caller.name, caller.avatarUrl) : getAvatarUrl("User", "");

                        const callTypeStr = callData.type === 'video' ? "Video Call" : "Audio Call";
                        document.getElementById('call-status').innerText = callTypeStr;

                        document.getElementById('answer-btn').classList.remove('hidden');
                        document.getElementById('in-call-controls').classList.add('hidden');
                        document.getElementById('caller-hangup-btn').classList.add('hidden');

                        if (callData.type === 'video') document.getElementById('answer-btn').innerHTML = '<i class="fa-solid fa-video"></i>';
                        else document.getElementById('answer-btn').innerHTML = '<i class="fa-solid fa-phone"></i>';

                        try { 
                            const ringtone = document.getElementById('ringtone-sound');
                            if(ringtone) ringtone.play().catch(e => {}); 
                        } catch (e) {}
                    }
                    if (callData.status === 'ended' && (currentCallId === callId || (incomingCallData && incomingCallData.id === callId))) {
                        window.resetCallUI();
                    }
                }
            });
        });
    };

    window.startCall = async (type) => {
        const activeContactMobile = getActiveContact();
        const myMobile = getMyMobile();
        if (!activeContactMobile || !myMobile) return;

        document.getElementById('call-modal').classList.remove('hidden');
        document.getElementById('call-modal').classList.add('flex');
        document.getElementById('call-name').innerText = document.getElementById('active-chat-name').innerText;
        document.getElementById('call-avatar').src = document.getElementById('active-chat-avatar').src;
        document.getElementById('call-status').innerText = "Calling...";

        document.getElementById('answer-btn').classList.add('hidden');
        document.getElementById('in-call-controls').classList.add('hidden');
        document.getElementById('caller-hangup-btn').classList.remove('hidden');
        document.getElementById('call-overlay').classList.remove('opacity-0', 'pointer-events-none');

        try {
            let constraints = { audio: true };
            if (type === 'video') constraints.video = { facingMode: "user" };

            try {
                localStream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (fallbackError) {
                console.warn("Camera failed, fallback to audio only.", fallbackError);
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                type = 'audio'; // Downgrade to audio
            }

            if (type === 'video') {
                const localVid = document.getElementById('local-video');
                localVid.srcObject = localStream;
                localVid.classList.remove('hidden');
            }

            pc = initializePeerConnection();
            localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

            // Create Unique Call ID
            const chatHash = myMobile < activeContactMobile ? myMobile + "_" + activeContactMobile : activeContactMobile + "_" + myMobile;
            currentCallId = "call_" + chatHash + "_" + Date.now();
            
            const callDocRef = doc(db, 'artifacts', SYNC_APP_ID, 'public', 'data', 'calls', currentCallId);
            const offerCandidates = collection(callDocRef, 'offerCandidates');
            const answerCandidates = collection(callDocRef, 'answerCandidates');

            pc.onicecandidate = event => { 
                if (event.candidate) addDoc(offerCandidates, event.candidate.toJSON()); 
            };

            const offerDescription = await pc.createOffer();
            await pc.setLocalDescription(offerDescription);

            await setDoc(callDocRef, {
                offer: { type: offerDescription.type, sdp: offerDescription.sdp },
                caller: myMobile, 
                callee: activeContactMobile, 
                type: type, 
                status: 'calling', 
                timestamp: Date.now()
            });

            pc.callUnsubscribe = onSnapshot(callDocRef, async (snapshot) => {
                const data = snapshot.data();
                if (pc && !remoteDescriptionSet && data?.answer) {
                    await pc.setRemoteDescription(new RTCSessionDescription(data.answer));
                    remoteDescriptionSet = true;

                    document.getElementById('call-status').innerText = "Connected";
                    document.getElementById('caller-hangup-btn').classList.add('hidden');
                    document.getElementById('in-call-controls').classList.remove('hidden');

                    if (type === 'video') {
                        document.getElementById('call-overlay').classList.add('opacity-0', 'pointer-events-none');
                        document.getElementById('cam-toggle-btn').classList.remove('hidden');
                    }

                    for (let cand of iceCandidateQueue) await pc.addIceCandidate(new RTCIceCandidate(cand)).catch(e => {});
                    iceCandidateQueue = [];

                    onSnapshot(answerCandidates, (candSnapshot) => {
                        candSnapshot.docChanges().forEach(change => {
                            if (change.type === 'added') processIceCandidate(change.doc.data());
                        });
                    });
                }
            });

        } catch (err) {
            console.error("Device media error:", err);
            alert("Microphone permission denied or device error.");
            window.resetCallUI();
        }
    };

    window.answerCall = async () => {
        if (!incomingCallData) return;

        const ringtone = document.getElementById('ringtone-sound');
        if (ringtone) { ringtone.pause(); ringtone.currentTime = 0; }

        document.getElementById('call-status').innerText = "Connecting...";
        document.getElementById('answer-btn').classList.add('hidden');

        let type = incomingCallData.type;

        try {
            let constraints = { audio: true };
            if (type === 'video') constraints.video = { facingMode: "user" };

            try {
                localStream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (fallbackError) {
                console.warn("Camera failed during answer, fallback to audio.", fallbackError);
                localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                type = 'audio'; // Downgrade to audio
            }

            if (type === 'video') {
                const localVid = document.getElementById('local-video');
                localVid.srcObject = localStream;
                localVid.classList.remove('hidden');
            }

            pc = initializePeerConnection();
            localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

            currentCallId = incomingCallData.id;
            const callDocRef = doc(db, 'artifacts', SYNC_APP_ID, 'public', 'data', 'calls', currentCallId);
            const answerCandidates = collection(callDocRef, 'answerCandidates');
            const offerCandidates = collection(callDocRef, 'offerCandidates');

            pc.onicecandidate = event => { 
                if (event.candidate) addDoc(answerCandidates, event.candidate.toJSON()); 
            };

            await pc.setRemoteDescription(new RTCSessionDescription(incomingCallData.offer));
            remoteDescriptionSet = true;

            const answerDescription = await pc.createAnswer();
            await pc.setLocalDescription(answerDescription);

            await updateDoc(callDocRef, { answer: { type: answerDescription.type, sdp: answerDescription.sdp }, status: 'answered' });

            document.getElementById('call-status').innerText = "Connected";
            document.getElementById('in-call-controls').classList.remove('hidden');

            if (type === 'video') {
                document.getElementById('call-overlay').classList.add('opacity-0', 'pointer-events-none');
                document.getElementById('cam-toggle-btn').classList.remove('hidden');
            }

            onSnapshot(offerCandidates, (snapshot) => {
                snapshot.docChanges().forEach(change => { 
                    if (change.type === 'added') processIceCandidate(change.doc.data()); 
                });
            });
        } catch (e) {
            console.error("Answer error:", e);
            alert("Could not connect: Microphone permission denied.");
            window.resetCallUI();
        }
    };

    window.hangupCall = async () => {
        const idToHangup = currentCallId || (incomingCallData ? incomingCallData.id : null);
        if (idToHangup) {
            const callDocRef = doc(db, 'artifacts', SYNC_APP_ID, 'public', 'data', 'calls', idToHangup);
            await updateDoc(callDocRef, { status: 'ended' }).catch(() => {});
        }
        window.resetCallUI();
    };

    window.resetCallUI = () => {
        const ringtone = document.getElementById('ringtone-sound');
        if (ringtone) { ringtone.pause(); ringtone.currentTime = 0; }
        
        document.getElementById('call-modal').classList.remove('flex'); 
        document.getElementById('call-modal').classList.add('hidden');
        document.getElementById('call-overlay').classList.remove('opacity-0', 'pointer-events-none');
        document.getElementById('local-video').classList.add('hidden'); 
        document.getElementById('remote-video').classList.add('hidden');
        document.getElementById('cam-toggle-btn').classList.add('hidden');

        if (localStream) { 
            localStream.getTracks().forEach(track => track.stop()); 
            localStream = null; 
        }
        if (pc) { 
            if (pc.callUnsubscribe) pc.callUnsubscribe(); 
            pc.close(); 
            pc = null; 
        }
        incomingCallData = null; 
        currentCallId = null; 
        remoteDescriptionSet = false; 
        iceCandidateQueue = [];
        
        const remoteVideo = document.getElementById('remote-video'); if (remoteVideo) remoteVideo.srcObject = null;
        const remoteAudio = document.getElementById('remote-audio'); if (remoteAudio) remoteAudio.srcObject = null;
        const localVideo = document.getElementById('local-video'); if (localVideo) localVideo.srcObject = null;
    };

    window.toggleMic = () => {
        if (!localStream) return;
        const audioTrack = localStream.getAudioTracks()[0];
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled;
            const btn = document.getElementById('mic-toggle-btn');
            if (audioTrack.enabled) { 
                btn.innerHTML = '<i class="fa-solid fa-microphone"></i>'; 
                btn.classList.replace('text-red-500', 'text-white'); 
            } else { 
                btn.innerHTML = '<i class="fa-solid fa-microphone-slash"></i>'; 
                btn.classList.replace('text-white', 'text-red-500'); 
            }
        }
    };

    window.toggleCamera = () => {
        if (!localStream) return;
        const videoTrack = localStream.getVideoTracks()[0];
        if (videoTrack) {
            videoTrack.enabled = !videoTrack.enabled;
            const btn = document.getElementById('cam-toggle-btn');
            if (videoTrack.enabled) { 
                btn.innerHTML = '<i class="fa-solid fa-video"></i>'; 
                btn.classList.replace('text-red-500', 'text-white'); 
            } else { 
                btn.innerHTML = '<i class="fa-solid fa-video-slash"></i>'; 
                btn.classList.replace('text-white', 'text-red-500'); 
            }
        }
    };
}