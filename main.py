"""
Activat VC Telegram Bot
Optimized for Render.com + Supabase
Python 3.10 | python-telegram-bot 21.x
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from telegram import Update, Poll
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode
from supabase import create_client, Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ============= LOGGING =============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============= CONFIGURATION =============
# Render автоматически предоставляет PORT для веб-сервисов
PORT = int(os.getenv('PORT', '8443'))

# Проверка версии Python
import sys
if sys.version_info >= (3, 12):
    logger.warning(f"⚠️ Python {sys.version_info.major}.{sys.version_info.minor} обнаружен. Рекомендуется 3.11")
    logger.warning("⚠️ Создайте runtime.txt с содержимым: python-3.11.10")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', '-1003812789640'))
TELEGRAM_ADMIN_IDS = [int(x.strip()) for x in os.getenv('TELEGRAM_ADMIN_IDS', '').split(',') if x.strip()]

# Thread IDs
DISCUSSION_THREAD_ID = int(os.getenv('TELEGRAM_DISCUSSION_THREAD_ID', '5'))
SIX_HANDSHAKES_THREAD_ID = int(os.getenv('TELEGRAM_SIX_HANDSHAKES_THREAD_ID', '6'))
FLOOD_THREAD_ID = int(os.getenv('TELEGRAM_FLOOD_THREAD_ID', '8'))
NETWORK_THREAD_ID = int(os.getenv('TELEGRAM_NETWORK_THREAD_ID', '7'))

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Проверка обязательных переменных
if not all([TELEGRAM_BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    logger.error("❌ Отсутствуют обязательные переменные окружения!")
    raise ValueError("Missing required environment variables")

if not TELEGRAM_ADMIN_IDS:
    logger.error("❌ TELEGRAM_ADMIN_IDS не может быть пустым!")
    raise ValueError("TELEGRAM_ADMIN_IDS is required")

# Инициализация Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("✅ Supabase подключен")
except Exception as e:
    logger.error(f"❌ Ошибка подключения Supabase: {e}")
    raise

# Глобальные переменные
scheduler = AsyncIOScheduler()
active_pitches: Dict[int, Dict] = {}

# ============= DATABASE FUNCTIONS =============

async def log_to_supabase(table: str, data: dict) -> bool:
    """Универсальная функция логирования в Supabase"""
    try:
        supabase.table(table).insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"DB error in {table}: {e}")
        await log_bot_error('error', f"DB error in {table}: {str(e)}")
        return False

async def log_bot_error(level: str, message: str):
    """Логирование ошибок бота"""
    try:
        supabase.table('bot_logs').insert({
            'level': level,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"Critical logging error: {e}")

async def log_message(user_id: int, username: str, text: str, thread_id: Optional[int] = None):
    """Логирование сообщений группы"""
    await log_to_supabase('group_logs', {
        'user_id': user_id,
        'username': username,
        'text': text,
        'thread_id': thread_id,
        'timestamp': datetime.now().isoformat()
    })

async def ensure_user_exists(user_id: int, username: str, first_name: str):
    """Создание или обновление пользователя"""
    try:
        result = supabase.table('users').select('*').eq('user_id', user_id).execute()
        if not result.data:
            await log_to_supabase('users', {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'join_date': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            })
        else:
            supabase.table('users').update({
                'last_active': datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
    except Exception as e:
        logger.error(f"User processing error: {e}")

# ============= HELPER FUNCTIONS =============

def is_admin(user_id: int) -> bool:
    """Проверка на админа"""
    return user_id in TELEGRAM_ADMIN_IDS

async def admin_only(update: Update) -> bool:
    """Проверка админских прав"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Команда только для администраторов.")
        return False
    return True

# ============= КОМАНДЫ: СОЦИАЛЬНЫЕ =============

