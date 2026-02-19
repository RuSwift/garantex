"""
Cron tasks functions
"""
import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import db
from db.models import EscrowModel

logger = logging.getLogger(__name__)




async def process_escrow_batch(
    session: AsyncSession,
    page: int,
    page_size: int = 10
) -> List[EscrowModel]:
    """
    Получить батч escrow записей с SELECT FOR UPDATE SKIP LOCKED
    
    Args:
        session: Database session
        page: Номер страницы (начиная с 0)
        page_size: Размер страницы
        
    Returns:
        Список заблокированных EscrowModel записей
    """
    # SELECT FOR UPDATE SKIP LOCKED - пропускает заблокированные записи
    stmt = (
        select(EscrowModel)
        .where(
            EscrowModel.status == 'pending'  # Фильтр по статусу
        )
        .order_by(EscrowModel.id)  # Важно: сортировка для стабильной пагинации
        .offset(page * page_size)
        .limit(page_size)
        .with_for_update(skip_locked=True)  # SELECT FOR UPDATE SKIP LOCKED
    )
    
    result = await session.execute(stmt)
    escrows = result.scalars().all()
    
    return list(escrows)


async def process_escrow(escrow: EscrowModel, session: AsyncSession) -> None:
    """
    Обработать одну escrow запись
    
    Args:
        escrow: EscrowModel запись
        session: Database session
    """
    try:
        # Здесь ваша логика обработки escrow
        logger.info(
            f"Processing escrow ID: {escrow.id}, "
            f"status: {escrow.status}, "
            f"blockchain: {escrow.blockchain}, "
            f"network: {escrow.network}"
        )
        
        # Пример: обновление статуса
        # escrow.status = 'active'
        # await session.flush()
        
        # Или другая логика обработки
        pass
        
    except Exception as e:
        logger.error(f"Error processing escrow {escrow.id}: {str(e)}")
        # Можно пометить запись как проблемную или оставить для повторной обработки
        raise


async def cron_task():
    """
    Функция, которая выполняется периодически (каждые 5 секунд)
    
    Обрабатывает escrow записи с использованием SELECT FOR UPDATE SKIP LOCKED
    для безопасной параллельной обработки несколькими воркерами.
    
    Блокировки освобождаются после каждого батча (commit), чтобы быстрее
    освобождать записи для других воркеров.
    """
    # Получаем сессию БД динамически
    if db.SessionLocal is None:
        logger.error("Database not initialized. Skipping cron task.")
        return
    
    async with db.SessionLocal() as session:
        try:
            page = 0
            page_size = 10  # Размер батча
            total_processed = 0
            
            while True:
                # Получаем батч записей с блокировкой
                escrows = await process_escrow_batch(session, page, page_size)
                
                if not escrows:
                    # Больше нет записей для обработки
                    break
                
                # Обрабатываем каждую запись
                for escrow in escrows:
                    try:
                        await process_escrow(escrow, session)
                        total_processed += 1
                    except Exception as e:
                        logger.error(f"Failed to process escrow {escrow.id}: {str(e)}")
                        # Продолжаем обработку следующих записей
                        continue
                
                # Коммитим изменения после обработки батча
                # Блокировки освобождаются здесь - записи становятся доступными для других воркеров
                await session.commit()
                
                # Если получили меньше записей, чем page_size, значит это последняя страница
                if len(escrows) < page_size:
                    break
                
                page += 1
                
                # Ограничение: обрабатываем максимум N страниц за один запуск
                # чтобы не блокировать другие задачи
                if page >= 100:  # Максимум 1000 записей за запуск (100 * 10)
                    break
            
            if total_processed > 0:
                logger.info(f"Processed {total_processed} escrow records")
                
        except Exception as e:
            logger.error(f"Error in cron_task: {str(e)}")
            await session.rollback()  # Блокировки освобождаются здесь при ошибке
            raise

