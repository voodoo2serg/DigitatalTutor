"""
DigitalTutor Bot - Deadline Reminder Scheduler
Автоматические напоминания о дедлайнах
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Global scheduler reference
_scheduler = None


async def check_deadlines_and_remind(bot):
    """Check upcoming deadlines and send reminders to students"""
    from bot.models import AsyncSessionContext, StudentWork, User  # Deadline removed
    
    now = datetime.utcnow()
    
    try:
        async with AsyncSessionContext() as session:
            # Get all active works with deadlines
            result = await session.execute(
                select(StudentWork, User)
                .join(User, StudentWork.student_id == User.id)
                .where(
                    StudentWork.deadline.isnot(None),
                    StudentWork.status.notin_(['accepted', 'rejected']),
                    StudentWork.is_archived == False,
                    User.is_active == True,
                    User.telegram_id.isnot(None),
                )
            )
            works_with_users = result.all()
            
            reminded_count = 0
            
            for work, user in works_with_users:
                if not work.deadline or not user.telegram_id:
                    continue
                
                days_left = (work.deadline - now).days
                work_key = f"deadline_reminded_{work.id}_{user.telegram_id}"
                
                # 7 days before - first reminder
                if days_left == 7:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"📅 <b>Напоминание о дедлайне</b>\n\n"
                                 f"📝 Работа: {work.title}\n"
                                 f"📆 Дедлайн: {work.deadline.strftime('%d.%m.%Y')}\n"
                                 f"⏳ Осталось: 7 дней\n\n"
                                 f"Не забудьте сдать работу вовремя!",
                            parse_mode="HTML"
                        )
                        reminded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send 7-day reminder to {user.telegram_id}: {e}")
                
                # 3 days before - second reminder
                elif days_left == 3:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"⏰ <b>Дедлайн через 3 дня!</b>\n\n"
                                 f"📝 Работа: {work.title}\n"
                                 f"📆 Дедлайн: {work.deadline.strftime('%d.%m.%Y')}\n"
                                 f"⏳ Осталось: 3 дня\n\n"
                                 f"Если нужна помощь — нажмите «💬 Написать руководителю»",
                            parse_mode="HTML"
                        )
                        reminded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send 3-day reminder to {user.telegram_id}: {e}")
                
                # 1 day before - urgent
                elif days_left == 1:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"🚨 <b>Дедлайн ЗАВТРА!</b>\n\n"
                                 f"📝 Работа: {work.title}\n"
                                 f"📆 Дедлайн: {work.deadline.strftime('%d.%m.%Y')}\n\n"
                                 f"Срочно завершите работу и сдайте через «➕ Сдать работу»!",
                            parse_mode="HTML"
                        )
                        reminded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send 1-day reminder to {user.telegram_id}: {e}")
                
                # Overdue
                elif days_left < 0 and days_left >= -1:
                    try:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"⚠️ <b>Дедлайн ПРОПУЩЕН!</b>\n\n"
                                 f"📝 Работа: {work.title}\n"
                                 f"📆 Был: {work.deadline.strftime('%d.%m.%Y')}\n"
                                 f"Просрочено: {abs(days_left)} дн.\n\n"
                                 f"Сдайте работу как можно скорее через «➕ Сдать работу».\n"
                                 f"Свяжитесь с руководителем через «💬 Написать руководителю»",
                            parse_mode="HTML"
                        )
                        reminded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send overdue notice to {user.telegram_id}: {e}")
            
            if reminded_count > 0:
                logger.info(f"Sent {reminded_count} deadline reminders")
            
            # Notify admin about overdue works
            overdue_result = await session.execute(
                select(StudentWork, User)
                .join(User, StudentWork.student_id == User.id)
                .where(
                    StudentWork.deadline < now,
                    StudentWork.status == 'submitted',
                    StudentWork.is_archived == False,
                )
            )
            overdue_works = overdue_result.all()
            
            if overdue_works:
                from bot.config import config
                for admin_id in config.ADMIN_IDS:
                    try:
                        text = f"📊 <b>Просроченные работы: {len(overdue_works)}</b>\n\n"
                        for work, user in overdue_works[:5]:
                            days_overdue = (now - work.deadline).days
                            text += f"• {work.title[:30]} — {user.full_name} ({days_overdue}д просрочки)\n"
                        
                        if len(overdue_works) > 5:
                            text += f"\n...и ещё {len(overdue_works) - 5}"
                        
                        await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Failed to notify admin {admin_id}: {e}")
    
    except Exception as e:
        logger.error(f"Deadline check error: {e}", exc_info=True)


def start_scheduler(bot):
    """Start the deadline reminder scheduler"""
    global _scheduler
    
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        
        _scheduler = AsyncIOScheduler()
        
        # Check deadlines every day at 9:00 AM Moscow time
        _scheduler.add_job(
            check_deadlines_and_remind,
            'cron',
            hour=9,
            minute=0,
            args=[bot],
            id='deadline_reminder',
            replace_existing=True,
        )
        
        # Also check every 6 hours for overdue detection
        _scheduler.add_job(
            check_deadlines_and_remind,
            'interval',
            hours=6,
            args=[bot],
            id='deadline_check_interval',
            replace_existing=True,
        )
        
        _scheduler.start()
        logger.info("Deadline reminder scheduler started (daily at 9:00 MSK + every 6h)")
        
    except ImportError:
        logger.warning("APScheduler not installed. Deadline reminders disabled.")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


def stop_scheduler():
    """Stop the scheduler"""
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
