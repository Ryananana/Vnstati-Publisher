from binascii import Error
from datetime import tzinfo
import subprocess
import logging
import os, sys
import telegram
import time, datetime, pytz
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from threading import Thread
from functools import wraps

vnstati_setting = ["vnstati", "-d", "-vs", "-o", "/tmp/vnstat.png"]
BOT_TOKEN = "BOT_TOKEN"
HOSTNAME = "HOSTNAME"
LIST_OF_ADMINS = [Admin's CHAT_ID]

"""Runtime Logging"""
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telegram.Bot(token=BOT_TOKEN)
localtime = time.asctime(time.localtime(time.time()))

def start(update: Update, context: CallbackContext):
    """Display chat id."""
    update.effective_message.reply_html(
        f'Your chat id is <code>{update.effective_chat.id}</code>.'
    )

def img_generator(args):
    ret = subprocess.run(args)
    if ret.returncode == 0:
        print("Image has been generated at: " + localtime)
    else:
        print("error:",ret)

def img_push(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    img_generator(vnstati_setting)
    img = os.path.abspath("/tmp/vnstat.png")
    bot.send_photo(chat_id, open(img,'rb'), caption = HOSTNAME + '\n' + "Generated at:" + localtime)

def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def periodic_img_push(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    context.job_queue.run_daily(img_publisher, datetime.time(hour=0, minute=0, tzinfo=pytz.timezone('Asia/Shanghai')), days=(0, 1, 2, 3, 4, 5, 6), context=chat_id, name=str(chat_id))
    text = 'Periodic image publisher successfully set!'
    update.message.reply_text(text)

def img_publisher(context: CallbackContext):
    img = os.path.abspath("/tmp/vnstat.png")
    chat_id = context.job.context
    img_generator(vnstati_setting)
    bot.send_photo(chat_id, open(img,'rb'), caption = HOSTNAME + '\n' + "Generated at:" + localtime)

def unset(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Periodic image publisher successfully cancelled!' if job_removed else 'You have no active publisher.'
    update.message.reply_text(text)

def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            text = "Unauthorized access denied for {}.".format(user_id)
            update.message.reply_text(text)
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def main():
    """Run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(BOT_TOKEN, use_context=True)

    def stop_and_restart():
        """Gracefully stop the Updater and replace the current process with a new one"""
        updater.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)
    
    @restricted
    def restart(update, context):
        update.message.reply_text('Bot is restarting...')
        Thread(target=stop_and_restart).start()

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Register the commands...
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('usage', img_push))
    dispatcher.add_handler(CommandHandler('set', periodic_img_push))
    dispatcher.add_handler(CommandHandler('unset', unset))
    dispatcher.add_handler(CommandHandler('restart', restart))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
