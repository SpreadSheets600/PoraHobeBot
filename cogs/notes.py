import discord
import datetime
import math

from discord.ext import commands
from discord.commands import slash_command, Option

from utils import (
    database,
)

SUBJECT_CHANNELS = {
    "c": 1387809784031608994,
    "dsa": 1387809822279208990,
    "math": 1387810459930988687,
    "python": 1387809701865197689,
    "economics": 1387810261527691344,
    "electronics": 1387810558153068594,
    "computer organization": 1387810527983567040,
}


class PaginatedNotesView(discord.ui.View):
    """A paginated view for displaying notes with navigation buttons."""
    
    def __init__(self, notes, notes_per_page=5):
        super().__init__(timeout=300)  # 5 minute timeout
        self.notes = notes
        self.notes_per_page = notes_per_page
        self.current_page = 0
        self.total_pages = max(1, math.ceil(len(notes) / notes_per_page)) if notes else 1
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page."""
        # Clear all items and re-add them with updated states
        self.clear_items()
        
        # Previous button
        prev_button = discord.ui.Button(
            label="Previous",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page == 0 or not self.notes,
            emoji="⬅️"
        )
        prev_button.callback = self.previous_page
        self.add_item(prev_button)
        
        # Next button  
        next_button = discord.ui.Button(
            label="Next",
            style=discord.ButtonStyle.secondary,
            disabled=self.current_page >= self.total_pages - 1 or not self.notes,
            emoji="➡️"
        )
        next_button.callback = self.next_page
        self.add_item(next_button)
    
    def create_embed(self):
        """Create embed for current page."""
        embed = discord.Embed(title="📚 Notes Index", color=discord.Color.purple())
        
        # Calculate start and end indices for current page
        start_idx = self.current_page * self.notes_per_page
        end_idx = min(start_idx + self.notes_per_page, len(self.notes))
        
        if not self.notes:
            embed.description = "No notes found."
            return embed
        
        # Add notes for current page
        for i in range(start_idx, end_idx):
            note = self.notes[i]
            note_id, title, file_url, timestamp, tags, user_id = note
            
            # Determine if it's a link or file
            is_link = file_url.startswith("http") and (
                "youtube.com" in file_url
                or "drive.google.com" in file_url
                or "youtu.be" in file_url
            )
            icon = "🔗" if is_link else "📄"
            
            # Format upload date (show only date, not full timestamp)
            upload_date = timestamp[:10] if timestamp else "Unknown"
            
            # Simplified display - title, subject, date, and access link
            embed.add_field(
                name=f"{icon} {title}",
                value=f"**Subject:** {tags.title() if tags else 'Unknown'}\n**Date:** {upload_date}\n[📥 Access]({file_url}) | ID: `{note_id}`",
                inline=False,
            )
        
        # Add pagination info in footer
        embed.set_footer(
            text=f"Page {self.current_page + 1} of {self.total_pages} • {len(self.notes)} total notes"
        )
        
        return embed
    
    async def previous_page(self, interaction: discord.Interaction):
        """Handle previous page button click."""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def next_page(self, interaction: discord.Interaction):
        """Handle next page button click."""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()


class NotesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            self.conn = database.initialize_database()
            self.cursor = self.conn.cursor()

        except Exception as e:
            print(f"[NotesCog] Database Initialization Failed : {e}")

            self.conn = None
            self.cursor = None

    @slash_command(
        name="note_send",
        description="Upload A Note File Or Share A Link For A Subject.",
    )
    async def note_send(
        self,
        ctx: discord.ApplicationContext,
        subject: Option(str, "Select The Subject", choices=list(SUBJECT_CHANNELS.keys())),  # type: ignore
        file: discord.Attachment = None,
        link: Option(str, "Paste A Link ( If Any )", required=False) = None,  # type: ignore
    ):
        import aiohttp

        await ctx.defer(ephemeral=True)

        subject_value = subject.lower()
        channel_id = SUBJECT_CHANNELS.get(subject_value)

        if not channel_id:
            await ctx.followup.send(
                f"Unknown Subject '{subject_value}'. Available : {', '.join(SUBJECT_CHANNELS.keys())}",
                ephemeral=True,
            )
            return

        if not file and not link:
            await ctx.followup.send(
                "Please Attach A File Or Provide A Link.", ephemeral=True
            )
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.followup.send(
                "Configured Channel Not Found. Contact Admin.", ephemeral=True
            )
            return

        try:
            file_url = None
            title = None
            if file:
                if file.size > 8 * 1024 * 1024:
                    await ctx.followup.send(
                        "File Is Too Large, Uploading To A Container ....",
                        ephemeral=True,
                    )
                    async with aiohttp.ClientSession() as session:
                        data = aiohttp.FormData()

                        data.add_field("reqtype", "fileupload")
                        file_bytes = await file.read()

                        data.add_field(
                            "fileToUpload", file_bytes, filename=file.filename
                        )

                        async with session.post(
                            "https://catbox.moe/user/api.php", data=data
                        ) as resp:
                            if resp.status == 200:
                                file_url = await resp.text()
                                title = file.filename
                                sent_msg = await channel.send(
                                    f"📄 Note Uploaded By {ctx.author.mention} For **{subject_value.title()}** : [View on Catbox]({file_url})"
                                )
                                thread = await sent_msg.create_thread(
                                    name=f"Note : {file.filename}"
                                )
                            else:
                                await ctx.followup.send(
                                    f"Failed To Upload. Status : {resp.status}",
                                    ephemeral=True,
                                )
                                return
                else:
                    sent_msg = await channel.send(
                        f"📄 Note Uploaded By {ctx.author.mention} For **{subject_value.title()}** :",
                        file=await file.to_file(),
                    )
                    thread = await sent_msg.create_thread(
                        name=f"Note : {file.filename}"
                    )
                    file_url = file.url
                    title = file.filename
            else:
                sent_msg = await channel.send(
                    f"🔗 Link Shared By {ctx.author.mention} For **{subject_value.title()}** : {link}"
                )
                thread = await sent_msg.create_thread(
                    name=f"Discussion : {link[:30]}..."
                )
                file_url = link
                title = link[:50]

            timestamp = datetime.datetime.utcnow().isoformat()
            self.cursor.execute(
                """
                INSERT INTO notes (title, content, file_url, channel_id, user_id, timestamp, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    "",
                    file_url,
                    str(channel_id),
                    str(ctx.author.id),
                    timestamp,
                    subject_value,
                ),
            )
            self.conn.commit()

            await ctx.followup.send(
                f"Note Sent To {channel.mention} And Thread Created : {thread.mention}",
                ephemeral=True,
            )
        except Exception as e:
            await ctx.followup.send(
                f"An Error Occurred While Uploading The Note : {e}", ephemeral=True
            )

    @slash_command(
        name="note_index",
        description="Search And List Notes For A Subject, Keyword, Or User.",
    )
    async def note_index(
        self,
        ctx: discord.ApplicationContext,
        subject: Option(str, "Filter By Subject", choices=list(SUBJECT_CHANNELS.keys()), required=False) = None,  # type: ignore
        keyword: Option(str, "Search By Keyword In Title", required=False) = None,  # type: ignore
        user: Option(discord.User, "Filter By User", required=False) = None,  # type: ignore
    ):
        await ctx.defer(ephemeral=True)

        query = "SELECT id, title, file_url, timestamp, tags, user_id FROM notes"

        params = []
        filters = []

        if subject:
            filters.append("tags = ?")
            params.append(subject.lower())

        if keyword:
            filters.append("title LIKE ?")
            params.append(f"%{keyword}%")

        if user:
            filters.append("user_id = ?")
            params.append(str(user.id))

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY timestamp DESC"

        try:
            self.cursor.execute(query, tuple(params))
            notes = self.cursor.fetchall()

        except Exception as e:
            await ctx.followup.send(f"Database Error : {e}", ephemeral=True)
            return

        if not notes:
            await ctx.followup.send("No Notes Found.", ephemeral=True)
            return

        # Create paginated view
        view = PaginatedNotesView(notes)
        embed = view.create_embed()
        
        await ctx.followup.send(embed=embed, view=view, ephemeral=True)

    @slash_command(
        name="note_delete",
        description="Delete a note by its ID (only your own notes or if admin)",
    )
    async def note_delete(
        self,
        ctx: discord.ApplicationContext,
        note_id: Option(int, "ID Of The Note To Delete"),  # type: ignore
    ):
        await ctx.defer(ephemeral=True)
        try:
            self.cursor.execute("SELECT user_id FROM notes WHERE id = ?", (note_id,))
            row = self.cursor.fetchone()

            if not row:
                await ctx.followup.send("Note Not Found.", ephemeral=True)
                return

            note_owner = row[0]

            if (
                str(ctx.author.id) != note_owner
                and not ctx.author.guild_permissions.administrator
            ):
                await ctx.followup.send(
                    "You Can Only Delete Your Own Notes Unless You Are An Admin.",
                    ephemeral=True,
                )
                return

            self.cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            self.conn.commit()

            await ctx.followup.send(f"Note ID {note_id} deleted.", ephemeral=True)

        except Exception as e:
            await ctx.followup.send(f"Error deleting note: {e}", ephemeral=True)

    @slash_command(name="note_help", description="Show help for the notes bot.")
    async def note_help(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)

        embed = discord.Embed(title="Notes Bot Help", color=discord.Color.green())
        embed.add_field(
            name="/note_send",
            value="Upload A File Or Share A Link For A Subject.",
            inline=False,
        )
        embed.add_field(
            name="/note_index",
            value="Search And List Notes By Subject, Keyword, Or User.",
            inline=False,
        )
        embed.add_field(
            name="/note_delete",
            value="Delete A Note By Its ID (Only Your Own Or If Admin).",
            inline=False,
        )
        embed.add_field(
            name="/note_help", value="Show This Help Message.", inline=False
        )
        await ctx.followup.send(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(NotesCog(bot))
