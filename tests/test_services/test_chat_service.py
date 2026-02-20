"""
Tests for ChatService
"""
import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import select

from core.utils import get_deal_did
from services.chat.service import ChatService
from db.models import Storage, Deal
from ledgers.chat.schemas import (
    ChatMessageCreate,
    MessageType,
    AttachmentType,
    FileAttachment,
    MessageSignature
)


class TestChatServiceAddMessage:
    """Test add_message method"""
    
    @pytest.mark.asyncio
    async def test_add_message_without_deal_uid(self, test_db):
        """Test adding message without deal_uid - should create 2 storage records and return message for owner"""
        owner_did = "did:test:sender1"  # owner_did must be one of sender_id or receiver_id
        service = ChatService(session=test_db, owner_did=owner_did)
        
        message = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id="did:test:receiver1",
            text="Hello, world!"
        )
        
        # Add message without deal_uid
        created_message = await service.add_message(message, deal_uid=None)
        
        # Should return single message for owner_did
        assert created_message is not None
        assert created_message.text == "Hello, world!"
        assert created_message.sender_id == "did:test:sender1"
        assert created_message.receiver_id == "did:test:receiver1"
        assert created_message.conversation_id == "did:test:receiver1"  # For sender, conversation_id = receiver
        
        # Check that 2 storage records were created (one for sender, one for receiver)
        result = await test_db.execute(
            select(Storage).where(Storage.space == "chat")
        )
        storage_records = result.scalars().all()
        assert len(storage_records) == 2
        
        # Check owner_dids
        owner_dids = {record.owner_did for record in storage_records}
        assert owner_dids == {"did:test:sender1", "did:test:receiver1"}
        
        # Check that all records have the same payload
        for record in storage_records:
            assert record.space == "chat"
            assert record.deal_uid is None
            assert record.payload["text"] == "Hello, world!"
            assert record.payload["sender_id"] == "did:test:sender1"
            assert record.payload["receiver_id"] == "did:test:receiver1"
    
    @pytest.mark.asyncio
    async def test_add_message_with_deal_uid(self, test_db):
        """Test adding message with deal_uid - should create records for all participants and return message for owner"""
        owner_did = "did:test:participant1"  # owner_did must be one of participants
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Create a Deal with participants
        deal_uid = "deal123"
        deal = Deal(
            uid=deal_uid,
            sender_did="did:test:participant1",
            receiver_did="did:test:participant2",
            arbiter_did="did:test:arbiter",
            label="Test Deal"
        )
        test_db.add(deal)
        await test_db.commit()
        
        message = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:participant1",
            receiver_id="did:test:participant2",
            text="Deal message"
        )
        
        # Add message with deal_uid
        created_message = await service.add_message(message, deal_uid=deal_uid)
        
        # Should return single message for owner_did
        assert created_message is not None
        assert created_message.text == "Deal message"
        assert created_message.conversation_id == get_deal_did(deal_uid)  # For deal messages, conversation_id = did:deal:xxx
        
        # Check that 3 storage records were created (one for each participant)
        result = await test_db.execute(
            select(Storage).where(Storage.space == "chat")
        )
        storage_records = result.scalars().all()
        assert len(storage_records) == 3
        
        # Check owner_dids
        owner_dids = {record.owner_did for record in storage_records}
        assert owner_dids == {
            "did:test:participant1",
            "did:test:participant2",
            "did:test:arbiter"
        }
        
        # Check that all records have deal_uid
        for record in storage_records:
            assert record.space == "chat"
            assert record.deal_uid == deal_uid
            assert record.payload["text"] == "Deal message"
    
    @pytest.mark.asyncio
    async def test_add_message_with_nonexistent_deal_uid(self, test_db):
        """Test adding message with nonexistent deal_uid - should fallback to sender/receiver"""
        owner_did = "did:test:sender1"  # owner_did must be one of sender_id or receiver_id
        service = ChatService(session=test_db, owner_did=owner_did)
        
        message = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id="did:test:receiver1",
            text="Message with nonexistent deal"
        )
        
        # Add message with nonexistent deal_uid
        created_message = await service.add_message(message, deal_uid="nonexistent_deal")
        
        # Should return single message for owner_did
        assert created_message is not None
        assert created_message.text == "Message with nonexistent deal"
        
        # Check that 2 storage records were created
        result = await test_db.execute(
            select(Storage).where(Storage.space == "chat")
        )
        storage_records = result.scalars().all()
        assert len(storage_records) == 2
        
        # Check owner_dids (should be sender and receiver)
        owner_dids = {record.owner_did for record in storage_records}
        assert owner_dids == {"did:test:sender1", "did:test:receiver1"}
    
    @pytest.mark.asyncio
    async def test_add_message_atomicity(self, test_db):
        """Test that add_message is atomic - all or nothing"""
        owner_did = "did:test:sender1"  # owner_did must be one of sender_id or receiver_id
        service = ChatService(session=test_db, owner_did=owner_did)
        
        message = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id="did:test:receiver1",
            text="Atomic test"
        )
        
        # Add message
        created_message = await service.add_message(message, deal_uid=None)
        assert created_message is not None
        
        # Check that records were committed
        result = await test_db.execute(
            select(Storage).where(Storage.space == "chat")
        )
        storage_records = result.scalars().all()
        assert len(storage_records) == 2
        
        # Verify commit was successful
        await test_db.commit()
        result = await test_db.execute(
            select(Storage).where(Storage.space == "chat")
        )
        storage_records_after = result.scalars().all()
        assert len(storage_records_after) == 2
    
    @pytest.mark.asyncio
    async def test_add_message_with_file_attachment(self, test_db):
        """Test adding message with file attachment"""
        owner_did = "did:test:sender1"  # owner_did must be one of sender_id or receiver_id
        service = ChatService(session=test_db, owner_did=owner_did)
        
        attachment = FileAttachment(
            id="att1",
            type=AttachmentType.DOCUMENT,
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            data="dGVzdCBkYXRh"  # base64 encoded "test data"
        )
        
        message = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.FILE,
            sender_id="did:test:sender1",
            receiver_id="did:test:receiver1",
            attachments=[attachment]
        )
        
        created_message = await service.add_message(message, deal_uid=None)
        
        assert created_message is not None
        assert created_message.attachments is not None
        assert len(created_message.attachments) == 1
        assert created_message.attachments[0].name == "test.pdf"
        
        # Check that attachment is stored in payload
        result = await test_db.execute(
            select(Storage).where(Storage.space == "chat")
        )
        storage_records = result.scalars().all()
        assert len(storage_records) == 2
        
        for record in storage_records:
            assert record.payload["message_type"] == "file"
            assert len(record.payload["attachments"]) == 1
            assert record.payload["attachments"][0]["name"] == "test.pdf"


