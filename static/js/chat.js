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
        },
        currentUserDid: {
            type: String,
            default: null
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
            loadingAttachments: {}, // Tracks loading state: {messageUuid_attachmentId: true}
            isUserAtBottom: true, // Track if user is at the bottom of chat
            isInitialHistoryLoad: false, // Track if this is the first history load
            visibleDownloadButton: null, // Tracks which image download button is visible
            isMobileDevice: false, // Track if device is mobile
            showSidebarOnMobile: true, // Show sidebar or chat area on mobile devices
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
        },
        shouldShowSidebar() {
            if (!this.isMobileDevice) return true;
            return this.showSidebarOnMobile || !this.selectedContact;
        },
        shouldShowChatArea() {
            if (!this.isMobileDevice) return true;
            return !this.showSidebarOnMobile && this.selectedContact;
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
        // Detect mobile device
        this.detectMobileDevice();
        window.addEventListener('resize', this.detectMobileDevice);
        
        // Close emoji picker when clicking outside
        this.$nextTick(() => {
            document.addEventListener('click', this.handleClickOutside);
        });
    },
    beforeDestroy() {
        window.removeEventListener('resize', this.detectMobileDevice);
        document.removeEventListener('click', this.handleClickOutside);
    },
    methods: {
        close() {
            // Reset mobile state when closing
            if (this.isMobileDevice) {
                this.showSidebarOnMobile = true;
            }
            this.$emit('close');
        },
        initChat() {
            if (!this.messages['gemini']) {
                this.$set(this.messages, 'gemini', [
                    {
                        uuid: 'init',
                        text: 'Привет! Как я могу помочь вам?',
                        sender: 'their',
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
        send_text_message(text, contactId = null, emitEvent = false) {
            const targetContactId = contactId || this.selectedContactId;
            // Allow sending if there's text OR pending attachments
            if ((!text || text.trim() === '') && this.pendingAttachments.length === 0) return;
            if (!targetContactId) return;
            
            const contact = this.contacts.find(c => c.id === targetContactId);
            if (!contact) return;
            
            const cid = targetContactId;
            const ts = Date.now();
            
            // Generate UUID for the message
            const messageUuid = this.generateUuid();
            
            // Use empty string if no text but there are attachments
            const messageText = text || '';
            
            const userMsg = {
                uuid: messageUuid,
                text: messageText,
                sender: 'mine',
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
            
            // Emit event only if requested (to avoid circular calls)
            if (emitEvent) {
                this.$emit('on_send_text_message', {
                    text: messageText,
                    contactId: targetContactId,
                    messageUuid: userMsg.uuid,
                    timestamp: ts,
                    attachments: attachmentsToEmit.length > 0 ? attachmentsToEmit : undefined
                });
            }
            
            return userMsg; // Return created message for convenience
        },
        
        send_documents_with_data(text, attachments) {
            const targetContactId = this.selectedContactId;
            if (!targetContactId) return;
            
            const contact = this.contacts.find(c => c.id === targetContactId);
            if (!contact) return;
            
            const cid = targetContactId;
            const ts = Date.now();
            
            // Generate UUID for message
            const messageUuid = this.generateUuid();
            
            console.log('=== send_documents_with_data ===');
            console.log('Text:', text);
            console.log('Attachments:', attachments);
            console.log('Contact ID:', targetContactId);
            
            const userMsg = {
                uuid: messageUuid,
                text: text || '',
                sender: 'mine',
                timestamp: ts,
                status: 'sent',
                signature: null,
                attachments: attachments.length > 0 ? [...attachments] : undefined
            };
            
            console.log('Created message:', userMsg);
            
            // Add message to conversation
            if (!this.messages[cid]) {
                this.$set(this.messages, cid, []);
            }
            this.messages[cid].push(userMsg);
            
            // Update last message preview
            contact.lastMessage = text || `${attachments.length} файл(ов)`;
            
            console.log('Messages after push:', this.messages[cid]);
            console.log('Total messages:', this.messages[cid].length);
            
            // Scroll to bottom after adding message
            this.$nextTick(this.scrollToBottom);
            
            // Emit on_send_documents event
            this.$emit('on_send_documents', {
                messageUuid: messageUuid,
                text: text || null,
                attachments: attachments,
                contactId: targetContactId,
                timestamp: ts
            });
            
            return userMsg;
        },
        
        send_documents(files, contactId = null, emitEvent = false) {
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
            
            // Emit event only if requested (to avoid circular calls)
            if (emitEvent) {
                this.$emit('on_send_documents', {
                    files: Array.from(files),
                    contactId: targetContactId,
                    timestamp: Date.now()
                });
            }
            
            return newAttachments; // Return created attachments for convenience
        },
        
        sign(messageUuid, text = null) {
            if (!messageUuid) {
                // Sign current input text
                if (!this.chatInputText.trim()) {
                    return;
                }
                this.isSigning = true;
                this.$emit('on_sign', {
                    type: 'input',
                    text: this.chatInputText.trim(),
                    messageUuid: null
                });
                return;
            }
            
            // Sign existing message
            const message = this.findMessageByUuid(messageUuid);
            if (!message) return;
            
            if (message.signature && message.signature.startsWith('0x')) {
                return; // Already signed
            }
            
            this.isSigning = true;
            const textToSign = text || message.text;
            
            this.$emit('on_sign', {
                type: 'message',
                text: textToSign,
                messageUuid: messageUuid,
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
        
        // Public method to set chat history
        set_history(history) {
            if (!history || !Array.isArray(history)) {
                console.warn('Chat.set_history: history must be an array');
                return;
            }
            
            // Mark as initial history load
            this.isInitialHistoryLoad = true;
            
            // Clear existing messages
            this.messages = {};
            
            // Group messages by conversationId
            const messagesByContact = {};
            
            history.forEach(msg => {
                const conversationId = msg.conversation_id;
                
                // Skip messages without conversation_id
                if (!conversationId) {
                    console.warn('Message without conversation_id:', msg);
                    return;
                }
                
                if (!messagesByContact[conversationId]) {
                    messagesByContact[conversationId] = [];
                }
                
                // Determine sender type based on sender_id
                let senderType = 'their';
                if (msg.sender_id && this.currentUserDid && msg.sender_id === this.currentUserDid) {
                    senderType = 'mine';
                } else if (msg.sender_id && this.currentUserDid && msg.sender_id !== this.currentUserDid) {
                    senderType = 'their';  // Собеседник
                }
                
                // Convert history message to chat message format
                const chatMessage = {
                    uuid: msg.uuid || msg.id || msg.messageId || this.generateUuid(),
                    text: msg.text || msg.message || '',
                    sender: senderType,
                    timestamp: msg.timestamp || (msg.created_at ? new Date(msg.created_at).getTime() : Date.now()),
                    status: msg.status || 'sent',
                    signature: msg.signature ? msg.signature.signature : null,
                    type: msg.message_type || msg.type || 'text',
                    attachments: msg.attachments || undefined
                };
                
                messagesByContact[conversationId].push(chatMessage);
            });
            
            // Sort messages by timestamp and set them
            Object.keys(messagesByContact).forEach(conversationId => {
                messagesByContact[conversationId].sort((a, b) => a.timestamp - b.timestamp);
                this.$set(this.messages, conversationId, messagesByContact[conversationId]);
            });
            
            // Create or update contacts from history
            Object.keys(messagesByContact).forEach(conversationId => {
                let contact = this.contacts.find(c => c.id === conversationId);
                
                if (!contact) {
                    // Find contact info from first message
                    const firstMsg = history.find(m => m.conversation_id === conversationId);
                    // Create new contact if it doesn't exist
                    contact = {
                        id: conversationId,
                        name: (firstMsg && firstMsg.contactName) || `Contact ${conversationId}`,
                        avatar: (firstMsg && firstMsg.contactAvatar) || null,
                        status: 'online',
                        lastMessage: '',
                        isTyping: false
                    };
                    this.contacts.push(contact);
                }
                
                // Update last message
                if (messagesByContact[conversationId].length > 0) {
                    const lastMsg = messagesByContact[conversationId][messagesByContact[conversationId].length - 1];
                    contact.lastMessage = lastMsg.text.substring(0, 50);
                }
            });
            
            // Auto-select first contact if none selected and history exists
            this.$nextTick(() => {
                const conversationIds = Object.keys(messagesByContact);
                if (conversationIds.length > 0 && !this.selectedContactId) {
                    // Select first contact
                    const firstConversationId = conversationIds[0];
                    const contact = this.contacts.find(c => c.id === firstConversationId);
                    if (contact) {
                        this.selectContact(contact);
                    }
                } else if (this.selectedContactId) {
                    this.scrollToBottom();
                }
                
                // Auto-load attachment data for all attachments without data
                this.autoLoadAttachments();
                
                // Reset initial load flag after scrolling
                setTimeout(() => {
                    this.isInitialHistoryLoad = false;
                }, 1000);
            });
        },
        
        // Helper methods
        findMessageByUuid(messageUuid) {
            for (const conversationId in this.messages) {
                const message = this.messages[conversationId].find(m => m.uuid === messageUuid);
                if (message) return message;
            }
            return null;
        },
        
        generateUuid() {
            // Generate UUID v4 (random)
            if (typeof crypto !== 'undefined' && crypto.randomUUID) {
                return crypto.randomUUID();
            }
            // Fallback for older browsers
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        },
        
        async downloadAttachment(messageUuid, attachmentId, attachmentName, mimeType) {
            try {
                // Emit event and let parent handle the download
                const attachmentData = await new Promise((resolve, reject) => {
                    this.$emit('on_download_attachment', {
                        messageUuid: messageUuid,
                        attachmentId: attachmentId,
                        attachmentName: attachmentName,
                        mimeType: mimeType,
                        resolve: resolve,
                        reject: reject
                    });
                });
                
                // Convert base64 to Blob and download
                const byteCharacters = atob(attachmentData.data);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: mimeType || attachmentData.mime_type });
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = attachmentName || attachmentData.name;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
            } catch (error) {
                console.error('Error downloading attachment:', error);
                alert('Ошибка загрузки файла');
            }
        },
        
        async handleDownloadDocument(messageUuid, attachment) {
            try {
                // If attachment doesn't have data yet, load it first
                if (!attachment.data) {
                    await this.loadAttachmentData(messageUuid, attachment);
                }
                
                // Now download the attachment (data should be available)
                if (attachment.data) {
                    // Convert base64 to Blob and download
                    const byteCharacters = atob(attachment.data);
                    const byteNumbers = new Array(byteCharacters.length);
                    for (let i = 0; i < byteCharacters.length; i++) {
                        byteNumbers[i] = byteCharacters.charCodeAt(i);
                    }
                    const byteArray = new Uint8Array(byteNumbers);
                    const blob = new Blob([byteArray], { type: attachment.mime_type });
                    
                    // Create download link
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = attachment.name;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }
            } catch (error) {
                console.error('Error downloading document:', error);
                alert('Ошибка скачивания документа');
            }
        },
        
        async loadAttachmentData(messageUuid, attachment) {
            const loadingKey = `${messageUuid}_${attachment.id}`;
            
            // Skip if already loading or has data
            if (this.loadingAttachments[loadingKey] || attachment.data) {
                return;
            }
            
            try {
                this.$set(this.loadingAttachments, loadingKey, true);
                
                // Emit event and wait for parent to provide data
                const attachmentData = await new Promise((resolve, reject) => {
                    this.$emit('on_load_attachment', {
                        messageUuid: messageUuid,
                        attachmentId: attachment.id,
                        attachment: attachment,
                        resolve: resolve,
                        reject: reject
                    });
                });
                
                // Update attachment in message with loaded data
                this.$set(attachment, 'data', attachmentData.data);
                
                // If it's a photo, create data URL for display
                if (attachment.type === 'photo' && attachmentData.data) {
                    const dataUrl = `data:${attachmentData.mime_type || attachment.mime_type};base64,${attachmentData.data}`;
                    this.$set(attachment, 'url', dataUrl);
                    
                    // Scroll to bottom if user was at bottom (image loaded, height changed)
                    this.$nextTick(() => {
                        this.scrollToBottomIfNeeded();
                    });
                }
                
            } catch (error) {
                console.error('Error loading attachment data:', error);
                alert('Ошибка загрузки вложения');
            } finally {
                this.$set(this.loadingAttachments, loadingKey, false);
            }
        },
        
        async autoLoadAttachments() {
            // Automatically load attachment data for all attachments without data
            const loadPromises = [];
            
            for (const conversationId in this.messages) {
                const messages = this.messages[conversationId];
                
                for (const message of messages) {
                    if (message.attachments && Array.isArray(message.attachments)) {
                        for (const attachment of message.attachments) {
                            // Load attachment data if it doesn't have data yet
                            if (!attachment.data) {
                                loadPromises.push(
                                    this.loadAttachmentData(message.uuid, attachment)
                                );
                            }
                        }
                    }
                }
            }
            
            // Load all attachments in parallel (with reasonable limit)
            if (loadPromises.length > 0) {
                console.log(`Auto-loading ${loadPromises.length} attachments...`);
                
                // Load in batches to avoid overwhelming the server
                const batchSize = 5;
                for (let i = 0; i < loadPromises.length; i += batchSize) {
                    const batch = loadPromises.slice(i, i + batchSize);
                    await Promise.allSettled(batch);
                    
                    // Scroll to bottom after each batch if user was at bottom
                    this.$nextTick(() => {
                        this.scrollToBottomIfNeeded();
                    });
                }
                
                console.log('All attachments loaded');
                
                // Final scroll to ensure we're at the bottom
                this.$nextTick(() => {
                    this.scrollToBottomIfNeeded();
                });
            }
        },
        
        // Internal methods
        selectContact(contact) {
            this.selectedContactId = contact.id;
            if (!this.messages[contact.id]) {
                this.$set(this.messages, contact.id, []);
            }
            // On mobile, hide sidebar and show chat area when contact is selected
            if (this.isMobileDevice) {
                this.showSidebarOnMobile = false;
            }
            this.$nextTick(this.scrollToBottom);
        },
        detectMobileDevice() {
            this.isMobileDevice = window.innerWidth < 768 || 
                                  (window.innerHeight > window.innerWidth && window.innerWidth < 1024);
        },
        goBackToContacts() {
            if (this.isMobileDevice) {
                this.showSidebarOnMobile = true;
            }
        },
        formatTime(ts) {
            return new Date(ts).toLocaleTimeString('ru-RU', {
                hour: '2-digit',
                minute: '2-digit'
            });
        },
        formatFileSize(bytes) {
            if (!bytes) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 10) / 10 + ' ' + sizes[i];
        },
        getImageContainerStyle(item) {
            // Calculate optimal aspect ratio and size for image container
            const style = {
                position: 'relative',
                background: '#f0f0f0',
                cursor: 'pointer'
            };
            
            if (item.width && item.height) {
                // Use actual aspect ratio if dimensions are available
                style.aspectRatio = `${item.width}/${item.height}`;
                // Limit height to reasonable maximum
                const maxHeight = 400;
                if (item.height > maxHeight) {
                    style.maxHeight = `${maxHeight}px`;
                } else {
                    style.minHeight = `${item.height}px`;
                }
            } else if (item.type === 'video') {
                // Default 16:9 for videos
                style.aspectRatio = '16/9';
                style.minHeight = '200px';
            } else {
                // Default square for photos without dimensions
                style.aspectRatio = '1';
                style.minHeight = '200px';
            }
            
            return style;
        },
        scrollToBottom() {
            const el = this.$refs.messageList;
            if (el) {
                el.scrollTop = el.scrollHeight;
                this.isUserAtBottom = true;
            }
        },
        checkIfUserAtBottom() {
            // Check if user is scrolled to the bottom (with 50px threshold)
            const el = this.$refs.messageList;
            if (!el) return true;
            
            const threshold = 50;
            const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
            this.isUserAtBottom = isAtBottom;
            return isAtBottom;
        },
        scrollToBottomIfNeeded() {
            // Scroll to bottom only if user is already at bottom or it's initial load
            if (this.isUserAtBottom || this.isInitialHistoryLoad) {
                this.$nextTick(() => {
                    this.scrollToBottom();
                });
            }
        },
        handleScroll() {
            // Track user scroll position
            this.checkIfUserAtBottom();
        },
        handleImageClick(messageUuid, item) {
            // If no data - load it
            if (!item.data) {
                this.loadAttachmentData(messageUuid, item);
                return;
            }
            
            // If data exists - show download button for 3 seconds
            const key = messageUuid + '_' + item.id;
            this.visibleDownloadButton = key;
            
            setTimeout(() => {
                if (this.visibleDownloadButton === key) {
                    this.visibleDownloadButton = null;
                }
            }, 3000);
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
            }
            // Reset input
            event.target.value = '';
        },
        
        // Remove pending attachment
        removePendingAttachment(id) {
            this.pendingAttachments = this.pendingAttachments.filter(a => a.id !== id);
        },
        
        // Handle send button click
        async handleSend() {
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
            
            // Обработать attachments с base64, если есть
            let processedAttachments = null;
            if (this.pendingAttachments.length > 0) {
                processedAttachments = await Promise.all(
                    this.pendingAttachments.map(async (att) => {
                        // Конвертируем файл в base64
                        const base64Data = await new Promise((resolve, reject) => {
                            const reader = new FileReader();
                            reader.onload = () => {
                                const base64 = reader.result.split(',')[1];
                                resolve(base64);
                            };
                            reader.onerror = reject;
                            reader.readAsDataURL(att.file);
                        });
                        
                        const processed = {
                            id: att.id,
                            type: att.type,
                            name: att.name,
                            size: att.file.size,
                            mime_type: att.file.type,
                            data: base64Data
                        };
                        
                        // Для фото добавляем url и получаем размеры
                        if (att.type === 'photo') {
                            const dataUrl = `data:${att.file.type};base64,${base64Data}`;
                            processed.url = dataUrl;
                            
                            // Получаем размеры изображения
                            try {
                                const dimensions = await new Promise((resolve, reject) => {
                                    const img = new Image();
                                    img.onload = () => {
                                        resolve({ width: img.width, height: img.height });
                                    };
                                    img.onerror = reject;
                                    img.src = dataUrl;
                                });
                                processed.width = dimensions.width;
                                processed.height = dimensions.height;
                            } catch (e) {
                                console.error('Failed to get image dimensions:', e);
                            }
                        } else if (att.type === 'video') {
                            processed.url = `data:${att.file.type};base64,${base64Data}`;
                        }
                        
                        return processed;
                    })
                );
                
                // Очистить pendingAttachments после обработки
                this.pendingAttachments = [];
            }
            
            // ПЕРЕКЛЮЧАТЕЛЬ: если есть attachments -> on_send_documents, иначе -> on_send_text_message
            if (processedAttachments && processedAttachments.length > 0) {
                // Есть файлы - вызвать send_documents_with_data
                console.log('=== handleSend: calling send_documents_with_data ===');
                console.log('Processed attachments:', processedAttachments);
                this.send_documents_with_data(messageText, processedAttachments);
            } else {
                // Только текст - вызвать send_text_message
                this.send_text_message(messageText, null, true);
            }
            
            // If there was a signature, attach it to the last message
            if (signature) {
                const contact = this.selectedContact;
                const cid = contact.id;
                if (this.messages[cid] && this.messages[cid].length > 0) {
                    const lastMsg = this.messages[cid][this.messages[cid].length - 1];
                    if (lastMsg.sender === 'mine') {
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
            this.sign(message.uuid, message.text);
        },
        
        // Handle signature result from parent
        onSignatureResult(messageUuid, signature) {
            this.isSigning = false;
            
            if (messageUuid) {
                const message = this.findMessageByUuid(messageUuid);
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
                    <div v-show="shouldShowSidebar" 
                         :style="{
                             width: isMobileDevice ? '100%' : '350px',
                             display: 'flex',
                             flexDirection: 'column',
                             flexShrink: 0,
                             background: 'white',
                             borderRight: isMobileDevice ? 'none' : '1px solid #e5e5e5'
                         }">
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
                    <div v-show="shouldShowChatArea || !isMobileDevice"
                         style="flex: 1; display: flex; flex-direction: column; background: #e7ebf0; position: relative; width: 100%;">
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
                                    <!-- Back button for mobile -->
                                    <button v-if="isMobileDevice"
                                            @click="goBackToContacts"
                                            style="padding: 8px; border: none; background: transparent; border-radius: 50%; cursor: pointer; color: #707579; margin-right: 4px; display: flex; align-items: center; justify-content: center;"
                                            title="Назад к списку"
                                    >
                                        <svg style="width: 24px; height: 24px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                                        </svg>
                                    </button>
                                    <div style="width: 40px; height: 40px; border-radius: 50%; background: #dbeafe; display: flex; align-items: center; justify-content: center; color: #2563eb; font-weight: bold; overflow: hidden;">
                                        <img v-if="selectedContact.avatar" :src="selectedContact.avatar" style="width: 100%; height: 100%; object-fit: cover;" />
                                        <span v-else style="font-size: 18px;">[[ selectedContact.name.charAt(0).toUpperCase() ]]</span>
                                    </div>
                                    <div>
                                        <p class="mb-0 fw-semibold" style="font-size: 15px; color: #212121; display: flex; align-items: center; gap: 8px;">
                                            <span>[[ selectedContact.name ]]</span>
                                            <span v-if="selectedContact.did" style="font-size: 12px; color: #707579; font-weight: normal;">
                                                [[ selectedContact.did ]]
                                            </span>
                                        </p>
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

                            <!-- Custom Header Addon Slot -->
                            <slot name="chat-header-addon"></slot>

                            <!-- Messages - Telegram Style -->
                            <div ref="messageList" @scroll="handleScroll" style="flex: 1; overflow-y: auto; padding: 8px 12px; z-index: 0;" class="telegram-scrollbar">
                                <div style="display: flex; flex-direction: column; gap: 4px;">
                                    <div 
                                        v-for="(m, idx) in currentMessages"
                                        :key="m.uuid"
                                        :style="{ 
                                            display: 'flex', 
                                            width: '100%', 
                                            justifyContent: m.sender === 'mine' ? 'flex-end' : 'flex-start',
                                            marginTop: (idx > 0 && currentMessages[idx-1].sender === m.sender) ? '2px' : '4px'
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
                                                backgroundColor: m.sender === 'mine' 
                                                    ? '#effdde' 
                                                    : (m.attachments && m.attachments.length > 0 ? '#e8e8e8' : 'white'),
                                                borderTopRightRadius: m.sender === 'mine' ? '4px' : '12px',
                                                borderTopLeftRadius: m.sender === 'mine' ? '12px' : '4px'
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
                                                     :style="Object.assign({}, getImageContainerStyle(item), { position: 'relative', cursor: 'pointer' })"
                                                     @click="handleImageClick(m.uuid, item)"
                                                     class="image-container"
                                                >
                                                    <!-- Loading indicator -->
                                                    <div v-if="loadingAttachments[m.uuid + '_' + item.id]" 
                                                         style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.05);">
                                                        <svg style="width: 24px; height: 24px; color: #666; animation: spin 1s linear infinite;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                                                        </svg>
                                                    </div>
                                                    <!-- Image with data -->
                                                    <img v-else-if="item.type === 'photo' && item.url" 
                                                         :src="item.url" 
                                                         :alt="item.name"
                                                         style="width: 100%; height: 100%; object-fit: cover; display: block;"
                                                    />
                                                    <!-- Download button for images (appears on hover/click) -->
                                                    <button v-if="item.type === 'photo' && item.data"
                                                            @click.stop="handleDownloadDocument(m.uuid, item)"
                                                            class="image-download-btn"
                                                            :class="{ 'button-visible': visibleDownloadButton === m.uuid + '_' + item.id }"
                                                            :style="{
                                                                position: 'absolute',
                                                                top: '50%',
                                                                left: '50%',
                                                                transform: 'translate(-50%, -50%)',
                                                                width: '48px',
                                                                height: '48px',
                                                                borderRadius: '50%',
                                                                border: 'none',
                                                                background: 'rgba(0, 0, 0, 0.6)',
                                                                color: 'white',
                                                                cursor: 'pointer',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                justifyContent: 'center',
                                                                opacity: '0',
                                                                transition: 'opacity 0.2s, background 0.2s, transform 0.2s',
                                                                zIndex: '10'
                                                            }"
                                                            @mouseenter="$event.target.style.background = 'rgba(0, 0, 0, 0.8)'"
                                                            @mouseleave="$event.target.style.background = 'rgba(0, 0, 0, 0.6)'"
                                                            title="Скачать изображение"
                                                    >
                                                        <svg style="width: 20px; height: 20px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                                                        </svg>
                                                    </button>
                                                    <!-- Placeholder if no data -->
                                                    <div v-else-if="item.type === 'photo' && !item.data" 
                                                         style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; flex-direction: column; gap: 8px; background: #e5e5e5;">
                                                        <svg style="width: 32px; height: 32px; color: #999;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                                                        </svg>
                                                        <span style="font-size: 11px; color: #666;">Нажмите для загрузки</span>
                                                    </div>
                                                    <!-- Video placeholder -->
                                                    <div v-else style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #000;">
                                                        <svg style="width: 32px; height: 32px; color: white; opacity: 0.8;" fill="currentColor" viewBox="0 0 24 24">
                                                            <path d="M8 5v14l11-7z"/>
                                                        </svg>
                                                        <span v-if="!item.data" style="position: absolute; top: 8px; left: 8px; background: rgba(0,0,0,0.5); color: white; font-size: 10px; padding: 2px 4px; border-radius: 4px;">Нажмите для загрузки</span>
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
                                                         backgroundColor: m.sender === 'mine' ? 'rgba(0,0,0,0.05)' : '#e3f2fd',
                                                         marginBottom: '4px',
                                                         minHeight: '56px'
                                                     }"
                                                >
                                                    <div :style="{
                                                        width: '40px',
                                                        height: '40px',
                                                        borderRadius: '50%',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        backgroundColor: m.sender === 'mine' ? '#4caf50' : '#2196f3',
                                                        color: 'white',
                                                        flexShrink: 0
                                                    }">
                                                        <svg style="width: 20px; height: 20px;" fill="currentColor" viewBox="0 0 24 24">
                                                            <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"/>
                                                        </svg>
                                                    </div>
                                                    <div style="flex: 1; min-width: 0;">
                                                        <p style="font-size: 14px; font-weight: 500; margin: 0; color: #212121; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">[[ doc.name ]]</p>
                                                        <p style="font-size: 10px; margin: 0; color: #707579; text-transform: uppercase;">[[ formatFileSize(doc.size) ]]</p>
                                                    </div>
                                                    <!-- Download button -->
                                                    <button 
                                                        @click="handleDownloadDocument(m.uuid, doc)"
                                                        :disabled="loadingAttachments[m.uuid + '_' + doc.id]"
                                                        :style="{
                                                            padding: '4px',
                                                            border: 'none',
                                                            background: 'transparent',
                                                            borderRadius: '50%',
                                                            cursor: loadingAttachments[m.uuid + '_' + doc.id] ? 'wait' : 'pointer',
                                                            color: '#707579',
                                                            opacity: loadingAttachments[m.uuid + '_' + doc.id] ? 0.5 : 1
                                                        }"
                                                    >
                                                        <!-- Loading spinner -->
                                                        <svg v-if="loadingAttachments[m.uuid + '_' + doc.id]" style="width: 18px; height: 18px; animation: spin 1s linear infinite;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                                                        </svg>
                                                        <!-- Download icon -->
                                                        <svg v-else style="width: 18px; height: 18px;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                                                        </svg>
                                                    </button>
                                                </div>
                                            </div>
                                            
                                            <!-- Text and Meta -->
                                            <div style="padding: 4px 8px; padding-bottom: 20px; position: relative; min-width: 100px;">
                                                <p v-if="m.text" style="font-size: 15px; white-space: pre-wrap; line-height: 1.4; margin: 0; padding-right: 50px; color: #212121;">[[ m.text ]]</p>
                                                
                                                <!-- Signature -->
                                                <div v-if="m.signature && m.signature.startsWith('0x')" 
                                                     :style="{
                                                         marginTop: '8px',
                                                         paddingTop: '8px',
                                                         borderTop: m.sender === 'mine' ? '1px solid rgba(255,255,255,0.25)' : '1px solid #e5e5e5',
                                                         fontSize: '11px',
                                                         color: m.sender === 'mine' ? 'rgba(255,255,255,0.9)' : '#707579'
                                                     }"
                                                >
                                                    ✓ Подписано<br>
                                                    <span style="fontFamily: 'monospace', opacity: 0.75, fontSize: '10px';">[[ m.signature.substring(0, 20) ]]...[[ m.signature.substring(m.signature.length - 10) ]]</span>
                                                </div>
                                                
                                                <!-- Sign button -->
                                                <div v-if="m.sender === 'mine' && isAuthenticated && (!m.signature || !m.signature.startsWith('0x'))" style="marginTop: 8px;">
                                                    <button 
                                                        @click="handleSignExistingMessage(m)"
                                                        :style="{
                                                            fontSize: '11px',
                                                            padding: '2px 8px',
                                                            border: 'none',
                                                            borderRadius: '4px',
                                                            background: m.sender === 'mine' ? 'rgba(255,255,255,0.9)' : '#f0f0f0',
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
                                                    bottom: '6px',
                                                    right: '10px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '4px',
                                                    userSelect: 'none',
                                                    whiteSpace: 'nowrap'
                                                }">
                                                    <span :style="{
                                                        fontSize: '11px',
                                                        color: m.sender === 'mine' ? 'rgba(0,0,0,0.5)' : '#707579'
                                                    }">[[ formatTime(m.timestamp) ]]</span>
                                                    <span v-if="m.sender === 'mine'" :style="{ color: '#4caf50' }">
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

