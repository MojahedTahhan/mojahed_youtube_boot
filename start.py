
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp
import os

TOKEN = '7813000878:AAFMCYYJ5bVOyvnHgObBnMO-KOdLcWcYIHI'
user_links = {}

def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎥 تحميل فيديو 480p", callback_data="video_480")],
        [InlineKeyboardButton("🎥 تحميل فيديو عالي الجودة", callback_data="video_hd")],
        [InlineKeyboardButton("🎧 تحميل صوت MP3", callback_data="audio_mp3")],
        [InlineKeyboardButton("🔁 رجوع للقائمة", callback_data="back_to_menu")]
    ])

async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    if "youtube.com" not in message and "youtu.be" not in message:
        await update.message.reply_text("❌ هذا ليس رابط يوتيوب.")
        return

    user_id = update.effective_user.id
    user_links[user_id] = message

    await update.message.reply_text(
        "✅ تم استلام الرابط، اختر ما تريد تحميله:",
        reply_markup=get_main_menu()
    )

async def handle_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_links:
        await query.edit_message_text("❌ لم أستلم منك رابط يوتيوب بعد. أرسل الرابط أولاً.")
        return

    choice = query.data
    url = user_links[user_id]

    msg = await query.edit_message_text("🔄 جاري بدء التحميل...")
    context.chat_data['progress_msg'] = msg
    context.chat_data['last_percent'] = 0

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = int(downloaded / total * 100)
                if percent - context.chat_data.get('last_percent', 0) >= 5:
                    context.chat_data['last_percent'] = percent
                    try:
                        context.application.create_task(
                            context.chat_data['progress_msg'].edit_text(f"📥 التحميل جاري: {percent}%")
                        )
                    except:
                        pass

    try:
        if choice == "video_480":
            ydl_opts = {
                'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
                'outtmpl': 'video.%(ext)s',
                'merge_output_format': 'mp4',
                'progress_hooks': [progress_hook]
            }
            ext = 'mp4'

        elif choice == "video_hd":
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': 'video.%(ext)s',
                'merge_output_format': 'mp4',
                'progress_hooks': [progress_hook]
            }
            ext = 'mp4'

        elif choice == "audio_mp3":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': 'audio.%(ext)s',
                'progress_hooks': [progress_hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }
            ext = 'mp3'

        else:
            await query.message.reply_text("❌ خيار غير معروف.")
            return

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if ext == "mp3":
                filename = filename.rsplit(".", 1)[0] + ".mp3"

        file_size = os.path.getsize(filename)

        await context.chat_data['progress_msg'].edit_text("✅ تم التحميل، جارٍ الإرسال...")

        if file_size < 49 * 1024 * 1024:
            with open(filename, 'rb') as file:
                if ext == "mp3":
                    await query.message.reply_audio(audio=file)
                else:
                    await query.message.reply_video(video=file)
        else:
            await query.message.reply_text("⚠️ الملف كبير جدًا لإرساله. إليك رابط الفيديو:")
            await query.message.reply_text(info.get("webpage_url", url))

        os.remove(filename)

    except Exception as e:
        await query.message.reply_text(f"❌ حدث خطأ: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_youtube_link))
    app.add_handler(CallbackQueryHandler(handle_menu_choice))
    app.run_polling()