class TestChatServiceGetHistory:
    """Test get_history method"""
    
    @pytest.mark.asyncio
    async def test_get_history_empty(self, test_db):
        """Test getting history when no messages exist"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        result = await service.get_history()
        
        assert result["messages"] == []
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["page_size"] == 50
        assert result["total_pages"] == 0
    
    @pytest.mark.asyncio
    async def test_get_history_with_messages(self, test_db):
        """Test getting history with messages"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Add some messages
        message1 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id=owner_did,
            text="Message 1"
        )
        await service.add_message(message1, deal_uid=None)
        
        # Create service for receiver to add message from their perspective
        service2 = ChatService(session=test_db, owner_did="did:test:sender1")
        message2 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id=owner_did,
            text="Message 2"
        )
        await service2.add_message(message2, deal_uid=None)
        
        # Get history for owner_did with conversation_id filter
        # conversation_id = sender_id for owner_did
        result = await service.get_history(conversation_id="did:test:sender1")
        
        assert len(result["messages"]) == 2
        assert result["total"] == 2
        # Messages should be ordered by id descending (newest first)
        # Message 2 was added after Message 1, so it should be first
        assert result["messages"][0].text == "Message 2"
        assert result["messages"][1].text == "Message 1"
    
    @pytest.mark.asyncio
    async def test_get_history_with_mixed_conversations(self, test_db):
        """Test getting history with both regular and deal-based conversations"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Create a Deal
        deal_uid = "deal123"
        deal = Deal(
            uid=deal_uid,
            sender_did=owner_did,
            receiver_did="did:test:participant2",
            arbiter_did="did:test:arbiter",
            label="Test Deal"
        )
        test_db.add(deal)
        await test_db.commit()
        
        # Add message without deal_uid (conversation_id = контрагент)
        message1 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id=owner_did,
            text="General message"
        )
        await service.add_message(message1, deal_uid=None)
        
        # Add message with deal_uid (conversation_id = deal_uid)
        message2 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id=owner_did,
            text="Deal message"
        )
        await service.add_message(message2, deal_uid=deal_uid)
        
        # Get history for regular conversation (conversation_id = sender)
        result = await service.get_history(conversation_id="did:test:sender1")
        assert len(result["messages"]) == 1
        assert result["messages"][0].text == "General message"
        
        # Get history for deal conversation (conversation_id = deal_uid or did:deal:xxx)
        result = await service.get_history(conversation_id=deal_uid)
        assert len(result["messages"]) == 1
        assert result["messages"][0].text == "Deal message"
        assert result["messages"][0].conversation_id == get_deal_did(deal_uid)
        
        # Note: Cannot get all messages without conversation_id filter
        # because get_history() filters by conversation_id IS NULL when conversation_id is not specified
        # So we verify both conversations separately
    
    @pytest.mark.asyncio
    async def test_get_history_with_pagination(self, test_db):
        """Test getting history with pagination"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Add 5 messages
        sender_id = "did:test:sender1"
        for i in range(5):
            message = ChatMessageCreate(
                uuid=str(uuid.uuid4()),
                message_type=MessageType.TEXT,
                sender_id=sender_id,
                receiver_id=owner_did,
                text=f"Message {i+1}"
            )
            await service.add_message(message, deal_uid=None)
        
        # Get first page (2 messages) with conversation_id filter
        result = await service.get_history(conversation_id=sender_id, page=1, page_size=2)
        assert len(result["messages"]) == 2
        assert result["total"] == 5
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert result["total_pages"] == 3
        
        # Get second page with conversation_id filter
        result = await service.get_history(conversation_id=sender_id, page=2, page_size=2)
        assert len(result["messages"]) == 2
        assert result["page"] == 2
    
    @pytest.mark.asyncio
    async def test_get_history_with_conversation_id_filter(self, test_db):
        """Test getting history filtered by conversation_id (auto-generated as counterparty DID)"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Add messages - conversation_id will be auto-generated as counterparty (not owner_did)
        # Message 1: from contact1 to owner1 → conversation_id = contact1
        message1 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:contact1",
            receiver_id=owner_did,
            text="From contact1 as sender"
        )
        await service.add_message(message1, deal_uid=None)
        
        # Message 2: from owner1 to contact2 → conversation_id = contact2
        message2 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id=owner_did,
            receiver_id="did:test:contact2",
            text="From contact2 as receiver"
        )
        await service.add_message(message2, deal_uid=None)
        
        # Message 3: from sender3 to owner1 → conversation_id = sender3
        message3 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender3",
            receiver_id=owner_did,
            text="Third conversation"
        )
        await service.add_message(message3, deal_uid=None)
        
        # Filter by conversation_id = "did:test:contact1" (counterparty)
        result = await service.get_history(conversation_id="did:test:contact1")
        assert len(result["messages"]) == 1
        assert result["messages"][0].text == "From contact1 as sender"
        
        # Filter by conversation_id = "did:test:contact2" (counterparty)
        result = await service.get_history(conversation_id="did:test:contact2")
        assert len(result["messages"]) == 1
        assert result["messages"][0].text == "From contact2 as receiver"
        
        # Filter by conversation_id = "did:test:sender3" (counterparty)
        result = await service.get_history(conversation_id="did:test:sender3")
        assert len(result["messages"]) == 1
        assert result["messages"][0].text == "Third conversation"
        
        # Note: Cannot get all messages without conversation_id filter
        # because get_history() filters by conversation_id IS NULL when conversation_id is not specified
        # So we verify all conversations separately
    
    @pytest.mark.asyncio
    async def test_conversation_id_with_deal_uid(self, test_db):
        """Test that conversation_id = deal_uid when message is related to a deal"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Create a deal
        deal_uid = "test-deal-uid-123"
        deal = Deal(
            uid=deal_uid,
            sender_did=owner_did,
            receiver_did="did:test:participant2",
            arbiter_did="did:test:arbiter",
            label="Test Deal"
        )
        test_db.add(deal)
        await test_db.commit()
        
        # Add message related to deal - conversation_id should be deal_uid
        message = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id=owner_did,
            receiver_id="did:test:participant2",
            text="Message related to deal"
        )
        await service.add_message(message, deal_uid=deal_uid)
        
        # Filter by conversation_id = deal_uid (normalized to did:deal:xxx in service)
        result = await service.get_history(conversation_id=deal_uid)
        assert len(result["messages"]) == 1
        assert result["messages"][0].text == "Message related to deal"
        assert result["messages"][0].conversation_id == get_deal_did(deal_uid)
    
    @pytest.mark.asyncio
    async def test_conversation_id_per_owner_did(self, test_db):
        """Test that conversation_id is calculated correctly for each owner_did"""
        alice_did = "did:test:alice"
        bob_did = "did:test:bob"
        
        # Create message from Alice to Bob
        service_alice = ChatService(session=test_db, owner_did=alice_did)
        message = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id=alice_did,
            receiver_id=bob_did,
            text="Hello Bob"
        )
        await service_alice.add_message(message, deal_uid=None)
        
        # Check Alice's storage: conversation_id should be Bob
        service_alice = ChatService(session=test_db, owner_did=alice_did)
        alice_history = await service_alice.get_history(conversation_id=bob_did)
        assert len(alice_history["messages"]) == 1
        assert alice_history["messages"][0].conversation_id == bob_did
        
        # Check Bob's storage: conversation_id should be Alice
        service_bob = ChatService(session=test_db, owner_did=bob_did)
        bob_history = await service_bob.get_history(conversation_id=alice_did)
        assert len(bob_history["messages"]) == 1
        assert bob_history["messages"][0].conversation_id == alice_did
        
        # Both should see the same message text
        assert alice_history["messages"][0].text == "Hello Bob"
        assert bob_history["messages"][0].text == "Hello Bob"
    
    @pytest.mark.asyncio
    async def test_get_history_with_after_message_uid_filter(self, test_db):
        """Test getting history filtered by after_message_uid"""
        owner_did = "did:test:owner1"
        sender_id = "did:test:sender1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Add 3 messages
        # conversation_id will be sender_id for owner_did
        message1 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id=sender_id,
            receiver_id=owner_did,
            text="Message 1"
        )
        await service.add_message(message1, deal_uid=None)
        
        message2 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id=sender_id,
            receiver_id=owner_did,
            text="Message 2"
        )
        await service.add_message(message2, deal_uid=None)
        
        message3 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id=sender_id,
            receiver_id=owner_did,
            text="Message 3"
        )
        await service.add_message(message3, deal_uid=None)
        
        # Get all messages with conversation_id filter (conversation_id = sender_id)
        all_messages = await service.get_history(conversation_id=sender_id)
        assert len(all_messages["messages"]) == 3
        
        # Use message2 UUID as after_message_uid filter
        # With desc ordering: messages[0]=Message3, messages[1]=Message2, messages[2]=Message1
        message2_uuid = all_messages["messages"][1].uuid
        
        # Get history after message2 with conversation_id filter
        result = await service.get_history(
            conversation_id=sender_id,
            after_message_uid=message2_uuid
        )
        
        # Should return only message3 (with id > message2.id), sorted desc (newest first)
        assert len(result["messages"]) == 1
        assert result["messages"][0].text == "Message 3"
        assert result["total"] == 1
    
    @pytest.mark.asyncio
    async def test_get_history_with_before_message_uid_filter(self, test_db):
        """Test getting history filtered by before_message_uid"""
        owner_did = "did:test:owner1"
        sender_id = "did:test:sender1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Add 3 messages
        message1 = ChatMessageCreate(uuid=str(uuid.uuid4()), message_type=MessageType.TEXT, sender_id=sender_id, receiver_id=owner_did, text="Message 1")
        await service.add_message(message1, deal_uid=None)
        message2 = ChatMessageCreate(uuid=str(uuid.uuid4()), message_type=MessageType.TEXT, sender_id=sender_id, receiver_id=owner_did, text="Message 2")
        await service.add_message(message2, deal_uid=None)
        message3 = ChatMessageCreate(uuid=str(uuid.uuid4()), message_type=MessageType.TEXT, sender_id=sender_id, receiver_id=owner_did, text="Message 3")
        await service.add_message(message3, deal_uid=None)
        
        # Get all messages to find message2 UUID
        all_messages = await service.get_history(conversation_id=sender_id)
        message2_uuid = all_messages["messages"][1].uuid  # With desc: [Message3, Message2, Message1]
        
        # Get history before message2
        result = await service.get_history(conversation_id=sender_id, before_message_uid=message2_uuid, page_size=10)
        
        # Should return only message1 (with id < message2.id), sorted desc
        assert len(result["messages"]) == 1
        assert result["messages"][0].text == "Message 1"
        assert result["total"] == 1


