import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from io import BytesIO
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio

load_dotenv()
TOKEN = "MTQwMjYzODg4MDUyNzc0NTE4OA.Guoi1r.7PQ9n5HPkmPlwv0ndbCrM1IAUlJWTZtQ_xDTNc"
OCR_API_KEY = "K84507104388957"
ROLE_ID = 1402640502657912884

# ✅ ID ข้อความที่ต้องไม่ถูกลบ
EXCLUDED_MESSAGE_IDS = [
    1402757155307655250
]

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 📄 OCR ด้วย aiohttp
async def process_image_online(image_url):
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(image_url) as img_resp:
                image_bytes = await img_resp.read()
            form_data = aiohttp.FormData()
            form_data.add_field('file', image_bytes, filename='image.png')
            form_data.add_field('apikey', OCR_API_KEY)
            form_data.add_field('language', 'eng')
            async with session.post('https://api.ocr.space/parse/image', data=form_data) as resp:
                result = await resp.json()
            if result.get("IsErroredOnProcessing"):
                return None, result.get("ErrorMessage", "Unknown OCR error")
            if not result.get("ParsedResults"):
                return None, "OCR ไม่สามารถอ่านข้อความจากภาพได้"
            text = result["ParsedResults"][0].get("ParsedText")
            if not text:
                return None, "ไม่พบข้อความในภาพ"
            return text, None
    except Exception as e:
        return None, str(e)

# ⏳ ลบข้อความโดยยกเว้นบางข้อความ
async def purge_all_after_delay(channel, delay=10, excluded_message_ids=[]):
    await asyncio.sleep(delay)

    def check(message):
        return message.id not in excluded_message_ids

    await channel.purge(check=check)

# 📶 บอทออนไลน์
@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์ในชื่อ {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"📡 ซิงค์คำสั่ง /verify แล้ว ({len(synced)} คำสั่ง)")
    except Exception as e:
        print(f"❌ Sync Error: {e}")

# 🧩 Slash command /verify
@bot.tree.command(name="verify", description="เริ่มการยืนยันตัวตนด้วยภาพ")
async def verify(interaction: discord.Interaction):
    await interaction.response.send_message(
        "📌 กรุณาส่ง โปรไฟล์ในเกม เพื่อยืนยันสมาชิกแฟม",
        ephemeral=True
    )

# 🔠 Prefix command !verify
@bot.command(name="verify")
async def verify_command(ctx):
    await ctx.send(
        "📌 กรุณาส่ง โปรไฟล์ในเกม เพื่อยืนยันสมาชิกแฟม"
    )

# 📩 รับภาพและประมวลผล OCR
@bot.event
async def on_message(message):
    if message.author.bot or not message.attachments or isinstance(message.channel, discord.DMChannel):
        return

    for attachment in message.attachments:
        if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
            checking_embed = discord.Embed(
                title="𓆩 🧸 𓆪 Fam [CLE]",
                description="🔍 กำลังตรวจสอบภาพ\nเพื่อยืนยันสมาชิก CLE",
                colour=0x00ff00,
                timestamp=datetime.now()
            )
            checking_embed.set_image(
                url="https://cdn.discordapp.com/attachments/1402663419462815744/1402671143969886259/giphy-downsized.gif"
            )
            checking_embed.set_footer(text="Make Embed By Wakumi")
            msg = await message.channel.send(embed=checking_embed)

            try:
                text, error = await process_image_online(attachment.url)

                if error:
                    error_embed = discord.Embed(
                        title="❗ OCR Error",
                        description=f"{error}",
                        color=discord.Color.red()
                    )
                    await msg.edit(embed=error_embed)
                    await purge_all_after_delay(message.channel, excluded_message_ids=EXCLUDED_MESSAGE_IDS)
                    return

                print("📷 ข้อความ OCR:", text)
                if text and "[cle]" in text.lower():
                    role = message.guild.get_role(ROLE_ID)
                    if role:
                        await message.author.add_roles(role)

                        try:
                            current_nick = message.author.display_name
                            if not current_nick.startswith("[CLE]"):
                                new_nick = f"[CLE] {current_nick}"
                                await message.author.edit(nick=new_nick)
                        except Exception as e:
                            print(f"❗ Error changing nickname: {e}")

                        success_embed = discord.Embed(
                            title="✅ ยืนยันตัวตนสำเร็จ! 🎉",
                            description="ได้รับบทบาทเรียบร้อยแล้ว และเปลี่ยนชื่อเรียบร้อย",
                            color=discord.Color.green()
                        )
                        await msg.edit(embed=success_embed)
                        await purge_all_after_delay(message.channel, excluded_message_ids=EXCLUDED_MESSAGE_IDS)
                    else:
                        no_role_embed = discord.Embed(
                            title="⚠️ ไม่พบ Role ตาม ID",
                            color=discord.Color.orange()
                        )
                        await msg.edit(embed=no_role_embed)
                        await purge_all_after_delay(message.channel, excluded_message_ids=EXCLUDED_MESSAGE_IDS)
                else:
                    fail_embed = discord.Embed(
                        title="❌ ไม่พบคำว่า `[CLE]` ในภาพ",
                        description="กรุณาส่งภาพใหม่อีกครั้ง",
                        color=discord.Color.red()
                    )
                    await msg.edit(embed=fail_embed)
                    await purge_all_after_delay(message.channel, excluded_message_ids=EXCLUDED_MESSAGE_IDS)
            except Exception as e:
                print(f"❗ OCR Error: {e}")
                error_embed = discord.Embed(
                    title="⚠️ เกิดข้อผิดพลาดในการวิเคราะห์ภาพ",
                    description=str(e),
                    color=discord.Color.red()
                )
                await msg.edit(embed=error_embed)
                await purge_all_after_delay(message.channel, excluded_message_ids=EXCLUDED_MESSAGE_IDS)

bot.run(TOKEN)