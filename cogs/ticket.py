import discord
import datetime
import chat_exporter
import io
import os
from discord.ext import commands
from discord.ext.commands import Cog
from discord_components import *
from bson import ObjectId
from database import mongo
from datetime import timedelta

# Function To Convert Time Left Into Structured Time Remaining String
def getTimeLeftStructured(timeleft, hoursMinsSeconds):
    if int(hoursMinsSeconds[0]) == 0 and int(hoursMinsSeconds[1]) > 00:
        return f"**{hoursMinsSeconds[1]}** Minutes **{hoursMinsSeconds[2]}** Seconds"
    if int(hoursMinsSeconds[0]) == 0 and int(hoursMinsSeconds[1]) == 00:
        return f"**{hoursMinsSeconds[2]}** Seconds"

# Function To Edit Channel By Ticket Status
async def editChannelNameByStatus(channel, status, ticketNumber):
    # Fetch Last Time Channel Was Updated
    entries = []
    collection = mongo["entries"]
    results = collection.find({"channel_id": f"{channel.id}"})
    for t in results:
        entries.append(t)

    async def editChannel():
        converted = convertToFont(f"{ticketNumber}")
        await channel.edit(name=f"{status}-{converted}")
        collection = mongo["entries"]
        collection.insert_one({"channel_id": f"{channel.id}", "time_edited": datetime.datetime.now()})

    if len(entries) < 2:
        await editChannel()
        return None

    lastEdited = entries[0]["time_edited"]
    editedBeforeLast = entries[1]["time_edited"]
    timePast = datetime.datetime.now() - lastEdited
    timePastBeforeLastEdited = datetime.datetime.now() - editedBeforeLast

    # If Channel Has Not Been Edited In 10 Minutes Or If its been 10 Minutes Since 2nd Channel Edit
    if timePast.total_seconds() >= 600 or len(entries) == 2 and timePastBeforeLastEdited.total_seconds() >= 600:
        await editChannel()
        return None

    # If Channel Has Been Edited 2 Times In 10 Minutes
    if len(entries) == 2 and timePast.total_seconds() < 600:
        secondsLeft = 600 - timePast.total_seconds()
        hoursMinsSeconds = str(timedelta(seconds=int(secondsLeft))).split(':')
        timeleftStructured = getTimeLeftStructured(timePast, hoursMinsSeconds)
        return timeleftStructured