async def shoutout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /shoutout @user причина"""
    if not await admin_only(update):
        return
    
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "Использование: /shoutout @username причина благодарности"
            )
            return
        
        username = context.args[0].replace('@', '')
        reason = ' '.join(context.args[1:])
        
        await log_to_supabase('shoutouts', {
            'from_user_id': update.effective_user.id,
            'to_username': username,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        message = f"🌟 <b>Shoutout!</b>\n\n@{username} получает благодарность за:\n<i>{reason}</i>\n\n— от {update.effective_user.first_name}"
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            message_thread_id=DISCUSSION_THREAD_ID,
            text=message,
            parse_mode=ParseMode.HTML
        )
        
        await update.message.reply_text("✅ Shoutout опубликован!")
        
    except Exception as e:
        logger.error(f"Shoutout error: {e}")
        await update.message.reply_text("❌ Ошибка при публикации")

async def challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /challenge текст"""
    if not await admin_only(update):
        return
    
    try:
        if not context.args:
            await update.message.reply_text("Использование: /challenge описание челленджа")
            return
        
        challenge_text = ' '.join(context.args)
        
        await log_to_supabase('challenges', {
            'text': challenge_text,
            'created_by': update.effective_user.id,
            'created_at': datetime.now().isoformat(),
            'is_active': True
        })
        
        message = f"🎯 <b>Новый челлендж недели!</b>\n\n{challenge_text}\n\nОтветьте на это сообщение с вашим решением!"
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            message_thread_id=DISCUSSION_THREAD_ID,
            text=message,
            parse_mode=ParseMode.HTML
        )
        
        await update.message.reply_text("✅ Челлендж запущен!")
        
    except Exception as e:
        logger.error(f"Challenge error: {e}")
        await update.message.reply_text("❌ Ошибка при запуске")

async def network_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /network текст"""
    try:
        if not context.args:
            await update.message.reply_text("Использование: /network ваш запрос на нетворкинг")
            return
        
        network_text = ' '.join(context.args)
        user = update.effective_user
        
        await log_to_supabase('networks', {
            'user_id': user.id,
            'username': user.username,
            'text': network_text,
            'timestamp': datetime.now().isoformat()
        })
        
        message = f"🤝 <b>Запрос на нетворкинг</b>\n\nОт: {user.first_name} (@{user.username})\n\n{network_text}"
        await context.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            message_thread_id=NETWORK_THREAD_ID,
            text=message,
            parse_mode=ParseMode.HTML
        )
        
        await update.message.reply_text("✅ Опубликовано в топике Нетворкинг!")
        
    except Exception as e:
        logger.error(f"Network error: {e}")
        await update.message.reply_text("❌ Ошибка публикации")

# ============= КОМАНДЫ: ПИТЧИ =============

async def ratepitch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /ratepitch - создание опроса"""
    try:
        message = await context.bot.send_poll(
            chat_id=TELEGRAM_CHAT_ID,
            message_thread_id=DISCUSSION_THREAD_ID,
            question="Оцените этот питч:",
            options=["⭐ 1", "⭐⭐ 2", "⭐⭐⭐ 3", "⭐⭐⭐⭐ 4", "⭐⭐⭐⭐⭐ 5"],
            is_anonymous=False,
            allows_multiple_answers=False
        )
        
        active_pitches[message.poll.id] = {
            'message_id': message.message_id,
            'author_id': update.effective_user.id,
            'created_at': datetime.now(),
            'chat_id': TELEGRAM_CHAT_ID,
            'thread_id': DISCUSSION_THREAD_ID
        }
        
        scheduler.add_job(
            close_pitch_poll,
            'date',
            run_date=datetime.now() + timedelta(hours=24),
            args=[context.bot, message.poll.id]
        )
        
        await update.message.reply_text("✅ Опрос создан! Результаты через 24 часа.")
        
    except Exception as e:
        logger.error(f"Ratepitch error: {e}")
        await update.message.reply_text("❌ Ошибка создания опроса")

async def close_pitch_poll(bot, poll_id: str):
    """Закрытие опроса через 24ч"""
    try:
        if poll_id not in active_pitches:
            return
        
        pitch_data = active_pitches[poll_id]
        poll = await bot.stop_poll(
            chat_id=pitch_data['chat_id'],
            message_id=pitch_data['message_id']
        )
        
        total_votes = sum(option.voter_count for option in poll.options)
        if total_votes > 0:
            weighted_sum = sum((i + 1) * option.voter_count for i, option in enumerate(poll.options))
            average_rating = weighted_sum / total_votes
            
            await log_to_supabase('pitch_ratings', {
                'author_id': pitch_data['author_id'],
                'average_rating': round(average_rating, 2),
                'total_votes': total_votes,
                'timestamp': datetime.now().isoformat()
            })
            
            await bot.send_message(
                chat_id=pitch_data['author_id'],
                text=f"📊 Результаты голосования:\n\n⭐ Средняя оценка: {average_rating:.1f}/5\n👥 Голосов: {total_votes}"
            )
        
        del active_pitches[poll_id]
        
    except Exception as e:
        logger.error(f"Close poll error: {e}")