class TestChatServiceGetLastSessions:
    """Test get_last_sessions method"""
    
    @pytest.mark.asyncio
    async def test_get_last_sessions_empty(self, test_db):
        """Test getting last sessions when no messages exist"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        sessions = await service.get_last_sessions()
        
        assert sessions == []
    
    @pytest.mark.asyncio
    async def test_get_last_sessions_grouped_by_conversation_id(self, test_db):
        """Test getting last sessions grouped by conversation_id"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Create deals
        deal1_uid = "deal1"
        deal1 = Deal(
            uid=deal1_uid,
            sender_did=owner_did,
            receiver_did="did:test:participant2",
            arbiter_did="did:test:arbiter",
            label="Deal 1"
        )
        test_db.add(deal1)
        
        deal2_uid = "deal2"
        deal2 = Deal(
            uid=deal2_uid,
            sender_did=owner_did,
            receiver_did="did:test:participant3",
            arbiter_did="did:test:arbiter",
            label="Deal 2"
        )
        test_db.add(deal2)
        await test_db.commit()
        
        # Add messages to different conversations
        # General chat message (conversation_id = sender)
        message1 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id=owner_did,
            text="General message 1"
        )
        await service.add_message(message1, deal_uid=None)
        
        # Deal 1 message (conversation_id = deal1_uid)
        message2 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id=owner_did,
            text="Deal 1 message"
        )
        await service.add_message(message2, deal_uid=deal1_uid)
        
        # Deal 2 message (conversation_id = deal2_uid)
        message3 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id="did:test:sender1",
            receiver_id=owner_did,
            text="Deal 2 message"
        )
        await service.add_message(message3, deal_uid=deal2_uid)
        
        # Get last sessions (могут быть и сессии с 0 сообщений от других сделок в БД)
        sessions = await service.get_last_sessions()
        
        # Минимум 3 сессии: общий чат с sender1, deal1, deal2
        assert len(sessions) >= 3
        
        # Check that sessions are sorted by last_message_time descending
        min_dt = datetime.min.replace(tzinfo=timezone.utc)
        for i in range(len(sessions) - 1):
            t1 = sessions[i]["last_message_time"] or min_dt
            t2 = sessions[i+1]["last_message_time"] or min_dt
            assert t1 >= t2
        
        # Check session structure
        conversation_ids = [s["conversation_id"] for s in sessions]
        for session in sessions:
            assert "conversation_id" in session
            assert "last_message_time" in session
            assert "message_count" in session
            assert "last_message" in session
            if session["last_message"] is not None:
                assert hasattr(session["last_message"], "text")
                assert hasattr(session["last_message"], "sender_id")
        
        # Ожидаемые сессии должны присутствовать (могут быть и другие — сделки с 0 сообщений)
        assert "did:test:sender1" in conversation_ids  # General chat
        assert get_deal_did(deal1_uid) in conversation_ids  # Deal 1
        assert get_deal_did(deal2_uid) in conversation_ids  # Deal 2
    
    @pytest.mark.asyncio
    async def test_get_last_sessions_with_limit(self, test_db):
        """Test getting last sessions with limit"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Create multiple deals and add messages
        for i in range(5):
            deal_uid = f"deal{i}"
            deal = Deal(
                uid=deal_uid,
                sender_did=owner_did,
                receiver_did=f"did:test:participant{i}",
                arbiter_did="did:test:arbiter",
                label=f"Deal {i}"
            )
            test_db.add(deal)
            await test_db.commit()
            
            message = ChatMessageCreate(
                uuid=str(uuid.uuid4()),
                message_type=MessageType.TEXT,
                sender_id="did:test:sender1",
                receiver_id=owner_did,
                text=f"Deal {i} message"
            )
            await service.add_message(message, deal_uid=deal_uid)
        
        # Get last sessions with limit
        sessions = await service.get_last_sessions(limit=3)
        
        assert len(sessions) == 3
    
    @pytest.mark.asyncio
    async def test_get_last_sessions_message_count(self, test_db):
        """Test that message_count is correct for each session"""
        owner_did = "did:test:owner1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Create a deal
        deal_uid = "deal1"
        deal = Deal(
            uid=deal_uid,
            sender_did=owner_did,
            receiver_did="did:test:participant2",
            arbiter_did="did:test:arbiter",
            label="Deal 1"
        )
        test_db.add(deal)
        await test_db.commit()
        
        # Add 3 messages to the deal
        for i in range(3):
            message = ChatMessageCreate(
                uuid=str(uuid.uuid4()),
                message_type=MessageType.TEXT,
                sender_id="did:test:sender1",
                receiver_id=owner_did,
                text=f"Deal message {i+1}"
            )
            await service.add_message(message, deal_uid=deal_uid)
        
        # Get last sessions
        sessions = await service.get_last_sessions()
        
        # Find the deal session (conversation_id = did:deal:xxx)
        deal_session = next((s for s in sessions if s["conversation_id"] == get_deal_did(deal_uid)), None)
        assert deal_session is not None
        assert deal_session["message_count"] == 3
    
    @pytest.mark.asyncio
    async def test_get_last_sessions_with_after_message_uid_filter(self, test_db):
        """Test getting last sessions filtered by after_message_uid"""
        owner_did = "did:test:owner1"
        sender_id = "did:test:sender1"
        service = ChatService(session=test_db, owner_did=owner_did)
        
        # Create a deal
        deal_uid = "test-deal-123"
        deal = Deal(
            uid=deal_uid,
            sender_did=owner_did,
            receiver_did="did:test:participant2",
            arbiter_did="did:test:arbiter",
            label="Test Deal"
        )
        test_db.add(deal)
        await test_db.commit()
        
        # Add messages to different conversations
        # Message 1: general conversation
        message1 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id=sender_id,
            receiver_id=owner_did,
            text="Message 1"
        )
        await service.add_message(message1, deal_uid=None)
        
        # Message 2: deal conversation
        message2 = ChatMessageCreate(
            uuid=str(uuid.uuid4()),
            message_type=MessageType.TEXT,
            sender_id=sender_id,
            receiver_id=owner_did,
            text="Message 2"
        )
        await service.add_message(message2, deal_uid=deal_uid)
        
        # Get all sessions to find message1 UUID
        all_sessions = await service.get_last_sessions()
        assert len(all_sessions) == 2
        
        # Find message1 UUID from general conversation session
        general_session = next(s for s in all_sessions if s["conversation_id"] == sender_id)
        message1_uuid = general_session["last_message"].uuid
        
        # Get sessions after message1
        result = await service.get_last_sessions(after_message_uid=message1_uuid)
        
        # Should return only deal session (with last message id > message1.id)
        assert len(result) == 1
        assert result[0]["conversation_id"] == get_deal_did(deal_uid)
        assert result[0]["last_message"].text == "Message 2"

