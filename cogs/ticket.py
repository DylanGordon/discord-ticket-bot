import discord
import datetime
from discord.ext import commands
from discord.ext.commands import Cog
from discord_components import *
from database import db,cursor,shorten

class ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_button_click(self, interaction):
        # If Button Click Not For Tickets Ignore Interaction
        counter = 0
        buttonTypes = ["closeticket","openticket","deleteticket","transcript"]
        for button in buttonTypes:
            if interaction.custom_id.startswith(button):
                counter += 1
        if counter == 0:
            return

        # If User Closes Ticket
        if interaction.custom_id.startswith("closeticket"):
            await interaction.respond(type=6)
            Q1 = f"SELECT ticket_status,ticket_owner,channel_id  FROM tickets WHERE id = {interaction.custom_id.split('closeticket')[1]}"
            cursor.execute(Q1)
            results = cursor.fetchall()
            # If Ticket Is Still Active Close Ticket
            if results[0][0] == "ACTIVE":
                ticketOwner = self.bot.get_user(int(results[0][1]))
                ticketChannel = self.bot.get_channel(int(results[0][2]))
                ticketclosedEmbed = discord.Embed(colour=0xFBFE32,description=f'Ticket Closed By {interaction.author.mention}')
                await ticketChannel.send(embed=ticketclosedEmbed)
                await ticketChannel.set_permissions(ticketOwner, read_messages=False, send_messages=False)

                # Support Team Controls With Button Interactions
                supportTeamControlsEmbed = discord.Embed(colour=0x2F3136, description='``` Support Team Ticket Controls ```')
                buttons = [Button(style=ButtonStyle.grey, emoji="🔓", label='Open', custom_id=f"openticket{interaction.custom_id.split('closeticket')[1]}"),Button(style=ButtonStyle.grey, emoji="⛔", label='Delete', custom_id=f"deleteticket{interaction.custom_id.split('closeticket')[1]}"), Button(style=ButtonStyle.grey, emoji="📔", label='Transcript', custom_id=f"transcript{interaction.custom_id.split('closeticket')[1]}"),]
                await ticketChannel.send(embed=supportTeamControlsEmbed, components=[buttons])

                # Set Ticket As Closed In Database
                Q2 = f"UPDATE tickets SET ticket_status = %s WHERE id = {interaction.custom_id.split('closeticket')[1]}"
                data = ("CLOSED",)
                cursor.execute(Q2, data)
                db.commit()
        # If User Opens Back Up Ticket
        if interaction.custom_id.startswith("openticket"):
            await interaction.respond(type=6)
            Q1 = f"SELECT ticket_status,ticket_owner,channel_id  FROM tickets WHERE id = {interaction.custom_id.split('openticket')[1]}"
            cursor.execute(Q1)
            results = cursor.fetchall()

            # If Ticket Is Closed Re Open Ticket
            if results[0][0] == "CLOSED":
                ticketOwner = self.bot.get_user(int(results[0][1]))
                ticketChannel = self.bot.get_channel(int(results[0][2]))
                ticketReopenedEmbed = discord.Embed(colour=0xFBFE32,description=f'Ticket Reopened By {interaction.author.mention}')
                await ticketChannel.send(embed=ticketReopenedEmbed)
                await ticketChannel.set_permissions(ticketOwner, read_messages=True, send_messages=True)

                # Set Ticket As ACTIVE In Database
                Q2 = f"UPDATE tickets SET ticket_status = %s WHERE id = {interaction.custom_id.split('openticket')[1]}"
                data = ("ACTIVE",)
                cursor.execute(Q2, data)
                db.commit()
        # If User Deletes Ticket
        if interaction.custom_id.startswith("deleteticket"):
            await interaction.respond(type=6)
            Q1 = f"SELECT ticket_status,channel_id  FROM tickets WHERE id = {interaction.custom_id.split('deleteticket')[1]}"
            cursor.execute(Q1)
            results = cursor.fetchall()

            # If Ticket Is Closed Delete Ticket
            if results[0][0] == "CLOSED":
                ticketChannel = self.bot.get_channel(int(results[0][1]))
                deleteingTicketEmbed = discord.Embed(colour=0xEF5250, description='<a:emojistorage1loading:824542310028017685> Ticket Will Be Deleted Momentarily <a:emojistorage1loading:824542310028017685>')
                await ticketChannel.send(embed=deleteingTicketEmbed)
                await ticketChannel.delete()

                # Set Ticket As DELETED In Database
                Q2 = f"UPDATE tickets SET ticket_status = %s WHERE id = {interaction.custom_id.split('deleteticket')[1]}"
                data = ("DELETED",)
                cursor.execute(Q2, data)
                db.commit()
        # If User Requests Transcript Of Ticket
        if interaction.custom_id.startswith("transcript"):
            await interaction.send("Coming Soon")

    @Cog.listener()
    async def on_select_option(self, res):
        selectID = res.component.custom_id
        selectOption = res.values[0]

        # If Select Reaction Is Not A Ticket Panel
        if not selectID.startswith("panel"):
            return

        # Fetch Selected Departments Ticket Category ID From Database
        Q1 = "SELECT department_category_id, department_role_id, id FROM panel_departments WHERE panel_id = %s AND department_name = %s"
        data = (selectID.split('panel')[1], selectOption)
        cursor.execute(Q1, data)
        results = cursor.fetchall()
        categoryID = int(results[0][0])
        roleID = int(results[0][1])
        category = discord.utils.get(res.guild.categories, id=categoryID) # Fetch Category By ID
        role = discord.utils.get(res.guild.roles, id=roleID) # Fetch Role By ID

        # If User Has More Than One Ticket Open On The Same Department
        Q2 = f"SELECT * from tickets WHERE department_id = {results[0][2]} AND ticket_owner = {res.author.id} AND ticket_status = 'ACTIVE'"
        cursor.execute(Q2)
        tickets = cursor.fetchall()
        if len(tickets) >= 1:
            await res.send(content="**Ticket Limit Reached**, You already have 1 ticket opened for the selected department")
            return

        # Make Interaction Response
        firstResMessage = await res.send(content=" <a:emojistorage1loading:824542310028017685> Creating Ticket <a:emojistorage1loading:824542310028017685>")

        # Add Ticket To Database
        Q3 = "INSERT INTO tickets (panel_id, department_id, ticket_owner, ticket_status, guild_id) VALUES (%s,%s,%s,%s,%s)"
        data = (selectID.split('panel')[1],results[0][2], res.author.id, "ACTIVE", res.guild.id)
        cursor.execute(Q3, data)
        db.commit()
        ticketID = cursor.lastrowid

        # Get Correct Ticket Number Based On Amount Of Tickets For Selected Department
        Q4 = f"SELECT id FROM tickets WHERE department_id = {results[0][2]}"
        cursor.execute(Q4)
        results = cursor.fetchall()

        # Create Ticket In Selected Department Category
        ticketOwner = res.author
        overwrites = {res.guild.default_role: discord.PermissionOverwrite(read_messages=False), ticketOwner: discord.PermissionOverwrite(read_messages=True), role: discord.PermissionOverwrite(read_messages=True)}
        ticketChannel = await res.guild.create_text_channel(f'Ticket #{len(results)}', category=category, overwrites=overwrites)
        welcomeTicketEmbed = discord.Embed(colour=0x388E3C, description=f'Thanks for creating a ticket {res.author.mention} A staff member will be with you shortly! \n To Close This Ticket React With 🔒', timestamp=datetime.datetime.utcnow())
        welcomeTicketEmbed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
        button = [Button(style=ButtonStyle.grey, emoji="🔒",label='Close', custom_id=f"closeticket{ticketID}")]
        orignalMessage = await ticketChannel.send(content=f"{res.author.mention}{role.mention}", embed=welcomeTicketEmbed, components=[button])
        await orignalMessage.pin()
        # Delete Message Has Been Pinned Message
        async for message in ticketChannel.history():
            if message.type.value == 6:
                await message.delete()

        # Make Final Interaction Message
        await res.edit_origin(content=f'Ticket Created <#{ticketChannel.id}>')

        # Add Channel ID To Ticket Database
        Q5 = f"UPDATE tickets SET channel_id = {ticketChannel.id} WHERE id = {ticketID}"
        cursor.execute(Q5)
        db.commit()

    @commands.command()
    async def panel(self, ctx):
        # Get Name Of Panel
        getPanelNameEmbed = discord.Embed(colour=0x388E3C,description='Please Enter The **Panel** __**Name**__')
        await ctx.send(embed=getPanelNameEmbed)
        msg = await self.bot.wait_for('message', timeout=60, check=lambda message: message.author == ctx.author)
        panelName = msg.content

        # Get Panel Description
        getPanelDescriptionEmbed = discord.Embed(colour=0x388E3C, description='Please Enter The **Panel** __**Description**__')
        await ctx.send(embed=getPanelDescriptionEmbed)
        msg = await self.bot.wait_for('message', timeout=60, check=lambda message: message.author == ctx.author)
        panelDescription = msg.content

        # Get Panel Embed Color
        getEmbedColorCodeEmbed = discord.Embed(colour=0x388E3C,description="🧬 Please Enter A __**Hexadecimal**__ Color Code!",)
        await ctx.send(embed=getEmbedColorCodeEmbed)
        msg = await self.bot.wait_for('message', timeout=60, check=lambda message: message.author == ctx.author)
        try:
            panelColorCode = int(hex(int(msg.content.replace("#", ""), 16)), 0)
        # If Given Color Code Isn't A Hexadecimal
        except:
            invalidColorEmbed = discord.Embed(colour=0xCD5C5C, description="⁉️ Invalid __**Hexadecimal**__!")
            await ctx.send(embed=invalidColorEmbed)
            return

        # Get Panel Emoji
        getPanelEmojiEmbed = discord.Embed(colour=0x388E3C, description='Please Enter The **Panel** __**Emoji**__')
        await ctx.send(embed=getPanelEmojiEmbed)
        msg = await self.bot.wait_for('message', timeout=60, check=lambda message: message.author == ctx.author)
        panelEmoji = msg.content

        # Gets Panel Channel
        textChannelList = []
        selectOptions = []

        # Put Every Channel Name And ID Into List
        for channel in ctx.guild.text_channels:
            textChannelList.append([channel.name, channel.id])

        # For Every Channel Create Selection Option
        for channel in textChannelList:
            selectOptions.append(SelectOption(label=channel[0], value=channel[1]))

        selectPanelChanelEmbed = discord.Embed(colour=0x388E3C, description='#️⃣ Please Select The **Panels** __**Channel**__')
        components = Select(placeholder="Please Select A Channel To Preview Your Panel In!", options=selectOptions)
        panelChannelMessage = await ctx.send(embed=selectPanelChanelEmbed, components=[components])

        # Wait For Interaction Response
        interaction = await self.bot.wait_for("select_option")
        await interaction.respond(type=6)
        panelChannelID = interaction.values[0]
        panelChannel = self.bot.get_channel(int(panelChannelID))

        # Checks If User Would Like To Add A Panel Image
        checkMarkEmoji = self.bot.get_emoji(805593664591626282)
        denyMarkEmoji = self.bot.get_emoji(805593723366932501)
        panelImageEmbed = discord.Embed(colour=0x388E3C,description='❓ Would You Like To **Add** A **Panel Image?**')
        buttons = [Button(style=ButtonStyle.grey, emoji=checkMarkEmoji, custom_id="checkyes"),Button(style=ButtonStyle.grey, emoji=denyMarkEmoji, custom_id="denyno")]
        await panelChannelMessage.edit(embed=panelImageEmbed, components=[buttons])

        # Wait For Interaction Response
        interaction = await self.bot.wait_for("button_click", timeout=30)
        await interaction.respond(type=6)

        # If User Selects Yes
        if interaction.custom_id == "checkyes":
            global panelImageURL
            uploadFileEmbed = discord.Embed(colour=0x388E3C, title="📁 Please Upload A File Attachment!")
            await panelChannelMessage.edit(embed=uploadFileEmbed, components=[])
            msg = await self.bot.wait_for('message', timeout=30, check=lambda message: message.author == ctx.author)

            # If User Doesnt Send File Attachment
            if len(msg.attachments) == 0:
                invalidImageEmbed = discord.Embed(title="**Invalid** File Type!", colour=0xFFD679)
                await ctx.send(embed=invalidImageEmbed)
                return
            panelImageURL = shorten(msg.attachments[0].url)
        if interaction.custom_id == "denyno":
            panelImageURL = "NULL"

        # Create At least One Department For Panel
        selectOptions = []
        queries = []
        async def createDepartment():
            departmentNameEmbed = discord.Embed(colour=0x388E3C, description="Please Enter A **Name** For Your Ticket **Department**")
            await ctx.send(content='Lets Create A Panel Department',embed=departmentNameEmbed, components=[])
            msg = await self.bot.wait_for('message', timeout=60, check=lambda message: message.author == ctx.author)
            departmentName = msg.content

            # Get Department Description
            departmentDescriptionEmbed = discord.Embed(colour=0x388E3C, description="Please Enter A **Description** For Your Ticket **Department**")
            await ctx.send(embed=departmentDescriptionEmbed)
            msg = await self.bot.wait_for('message', timeout=60, check=lambda message: message.author == ctx.author)
            departmentDescription = msg.content

            # Get Department Emoji
            departmentemojiEmbed = discord.Embed(colour=0x388E3C,description="Please Enter A **Emoji For Your Ticket **Department**")
            await ctx.send(embed=departmentemojiEmbed)
            msg = await self.bot.wait_for('message', timeout=60, check=lambda message: message.author == ctx.author)
            departmentEmoji = msg.content

            # Select Department Role
            guildRoles = []
            roleSelectOptions = []
            # Fetch All Guild Roles
            for role in ctx.guild.roles:
                guildRoles.append([role.name, role.id])
            # For Every Role Create Select Option
            for role in guildRoles:
                roleSelectOptions.append(SelectOption(label=role[0], value=role[1]))

            departmentRoleEmbed = discord.Embed(colour=0x0078D7, description='#️⃣ Please Select A ** Department Role**!')
            components = Select(placeholder=f"Please Select A Department Role",options=roleSelectOptions)
            departmentRoleMessage = await ctx.send(embed=departmentRoleEmbed, components=[components])

            # Wait For Interaction Response
            interaction = await self.bot.wait_for("select_option", timeout=20)
            await interaction.respond(type=6)
            departmentRoleID = interaction.values[0]

            # Select A Department Ticket Category
            categoryList = []
            categoryselectOptions = []

            # Put Every Category Name And ID Into List
            for category in ctx.guild.categories:
                categoryList.append([category.name, category.id])
            # For Every Category Create Selection Option
            for category in categoryList:
                categoryselectOptions.append(SelectOption(label=category[0], value=category[1]))

            selectPanelCategoryEmbed = discord.Embed(colour=0x388E3C,description='#️⃣ Please Select The **Panels** __**Category**__')
            components = Select(placeholder="Please Select A Category To Create Your Tickets In!", options=categoryselectOptions)
            await departmentRoleMessage.edit(embed=selectPanelCategoryEmbed, components=[components])

            # Wait For Interaction Response
            interaction = await self.bot.wait_for("select_option")
            await interaction.respond(type=6)
            departmentCategoryID = interaction.values[0]

            # Create A Select Option For Select Table And Create Database Query
            selectOptions.append(SelectOption(label=departmentName, description=departmentDescription, emoji=departmentEmoji,value=departmentName,))
            data = (departmentName, departmentDescription, departmentEmoji, departmentRoleID, departmentCategoryID)
            queries.append(["INSERT INTO panel_departments (panel_id, department_name, department_description, department_emoji, department_role_id, department_category_id) VALUES (%s,%s,%s,%s,%s,%s)", data])

            # Checks If User Would Like To Add Another Department
            departmentEmbed = discord.Embed(colour=0x388E3C,description='❓ Would You Like To **Add** Another **Department?**')
            buttons = [Button(style=ButtonStyle.grey, emoji=checkMarkEmoji, custom_id="checkyes"),Button(style=ButtonStyle.grey, emoji=denyMarkEmoji, custom_id="denyno")]
            latestMessage = await departmentRoleMessage.edit(embed=departmentEmbed, components=[buttons])

            # Wait For Interaction Response
            interaction = await self.bot.wait_for("button_click", timeout=30)
            await interaction.respond(type=6)

            # If User Selects Yes
            if interaction.custom_id == "checkyes":
                await createDepartment()
            if interaction.custom_id == "denyno":
                return
        await createDepartment()

        # Confirms User Wants To Create Panel
        createPanelEmbed = discord.Embed(colour=0x388E3C,description='❓ Are You Sure You Want To **Create** This **Panel?**')
        buttons = [Button(style=ButtonStyle.grey, emoji=checkMarkEmoji, custom_id="checkyes"),Button(style=ButtonStyle.grey, emoji=denyMarkEmoji, custom_id="denyno")]
        createPanelMessage = await ctx.send(embed=createPanelEmbed, components=[buttons])

        # Wait For Interaction Response
        interaction = await self.bot.wait_for("button_click", timeout=30)
        await interaction.respond(type=6)

        # if User Selects No
        if interaction.custom_id == "denyno":
            deletedPanelEmbed = discord.Embed(colour=0x388E3C,description='**Disgarded** Panel!')
            await createPanelMessage.edit(deletedPanelEmbed, components=[])
            return
        if interaction.custom_id == "checkyes":
            # Insert Panel Into Database
            Q1 = f"INSERT INTO ticket_panels (panel_name, panel_description, panel_color, panel_emoji, panel_image, guild_id, channel_id) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            data = (panelName, panelDescription, panelColorCode, panelEmoji, panelImageURL, ctx.guild.id, panelChannelID)
            cursor.execute(Q1, data)
            db.commit()

            # Send Out Ticket Panel
            finalPanelEmbed = discord.Embed(colour=0x2F3136, title=panelName,description=f'{panelEmoji}{panelDescription}')
            components = Select(placeholder="Please Select A Ticket Department!", options=selectOptions, custom_id=f'panel{cursor.lastrowid}')
            panel = await panelChannel.send(embed=finalPanelEmbed, components=[components])
            panelID = cursor.lastrowid

            # Add Message ID To Panel Database
            Q2 = f"UPDATE ticket_panels SET message_id = {panel.id} WHERE panel_id = {panelID}"
            cursor.execute(Q2)
            db.commit()

            # Add All Selection Options To Database
            for query in queries:
                data = list(query[1])
                data.insert(0, panelID)
                data = tuple(data)

                db.reconnect(attempts=5)
                cursor.execute(query[0], data)
                db.commit()

def setup(bot):
    bot.add_cog(ticket(bot))