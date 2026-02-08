"""
Service for managing user advertisements
"""
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, or_, and_
from db.models import Advertisement, WalletUser


class AdvertisementService:
    """Service for managing advertisements"""
    
    @staticmethod
    async def create_advertisement(
        user_id: int,
        name: str,
        description: str,
        fee: str,
        min_limit: int,
        max_limit: int,
        currency: str,
        db: AsyncSession
    ) -> Advertisement:
        """
        Create a new advertisement
        
        Args:
            user_id: Owner user ID
            name: Display name for the advertisement
            description: Detailed description
            fee: Fee percentage
            min_limit: Minimum transaction limit
            max_limit: Maximum transaction limit
            currency: Currency code
            db: Database session
            
        Returns:
            Created Advertisement
            
        Raises:
            ValueError: If validation fails
        """
        # Validate limits
        if min_limit < 0:
            raise ValueError("Minimum limit must be non-negative")
        
        if max_limit < min_limit:
            raise ValueError("Maximum limit must be greater than or equal to minimum limit")
        
        # Validate fee
        try:
            fee_float = float(fee)
            if fee_float < 0 or fee_float > 100:
                raise ValueError("Fee must be between 0 and 100")
        except ValueError:
            raise ValueError("Fee must be a valid number")
        
        # Create advertisement
        advertisement = Advertisement(
            user_id=user_id,
            name=name.strip(),
            description=description.strip(),
            fee=fee,
            min_limit=min_limit,
            max_limit=max_limit,
            currency=currency.upper().strip(),
            is_active=True,
            is_verified=False,
            rating="0.0",
            deals_count=0
        )
        
        db.add(advertisement)
        await db.commit()
        await db.refresh(advertisement)
        
        return advertisement
    
    @staticmethod
    async def get_by_id(
        advertisement_id: int,
        db: AsyncSession
    ) -> Optional[Advertisement]:
        """
        Get advertisement by ID
        
        Args:
            advertisement_id: Advertisement ID
            db: Database session
            
        Returns:
            Advertisement if found, None otherwise
        """
        result = await db.execute(
            select(Advertisement).where(Advertisement.id == advertisement_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_advertisements(
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        db: AsyncSession = None
    ) -> Tuple[List[Advertisement], int]:
        """
        Get all advertisements for a specific user with pagination
        
        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Number of items per page
            db: Database session
            
        Returns:
            Tuple of (list of advertisements, total count)
        """
        # Get total count
        count_result = await db.execute(
            select(Advertisement).where(Advertisement.user_id == user_id)
        )
        total = len(count_result.scalars().all())
        
        # Get paginated results
        offset = (page - 1) * page_size
        result = await db.execute(
            select(Advertisement)
            .where(Advertisement.user_id == user_id)
            .order_by(Advertisement.created_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        advertisements = result.scalars().all()
        
        return list(advertisements), total
    
    @staticmethod
    async def search_advertisements(
        query: Optional[str] = None,
        currency: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_verified: Optional[bool] = None,
        min_amount: Optional[int] = None,
        max_amount: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        db: AsyncSession = None
    ) -> Tuple[List[Advertisement], int]:
        """
        Search advertisements with filters and pagination
        
        Args:
            query: Search query (name or description)
            currency: Filter by currency
            is_active: Filter by active status
            is_verified: Filter by verified status
            min_amount: Minimum amount filter
            max_amount: Maximum amount filter
            page: Page number (1-indexed)
            page_size: Number of items per page
            db: Database session
            
        Returns:
            Tuple of (list of advertisements, total count)
        """
        # Build query
        stmt = select(Advertisement)
        conditions = []
        
        # Text search
        if query:
            search_term = f"%{query}%"
            conditions.append(
                or_(
                    Advertisement.name.ilike(search_term),
                    Advertisement.description.ilike(search_term)
                )
            )
        
        # Currency filter
        if currency:
            conditions.append(Advertisement.currency == currency.upper())
        
        # Active status filter
        if is_active is not None:
            conditions.append(Advertisement.is_active == is_active)
        
        # Verified status filter
        if is_verified is not None:
            conditions.append(Advertisement.is_verified == is_verified)
        
        # Amount filters
        if min_amount is not None:
            conditions.append(Advertisement.max_limit >= min_amount)
        
        if max_amount is not None:
            conditions.append(Advertisement.min_limit <= max_amount)
        
        # Apply conditions
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Get total count
        count_result = await db.execute(stmt)
        total = len(count_result.scalars().all())
        
        # Get paginated results
        offset = (page - 1) * page_size
        stmt = stmt.order_by(Advertisement.created_at.desc()).limit(page_size).offset(offset)
        result = await db.execute(stmt)
        advertisements = result.scalars().all()
        
        return list(advertisements), total
    
    @staticmethod
    async def update_advertisement(
        advertisement_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        fee: Optional[str] = None,
        min_limit: Optional[int] = None,
        max_limit: Optional[int] = None,
        currency: Optional[str] = None,
        is_active: Optional[bool] = None,
        escrow_enabled: Optional[bool] = None,
        db: AsyncSession = None
    ) -> Advertisement:
        """
        Update advertisement
        
        Args:
            advertisement_id: Advertisement ID
            user_id: User ID (for ownership verification)
            name: New name (optional)
            description: New description (optional)
            fee: New fee (optional)
            min_limit: New minimum limit (optional)
            max_limit: New maximum limit (optional)
            currency: New currency (optional)
            is_active: New active status (optional)
            db: Database session
            
        Returns:
            Updated Advertisement
            
        Raises:
            ValueError: If advertisement not found or validation fails
        """
        # Get advertisement
        advertisement = await AdvertisementService.get_by_id(advertisement_id, db)
        if not advertisement:
            raise ValueError("Advertisement not found")
        
        # Check ownership
        if advertisement.user_id != user_id:
            raise ValueError("You don't have permission to edit this advertisement")
        
        # Build update values
        update_values = {}
        
        if name is not None:
            update_values['name'] = name.strip()
        
        if description is not None:
            update_values['description'] = description.strip()
        
        if fee is not None:
            try:
                fee_float = float(fee)
                if fee_float < 0 or fee_float > 100:
                    raise ValueError("Fee must be between 0 and 100")
            except ValueError:
                raise ValueError("Fee must be a valid number")
            update_values['fee'] = fee
        
        if min_limit is not None:
            if min_limit < 0:
                raise ValueError("Minimum limit must be non-negative")
            update_values['min_limit'] = min_limit
        
        if max_limit is not None:
            # Check against current or new min_limit
            current_min = update_values.get('min_limit', advertisement.min_limit)
            if max_limit < current_min:
                raise ValueError("Maximum limit must be greater than or equal to minimum limit")
            update_values['max_limit'] = max_limit
        
        if currency is not None:
            update_values['currency'] = currency.upper().strip()
        
        if is_active is not None:
            update_values['is_active'] = is_active
        
        if escrow_enabled is not None:
            update_values['escrow_enabled'] = escrow_enabled
        
        # Check that at least one field is being updated
        if not update_values:
            raise ValueError("At least one field must be provided for update")
        
        # Apply updates
        await db.execute(
            update(Advertisement)
            .where(Advertisement.id == advertisement_id)
            .values(**update_values)
        )
        await db.commit()
        await db.refresh(advertisement)
        
        return advertisement
    
    @staticmethod
    async def delete_advertisement(
        advertisement_id: int,
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """
        Delete advertisement
        
        Args:
            advertisement_id: Advertisement ID
            user_id: User ID (for ownership verification)
            db: Database session
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If advertisement not found or permission denied
        """
        # Get advertisement
        advertisement = await AdvertisementService.get_by_id(advertisement_id, db)
        if not advertisement:
            raise ValueError("Advertisement not found")
        
        # Check ownership
        if advertisement.user_id != user_id:
            raise ValueError("You don't have permission to delete this advertisement")
        
        # Delete advertisement
        await db.execute(
            delete(Advertisement).where(Advertisement.id == advertisement_id)
        )
        await db.commit()
        
        return True
    
    @staticmethod
    async def toggle_active_status(
        advertisement_id: int,
        user_id: int,
        db: AsyncSession
    ) -> Advertisement:
        """
        Toggle advertisement active status
        
        Args:
            advertisement_id: Advertisement ID
            user_id: User ID (for ownership verification)
            db: Database session
            
        Returns:
            Updated Advertisement
            
        Raises:
            ValueError: If advertisement not found or permission denied
        """
        # Get advertisement
        advertisement = await AdvertisementService.get_by_id(advertisement_id, db)
        if not advertisement:
            raise ValueError("Advertisement not found")
        
        # Check ownership
        if advertisement.user_id != user_id:
            raise ValueError("You don't have permission to modify this advertisement")
        
        # Toggle status
        new_status = not advertisement.is_active
        await db.execute(
            update(Advertisement)
            .where(Advertisement.id == advertisement_id)
            .values(is_active=new_status)
        )
        await db.commit()
        await db.refresh(advertisement)
        
        return advertisement