# Epic Font Shit
def convertToFont(ticketNumber):
    finalTicketNumber = ""
    fonts = {"1": "𝟏", "2": "𝟐", "3": "𝟑", "4": "𝟒", "5": "𝟓", "6": "𝟔", "7": "𝟕", "8": "𝟖", "9": "𝟗","0": "𝟎"}
    for number in ticketNumber:
        finalTicketNumber = finalTicketNumber + fonts[f"{number}"]
    return finalTicketNumber

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
                buttonType = button
        if counter == 0:
            return

        # If Button Click Is From A Ticket That Is Not In Database
        amount = []
        collection = mongo["tickets"]
        results = collection.find({"_id": ObjectId(f"{interaction.custom_id.split(buttonType)[1]}")})
        for t in results:
            amount.append(t)
        if len(amount) == 0:
            return

        # If User Closes Ticket
        if interaction.custom_id.startswith("closeticket"):
            await interaction.respond(type=6)
            results = collection.find_one({"_id": ObjectId(f"{interaction.custom_id.split('closeticket')[1]}")})
            # If Ticket Is Still Active Close Ticket
            if results["ticket_status"] == "ACTIVE":
                ticketOwner = self.bot.get_user(int(results["ticket_owner"]))
                ticketChannel = self.bot.get_channel(int(results["channel_id"]))
                ticketclosedEmbed = discord.Embed(colour=0xFBFE32,description=f'Ticket Closed By {interaction.author.mention}')
                await ticketChannel.set_permissions(ticketOwner, read_messages=False, send_messages=False)
                ratelimit = await editChannelNameByStatus(ticketChannel,'𝐂𝐥𝐨𝐬𝐞𝐝',results["department_ticket_number"])
                if ratelimit == None:
                    await ticketChannel.send(embed=ticketclosedEmbed)
                else:
                    await ticketChannel.send(content=f"Channel renamed too quickly, Timeout: {ratelimit} - Skipping",embed=ticketclosedEmbed)

                # Support Team Controls With Button Interactions
                supportTeamControlsEmbed = discord.Embed(colour=0x2F3136, description='``` Support Team Ticket Controls ```')
                buttons = [Button(style=ButtonStyle.grey, emoji="🔓", label='Open', custom_id=f"openticket{interaction.custom_id.split('closeticket')[1]}"),Button(style=ButtonStyle.grey, emoji="⛔", label='Delete', custom_id=f"deleteticket{interaction.custom_id.split('closeticket')[1]}"), Button(style=ButtonStyle.grey, emoji="📔", label='Transcript', custom_id=f"transcript{interaction.custom_id.split('closeticket')[1]}"),]
                supportPanel = await ticketChannel.send(embed=supportTeamControlsEmbed, components=[buttons])

                # If Ticket Owner Does Not Close Ticket DM Ticket Owner
                if int(interaction.author.id) != int(results["ticket_owner"]):
                    ticketClosedEmbed = discord.Embed(colour=0x388E3C, title='Ticket Closed',description=f'Your ticket in {interaction.guild.name} has been closed by {interaction.author.mention}',timestamp=datetime.datetime.utcnow())
                    await ticketOwner.send(embed=ticketClosedEmbed)

                # Set Ticket As Closed In Database & Set Support Panel Message ID
                collection = mongo["tickets"]
                collection.update_one({"_id": ObjectId(f"{interaction.custom_id.split('closeticket')[1]}")}, {"$set": {"ticket_status": "CLOSED", "support_panel_message_id":f"{supportPanel.id}"}})

        # If User Opens Back Up Ticket
        if interaction.custom_id.startswith("openticket"):
            await interaction.respond(type=6)
            collection = mongo["tickets"]
            results = collection.find_one({"_id": ObjectId(f"{interaction.custom_id.split('openticket')[1]}")})


            # If Ticket Is Closed Re Open Ticket
            if results["ticket_status"] == "CLOSED":
                ticketOwner = self.bot.get_user(int(results["ticket_owner"]))
                ticketChannel = self.bot.get_channel(int(results["channel_id"]))
                supportPanel = await ticketChannel.fetch_message(int(results["support_panel_message_id"]))
                await supportPanel.delete()
                ticketReopenedEmbed = discord.Embed(colour=0xFBFE32,description=f'Ticket Reopened By {interaction.author.mention}')
                await ticketChannel.set_permissions(ticketOwner, read_messages=True, send_messages=True)
                ratelimit = await editChannelNameByStatus(ticketChannel, '𝐓𝐢𝐜𝐤𝐞𝐭', results["department_ticket_number"])
                if ratelimit == None:
                    await ticketChannel.send(embed=ticketReopenedEmbed)
                else:
                    await ticketChannel.send(content=f"Channel renamed too quickly, Timeout: {ratelimit} - Skipping",embed=ticketReopenedEmbed)

                # Send Ticket Owner Message Letting Them Know The Ticket Has Been Reopened
                ticketReopenedEmbed = discord.Embed(colour=0x388E3C, title='Ticket Reopened',description=f'Your ticket in {interaction.guild.name} has been reopened by {interaction.author.mention} \n Click [here](https://discord.com/channels/{interaction.guild.id}/{ticketChannel.id}) to view your ticket',timestamp=datetime.datetime.utcnow())
                await ticketOwner.send(embed=ticketReopenedEmbed)

                # Set Ticket As ACTIVE In Database
                collection.update_one({"_id": ObjectId(f"{interaction.custom_id.split('openticket')[1]}")}, {"$set": {"ticket_status": f"ACTIVE", "support_panel_message_id": "NULL"}})

        # If User Deletes Ticket
        if interaction.custom_id.startswith("deleteticket"):
            await interaction.respond(type=6)
            results = collection.find_one({"_id": ObjectId(f"{interaction.custom_id.split('deleteticket')[1]}")})

            # If Ticket Is Closed Delete Ticket
            if results["ticket_status"] == "CLOSED":
                ticketChannel = self.bot.get_channel(int(results["channel_id"]))
                deleteingTicketEmbed = discord.Embed(colour=0xEF5250,description=' <a:loading:1031771879561768980> Ticket Will Be Deleted Momentarily  <a:loading:1031771879561768980> ')
                await ticketChannel.send(embed=deleteingTicketEmbed)
                await ticketChannel.delete()

                # Set Ticket As DELETED In Database
                collection = mongo['tickets']
                collection.update_one({"_id": ObjectId(f"{interaction.custom_id.split('deleteticket')[1]}")},{"$set": {"ticket_status": f"DELETED", "support_panel_message_id": "NULL"}})

                # Delete All Channel Edit Logs In Database
                collection = mongo['entries']
                collection.delete_many({"channel_id":f"{results['channel_id']}"})

        # If User Requests Transcript Of Ticket
        if interaction.custom_id.startswith("transcript"):
            await interaction.respond(type=6)
            transcript = await chat_exporter.export(interaction.channel, set_timezone='EST')
            transcript = "\n".join(transcript.split("\n")[8:])
            transcriptFile = discord.File(io.BytesIO(transcript.encode()),filename=f"transcript-{interaction.channel.name}.html")
            transcriptChannel = self.bot.get_channel(int(os.getenv("transcriptchannelid")))
            message = await transcriptChannel.send(content=f"Transcript Saved In {interaction.channel.name}", file=transcriptFile)
            transcriptEmbed = discord.Embed(colour=0x388E3C,title="Transcript Saved!", description=f"Click [here]({message.attachments[0].url}) to download your transcript!", timestamp=datetime.datetime.utcnow())
            await interaction.channel.send(embed=transcriptEmbed)

    @Cog.listener()
    async def on_select_option(self, res):
        selectID = res.component.custom_id
        selectOption = res.values[0]

        # If Select Reaction Is Not A Ticket Panel
        if not selectID.startswith("panel"):
            return

        # If Select Reaction Is From A Panel Deleted In The Database
        collection = mongo['ticket_panels']
        result = collection.find_one({"_id": ObjectId(f"{selectID.split('panel')[1]}")})
        if result == None:
            return

        # Fetch Selected Departments Ticket Category ID From Database
        collection = mongo['panel_departments']
        result = collection.find_one({"panel_id":f"{selectID.split('panel')[1]}", "department_name":f"{selectOption}"})
        category = discord.utils.get(res.guild.categories, id=int(result['department_category_id'])) # Fetch Category By ID
        role = discord.utils.get(res.guild.roles, id=int(result["department_role_id"])) # Fetch Role By ID

        # Fetch Users Open Tickets
        tickets = []
        collection = mongo["tickets"]
        results = collection.find({"department_name": result['department_name'], "ticket_owner": f"{res.author.id}", "ticket_status": "ACTIVE"})
        for t in results:
            tickets.append(t)


        # If User Has More Than One Ticket Open On The Same Department
        if len(tickets) >= 1:
            await res.send(content="**Ticket Limit Reached**, You already have 1 ticket opened for the selected department")
            return

        # Get Real Ticket Count For Department
        realtickets = []
        collection = mongo["tickets"]
        results = collection.find({"department_name": result['department_name']})
        for t in results:
            realtickets.append(t)

        # Make Interaction Response
        await res.send(content=" <a:loading:1031771879561768980> Creating Ticket <a:loading:1031771879561768980>")

        # Add Ticket To Database
        collection = mongo['tickets']
        _id = collection.insert_one({"panel_id": selectID.split('panel')[1], "department_name":result['department_name'] ,"department_id": result['department_category_id'], "department_ticket_number": len(realtickets)+23,"ticket_owner": f"{res.author.id}", "ticket_status": "ACTIVE", "guild_id": f"{res.guild.id}"})
        ticketID = _id.inserted_id

        # Create Ticket In Selected Department Category
        ticketOwner = res.author
        overwrites = {res.guild.default_role: discord.PermissionOverwrite(read_messages=False), ticketOwner: discord.PermissionOverwrite(read_messages=True), role: discord.PermissionOverwrite(read_messages=True)}
        ticketChannel = await res.guild.create_text_channel(f'𝐓𝐢𝐜𝐤𝐞𝐭 #{convertToFont(f"{len(realtickets)+23}")}', category=category, overwrites=overwrites)
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
        #await res.edit_origin(content=f'Ticket Created <#{ticketChannel.id}>')

        # Add Channel ID To Ticket Database
        collection = mongo["tickets"]
        collection.update_one({"_id": ObjectId(f"{ticketID}")}, {"$set": {"channel_id": f"{ticketChannel.id}"}})

    # Command To Create Ticket Panels With A Selection Menu
    @commands.command()
    async def panel(self, ctx):
        if not ctx.author.id == 750891444444725318:
            return

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
        checkMarkEmoji = self.bot.get_emoji(1031718789374541975)
        denyMarkEmoji = self.bot.get_emoji(1031718790456684574)
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
            panelImageURL = msg.attachments[0].url
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
            departmentemojiEmbed = discord.Embed(colour=0x388E3C,description="Please Enter A **Emoji For Your Ticket **Department")
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

            # Create A Select Option For Select Table And Add To MongoDB
            selectOptions.append(SelectOption(label=departmentName, description=departmentDescription, emoji=departmentEmoji,value=departmentName,))
            queries.append({"department_name":departmentName, "department_description":departmentDescription, "department_emoji":departmentEmoji, "department_role_id":departmentRoleID, "department_category_id":departmentCategoryID})

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
            deletedPanelEmbed = discord.Embed(colour=0x00F0C5,title='<a:verifiedcheck:870959062240591923> **Disgarded** Panel! <a:verifiedcheck:870959062240591923>')
            await createPanelMessage.edit(embed=deletedPanelEmbed, components=[])
            return

        if interaction.custom_id == "checkyes":
            # Insert Panel Into Database
            collection = mongo['ticket_panels']
            _id = collection.insert_one({"panel_name": panelName, "panel_description": panelDescription,"panel_color": panelColorCode, "panel_image": panelImageURL,"guild_id": f"{ctx.guild.id}", "channel_id":panelChannelID})
            magicNumber = _id.inserted_id

            # Send Out Ticket Panel
            finalPanelEmbed = discord.Embed(colour=0x2F3136, title=panelName,description=f'{panelDescription}')
            components = Select(placeholder="Click Me To Select A Ticket Department!", options=selectOptions, custom_id=f'panel{magicNumber}')
            if not panelImageURL == "NULL":
                finalPanelEmbed.set_image(url=panelImageURL)
            panel = await panelChannel.send(embed=finalPanelEmbed, components=[components], file=discord.File('Rainbow_Line.gif'))
            await panelChannel.send(file=discord.File('Rainbow_Line.gif'))

            # Add Message ID To Panel Database
            collection.update_one({"_id": magicNumber}, {"$set": {"message_id": f"{panel.id}"}})

            # Add All Selection Options To Database
            collection = mongo['panel_departments']
            for query in queries:
                query["panel_id"] = f"{magicNumber}" # Dont Forget The Secret Sauce
                collection.insert_one(query)

def setup(bot):
    bot.add_cog(ticket(bot))