async def mentor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mentor тема"""
    try:
        if not context.args:
            await update.message.reply_text("Использование: /mentor тема для менторства")
            return
        
        topic = ' '.join(context.args).lower()
        
        mentors = {
            'продукт': ['@mentor_product1', '@mentor_product2'],
            'маркетинг': ['@mentor_marketing1'],
            'технологии': ['@mentor_tech1', '@mentor_tech2'],
            'финансы': ['@mentor_finance1'],
            'продажи': ['@mentor_sales1']
        }
        
        found_mentors = []
        for key, values in mentors.items():
            if key in topic:
                found_mentors.extend(values)
        
        if found_mentors:
            message = f"🎓 <b>Менторы по теме '{topic}':</b>\n\n" + '\n'.join(found_mentors)
        else:
            message = "🤔 Менторы не найдены. Попробуйте уточнить запрос."
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Mentor error: {e}")
        await update.message.reply_text("❌ Ошибка поиска")

# ============= КОМАНДЫ: АНАЛИТИКА =============

async def growth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /growth - статистика"""
    if not await admin_only(update):
        return
    
    try:
        users_result = supabase.table('users').select('*').execute()
        users = users_result.data
        
        total_users = len(users)
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        new_week = sum(1 for u in users if datetime.fromisoformat(u['join_date']) > week_ago)
        new_month = sum(1 for u in users if datetime.fromisoformat(u['join_date']) > month_ago)
        active_week = sum(1 for u in users if datetime.fromisoformat(u['last_active']) > week_ago)
        
        retention_7d = (active_week / total_users * 100) if total_users > 0 else 0
        
        logs_result = supabase.table('group_logs').select('*').gte('timestamp', week_ago.isoformat()).execute()
        messages_week = len(logs_result.data)
        
        message = f"""
📈 <b>Статистика Activat VC</b>

👥 <b>Пользователи:</b>
• Всего: {total_users}
• Новых за неделю: {new_week}
• Новых за месяц: {new_month}

💬 <b>Активность:</b>
• Сообщений за неделю: {messages_week}
• Активных за неделю: {active_week}

📊 <b>Retention:</b>
• 7-дневный: {retention_7d:.1f}%

🕐 {now.strftime('%d.%m.%Y %H:%M')}
"""
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Growth error: {e}")
        await update.message.reply_text("❌ Ошибка получения статистики")

# ============= КОМАНДЫ: ТЕХНИЧЕСКИЕ =============

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /restart"""
    if not await admin_only(update):
        return
    
    try:
        await update.message.reply_text("🔄 Бот перезапускается...")
        await log_bot_error('info', 'Bot restart initiated')
        
        # На Render рестарт происходит через Dashboard или Git push
        await update.message.reply_text(
            "✅ Для полного рестарта используйте:\n"
            "1. Render Dashboard → Manual Deploy\n"
            "2. Git push для автоматического деплоя"
        )
        
    except Exception as e:
        logger.error(f"Restart error: {e}")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search слово"""
    try:
        if not context.args:
            await update.message.reply_text("Использование: /search ключевое слово")
            return
        
        search_term = ' '.join(context.args).lower()
        
        logs_result = supabase.table('group_logs')\
            .select('*')\
            .order('timestamp', desc=True)\
            .limit(100)\
            .execute()
        
        messages = logs_result.data
        found = [
            msg for msg in messages
            if msg.get('text') and search_term in msg['text'].lower()
        ][:5]
        
        if found:
            message = f"🔍 <b>Найдено {len(found)} результатов по '{search_term}':</b>\n\n"
            for i, msg in enumerate(found, 1):
                username = msg.get('username', 'Unknown')
                text = msg.get('text', '')[:100]
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%d.%m %H:%M')
                message += f"{i}. @{username} ({timestamp}):\n{text}...\n\n"
        else:
            message = f"❌ Ничего не найдено по '{search_term}'"
        
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text("❌ Ошибка поиска")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🤖 <b>Activat VC Bot</b>

