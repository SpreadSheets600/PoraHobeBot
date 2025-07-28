import os
import dotenv
import discord
import datetime
from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    render_template,
    render_template_string,
    redirect,
    url_for,
    flash,
    send_file,
    session,
)
from utils.database import get_note_by_id, update_note
from PIL import Image, ImageDraw, ImageFont
from werkzeug.utils import secure_filename
import threading
import requests
import sqlite3
import io

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "docx",
    "pptx",
    "txt",
    "zip",
    "rar",
    "csv",
    "xlsx",
    "mp4",
    "mp3",
}

SUBJECT_CHANNELS = {
    "c": 1387809784031608994,
    "dsa": 1387809822279208990,
    "math": 1387810459930988687,
    "python": 1387809701865197689,
    "economics": 1387810261527691344,
    "electronics": 1387810558153068594,
    "computer organization": 1387810527983567040,
    "other": 1398993763673575424,
}

ADMIN = [
    123456789012345678,
]


dotenv.load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)


app = Flask(__name__, template_folder="templates")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://0.0.0.0:PORT/callback")
DISCORD_OAUTH_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_API_USER_URL = "https://discord.com/api/users/@me"
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

PORT = int(os.getenv("PORT", 5000))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_note_to_db(title, file_url, channel_id, user_id, subject):
    try:
        conn = sqlite3.connect("notes.db")
        cursor = conn.cursor()
        import datetime

        timestamp = datetime.datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO notes (title, content, file_url, channel_id, user_id, timestamp, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title, "", file_url, str(channel_id), str(user_id), timestamp, subject),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Flask] Failed to save note to DB: {e}")


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if not session.get("user_id"):
        flash("Please Log In With Discord To Upload Notes!", "error")
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    username = session.get("username")
    avatar_url = session.get("avatar_url")

    if request.method == "POST":
        subject = request.form.get("subject", "").strip().lower()
        upload_type = request.form.get("upload_type")
        link = request.form.get("link", "").strip()
        custom_title = request.form.get("title", "").strip()

        if not subject or subject not in SUBJECT_CHANNELS:
            flash("Invalid Or Missing Subject.", "error")
            return redirect(request.url)

        if upload_type == "file":
            files = request.files.getlist("file")
            if not files or all(f.filename == "" for f in files):
                flash("No File Selected.", "error")
                return redirect(request.url)

            for file in files:
                if not allowed_file(file.filename):
                    flash(f"File Type Not Allowed: {file.filename}", "error")
                    return redirect(request.url)
                file.seek(0, os.SEEK_END)
                filesize = file.tell()
                file.seek(0)
                if filesize > 100 * 1024 * 1024:
                    flash(f"File Too Large (Max 100MB): {file.filename}", "error")
                    return redirect(request.url)

            for file in files:
                filename = secure_filename(file.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                try:
                    file.save(save_path)
                except Exception as e:
                    flash(f"Failed To Save File : {filename} ({e})", "error")
                    return redirect(request.url)

                file_url = url_for("uploaded_file", filename=filename, _external=True)

                note_title = (
                    custom_title if len(files) == 1 and custom_title else filename
                )

                try:
                    requests.post(
                        "http://0.0.0.0:PORT/api/upload",
                        json={
                            "subject": subject,
                            "user_id": user_id,
                            "file_url": file_url,
                            "title": note_title,
                            "filesize": os.path.getsize(save_path),
                        },
                    )
                except Exception as e:
                    flash(f"Failed To Notify Via Discord Bot : {e}", "error")

                save_note_to_db(
                    note_title, file_url, SUBJECT_CHANNELS[subject], user_id, subject
                )

            flash("File(s) Uploaded And Will Be Sent To Discord!", "success")
            return redirect(request.url)

        elif upload_type == "link":
            if not link:
                flash("No Link Provided.", "error")
                return redirect(request.url)

            try:
                requests.post(
                    "http://0.0.0.0:PORT/api/upload",
                    json={
                        "subject": subject,
                        "user_id": user_id,
                        "file_url": link,
                        "title": link,
                        "filesize": 0,
                    },
                )
            except Exception as e:
                flash(f"Failed To Notify Via Discord Bot : {e}", "error")

            save_note_to_db(link, link, SUBJECT_CHANNELS[subject], user_id, subject)
            flash("Link Uploaded And Will Be Sent To Discord!", "success")

            return redirect(request.url)

        else:
            flash("Invalid Upload Type.", "error")
            return redirect(request.url)

    subjects = list(SUBJECT_CHANNELS.keys())
    return render_template(
        "upload.html",
        subjects=subjects,
        user_id=user_id,
        username=username,
        avatar_url=avatar_url,
    )


@app.route("/login")
def login():
    discord_auth_url = (
        f"{DISCORD_OAUTH_AUTHORIZE_URL}?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
    )
    return redirect(discord_auth_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Missing Code In Callback", 400

    token_data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify guilds.join",
    }

    token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post(
        DISCORD_OAUTH_TOKEN_URL, data=token_data, headers=token_headers
    )

    if token_resp.status_code != 200:
        return f"Token Exchange Failed : {token_resp.text}", 400

    token_json = token_resp.json()
    access_token = token_json.get("access_token")

    if not access_token:
        return "Access Token Not Found", 400

    user_headers = {"Authorization": f"Bearer {access_token}"}
    user_resp = requests.get(DISCORD_API_USER_URL, headers=user_headers)

    if user_resp.status_code != 200:
        return f"Failed To Fetch User Info : {user_resp.text}", 400

    user_json = user_resp.json()
    user_id = user_json["id"]

    add_user_url = (
        f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{user_id}"
    )
    bot_headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json",
    }

    add_data = {
        "access_token": access_token,
        "nick": user_json.get("username"),
    }

    add_user_resp = requests.put(
        add_user_url,
        headers=bot_headers,
        json=add_data,
    )

    if add_user_resp.status_code not in (201, 204):
        print(
            "[ERROR] Failed To Add User :",
            add_user_resp.status_code,
            add_user_resp.text,
        )
        return "Failed To Add User To Guild", 400

    session["user_id"] = user_json["id"]
    session["username"] = user_json["username"]
    session["avatar_url"] = (
        f"https://cdn.discordapp.com/avatars/{user_json['id']}/{user_json['avatar']}.png"
        if user_json.get("avatar")
        else None
    )

    print(f"[INFO] User {user_json['username']} Added To Guild Successfully")
    return redirect(url_for("upload_file"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged Out")
    return redirect(url_for("upload_file"))


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# DownloadButton class must be defined before usage
class DownloadButton(discord.ui.View):
    def __init__(self, download_link: str):
        super().__init__(timeout=None)
        self.download_link = download_link
        button_download = discord.ui.Button(
            label="Download", style=discord.ButtonStyle.url, url=self.download_link
        )
        self.add_item(button_download)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    data = request.json

    subject = data.get("subject")
    user_id = data.get("user_id")
    file_title = data.get("title")

    file_url = data.get("file_url")
    file_size = data.get("filesize", 0)

    channel_id = SUBJECT_CHANNELS.get(subject)

    if not channel_id:
        return jsonify({"error": "Invalid Subject"}), 400

    async def send_note():
        channel = bot.get_channel(channel_id)

        if channel:
            embed = discord.Embed(
                title=f"Note : {file_title}",
                description=f"Uploaded For **{subject.title()}**",
                color=discord.Color.blue(),
            )

            embed.add_field(name="File Size", value=f"{file_size}")

            embed.add_field(
                name="Uploaded By",
                value=(
                    f"<@{user_id}>"
                    if user_id
                    else "Unknown User ( Nirghat Subhrajit XD )"
                ),
            )

            await channel.send(embed=embed, view=DownloadButton(download_link=file_url))

    bot.loop.create_task(send_note())
    return jsonify({"status": "ok"})


@app.route("/notes", methods=["GET"])
def view_notes():
    q = request.args.get("q", "").strip()
    tag = request.args.get("tag", "").strip().lower()
    conn = sqlite3.connect("notes.db")

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM notes"

    params = []
    filters = []

    if tag:
        filters.append("tags = ?")
        params.append(tag)

    if q:
        filters.append("title LIKE ?")
        params.append(f"%{q}%")

    if filters:
        query += " WHERE " + " AND ".join(filters)

    query += " ORDER BY timestamp DESC"

    cursor.execute(query, params)
    notes = cursor.fetchall()
    conn.close()

    notes = [dict(note) for note in notes]
    subjects = list(SUBJECT_CHANNELS.keys())

    total_users = len(set(note["user_id"] for note in notes if note["user_id"]))

    is_admin = False
    user_id = session.get("user_id")
    username = session.get("username").split("#")[0]
    avatar_url = session.get("avatar_url")
    if user_id and int(user_id) in ADMIN:
        is_admin = True

    return render_template(
        "notes_list.html",
        notes=notes,
        subjects=subjects,
        request=request,
        is_admin=is_admin,
        user_id=user_id,
        username=username,
        avatar_url=avatar_url,
        total_users=total_users,
    )


@app.route("/edit_note/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):
    user_id = session.get("user_id")
    conn = sqlite3.connect("notes.db")
    conn.row_factory = sqlite3.Row

    note = get_note_by_id(conn, note_id)
    if not note:
        conn.close()
        return render_template_string(
            "<h2>Note not found.</h2><a href='/notes'>Back To Notes List</a>"
        )

    if not (
        user_id and (int(user_id) in ADMIN or str(user_id) == str(note.get("user_id")))
    ):
        conn.close()
        flash("You are not authorized to edit this note.", "error")
        return redirect(url_for("view_notes"))
    message = None
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        file_url = request.form.get("file_url", "").strip()
        tags = request.form.get("tags", "").strip()
        update_note(
            conn, note_id, title=title, content=content, file_url=file_url, tags=tags
        )
        message = "Note updated successfully!"

        note = get_note_by_id(conn, note_id)
    username = session.get("username")
    avatar_url = session.get("avatar_url")
    conn.close()
    return render_template(
        "edit_note.html",
        note=note,
        message=message,
        user_id=user_id,
        username=username,
        avatar_url=avatar_url,
    )


@app.route("/delete_note/<int:note_id>", methods=["POST"])
def delete_note(note_id):
    user_id = session.get("user_id")

    conn = sqlite3.connect("notes.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()

    if not note:
        flash("Note Not Found!", "error")
        return redirect(url_for("view_notes"))

    note_user_id = note[0]

    if (
        not note_user_id
        or not user_id
        or not (int(user_id) in ADMIN or int(note_user_id) == int(user_id))
    ):
        flash("You Are Not Authorized To Delete Notes!", "error")
        return redirect(url_for("view_notes"))

    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

    flash("Note deleted successfully!", "success")
    return redirect(url_for("view_notes"))


@app.route("/frontpages", methods=["GET", "POST"])
def generate_frontpage():
    if not session.get("user_id"):
        flash("Please Log In With Discord Use This Feature", "error")
        return redirect(url_for("login"))

    user_id = session.get("user_id")
    username = session.get("username")
    avatar_url = session.get("avatar_url")

    subject_codes = {
        "Data Structures & Algorithms Lab": "PCC - CS391",
        "Computer Organization Lab": "PCC - CS392",
        "IT Workshop": "PCC - CS393",
        "Analog & Digital Electronics Lab": "ES - CS391",
    }

    if request.method == "POST":
        name = request.form["name"]
        roll = request.form["roll"]
        reg = request.form["reg"]

        subject = request.form["subject"]
        section = request.form["section"]

        semester = int(request.form["semester"])
        if semester == 1:
            semester_final = "1ST"
        elif semester == 2:
            semester_final = "2ND"
        elif semester == 3:
            semester_final = "3RD"
        elif semester >= 4 and semester <= 8:
            semester_final = "4TH"

        year = int(request.form["year"])
        if year == 1:
            year_final = "1ST"
        elif year == 2:
            year_final = "2ND"
        elif year == 3:
            year_final = "3RD"
        elif year == 4:
            year_final = "4TH"

        print(
            f"Received Data : Name : {name} \nRoll : {roll} \nReg : {reg} \nSection : {section} \nSubject : {subject}"
        )

        subject_code = subject_codes.get(subject, "N/A")

        img = Image.open("static/blank_template.png")
        draw = ImageDraw.Draw(img)

        font = ImageFont.truetype("static/Sans.ttf", size=45)

        x = 140
        y = 800
        line_height = 60

        draw.text((x, y), f"Name : {name}", font=font, fill="black")
        draw.text((x, y + line_height), f"Roll No. : {roll}", font=font, fill="black")
        draw.text((x, y + 2 * line_height), f"Reg No. : {reg}", font=font, fill="black")

        draw.text((x, y + 4.5 * line_height), "Stream : CSE", font=font, fill="black")
        draw.text(
            (x, y + 5.5 * line_height), f"Section : {section}", font=font, fill="black"
        )

        draw.text(
            (x, y + 7.5 * line_height),
            f"Semester : {semester_final}",
            font=font,
            fill="black",
        )
        draw.text(
            (x, y + 8.5 * line_height), f"Year : {year_final}", font=font, fill="black"
        )

        draw.text(
            (x, y + 10.5 * line_height),
            f"Subject Code : {subject_code}",
            font=font,
            fill="black",
        )
        draw.text(
            (x, y + 11.5 * line_height),
            f"Subject Name : {subject}",
            font=font,
            fill="black",
        )

        img_io = io.BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)

        return send_file(
            img_io,
            mimetype="image/png",
            as_attachment=True,
            download_name=f"{name}-{subject}-FrontPageCover.png",
        )

    subjects = [
        "Data Structures & Algorithms Lab",
        "Computer Organization Lab",
        "IT Workshop",
        "Analog & Digital Electronics Lab",
    ]
    return render_template(
        "form.html",
        subjects=subjects,
        user_id=user_id,
        username=username,
        avatar_url=avatar_url,
    )


@app.route("/wallpapers", methods=["GET", "POST"])
def upload_wallpapers():
    if request.method == "GET":
        if not session.get("user_id"):
            flash("Please Log In With Discord Use This Feature", "error")
            return redirect(url_for("login"))

        user_id = session.get("user_id")
        username = session.get("username")
        avatar_url = session.get("avatar_url")

        conn = sqlite3.connect("notes.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM notes WHERE tags='wallpaper' ORDER BY timestamp DESC"
        )
        wallpapers = cursor.fetchall()
        conn.close()

        wallpapers = [dict(w) for w in wallpapers]
        user_id = session.get("user_id")

        return render_template(
            "wallpapers.html",
            wallpapers=wallpapers,
            user_id=user_id,
            username=username,
            avatar_url=avatar_url,
        )

    elif request.method == "POST":
        if not session.get("user_id"):
            flash("Please Log In With Discord Use This Feature", "error")
            return redirect(url_for("login"))

        user_id = session.get("user_id")
        files = request.files.getlist("wallpaper")

        if not files or all(f.filename == "" for f in files):
            flash("No Wallpaper Selected.", "error")
            return redirect(url_for("upload_file"))

        wallpaper_folder = os.path.join(app.config["UPLOAD_FOLDER"], "wallpapers")

        os.makedirs(wallpaper_folder, exist_ok=True)

        for file in files:
            if not allowed_file(file.filename):
                flash(f"File Type Not Allowed: {file.filename}", "error")
                return redirect(url_for("upload_file"))
            file.seek(0, os.SEEK_END)
            filesize = file.tell()
            file.seek(0)
            if filesize > 50 * 1024 * 1024:
                flash(f"Wallpaper Too Large (Max 50MB): {file.filename}", "error")
                return redirect(url_for("upload_file"))
        for file in files:
            filename = secure_filename(file.filename)
            save_path = os.path.join(wallpaper_folder, filename)
            try:
                file.save(save_path)
            except Exception as e:
                flash(f"Failed To Save Wallpaper : {filename} ({e})", "error")
                return redirect(url_for("upload_file"))
            file_url = url_for("serve_wallpaper", filename=filename, _external=True)
            try:
                conn = sqlite3.connect("notes.db")
                cursor = conn.cursor()
                timestamp = datetime.datetime.utcnow().isoformat()
                cursor.execute(
                    """
                    INSERT INTO notes (title, content, file_url, channel_id, user_id, timestamp, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        filename,
                        "",
                        file_url,
                        "wallpaper",
                        str(user_id),
                        timestamp,
                        "wallpaper",
                    ),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Flask] Failed to save wallpaper to notes DB: {e}")
        flash("Wallpaper Uploaded Successfully!", "success")

        return redirect(url_for("upload_file"))
    return redirect(url_for("upload_file"))


@app.route("/uploads/wallpapers/<filename>")
def serve_wallpaper(filename):
    wallpaper_folder = os.path.join(app.config["UPLOAD_FOLDER"], "wallpapers")
    return send_from_directory(wallpaper_folder, filename)


def run_flask():
    app.run(host="0.0.0.0", port=PORT, debug=True, use_reloader=False)


@bot.event
async def on_ready():

    print("--------------------------------")
    print("----- + LOADED PoraHobe  + -----")
    print("--------------------------------")

    await bot.change_presence(activity=discord.Game(name="With Life"))

    start_time = datetime.datetime.now()
    bot.start_time = start_time

    print("----- + LOADING COMMANDS + -----")
    print("--------------------------------")

    for command in bot.walk_application_commands():
        print(f"----- + Loaded : {command.name} ")

    print("--------------------------------")
    print(f"---- + Loaded : {len(list(bot.walk_application_commands()))}  Commands + -")
    print("--------------------------------")

    print("------- + LOADING COGS + -------")
    print(f"----- + Loaded : {len(bot.cogs)} Cogs + ------")
    print("--------------------------------")

    print("----- + Database Initialized + -----")


bot.load_extension("cogs.notes")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(TOKEN)
