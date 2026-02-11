// Chat Component - Fullscreen Modal with Event-Based API
Vue.component('Chat', {
    delimiters: ['[[', ']]'],
    props: {
        show: {
            type: Boolean,
            default: false
        },
        walletAddress: {
            type: String,
            default: ''
        },
        isAuthenticated: {
            type: Boolean,
            default: false
        }
    },
    data() {
        return {
            chatSearchQuery: '',
            chatInputText: '',
            selectedContactId: null,
            isSigning: false,
            pendingSignature: null,
            isRecordingAudio: false,
            isRecordingVideo: false,
            pendingAttachments: [], // Files waiting to be sent together
            escrowData: {
                wallet: null,
                balance: '0',
                amount: '0',
                status: 'pending',
                guarantor: null
            },
            isStatusPanelCollapsed: false,
            showEmojiPicker: false,
            contacts: [
                {
                    id: 'gemini',
                    name: 'Gemini AI Assistant',
                    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=Gemini',
                    status: 'online',
                    lastMessage: 'Привет! Я ваш AI помощник.',
                    isTyping: false
                }
            ],
            messages: {},
            emojiCategories: {
                'smileys': ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘', '😗', '😚', '😙', '😋', '😛', '😜', '🤪', '😝', '🤑', '🤗', '🤭', '🤫', '🤔'],
                'gestures': ['👋', '🤚', '🖐', '✋', '🖖', '👌', '🤌', '🤏', '✌️', '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '👍', '👎', '✊', '👊', '🤛', '🤜', '👏', '🙌', '👐', '🤲', '🤝'],
                'people': ['👶', '🧒', '👦', '👧', '🧑', '👱', '👨', '🧔', '👩', '🧓', '👴', '👵', '🙍', '🙎', '🙅', '🙆', '💁', '🙋', '🧏', '🙇', '🤦', '🤷', '👮', '🕵️', '💂', '🥷', '👷', '🤴', '👸', '👳'],
                'animals': ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐽', '🐸', '🐵', '🙈', '🙉', '🙊', '🐒', '🐔', '🐧', '🐦', '🐤', '🐣', '🐥', '🦆', '🦅', '🦉', '🦇'],
                'food': ['🍏', '🍎', '🍐', '🍊', '🍋', '🍌', '🍉', '🍇', '🍓', '🍈', '🍒', '🍑', '🥭', '🍍', '🥥', '🥝', '🍅', '🍆', '🥑', '🥦', '🥬', '🥒', '🌶', '🌽', '🥕', '🥔', '🍠', '🥐', '🥯', '🍞'],
                'activities': ['⚽', '🏀', '🏈', '⚾', '🥎', '🎾', '🏐', '🏉', '🥏', '🎱', '🏓', '🏸', '🏒', '🏑', '🥍', '🏏', '🥅', '⛳', '🏹', '🎣', '🥊', '🥋', '🎽', '🛹', '🛷', '⛸', '🥌', '🎿', '⛷', '🏂'],
                'objects': ['⌚', '📱', '📲', '💻', '⌨️', '🖥', '🖨', '🖱', '🖲', '🕹', '🗜', '💾', '💿', '📀', '📼', '📷', '📸', '📹', '🎥', '📽', '🎞', '📞', '☎️', '📟', '📠', '📺', '📻', '🎙', '🎚', '🎛'],
                'symbols': ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝', '💟', '☮️', '✝️', '☪️', '🕉', '☸️', '✡️', '🔯', '🕎', '☯️', '☦️', '🛐']
            }
        }
    },
    computed: {
        filteredContacts() {
            const q = this.chatSearchQuery.toLowerCase();
            return this.contacts.filter(c =>
                c.name.toLowerCase().includes(q)
            );
        },
        selectedContact() {
            return this.contacts.find(c => c.id === this.selectedContactId);
        },
        currentMessages() {
            return this.messages[this.selectedContactId] || [];
        }
    },
    watch: {
        show(newVal) {
            if (newVal) {
                this.initChat();
            }
        }
    },
    mounted() {
        // Close emoji picker when clicking outside
        this.$nextTick(() => {
            document.addEventListener('click', this.handleClickOutside);
        });
    },
    beforeDestroy() {
        document.removeEventListener('click', this.handleClickOutside);
    },
    methods: {
        close() {
            this.$emit('close');
        },
        initChat() {
            if (!this.messages['gemini']) {
                this.$set(this.messages, 'gemini', [
                    {
                        id: 'init',
                        text: 'Привет! Как я могу помочь вам?',
                        sender: 'bot',
                        timestamp: Date.now() - 60000
                    }
                ]);
            }
            this.loadEscrowData();
        },
        async loadEscrowData() {
            if (!this.isAuthenticated || !this.walletAddress) {
                return;
            }
            
            try {
                this.escrowData = {
                    wallet: this.walletAddress,
                    balance: '1.5',
                    amount: '0.5',
                    status: 'pending',
                    guarantor: null
                };
            } catch (error) {
                console.error('Error loading escrow data:', error);
            }
        },
        formatWallet(address) {
            if (!address) return '-';
            return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
        },
        
        // Public methods exposed to parent components
        send_text_message(text, contactId = null) {
            const targetContactId = contactId || this.selectedContactId;
            // Allow sending if there's text OR pending attachments
            if ((!text || text.trim() === '') && this.pendingAttachments.length === 0) return;
            if (!targetContactId) return;
            
            const contact = this.contacts.find(c => c.id === targetContactId);
            if (!contact) return;
            
            const cid = targetContactId;
            const ts = Date.now();
            
            // Use empty string if no text but there are attachments
            const messageText = text || '';
            
            const userMsg = {
                id: 'u-' + ts,
                text: messageText,
                sender: 'user',
                timestamp: ts,
                status: 'sent',
                signature: null,
                attachments: this.pendingAttachments.length > 0 ? this.pendingAttachments : undefined
            };
            
            if (!this.messages[cid]) {
                this.$set(this.messages, cid, []);
            }
            this.messages[cid].push(userMsg);
            contact.lastMessage = messageText || (this.pendingAttachments.length > 0 ? `${this.pendingAttachments.length} файл(ов)` : '');
            
            // Clear pending attachments after sending
            const attachmentsToEmit = [...this.pendingAttachments];
            this.pendingAttachments = [];
            
            this.$nextTick(this.scrollToBottom);
            
            // Emit event
            this.$emit('on_send_text_message', {
                text: messageText,
                contactId: targetContactId,
                messageId: userMsg.id,
                timestamp: ts,
                attachments: attachmentsToEmit.length > 0 ? attachmentsToEmit : undefined
            });
        },
        
        send_documents(files, contactId = null) {
            const targetContactId = contactId || this.selectedContactId;
            if (!files || !files.length || !targetContactId) return;
            
            const contact = this.contacts.find(c => c.id === targetContactId);
            if (!contact) return;
            
            // Add files to pending attachments (they will be grouped together)
            const newAttachments = Array.from(files).map((file) => {
                const isImage = file.type.startsWith('image/');
                const isVideo = file.type.startsWith('video/');
                const type = isImage ? 'photo' : (isVideo ? 'video' : 'document');
                
                return {
                    id: Math.random().toString(36).substr(2, 9),
                    type: type,
                    name: file.name,
                    url: URL.createObjectURL(file),
                    size: (file.size / 1024).toFixed(1) + ' KB',
                    file: file
                };
            });
            
            this.pendingAttachments = [...this.pendingAttachments, ...newAttachments];
            
            // Emit event
            this.$emit('on_send_documents', {
                files: Array.from(files),
                contactId: targetContactId,
                timestamp: Date.now()
            });
        },
        
        sign(messageId, text = null) {
            if (!messageId) {
                // Sign current input text
                if (!this.chatInputText.trim()) {
                    return;
                }
                this.isSigning = true;
                this.$emit('on_sign', {
                    type: 'input',
                    text: this.chatInputText.trim(),
                    messageId: null
                });
                return;
            }
            
            // Sign existing message
            const message = this.findMessageById(messageId);
            if (!message) return;
            
            if (message.signature && message.signature.startsWith('0x')) {
                return; // Already signed
            }
            
            this.isSigning = true;
            const textToSign = text || message.text;
            
            this.$emit('on_sign', {
                type: 'message',
                text: textToSign,
                messageId: messageId,
                message: message
            });
        },
        
        record_audio() {
            if (this.isRecordingAudio) {
                // Stop recording
                this.isRecordingAudio = false;
                this.$emit('on_audio', {
                    action: 'stop',
                    contactId: this.selectedContactId
                });
            } else {
                // Start recording
                this.isRecordingAudio = true;
                this.isRecordingVideo = false; // Stop video if recording
                this.$emit('on_audio', {
                    action: 'start',
                    contactId: this.selectedContactId
                });
            }
        },
        
        record_video() {
            if (this.isRecordingVideo) {
                // Stop recording
                this.isRecordingVideo = false;
                this.$emit('on_video', {
                    action: 'stop',
                    contactId: this.selectedContactId
                });
            } else {
                // Start recording
                this.isRecordingVideo = true;
                this.isRecordingAudio = false; // Stop audio if recording
                this.$emit('on_video', {
                    action: 'start',
                    contactId: this.selectedContactId
                });
            }
        },
        
        // Public method to load chat history
        load_history(history) {
            if (!history || !Array.isArray(history)) {
                console.warn('Chat.load_history: history must be an array');
                return;
            }
            
            // Clear existing messages
            this.messages = {};
            
            // Group messages by contactId
            const messagesByContact = {};
            
            history.forEach(msg => {
                const contactId = msg.contactId || msg.contact_id || 'default';
                
                if (!messagesByContact[contactId]) {
                    messagesByContact[contactId] = [];
                }
                
                // Convert history message to chat message format
                const chatMessage = {
                    id: msg.id || msg.messageId || 'msg-' + Date.now() + '-' + Math.random(),
                    text: msg.text || msg.message || '',
                    sender: msg.sender || (msg.senderId ? 'user' : 'bot'),
                    timestamp: msg.timestamp || msg.created_at || Date.now(),
                    status: msg.status || 'sent',
                    signature: msg.signature || null,
                    type: msg.type || 'text'
                };
                
                messagesByContact[contactId].push(chatMessage);
            });
            
            // Sort messages by timestamp and set them
            Object.keys(messagesByContact).forEach(contactId => {
                messagesByContact[contactId].sort((a, b) => a.timestamp - b.timestamp);
                this.$set(this.messages, contactId, messagesByContact[contactId]);
            });
            
            // Create or update contacts from history
            Object.keys(messagesByContact).forEach(contactId => {
                let contact = this.contacts.find(c => c.id === contactId);
                
                if (!contact) {
                    // Find contact info from first message
                    const firstMsg = history.find(m => (m.contactId || m.contact_id) === contactId);
                    // Create new contact if it doesn't exist
                    contact = {
                        id: contactId,
                        name: (firstMsg && firstMsg.contactName) || `Contact ${contactId}`,
                        avatar: (firstMsg && firstMsg.contactAvatar) || null,
                        status: 'online',
                        lastMessage: '',
                        isTyping: false
                    };
                    this.contacts.push(contact);
                }
                
                // Update last message
                if (messagesByContact[contactId].length > 0) {
                    const lastMsg = messagesByContact[contactId][messagesByContact[contactId].length - 1];
                    contact.lastMessage = lastMsg.text.substring(0, 50);
                }
            });
            
            // Auto-select first contact if none selected and history exists
            this.$nextTick(() => {
                const contactIds = Object.keys(messagesByContact);
                if (contactIds.length > 0 && !this.selectedContactId) {
                    // Select first contact
                    const firstContactId = contactIds[0];
                    const contact = this.contacts.find(c => c.id === firstContactId);
                    if (contact) {
                        this.selectContact(contact);
                    }
                } else if (this.selectedContactId) {
                    this.scrollToBottom();
                }
            });
        },
        
        // Helper methods
        findMessageById(messageId) {
            for (const contactId in this.messages) {
                const message = this.messages[contactId].find(m => m.id === messageId);
                if (message) return message;
            }
            return null;
        },
        
        // Internal methods
        selectContact(contact) {
            this.selectedContactId = contact.id;
            if (!this.messages[contact.id]) {
                this.$set(this.messages, contact.id, []);
            }
            this.$nextTick(this.scrollToBottom);
        },
        formatTime(ts) {
            return new Date(ts).toLocaleTimeString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit'
            });
        },
        scrollToBottom() {
            const el = this.$refs.messageList;
            if (el) el.scrollTop = el.scrollHeight;
        },
        adjustTextareaHeight() {
            this.$nextTick(() => {
                const textarea = this.$refs.textareaInput;
                if (textarea) {
                    textarea.style.height = 'auto';
                    textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
                }
            });
        },
        
        toggleEmojiPicker(event) {
            if (event) {
                event.stopPropagation();
            }
            this.showEmojiPicker = !this.showEmojiPicker;
        },
        
        insertEmoji(emoji) {
            const textarea = this.$refs.textareaInput;
            if (textarea) {
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const text = this.chatInputText;
                this.chatInputText = text.substring(0, start) + emoji + text.substring(end);
                this.$nextTick(() => {
                    textarea.focus();
                    textarea.setSelectionRange(start + emoji.length, start + emoji.length);
                    this.adjustTextareaHeight();
                });
            } else {
                this.chatInputText += emoji;
            }
            // Close emoji picker after inserting emoji
            this.showEmojiPicker = false;
        },
        
        handleClickOutside(event) {
            if (!this.showEmojiPicker) return;
            
            // Check if click is on emoji button
            const target = event.target;
            const emojiButton = target.closest('button[title="Emoji"]');
            
            // Don't close if clicking on emoji button (it will toggle)
            if (emojiButton) {
                return;
            }
            
            // Check if click is inside picker using ref
            if (this.$refs.emojiPicker && this.$refs.emojiPicker.contains(target)) {
                return; // Don't close if clicking inside picker
            }
            
            // Close if clicking outside
            this.showEmojiPicker = false;
        },
        clearPendingSignatureIfTextChanged() {
            if (this.pendingSignature && !this.chatInputText.includes('[Подписано:')) {
                this.pendingSignature = null;
            }
        },
        
        // Handle file input
        handleFileSelect(event) {
            const files = event.target.files;
            if (files && files.length > 0) {
                // Add files to pending attachments (they will be sent together with text)
                const newAttachments = Array.from(files).map((file) => {
                    const isImage = file.type.startsWith('image/');
                    const isVideo = file.type.startsWith('video/');
                    const type = isImage ? 'photo' : (isVideo ? 'video' : 'document');
                    
                    return {
                        id: Math.random().toString(36).substr(2, 9),
                        type: type,
                        name: file.name,
                        url: URL.createObjectURL(file),
                        size: (file.size / 1024).toFixed(1) + ' KB',
                        file: file
                    };
                });
                
                this.pendingAttachments = [...this.pendingAttachments, ...newAttachments];
                
                // Emit event
                this.$emit('on_send_documents', {
                    files: Array.from(files),
                    contactId: this.selectedContactId,
                    timestamp: Date.now()
                });
            }
            // Reset input
            event.target.value = '';
        },
        
        // Remove pending attachment
        removePendingAttachment(id) {
            this.pendingAttachments = this.pendingAttachments.filter(a => a.id !== id);
        },
        
        // Handle send button click
        handleSend() {
            const text = this.chatInputText.trim();
            // Allow sending if there's text OR pending attachments
            if ((!text && this.pendingAttachments.length === 0) || !this.selectedContactId) return;
            
            let messageText = text || ''; // Allow empty text if there are attachments
            let signature = null;
            
            if (text && this.pendingSignature) {
                messageText = text.replace(/\n\n\[Подписано: .+?\]/, '').trim();
                signature = this.pendingSignature;
                this.pendingSignature = null;
            } else if (text) {
                const signatureMatch = text.match(/\[Подписано: (.+?)\]/);
                if (signatureMatch) {
                    messageText = text.replace(/\n\n\[Подписано: .+?\]/, '').trim();
                }
            }
            
            this.chatInputText = '';
            this.$nextTick(() => {
                const textarea = this.$refs.textareaInput;
                if (textarea) {
                    textarea.style.height = 'auto';
                }
            });
            this.send_text_message(messageText);
            
            // If there was a signature, attach it to the last message
            if (signature) {
                const contact = this.selectedContact;
                const cid = contact.id;
                if (this.messages[cid] && this.messages[cid].length > 0) {
                    const lastMsg = this.messages[cid][this.messages[cid].length - 1];
                    if (lastMsg.sender === 'user') {
                        this.$set(lastMsg, 'signature', signature);
                    }
                }
            }
        },
        
        // Handle sign button click
        handleSignClick() {
            if (!this.chatInputText.trim()) {
                return;
            }
            this.sign(null, this.chatInputText.trim());
        },
        
        // Handle sign existing message
        handleSignExistingMessage(message) {
            this.sign(message.id, message.text);
        },
        
        // Handle signature result from parent
        onSignatureResult(messageId, signature) {
            this.isSigning = false;
            
            if (messageId) {
                const message = this.findMessageById(messageId);
                if (message) {
                    this.$set(message, 'signature', signature);
                }
            } else {
                // Signature for input text
                this.pendingSignature = signature;
                const cleanMessage = this.chatInputText.replace(/\n\n\[Подписано: .+?\]/, '').trim();
                const signedText = `${cleanMessage}\n\n[Подписано: ${signature.substring(0, 10)}...${signature.substring(signature.length - 8)}]`;
                this.chatInputText = signedText;
            }
        }
    },
    template: `
        <div>
            <style>
                @keyframes pulse {
                    0%, 100% {
                        opacity: 1;
                        transform: scale(1);
                    }
                    50% {
                        opacity: 0.5;
                        transform: scale(1.1);
                    }
                }
                .telegram-scrollbar::-webkit-scrollbar {
                    width: 6px;
                }
                .telegram-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .telegram-scrollbar::-webkit-scrollbar-thumb {
                    background: #c1c1c1;
                    border-radius: 10px;
                }
                .telegram-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #a8a8a8;
                }
            </style>
            <modal-window v-if="show" :width="'98%'" :height="'98%'" @close="close">
            <template #header>
                <div class="d-flex justify-content-between align-items-center w-100">
                    <h3 class="mb-0">Чат</h3>
                    <button 
                        @click="close"
                        class="btn btn-sm btn-outline-secondary"
                        title="Закрыть"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width: 20px; height: 20px;">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
            </template>
            <template #body>
                <!-- Chat Container - Telegram Style -->
                <div class="d-flex h-100 telegram-scrollbar" style="height: 100%; overflow: hidden; background: #f4f4f5;">
                    <!-- Sidebar - Telegram Style -->
                    <div style="width: 350px; display: flex; flex-direction: column; flex-shrink: 0; background: white; border-right: 1px solid #e5e5e5;">
                        <!-- Search Header -->
                        <div style="padding: 12px;">
                            <div style="position: relative;">
                                <svg style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 18px; height: 18px; color: #9ca3af;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                </svg>
                                <input 
                                    type="text" 
                                    v-model="chatSearchQuery"
                                    placeholder="Search"
                                    style="width: 100%; background: #f0f0f0; border-radius: 20px; padding: 8px 12px 8px 40px; border: none; outline: none; font-size: 14px;"
                                />
                            </div>
                        </div>
                        
                        <!-- Chat List -->
                        <div style="flex: 1; overflow-y: auto;" class="telegram-scrollbar">
                            <div 
                                v-for="c in filteredContacts"
                                :key="c.id"
                                @click="selectContact(c)"
                                :style="{
                                    padding: '12px',
                                    cursor: 'pointer',
                                    transition: 'background 0.2s',
                                    backgroundColor: selectedContactId === c.id ? '#4082bc' : 'transparent',
                                    color: selectedContactId === c.id ? 'white' : 'inherit'
                                }"
                                @mouseenter="$event.target.style.backgroundColor = selectedContactId === c.id ? '#4082bc' : '#f5f5f5'"
                                @mouseleave="$event.target.style.backgroundColor = selectedContactId === c.id ? '#4082bc' : 'transparent'"
                            >
                                <div class="d-flex align-items-center" style="gap: 12px;">
                                    <div style="position: relative; flex-shrink: 0;">
                                        <div style="width: 56px; height: 56px; border-radius: 50%; background: #dbeafe; display: flex; align-items: center; justify-content: center; color: #2563eb; font-weight: bold; overflow: hidden;">
                                            <img v-if="c.avatar" :src="c.avatar" style="width: 100%; height: 100%; object-fit: cover;" />
                                            <span v-else style="font-size: 20px;">[[ c.name.charAt(0).toUpperCase() ]]</span>
                                        </div>
                                        <div v-if="c.status === 'online'" style="position: absolute; bottom: 0; right: 0; width: 14px; height: 14px; background: #10b981; border: 2px solid white; border-radius: 50%;"></div>
                                    </div>
                                    <div style="flex: 1; min-width: 0;">
                                        <div class="d-flex align-items-center justify-content-between mb-1">
                                            <p class="mb-0 fw-semibold text-truncate" :style="{ fontSize: '15px', color: selectedContactId === c.id ? 'white' : '#212121' }">[[ c.name ]]</p>
                                            <span :style="{ fontSize: '12px', color: selectedContactId === c.id ? 'rgba(255,255,255,0.7)' : '#9ca3af' }">[[ formatTime(Date.now() - 3600000) ]]</span>
                                        </div>
                                        <p class="mb-0 text-truncate" :style="{ fontSize: '13px', color: selectedContactId === c.id ? 'rgba(255,255,255,0.8)' : '#707579' }">
                                            [[ c.isTyping ? 'печатает...' : (c.lastMessage || 'No messages yet') ]]
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Chat Area - Telegram Style -->
                    <div style="flex: 1; display: flex; flex-direction: column; background: #e7ebf0; position: relative;">
                        <!-- Background Pattern -->
                        <div style="position: absolute; inset: 0; opacity: 0.03; pointer-events: none; background-image: url('data:image/svg+xml,%3Csvg width=\'100\' height=\'100\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cdefs%3E%3Cpattern id=\'grid\' width=\'100\' height=\'100\' patternUnits=\'userSpaceOnUse\'%3E%3Cpath d=\'M 100 0 L 0 0 0 100\' fill=\'none\' stroke=\'%23d4d4d4\' stroke-width=\'0.5\' opacity=\'0.3\'/%3E%3C/pattern%3E%3C/defs%3E%3Crect width=\'100\' height=\'100\' fill=\'url(%23grid)\' /%3E%3C/svg%3E');"></div>
                        
                        <div v-if="!selectedContact" class="d-flex align-items-center justify-content-center h-100" style="color: #707579;">
                            <div class="text-center">
                                <svg style="width: 64px; height: 64px; margin: 0 auto 16px; color: #d1d5db;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                                </svg>
                                <p style="font-size: 18px;">Выберите чат для начала общения</p>
                            </div>
                        </div>

                        <template v-else>
                            <!-- Chat Header - Telegram Style -->
                            <div style="background: white; border-bottom: 1px solid #e5e5e5; padding: 8px 16px; display: flex; align-items: center; justify-content: space-between; z-index: 10; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                                <div class="d-flex align-items-center" style="gap: 12px;">
                                    <div style="width: 40px; height: 40px; border-radius: 50%; background: #dbeafe; display: flex; align-items: center; justify-content: center; color: #2563eb; font-weight: bold; overflow: hidden;">
                                        <img v-if="selectedContact.avatar" :src="selectedContact.avatar" style="width: 100%; height: 100%; object-fit: cover;" />
                                        <span v-else style="font-size: 18px;">[[ selectedContact.name.charAt(0).toUpperCase() ]]</span>
                                    </div>
                                    <div>
                                        <p class="mb-0 fw-semibold" style="font-size: 15px; color: #212121;">[[ selectedContact.name ]]</p>
                                        <p class="mb-0" :style="{ fontSize: '12px', color: selectedContact.status === 'online' ? '#4082bc' : '#707579' }">
                                            [[ selectedContact.status === 'online' ? 'online' : 'last seen recently' ]]
                                        </p>
                                    </div>
                                </div>
                                <div style="display: flex; gap: 4px; color: #707579;">
                                    <button style="padding: 8px; border: none; background: transparent; border-radius: 50%; cursor: pointer; color: #707579;" title="Search">
                                        <svg style="width: 20px; height: 20px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                        </svg>
                                    </button>
                                    <button style="padding: 8px; border: none; background: transparent; border-radius: 50%; cursor: pointer; color: #707579;" title="Phone">
                                        <svg style="width: 20px; height: 20px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path>
                                        </svg>
                                    </button>
                                    <button style="padding: 8px; border: none; background: transparent; border-radius: 50%; cursor: pointer; color: #707579;" title="More">
                                        <svg style="width: 20px; height: 20px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"></path>
                                        </svg>
                                    </button>
                                </div>
                            </div>

                            <!-- Escrow Status Panel -->
                            <div v-if="escrowData.wallet" class="bg-light border-bottom px-4 py-3" style="flex-shrink: 0;">
                                <div class="d-flex align-items-center justify-content-between" style="cursor: pointer;" @click="isStatusPanelCollapsed = !isStatusPanelCollapsed">
                                    <div class="d-flex align-items-center" style="gap: 8px;">
                                        <span style="font-size: 18px;">💼</span>
                                        <span class="fw-semibold">Статус эскроу</span>
                                    </div>
                                    <svg 
                                        style="width: 20px; height: 20px; color: #6b7280; transition: transform 0.3s;"
                                        :style="{ transform: isStatusPanelCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }"
                                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                    >
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                    </svg>
                                </div>
                                <div v-show="!isStatusPanelCollapsed" class="mt-3" style="display: flex; flex-direction: column; gap: 8px; font-size: 14px;">
                                    <div class="d-flex justify-content-between">
                                        <span class="text-muted">Кошелек эскроу:</span>
                                        <span class="font-monospace fw-semibold">[[ formatWallet(escrowData.wallet) ]]</span>
                                    </div>
                                    <div class="d-flex justify-content-between">
                                        <span class="text-muted">Баланс:</span>
                                        <span class="fw-semibold">[[ escrowData.balance ]] USDT</span>
                                    </div>
                                    <div class="d-flex justify-content-between">
                                        <span class="text-muted">Сумма:</span>
                                        <span class="fw-semibold">[[ escrowData.amount ]] USDT</span>
                                    </div>
                                    <div v-if="escrowData.guarantor" class="d-flex justify-content-between">
                                        <span class="text-muted">Гарант:</span>
                                        <span class="font-monospace fw-semibold">[[ formatWallet(escrowData.guarantor) ]]</span>
                                    </div>
                                    <div class="d-flex justify-content-between">
                                        <span class="text-muted">Статус:</span>
                                        <span :class="[
                                            'badge',
                                            escrowData.status === 'success' ? 'bg-success' :
                                            escrowData.status === 'rejected' ? 'bg-danger' :
                                            'bg-warning'
                                        ]" style="text-transform: uppercase; font-size: 11px;">
                                            [[ escrowData.status === 'success' ? 'Успешно' : escrowData.status === 'rejected' ? 'Отклонено' : 'В ожидании' ]]
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <!-- Messages - Telegram Style -->
                            <div ref="messageList" style="flex: 1; overflow-y: auto; padding: 8px 12px; z-index: 0;" class="telegram-scrollbar">
                                <div style="display: flex; flex-direction: column; gap: 4px;">
                                    <div 
                                        v-for="(m, idx) in currentMessages"
                                        :key="m.id"
                                        :style="{ 
                                            display: 'flex', 
                                            width: '100%', 
                                            justifyContent: m.sender === 'user' ? 'flex-end' : 'flex-start',
                                            marginTop: (idx > 0 && currentMessages[idx-1].sender === m.sender) ? '-4px' : '4px'
                                        }"
                                    >
                                        <div 
                                            :style="{
                                                maxWidth: (m.attachments && m.attachments.length > 0) ? '50%' : '92%',
                                                borderRadius: '12px',
                                                padding: '6px',
                                                boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                                                position: 'relative',
                                                overflow: 'hidden',
                                                backgroundColor: m.sender === 'user' ? '#effdde' : 'white',
                                                borderTopRightRadius: m.sender === 'user' ? '4px' : '12px',
                                                borderTopLeftRadius: m.sender === 'user' ? '12px' : '4px'
                                            }"
                                        >
                                            <!-- Media Grid (Telegram style album) -->
                                            <div v-if="m.attachments && m.attachments.filter(a => a.type === 'photo' || a.type === 'video').length > 0" 
                                                 :style="{
                                                     display: 'grid',
                                                     gap: '2px',
                                                     marginBottom: m.text ? '4px' : '0',
                                                     borderRadius: '8px',
                                                     overflow: 'hidden',
                                                     gridTemplateColumns: m.attachments.filter(a => a.type === 'photo' || a.type === 'video').length === 1 ? '1fr' : 'repeat(2, 1fr)'
                                                 }"
                                            >
                                                <div v-for="item in m.attachments.filter(a => a.type === 'photo' || a.type === 'video')" 
                                                     :key="item.id"
                                                     style="position: relative; aspect-ratio: 1; background: #f0f0f0; cursor: pointer;"
                                                >
                                                    <img v-if="item.type === 'photo'" 
                                                         :src="item.url" 
                                                         :alt="item.name"
                                                         style="width: 100%; height: 100%; object-fit: cover;"
                                                    />
                                                    <div v-else style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #000;">
                                                        <svg style="width: 32px; height: 32px; color: white; opacity: 0.8;" fill="currentColor" viewBox="0 0 24 24">
                                                            <path d="M8 5v14l11-7z"/>
                                                        </svg>
                                                        <span style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.5); color: white; font-size: 10px; padding: 2px 4px; border-radius: 4px;">0:15</span>
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            <!-- Documents list -->
                                            <div v-if="m.attachments && m.attachments.filter(a => a.type === 'document').length > 0" 
                                                 style="margin-bottom: 4px;"
                                            >
                                                <div v-for="doc in m.attachments.filter(a => a.type === 'document')" 
                                                     :key="doc.id"
                                                     :style="{
                                                         display: 'flex',
                                                         alignItems: 'center',
                                                         gap: '12px',
                                                         padding: '8px',
                                                         borderRadius: '8px',
                                                         backgroundColor: m.sender === 'user' ? 'rgba(0,0,0,0.05)' : '#e3f2fd',
                                                         marginBottom: '4px'
                                                     }"
                                                >
                                                    <div :style="{
                                                        width: '40px',
                                                        height: '40px',
                                                        borderRadius: '50%',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        backgroundColor: m.sender === 'user' ? '#4caf50' : '#2196f3',
                                                        color: 'white',
                                                        flexShrink: 0
                                                    }">
                                                        <svg style="width: 20px; height: 20px;" fill="currentColor" viewBox="0 0 24 24">
                                                            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                                                        </svg>
                                                    </div>
                                                    <div style="flex: 1; min-width: 0;">
                                                        <p style="font-size: 14px; font-weight: 500; margin: 0; color: #212121; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">[[ doc.name ]]</p>
                                                        <p style="font-size: 10px; margin: 0; color: #707579; text-transform: uppercase;">[[ doc.size ]]</p>
                                                    </div>
                                                    <button style="padding: 4px; border: none; background: transparent; border-radius: 50%; cursor: pointer; color: #707579;">
                                                        <svg style="width: 18px; height: 18px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                                                        </svg>
                                                    </button>
                                                </div>
                                            </div>
                                            
                                            <!-- Text and Meta -->
                                            <div style="padding: 4px 8px; position: relative; paddingBottom: 16px; minWidth: '100px';">
                                                <p v-if="m.text" style="font-size: 15px; white-space: pre-wrap; line-height: 1.4; margin: 0; color: #212121;">[[ m.text ]]</p>
                                                
                                                <!-- Signature -->
                                                <div v-if="m.signature && m.signature.startsWith('0x')" 
                                                     :style="{
                                                         marginTop: '8px',
                                                         paddingTop: '8px',
                                                         borderTop: m.sender === 'user' ? '1px solid rgba(255,255,255,0.25)' : '1px solid #e5e5e5',
                                                         fontSize: '11px',
                                                         color: m.sender === 'user' ? 'rgba(255,255,255,0.9)' : '#707579'
                                                     }"
                                                >
                                                    ✓ Подписано<br>
                                                    <span style="fontFamily: 'monospace', opacity: 0.75, fontSize: '10px';">[[ m.signature.substring(0, 20) ]]...[[ m.signature.substring(m.signature.length - 10) ]]</span>
                                                </div>
                                                
                                                <!-- Sign button -->
                                                <div v-if="m.sender === 'user' && isAuthenticated && (!m.signature || !m.signature.startsWith('0x'))" style="marginTop: 8px;">
                                                    <button 
                                                        @click="handleSignExistingMessage(m)"
                                                        :style="{
                                                            fontSize: '11px',
                                                            padding: '2px 8px',
                                                            border: 'none',
                                                            borderRadius: '4px',
                                                            background: m.sender === 'user' ? 'rgba(255,255,255,0.9)' : '#f0f0f0',
                                                            color: '#212121',
                                                            cursor: 'pointer'
                                                        }"
                                                        title="Подписать сообщение"
                                                    >
                                                        🔐 Подписать
                                                    </button>
                                                </div>
                                                
                                                <!-- Timestamp and Status -->
                                                <div :style="{
                                                    position: 'absolute',
                                                    bottom: '4px',
                                                    right: '8px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px',
                                                    userSelect: 'none'
                                                }">
                                                    <span :style="{
                                                        fontSize: '10px',
                                                        color: m.sender === 'user' ? 'rgba(0,0,0,0.5)' : '#707579'
                                                    }">[[ formatTime(m.timestamp) ]]</span>
                                                    <span v-if="m.sender === 'user'" :style="{ color: '#4caf50' }">
                                                        <svg v-if="m.status === 'read'" style="width: 14px; height: 14px;" fill="currentColor" viewBox="0 0 24 24">
                                                            <path d="M9,20.42L2.79,14.21L5.62,11.38L9,14.77L18.88,4.88L21.71,7.71L9,20.42Z"/>
                                                        </svg>
                                                        <svg v-else style="width: 14px; height: 14px;" fill="currentColor" viewBox="0 0 24 24">
                                                            <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/>
                                                        </svg>
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Chat Input - Telegram Style -->
                            <div style="background: white; border-top: 1px solid #e5e5e5; padding: 12px; z-index: 10;">
                                <div>
                                    <!-- Pending Attachments Preview (Grouped) -->
                                    <div v-if="pendingAttachments.length > 0" 
                                         style="display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; background: #f5f5f5; padding: 12px; border-radius: 8px; border: 1px solid #e5e5e5;"
                                    >
                                        <div v-for="att in pendingAttachments" 
                                             :key="att.id"
                                             style="position: relative; background: white; padding: 6px; border-radius: 4px; border: 1px solid #e5e5e5; box-shadow: 0 1px 2px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 8px;"
                                        >
                                            <img v-if="att.type === 'photo'" 
                                                 :src="att.url" 
                                                 style="width: 48px; height: 48px; object-fit: cover; border-radius: 4px;"
                                            />
                                            <div v-else-if="att.type === 'video'" 
                                                 style="width: 48px; height: 48px; background: #000; border-radius: 4px; display: flex; align-items: center; justify-content: center;"
                                            >
                                                <svg style="width: 20px; height: 20px; color: white;" fill="currentColor" viewBox="0 0 24 24">
                                                    <path d="M8 5v14l11-7z"/>
                                                </svg>
                                            </div>
                                            <div v-else 
                                                 style="width: 48px; height: 48px; background: #e3f2fd; border-radius: 4px; display: flex; align-items: center; justify-content: center;"
                                            >
                                                <svg style="width: 20px; height: 20px; color: #2196f3;" fill="currentColor" viewBox="0 0 24 24">
                                                    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                                                </svg>
                                            </div>
                                            <div style="max-width: 100px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">
                                                <p style="font-size: 10px; font-weight: 500; margin: 0; color: #212121;">[[ att.name ]]</p>
                                                <p style="font-size: 9px; margin: 0; color: #707579;">[[ att.size ]]</p>
                                            </div>
                                            <button 
                                                @click="removePendingAttachment(att.id)"
                                                style="position: absolute; top: -8px; right: -8px; background: #ef5350; color: white; border: none; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.2); padding: 0;"
                                                title="Удалить"
                                            >
                                                <svg style="width: 12px; height: 12px;" fill="currentColor" viewBox="0 0 24 24">
                                                    <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"/>
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                    
                                    <form @submit.prevent="handleSend" style="display: flex; align-items: flex-end; gap: 8px;">
                                        <div style="display: flex; align-items: center; gap: 4px;">
                                            <button 
                                                type="button"
                                                @click="$refs.fileInput.click()"
                                                style="padding: 8px; border: none; background: transparent; border-radius: 50%; cursor: pointer; color: #707579; transition: all 0.2s;"
                                                :style="{ color: '#4082bc', backgroundColor: '#e3f2fd' }"
                                                onmouseover="this.style.backgroundColor='#bbdefb'"
                                                onmouseout="this.style.backgroundColor='#e3f2fd'"
                                                title="Прикрепить файл"
                                            >
                                                <svg style="width: 22px; height: 22px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path>
                                                </svg>
                                            </button>
                                            <input 
                                                type="file" 
                                                ref="fileInput"
                                                @change="handleFileSelect"
                                                multiple
                                                accept="image/*,video/*,.pdf,.doc,.docx,.txt"
                                                style="display: none;"
                                            />
                                            
                                        </div>
                                        
                                        <div style="flex: 1; background: #f0f0f0; border-radius: 24px; display: flex; align-items: flex-end; padding: 4px; min-height: 44px; position: relative;">
                                            <textarea
                                                v-model="chatInputText"
                                                @input="clearPendingSignatureIfTextChanged; adjustTextareaHeight()"
                                                @keydown.enter.exact.prevent="handleSend"
                                                @keydown.enter.shift.exact=""
                                                placeholder="Message"
                                                style="width: 100%; background: transparent; border: none; outline: none; padding: 8px 12px; resize: none; max-height: 128px; font-size: 15px; color: #212121; font-family: inherit; overflow-y: auto;"
                                                rows="1"
                                                ref="textareaInput"
                                            ></textarea>
                                            <div style="position: relative;">
                                                <button 
                                                    type="button"
                                                    @click.stop="toggleEmojiPicker"
                                                    style="padding: 8px; border: none; background: transparent; border-radius: 50%; cursor: pointer; color: #707579;"
                                                    title="Emoji"
                                                >
                                                    😊
                                                </button>
                                                
                                                <!-- Emoji Picker -->
                                                <div v-if="showEmojiPicker" 
                                                     ref="emojiPicker"
                                                     style="position: absolute; bottom: calc(100% + 8px); right: 0; background: white; border: 1px solid #e5e5e5; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); width: 320px; max-height: 300px; overflow-y: auto; z-index: 1000; padding: 12px;"
                                                     class="telegram-scrollbar"
                                                     @click.stop
                                                >
                                                <div v-for="(emojis, category) in emojiCategories" :key="category" style="margin-bottom: 12px;">
                                                    <div style="font-size: 11px; font-weight: 600; color: #707579; margin-bottom: 8px; text-transform: uppercase;">[[ category ]]</div>
                                                    <div style="display: grid; grid-template-columns: repeat(8, 1fr); gap: 4px;">
                                                        <button 
                                                            v-for="emoji in emojis" 
                                                            :key="emoji"
                                                            @click="insertEmoji(emoji)"
                                                            style="padding: 8px; border: none; background: transparent; border-radius: 6px; cursor: pointer; font-size: 20px; transition: background 0.2s;"
                                                            @mouseenter="$event.target.style.backgroundColor = '#f0f0f0'"
                                                            @mouseleave="$event.target.style.backgroundColor = 'transparent'"
                                                            :title="emoji"
                                                        >
                                                            [[ emoji ]]
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        
                                        <button 
                                            type="submit"
                                            :disabled="!chatInputText.trim() && pendingAttachments.length === 0"
                                            :style="{
                                                padding: '12px',
                                                borderRadius: '50%',
                                                border: 'none',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                transition: 'all 0.2s',
                                                backgroundColor: (chatInputText.trim() || pendingAttachments.length > 0) ? '#4082bc' : '#c1c1c1',
                                                color: 'white',
                                                cursor: (chatInputText.trim() || pendingAttachments.length > 0) ? 'pointer' : 'not-allowed',
                                                boxShadow: (chatInputText.trim() || pendingAttachments.length > 0) ? '0 2px 4px rgba(64,130,188,0.3)' : 'none'
                                            }"
                                            title="Отправить"
                                        >
                                            <svg style="width: 22px; height: 22px; margin-left: 2px;" fill="currentColor" viewBox="0 0 24 24">
                                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                                            </svg>
                                        </button>
                                    </form>
                                </div>
                            </div>
                        </template>
                    </div>
                </div>
            </template>
        </modal-window>
        </div>
    `
});