<b>Для всех:</b>
/network [текст] - нетворкинг
/mentor [тема] - найти ментора
/search [слово] - поиск в истории
/help - это сообщение

<b>Только админы:</b>
/shoutout @user [причина] - благодарность
/challenge [текст] - челлендж недели
/ratepitch - оценка питча
/growth - статистика
/restart - перезапуск

<b>Авто-функции:</b>
• Архивация питчей с #pitch
• Еженедельные отчеты
• Анализ настроений
• Топ-3 питчей месяца

Присоединяйтесь к топикам! 🚀
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 Привет! Я бот Activat VC.\n\nИспользуйте /help для списка команд."
    )

# ============= ОБРАБОТКА СООБЩЕНИЙ =============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений"""
    try:
        if not update.message or not update.message.text:
            return
        
        user = update.effective_user
        message = update.message
        
        await ensure_user_exists(user.id, user.username or '', user.first_name or '')
        await log_message(user.id, user.username or '', message.text, message.message_thread_id)
        
        if '#pitch' in message.text.lower():
            await log_to_supabase('pitches', {
                'user_id': user.id,
                'username': user.username,
                'text': message.text,
                'timestamp': datetime.now().isoformat(),
                'likes': 0
            })
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка новых участников"""
    try:
        for new_member in update.message.new_chat_members:
            await ensure_user_exists(
                new_member.id,
                new_member.username or '',
                new_member.first_name or ''
            )
            
            welcome_msg = f"""
👋 Добро пожаловать, {new_member.first_name}!

Мы рады видеть вас в Activat VC!

📌 <b>Команды:</b>
/network - нетворкинг
/mentor - найти ментора
/search - поиск в истории

Присоединяйтесь к обсуждениям! 🚀
"""
            await context.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=welcome_msg,
                parse_mode=ParseMode.HTML
            )
            
    except Exception as e:
        logger.error(f"New member error: {e}")

# ============= АВТОМАТИЧЕСКИЕ ЗАДАЧИ =============

async def weekly_sentiment_analysis():
    """Еженедельный анализ настроений"""
    try:
        week_ago = datetime.now() - timedelta(days=7)
        logs_result = supabase.table('group_logs').select('text').gte('timestamp', week_ago.isoformat()).execute()
        
        positive_emojis = ['😊', '😄', '🎉', '❤️', '👍', '🔥', '✨', '💪', '🚀', '⭐']
        negative_emojis = ['😢', '😞', '😠', '👎', '💔', '😰']
        neutral_emojis = ['🤔', '🙂', '😐']
        
        positive_count = sum(sum(msg.get('text', '').count(e) for e in positive_emojis) for msg in logs_result.data)
        negative_count = sum(sum(msg.get('text', '').count(e) for e in negative_emojis) for msg in logs_result.data)
        neutral_count = sum(sum(msg.get('text', '').count(e) for e in neutral_emojis) for msg in logs_result.data)
        
        total_emojis = positive_count + negative_count + neutral_count
        sentiment_score = ((positive_count - negative_count) / total_emojis * 100) if total_emojis > 0 else 0
        
        await log_to_supabase('sentiment_logs', {
            'week_start': week_ago.isoformat(),
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'sentiment_score': round(sentiment_score, 2),
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"Sentiment analysis: score={sentiment_score:.2f}")
        
    except Exception as e:
        logger.error(f"Sentiment error: {e}")
        await log_bot_error('error', f"Sentiment failed: {str(e)}")

async def weekly_challenge_summary(bot):
    """Еженедельная сводка челленджа"""
    try:
        week_ago = datetime.now() - timedelta(days=7)
        challenges_result = supabase.table('challenges')\
            .select('*')\
            .eq('is_active', True)\
            .gte('created_at', week_ago.isoformat())\
            .execute()
        
        if not challenges_result.data:
            return
        
        logs_result = supabase.table('group_logs')\
            .select('*')\
            .eq('thread_id', DISCUSSION_THREAD_ID)\
            .gte('timestamp', week_ago.isoformat())\
            .execute()
        
        response_count = len(logs_result.data)
        participants = len(set(log['user_id'] for log in logs_result.data))
        
        summary = f"""
