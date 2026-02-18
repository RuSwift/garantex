"""
Tests for DealsService
"""
import pytest
from sqlalchemy import select

from services.deals.service import DealsService
from db.models import Deal
from core.exceptions import DealAccessDeniedError
from ledgers.chat.schemas import FileAttachment, AttachmentType


class TestDealsServiceOwnership:
    """Test deal ownership checks"""
    
    @pytest.mark.asyncio
    async def test_create_deal_by_owner(self, test_db):
        """Test creating deal by owner - should succeed"""
        owner_did = "did:test:owner1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        deal = await service.create_deal(
            sender_did=owner_did,
            receiver_did="did:test:receiver1",
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        assert deal is not None
        assert deal.sender_did == owner_did  # Owner is sender_did
        assert deal.sender_did == owner_did
        assert deal.receiver_did == "did:test:receiver1"
        assert deal.arbiter_did == "did:test:arbiter1"
    
    @pytest.mark.asyncio
    async def test_create_deal_by_non_participant_fails(self, test_db):
        """Test creating deal where owner_did is not a participant - should fail"""
        owner_did = "did:test:owner1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        with pytest.raises(ValueError, match="owner_did.*must be a participant"):
            await service.create_deal(
                sender_did="did:test:sender1",
                receiver_did="did:test:receiver1",
                arbiter_did="did:test:arbiter1",
                label="Test Deal"
            )
    
    @pytest.mark.asyncio
    async def test_create_deal_as_receiver(self, test_db):
        """Test creating deal where owner_did is receiver - should succeed"""
        owner_did = "did:test:receiver1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        deal = await service.create_deal(
            sender_did="did:test:sender1",
            receiver_did=owner_did,
            arbiter_did="did:test:arbiter1",
            label="Test Deal as Receiver"
        )
        
        assert deal is not None
        assert deal.receiver_did == owner_did
        assert deal.sender_did == "did:test:sender1"
        assert deal.arbiter_did == "did:test:arbiter1"
    
    @pytest.mark.asyncio
    async def test_create_deal_as_arbiter(self, test_db):
        """Test creating deal where owner_did is arbiter - should succeed"""
        owner_did = "did:test:arbiter1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        deal = await service.create_deal(
            sender_did="did:test:sender1",
            receiver_did="did:test:receiver1",
            arbiter_did=owner_did,
            label="Test Deal as Arbiter"
        )
        
        assert deal is not None
        assert deal.arbiter_did == owner_did
        assert deal.sender_did == "did:test:sender1"
        assert deal.receiver_did == "did:test:receiver1"
    
    @pytest.mark.asyncio
    async def test_update_deal_by_owner(self, test_db):
        """Test updating deal by owner - should succeed"""
        owner_did = "did:test:owner1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        # Create deal
        deal = await service.create_deal(
            sender_did=owner_did,
            receiver_did="did:test:receiver1",
            arbiter_did="did:test:arbiter1",
            label="Original Label"
        )
        
        # Update deal by owner
        updated_deal = await service.update_deal(
            deal_uid=deal.uid,
            label="Updated Label"
        )
        
        assert updated_deal is not None
        assert updated_deal.label == "Updated Label"
    
    @pytest.mark.asyncio
    async def test_update_deal_by_non_owner_fails(self, test_db):
        """Test updating deal by non-owner - should raise DealAccessDeniedError"""
        owner_did = "did:test:owner1"
        non_owner_did = "did:test:receiver1"
        
        # Create deal by owner
        owner_service = DealsService(session=test_db, owner_did=owner_did)
        deal = await owner_service.create_deal(
            sender_did=owner_did,
            receiver_did=non_owner_did,
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Try to update by non-owner
        non_owner_service = DealsService(session=test_db, owner_did=non_owner_did)
        
        with pytest.raises(DealAccessDeniedError) as exc_info:
            await non_owner_service.update_deal(
                deal_uid=deal.uid,
                label="Hacked Label"
            )
        
        assert exc_info.value.deal_uid == deal.uid
        assert exc_info.value.owner_did == owner_did
        assert exc_info.value.attempted_by == non_owner_did
    
    @pytest.mark.asyncio
    async def test_update_requisites_by_owner(self, test_db):
        """Test updating requisites by owner - should succeed"""
        owner_did = "did:test:owner1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        # Create deal
        deal = await service.create_deal(
            sender_did=owner_did,
            receiver_did="did:test:receiver1",
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Update requisites by owner
        requisites = {
            "fio": "Иванов Иван Иванович",
            "purpose": "Оплата услуг",
            "currency": "USD",
            "amount": 1000.00
        }
        
        updated_requisites = await service.update_requisites(
            deal_uid=deal.uid,
            requisites=requisites
        )
        
        assert updated_requisites is not None
        assert updated_requisites["fio"] == "Иванов Иван Иванович"
        assert updated_requisites["currency"] == "USD"
    
    @pytest.mark.asyncio
    async def test_update_requisites_by_non_owner_fails(self, test_db):
        """Test updating requisites by non-owner - should raise DealAccessDeniedError"""
        owner_did = "did:test:owner1"
        non_owner_did = "did:test:receiver1"
        
        # Create deal by owner
        owner_service = DealsService(session=test_db, owner_did=owner_did)
        deal = await owner_service.create_deal(
            sender_did=owner_did,
            receiver_did=non_owner_did,
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Try to update requisites by non-owner
        non_owner_service = DealsService(session=test_db, owner_did=non_owner_did)
        
        requisites = {
            "fio": "Hacked Name",
            "currency": "USD"
        }
        
        with pytest.raises(DealAccessDeniedError) as exc_info:
            await non_owner_service.update_requisites(
                deal_uid=deal.uid,
                requisites=requisites
            )
        
        assert exc_info.value.deal_uid == deal.uid
        assert exc_info.value.owner_did == owner_did
        assert exc_info.value.attempted_by == non_owner_did
    
    @pytest.mark.asyncio
    async def test_add_attachment_by_owner(self, test_db):
        """Test adding attachment by owner - should succeed"""
        owner_did = "did:test:owner1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        # Create deal
        deal = await service.create_deal(
            sender_did=owner_did,
            receiver_did="did:test:receiver1",
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Add attachment by owner
        attachment = FileAttachment(
            id="att1",
            type=AttachmentType.DOCUMENT,
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            data="dGVzdCBkYXRh"  # base64 "test data"
        )
        
        attachments = await service.add_attachment(
            deal_uid=deal.uid,
            attachment=attachment
        )
        
        assert attachments is not None
        assert len(attachments) == 1
        assert attachments[0]["name"] == "test.pdf"
    
    @pytest.mark.asyncio
    async def test_add_attachment_by_non_owner_fails(self, test_db):
        """Test adding attachment by non-owner - should raise DealAccessDeniedError"""
        owner_did = "did:test:owner1"
        non_owner_did = "did:test:receiver1"
        
        # Create deal by owner
        owner_service = DealsService(session=test_db, owner_did=owner_did)
        deal = await owner_service.create_deal(
            sender_did=owner_did,
            receiver_did=non_owner_did,
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Try to add attachment by non-owner
        non_owner_service = DealsService(session=test_db, owner_did=non_owner_did)
        
        attachment = FileAttachment(
            id="att1",
            type=AttachmentType.DOCUMENT,
            name="hacked.pdf",
            size=1024,
            mime_type="application/pdf",
            data="dGVzdCBkYXRh"
        )
        
        with pytest.raises(DealAccessDeniedError) as exc_info:
            await non_owner_service.add_attachment(
                deal_uid=deal.uid,
                attachment=attachment
            )
        
        assert exc_info.value.deal_uid == deal.uid
        assert exc_info.value.owner_did == owner_did
        assert exc_info.value.attempted_by == non_owner_did
    
    @pytest.mark.asyncio
    async def test_remove_attachment_by_owner(self, test_db):
        """Test removing attachment by owner - should succeed"""
        owner_did = "did:test:owner1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        # Create deal
        deal = await service.create_deal(
            sender_did=owner_did,
            receiver_did="did:test:receiver1",
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Add attachment
        attachment = FileAttachment(
            id="att1",
            type=AttachmentType.DOCUMENT,
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            data="dGVzdCBkYXRh"
        )
        
        attachments = await service.add_attachment(
            deal_uid=deal.uid,
            attachment=attachment
        )
        
        assert len(attachments) == 1
        
        # Remove attachment by owner
        attachment_uuid = attachments[0].get("message_uuid") or attachments[0].get("attachment_id")
        updated_attachments = await service.remove_attachment(
            deal_uid=deal.uid,
            attachment_uuid=attachment_uuid
        )
        
        assert updated_attachments is not None
        assert len(updated_attachments) == 0
    
    @pytest.mark.asyncio
    async def test_remove_attachment_by_non_owner_fails(self, test_db):
        """Test removing attachment by non-owner - should raise DealAccessDeniedError"""
        owner_did = "did:test:owner1"
        non_owner_did = "did:test:receiver1"
        
        # Create deal by owner
        owner_service = DealsService(session=test_db, owner_did=owner_did)
        deal = await owner_service.create_deal(
            sender_did=owner_did,
            receiver_did=non_owner_did,
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Add attachment by owner
        attachment = FileAttachment(
            id="att1",
            type=AttachmentType.DOCUMENT,
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            data="dGVzdCBkYXRh"
        )
        
        attachments = await owner_service.add_attachment(
            deal_uid=deal.uid,
            attachment=attachment
        )
        
        # Try to remove attachment by non-owner
        non_owner_service = DealsService(session=test_db, owner_did=non_owner_did)
        
        attachment_uuid = attachments[0].get("message_uuid") or attachments[0].get("attachment_id")
        
        with pytest.raises(DealAccessDeniedError) as exc_info:
            await non_owner_service.remove_attachment(
                deal_uid=deal.uid,
                attachment_uuid=attachment_uuid
            )
        
        assert exc_info.value.deal_uid == deal.uid
        assert exc_info.value.owner_did == owner_did
        assert exc_info.value.attempted_by == non_owner_did
    
    @pytest.mark.asyncio
    async def test_delete_deal_by_owner(self, test_db):
        """Test deleting deal by owner - should succeed"""
        owner_did = "did:test:owner1"
        service = DealsService(session=test_db, owner_did=owner_did)
        
        # Create deal
        deal = await service.create_deal(
            sender_did=owner_did,
            receiver_did="did:test:receiver1",
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Delete deal by owner
        deleted = await service.delete_deal(deal_uid=deal.uid)
        
        assert deleted is True
        
        # Verify deal is deleted
        result = await test_db.execute(
            select(Deal).where(Deal.uid == deal.uid)
        )
        deleted_deal = result.scalar_one_or_none()
        assert deleted_deal is None
    
    @pytest.mark.asyncio
    async def test_delete_deal_by_non_owner_fails(self, test_db):
        """Test deleting deal by non-owner - should raise DealAccessDeniedError"""
        owner_did = "did:test:owner1"
        non_owner_did = "did:test:receiver1"
        
        # Create deal by owner
        owner_service = DealsService(session=test_db, owner_did=owner_did)
        deal = await owner_service.create_deal(
            sender_did=owner_did,
            receiver_did=non_owner_did,
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Try to delete by non-owner
        non_owner_service = DealsService(session=test_db, owner_did=non_owner_did)
        
        with pytest.raises(DealAccessDeniedError) as exc_info:
            await non_owner_service.delete_deal(deal_uid=deal.uid)
        
        assert exc_info.value.deal_uid == deal.uid
        assert exc_info.value.owner_did == owner_did
        assert exc_info.value.attempted_by == non_owner_did
        
        # Verify deal still exists
        result = await test_db.execute(
            select(Deal).where(Deal.uid == deal.uid)
        )
        existing_deal = result.scalar_one_or_none()
        assert existing_deal is not None
    
    @pytest.mark.asyncio
    async def test_get_deal_by_participant(self, test_db):
        """Test getting deal by participant (non-owner) - should succeed (read-only access)"""
        owner_did = "did:test:owner1"
        participant_did = "did:test:receiver1"
        
        # Create deal by owner
        owner_service = DealsService(session=test_db, owner_did=owner_did)
        deal = await owner_service.create_deal(
            sender_did=owner_did,
            receiver_did=participant_did,
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Get deal by participant (should succeed - read access)
        participant_service = DealsService(session=test_db, owner_did=participant_did)
        retrieved_deal = await participant_service.get_deal(deal_uid=deal.uid)
        
        assert retrieved_deal is not None
        assert retrieved_deal.uid == deal.uid
        assert retrieved_deal.label == "Test Deal"
    
    @pytest.mark.asyncio
    async def test_get_requisites_by_participant(self, test_db):
        """Test getting requisites by participant (non-owner) - should succeed (read-only access)"""
        owner_did = "did:test:owner1"
        participant_did = "did:test:receiver1"
        
        # Create deal by owner
        owner_service = DealsService(session=test_db, owner_did=owner_did)
        deal = await owner_service.create_deal(
            sender_did=owner_did,
            receiver_did=participant_did,
            arbiter_did="did:test:arbiter1",
            label="Test Deal"
        )
        
        # Set requisites by owner
        requisites = {
            "fio": "Иванов Иван Иванович",
            "currency": "USD"
        }
        await owner_service.update_requisites(deal_uid=deal.uid, requisites=requisites)
        
        # Get requisites by participant (should succeed - read access)
        participant_service = DealsService(session=test_db, owner_did=participant_did)
        retrieved_requisites = await participant_service.get_requisites(deal_uid=deal.uid)
        
        assert retrieved_requisites is not None
        assert retrieved_requisites["fio"] == "Иванов Иван Иванович"
        assert retrieved_requisites["currency"] == "USD"

