// ============================================
// Utility functions for call simulator
// ============================================

function formatTime(date) {
    return new Date(date).toLocaleTimeString();
}

function getStatusBadge(status) {
    const badges = {
        'resolved': '<span class="badge badge-success">✅ Resolved</span>',
        'unresolved': '<span class="badge badge-danger">❌ Unresolved</span>',
        'not_asked': '<span class="badge badge-warning">⏳ Not Asked</span>'
    };
    return badges[status] || badges.not_asked;
}

// Export for use in other files
window.formatTime = formatTime;
window.getStatusBadge = getStatusBadge;

// ============================================
// Call Simulator Functions
// ============================================

let sessionId = null;
let callActive = false;
let awaitingFeedback = false;
let isListening = false;
let recognition = null;
let isProcessing = false;
let manualRestart = false;

// ============================================
// SPEECH RECOGNITION
// ============================================

function initSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        document.getElementById('voiceStatus').innerHTML = '❌ Browser doesn\'t support voice. Use Chrome or Edge.';
        document.getElementById('micBtn').disabled = true;
        return false;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    
    recognition.onstart = function() {
        isListening = true;
        document.getElementById('micBtn').classList.add('listening');
        document.getElementById('micBtn').innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="6" y="6" width="12" height="12" rx="2"/>
                <line x1="6" y1="18" x2="18" y2="6"/>
            </svg>
        `;
        document.getElementById('voiceStatus').innerHTML = '🎤 <span class="highlight">Listening...</span> Speak now!';
        document.getElementById('status-dot').className = 'dot listening';
        document.getElementById('status-text').textContent = 'Listening';
    };
    
    recognition.onresult = function(event) {
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript = event.results[i][0].transcript;
                break;
            }
        }
        
        if (finalTranscript && !isProcessing && callActive) {
            try { recognition.stop(); } catch(e) {}
            
            document.getElementById('voiceStatus').innerHTML = '🗣️ You said: "' + finalTranscript + '"';
            document.getElementById('message-input').value = finalTranscript;
            
            if (callActive && !isProcessing) {
                setTimeout(sendMessage, 300);
            }
        }
    };
    
    recognition.onerror = function(event) {
        console.error('Speech error:', event.error);
        if (event.error === 'not-allowed') {
            document.getElementById('voiceStatus').innerHTML = '❌ Microphone access denied. Allow mic access.';
        } else if (event.error === 'no-speech') {
            if (callActive && !isProcessing && !manualRestart) {
                document.getElementById('voiceStatus').innerHTML = '🔇 No speech detected. Try again.';
                setTimeout(function() {
                    if (callActive && !isProcessing) {
                        startListening();
                    }
                }, 1000);
            }
        } else if (event.error === 'aborted') {
            // User stopped, ignore
        } else {
            document.getElementById('voiceStatus').innerHTML = '❌ Error: ' + event.error;
            if (callActive && !isProcessing && !manualRestart) {
                setTimeout(function() {
                    if (callActive && !isProcessing) {
                        startListening();
                    }
                }, 2000);
            }
        }
    };
    
    recognition.onend = function() {
        isListening = false;
        if (callActive && !isProcessing && !manualRestart) {
            setTimeout(function() {
                if (callActive && !isProcessing) {
                    startListening();
                }
            }, 500);
        } else if (!callActive) {
            document.getElementById('mic-ring').className = 'pulse-ring inactive';
            document.getElementById('mic-status-text').textContent = '📞 Call ended';
        }
    };
    
    return true;
}

function startListening() {
    if (!recognition) {
        if (!initSpeechRecognition()) return;
    }
    if (isListening) return;
    if (!callActive) return;
    if (isProcessing) return;
    if (manualRestart) return;
    
    try {
        recognition.start();
    } catch (e) {
        console.error('Start error:', e);
        setTimeout(function() {
            if (callActive && !isProcessing && !manualRestart) {
                try { recognition.start(); } catch(e) {}
            }
        }, 500);
    }
}

function stopListening() {
    manualRestart = true;
    if (recognition) {
        try {
            recognition.stop();
        } catch (e) {}
    }
    isListening = false;
    document.getElementById('mic-ring').className = 'pulse-ring inactive';
    document.getElementById('mic-status-text').textContent = '⏸️ Paused';
    setTimeout(function() {
        manualRestart = false;
    }, 1000);
}

// ============================================
// SPEECH SYNTHESIS
// ============================================

function speakText(text) {
    return new Promise(function(resolve) {
        if (!('speechSynthesis' in window)) {
            resolve();
            return;
        }
        
        stopListening();
        window.speechSynthesis.cancel();
        
        const cleanText = text.replace(/[^\w\s.,?!'"]/g, '').trim();
        if (!cleanText) {
            resolve();
            return;
        }
        
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'en-US';
        utterance.rate = 0.9;
        utterance.pitch = 1;
        utterance.volume = 1;
        
        const voices = window.speechSynthesis.getVoices();
        const preferredVoice = voices.find(function(v) {
            return v.name.includes('Google') || 
                   v.name.includes('Samantha') || 
                   v.name.includes('Zira') ||
                   v.name.includes('David');
        });
        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }
        
        utterance.onstart = function() {
            document.getElementById('mic-ring').className = 'pulse-ring speaking';
            document.getElementById('mic-status-text').textContent = '🔊 Speaking...';
            document.getElementById('status-dot').className = 'dot speaking';
            document.getElementById('status-text').textContent = 'Speaking';
            document.getElementById('voiceStatus').innerHTML = '🔊 <span class="highlight">Speaking...</span>';
        };
        
        utterance.onend = function() {
            if (callActive && !isProcessing) {
                document.getElementById('status-dot').className = 'dot';
                document.getElementById('status-text').textContent = 'In Call';
                document.getElementById('mic-ring').className = 'pulse-ring';
                document.getElementById('mic-status-text').textContent = '🎤 Listening...';
                document.getElementById('voiceStatus').innerHTML = '🎤 <span class="highlight">Listening...</span> Speak now!';
                setTimeout(function() {
                    if (callActive && !isProcessing) {
                        startListening();
                    }
                }, 300);
            }
            resolve();
        };
        
        utterance.onerror = function(e) {
            console.error('Speech error:', e);
            if (callActive && !isProcessing) {
                setTimeout(function() {
                    if (callActive && !isProcessing) {
                        startListening();
                    }
                }, 300);
            }
            resolve();
        };
        
        window.speechSynthesis.speak(utterance);
        
        setTimeout(function() {
            if (callActive && !isProcessing) {
                startListening();
            }
            resolve();
        }, 30000);
    });
}

// ============================================
// CALL FUNCTIONS
// ============================================

function startCall() {
    const student = document.getElementById('student-select').value;
    isProcessing = false;
    manualRestart = false;
    
    document.getElementById('start-btn').disabled = true;
    document.getElementById('end-btn').disabled = false;
    document.getElementById('status-dot').className = 'dot';
    document.getElementById('status-text').textContent = 'Connecting...';
    document.getElementById('voiceStatus').innerHTML = '⏳ <span class="highlight">Connecting...</span>';
    
    fetch('/api/call/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ student: student })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        sessionId = data.session_id;
        callActive = true;
        awaitingFeedback = false;
        
        document.getElementById('messages').innerHTML = '';
        document.getElementById('voiceStatus').innerHTML = '🔊 <span class="highlight">AI is speaking...</span>';
        document.getElementById('mic-ring').className = 'pulse-ring speaking';
        document.getElementById('mic-status-text').textContent = '🔊 Speaking...';
        document.getElementById('status-dot').className = 'dot';
        document.getElementById('status-text').textContent = 'In Call';
        
        addMessage('assistant', data.response);
        speakText(data.response);
    })
    .catch(function(err) {
        alert('Error: ' + err.message);
        document.getElementById('start-btn').disabled = false;
        document.getElementById('end-btn').disabled = true;
        document.getElementById('status-text').textContent = 'Error';
    });
}

function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    if (!message || !sessionId || !callActive || isProcessing) return;
    
    isProcessing = true;
    input.value = '';
    addMessage('user', message);
    document.getElementById('voiceStatus').innerHTML = '⏳ <span class="highlight">Thinking...</span>';
    document.getElementById('status-dot').className = 'dot listening';
    document.getElementById('status-text').textContent = 'Processing';
    document.getElementById('mic-ring').className = 'pulse-ring inactive';
    document.getElementById('mic-status-text').textContent = '⏳ Processing...';
    
    fetch('/api/call/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: sessionId,
            message: message
        })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.error) {
            alert('Error: ' + data.error);
            isProcessing = false;
            if (callActive) {
                setTimeout(startListening, 500);
            }
            return;
        }
        
        addMessage('assistant', data.response);
        document.getElementById('voiceStatus').innerHTML = '🔊 <span class="highlight">Speaking...</span>';
        document.getElementById('mic-ring').className = 'pulse-ring speaking';
        document.getElementById('mic-status-text').textContent = '🔊 Speaking...';
        document.getElementById('status-dot').className = 'dot speaking';
        document.getElementById('status-text').textContent = 'Speaking';
        
        speakText(data.response).then(function() {
            isProcessing = false;
            
            if (data.ended) {
                callActive = false;
                document.getElementById('start-btn').disabled = false;
                document.getElementById('end-btn').disabled = true;
                document.getElementById('status-dot').className = 'dot inactive';
                document.getElementById('status-text').textContent = 'Call Ended';
                document.getElementById('mic-ring').className = 'pulse-ring inactive';
                document.getElementById('mic-status-text').textContent = '📞 Call ended';
                document.getElementById('voiceStatus').innerHTML = 'Call ended. Press "Start Call" again.';
                
                if (data.resolved) {
                    document.getElementById('status-text').textContent = 'Resolved';
                } else if (data.transfer) {
                    document.getElementById('status-text').textContent = 'Transferred to Human';
                }
            } else {
                document.getElementById('status-dot').className = 'dot listening';
                document.getElementById('status-text').textContent = 'Listening';
                document.getElementById('mic-ring').className = 'pulse-ring listening';
                document.getElementById('mic-status-text').textContent = '🎤 Listening... Speak now!';
                document.getElementById('voiceStatus').innerHTML = '🎤 <span class="highlight">Listening...</span> Speak now!';
                setTimeout(startListening, 300);
            }
            
            if (data.awaiting_feedback) {
                awaitingFeedback = true;
                document.getElementById('voiceStatus').innerHTML = '🤔 Please say <span class="highlight">"Yes"</span> or <span class="highlight">"No"</span>';
            }
        });
    })
    .catch(function(err) {
        alert('Error: ' + err.message);
        isProcessing = false;
        if (callActive) {
            setTimeout(startListening, 500);
        }
    });
}

function addMessage(role, text) {
    const container = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + role;
    
    const label = role === 'user' ? 'You' : 'AI Agent';
    messageDiv.innerHTML = `
        <div class="label">${label}</div>
        <div class="bubble">${text}</div>
    `;
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function quickMessage(text) {
    if (!callActive) {
        alert('Please start a call first!');
        return;
    }
    if (isProcessing) {
        document.getElementById('voiceStatus').innerHTML = '⏳ Please wait for AI to respond...';
        return;
    }
    stopListening();
    document.getElementById('message-input').value = text;
    sendMessage();
}

function endCall() {
    if (!sessionId) return;
    
    if (confirm('End this call?')) {
        manualRestart = true;
        if (isListening) {
            try { recognition.stop(); } catch(e) {}
        }
        isListening = false;
        
        fetch('/api/call/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        })
        .then(function() {
            callActive = false;
            isProcessing = false;
            document.getElementById('start-btn').disabled = false;
            document.getElementById('end-btn').disabled = true;
            document.getElementById('status-dot').className = 'dot inactive';
            document.getElementById('status-text').textContent = 'Call Ended';
            document.getElementById('mic-ring').className = 'pulse-ring inactive';
            document.getElementById('mic-status-text').textContent = '📞 Call ended';
            addMessage('assistant', 'Call ended. Thank you for using EduCall AI!');
            document.getElementById('voiceStatus').innerHTML = 'Call ended. Press "Start Call" again.';
            window.speechSynthesis.cancel();
            manualRestart = false;
        });
    }
}

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.getVoices();
        window.speechSynthesis.onvoiceschanged = function() {
            window.speechSynthesis.getVoices();
        };
        setTimeout(function() {
            window.speechSynthesis.getVoices();
        }, 500);
    }
    
    initSpeechRecognition();
});