📊 <b>Итоги челленджа недели</b>

🎯 {challenges_result.data[0]['text'][:100]}...

📈 <b>Результаты:</b>
• Ответов: {response_count}
• Участников: {participants}

Спасибо всем! 🎉
"""
        
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            message_thread_id=DISCUSSION_THREAD_ID,
            text=summary,
            parse_mode=ParseMode.HTML
        )
        
        supabase.table('challenges').update({'is_active': False}).eq('id', challenges_result.data[0]['id']).execute()
        
    except Exception as e:
        logger.error(f"Challenge summary error: {e}")

async def monthly_pitch_archive(bot):
    """Ежемесячный топ-3 питчей"""
    try:
        month_ago = datetime.now() - timedelta(days=30)
        pitches_result = supabase.table('pitches')\
            .select('*')\
            .gte('timestamp', month_ago.isoformat())\
            .order('likes', desc=True)\
            .limit(3)\
            .execute()
        
        if not pitches_result.data:
            return
        
        message = "🏆 <b>Топ-3 питча месяца:</b>\n\n"
        for i, pitch in enumerate(pitches_result.data, 1):
            username = pitch.get('username', 'Unknown')
            likes = pitch.get('likes', 0)
            text = pitch.get('text', '')[:150]
            message += f"{i}. @{username} (❤️ {likes})\n{text}...\n\n"
        
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            message_thread_id=DISCUSSION_THREAD_ID,
            text=message,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Pitch archive error: {e}")

async def check_bot_uptime(bot):
    """Проверка uptime каждые 5 минут"""
    try:
        me = await bot.get_me()
        logger.info(f"Uptime check: Bot {me.username} is alive")
    except Exception as e:
        logger.error(f"Uptime check failed: {e}")
        await log_bot_error('critical', f"Bot offline: {str(e)}")

# ============= SCHEDULER =============

def setup_scheduler(application: Application):
    """Настройка планировщика"""
    
    scheduler.add_job(
        weekly_sentiment_analysis,
        CronTrigger(day_of_week='mon', hour=10, minute=0),
        id='weekly_sentiment'
    )
    
    scheduler.add_job(
        weekly_challenge_summary,
        CronTrigger(day_of_week='sun', hour=20, minute=0),
        args=[application.bot],
        id='weekly_challenge'
    )
    
    scheduler.add_job(
        monthly_pitch_archive,
        CronTrigger(day=1, hour=12, minute=0),
        args=[application.bot],
        id='monthly_pitches'
    )
    
    scheduler.add_job(
        check_bot_uptime,
        'interval',
        minutes=5,
        args=[application.bot],
        id='uptime_check'
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started")

# ============= INITIALIZATION =============

async def post_init(application: Application):
    """Инициализация после запуска"""
    await log_bot_error('info', 'Bot started on Render')
    logger.info("✅ Bot initialized successfully")

# ============= MAIN =============

def main():
    """Основная функция"""
    
    logger.info("🚀 Starting Activat VC Bot on Render.com")
    logger.info(f"📍 Chat ID: {TELEGRAM_CHAT_ID}")
    logger.info(f"👮 Admins: {len(TELEGRAM_ADMIN_IDS)}")
    
    # Создаем приложение БЕЗ JobQueue (используем только APScheduler)
    # job_queue=False критически важно для Python 3.14+
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .job_queue(None)  # КРИТИЧНО: отключаем встроенный JobQueue
        .concurrent_updates(True)
        .build()
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("shoutout", shoutout_command))
    application.add_handler(CommandHandler("challenge", challenge_command))
    application.add_handler(CommandHandler("network", network_command))
    application.add_handler(CommandHandler("ratepitch", ratepitch_command))
    application.add_handler(CommandHandler("mentor", mentor_command))
    application.add_handler(CommandHandler("growth", growth_command))
    application.add_handler(CommandHandler("restart", restart_command))
    application.add_handler(CommandHandler("search", search_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member))
    
    # Настраиваем планировщик
    setup_scheduler(application)
    
    logger.info("✅ Starting polling mode (optimal for Render free tier)")
    
    # Запускаем бота в polling режиме (оптимально для Render)
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
