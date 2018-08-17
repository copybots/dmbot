import discord
import aiohttp
import asyncio
import time
import json
import requests
import os

#----------------------------------------------------------------------------------------------------
# These variables must be filled out in order for the bot to work.
#
# selfbot: If you want a selfbot, just leave it as True, but if you ever want to use it on a normal bot, set it to False.
# token : The account token on which the bot will be running.
# commands_server_id : The bot will only respond to commands in the server with this server ID.
#                      If you leave it blank, the bot will respond to commands in every server.
# commands_channel_id : The bot will only respond to commands in the channel with this channel ID.
#                       If you leave it blank, the bot will respond to commands in every channel (in the server
#                       with the server ID that you put).

selfbot = True
token = str(os.environ.get("BOT_TOKEN"))
commands_server_id = str(os.environ.get("COMMANDS_SERVER_ID"))
commands_channel_id = str(os.environ.get("COMMANDS_CHANNEL_ID"))

#----------------------------------------------------------------------------------------------------

bot = discord.Client()
filebot = discord.Client()

messages_currently_sending = []
filebot_token = str(os.environ.get("FILEBOT_TOKEN"))
storage_server_id = str(os.environ.get("STORAGE_SERVER_ID"))
storage_channel_id = str(os.environ.get("STORAGE_CHANNEL_ID"))
filename = "dmbotfile.cfg"



async def get_latest_bot_message(storage_channel_object):

	message_object_found = False
	async for message_object in filebot.logs_from(storage_channel_object):
		if message_object.author.id == filebot.user.id:
			message_object_found = True
			return message_object
			break
	if not message_object_found:
		return None

async def save_data(data_to_save):

	global storage_server_id
	global storage_channel_id
	global filename

	storage_server_object = filebot.get_server(storage_server_id)
	storage_channel_object = storage_server_object.get_channel(storage_channel_id)

	latest_bot_message = await get_latest_bot_message(storage_channel_object)

	filehandle = open(filename, "w")
	json.dump(data_to_save, filehandle)
	filehandle.close()
	filehandle = open(filename, "rb")

	if latest_bot_message == None:
		await filebot.send_file(storage_channel_object, filehandle, content="filesave")
	else:
		await filebot.delete_message(latest_bot_message)
		await filebot.send_file(storage_channel_object, filehandle, content="filesave")

async def load_data():

	global storage_server_id
	global storage_channel_id
	global filename

	storage_server_object = filebot.get_server(storage_server_id)
	storage_channel_object = storage_server_object.get_channel(storage_channel_id)

	latest_bot_message = await get_latest_bot_message(storage_channel_object)

	if latest_bot_message == None:
		return None
	else:
		file_url = latest_bot_message.attachments[0]["url"]
		r = requests.get(file_url)
		if r.status_code == 200:
			return(r.json())
		else:
			print("[ERROR] Error Retrieving File (Status Code {0})".format(r.status_code))
			return None



commands_server_id_exists = False
commands_channel_id_exists = False



@bot.event
async def on_ready():
	await bot.wait_until_ready()

	global commands_server_id
	global commands_channel_id
	global commands_server_id_exists
	global commands_channel_id_exists

	commands_server_id = commands_server_id.strip()
	commands_channel_id = commands_channel_id.strip()

	if (len(commands_server_id) != 0):
			try:
				commands_server_id = bot.get_server(commands_server_id).id
			except Exception:
				print("Exiting: Invalid commands_server_id ({0})".format(commands_server_id))
				time.sleep(5)
				raise SystemExit
			commands_server_id_exists = True
			if (len(commands_channel_id) != 0):
				try:
					commands_channel_id = bot.get_server(commands_server_id).get_channel(commands_channel_id).id
				except Exception:
					print("Exiting: Invalid commands_channel_id ({0})".format(commands_channel_id))
					time.sleep(5)
					raise SystemExit
				commands_channel_id_exists = True


	print (bot.user.name + " is ready")
	print ("ID: " + bot.user.id)

serverlist = []
rolelist = []
memberlist = []
delay = 1.0
errordelay = 60.0
messagecount = 1
members_already_messaged = []

@filebot.event
async def on_ready():
	await filebot.wait_until_ready()

	global serverlist
	global rolelist
	global memberlist
	global delay
	global errordelay
	global messagecount
	global members_already_messaged
	global filedata

	filedata = await load_data()
	if filedata == None:
		filedata = {
			"serverlist" : [],
			"rolelist" : [],
			"memberlist" : [],
			"delay" : 1.0,
			"errordelay" : 60.0,
			"messagecount" : 1,
			"members_already_messaged" : []
		}
	else:
		pass
	serverlist = filedata["serverlist"]
	rolelist = filedata["rolelist"]
	memberlist = filedata["memberlist"]
	delay = float(filedata["delay"])
	errordelay = float(filedata["errordelay"])
	messagecount = int(filedata["messagecount"])
	members_already_messaged = filedata["members_already_messaged"]


	print (filebot.user.name + " is ready")
	print ("ID: " + filebot.user.id)



@bot.event
async def on_message(message):

	global serverlist
	global rolelist
	global memberlist
	global delay
	global errordelay
	global messagecount
	global members_already_messaged
	global filedata

	global commands_server_id
	global commands_channel_id
	global commands_server_id_exists
	global commands_channel_id_exists

	role_dict = {}

	for server_id in serverlist:
		try:
			server_object = bot.get_server(server_id)
			if len(server_object.roles) > 1:
				role_dict[server_object] = []
				for role_object in server_object.roles:
					if not role_object.is_everyone:
						role_dict[server_object].append(role_object)
			else:
				role_dict[server_object] = []
		except Exception:
			pass


	commands_channel_object = bot.get_server(commands_server_id).get_channel(commands_channel_id)


	if (message.author.id != bot.user.id) and (message.server != None):
		if ((not commands_server_id_exists) or (message.server.id == commands_server_id)) and ((not commands_channel_id_exists) or (message.channel.id == commands_channel_id)):



			if (message.content[:6] == "!send "):
				if (serverlist != []):

					members_checked = []
					valid_members = []

					messages_currently_sending.append(message.content[6:])

					for server_id in serverlist:
						server_object = bot.get_server(server_id)
						if server_object != None:
							for member_object in server_object.members:
								if not (member_object.id in members_checked):
									members_checked.append(member_object.id)

									if not (member_object.id in memberlist):


										# For making a list of all the roles that the user has in all the servers in the serverlist.
										#
										member_roles = []
										for server_id2 in serverlist:
											server_object2 = bot.get_server(server_id2)
											if server_object2 != None:
												for member_object2 in server_object2.members:
													if member_object2.id == member_object.id:
														for role_object in member_object2.roles:
															if not role_object.is_everyone:
																member_roles.append(role_object.id)


										member_roles_notinrolelist_bool = True
										for member_role_id in member_roles:
											if member_role_id in rolelist:
												member_roles_notinrolelist_bool = False


										if member_roles_notinrolelist_bool:
											if not(member_object.id in members_already_messaged):
												valid_members.append(member_object)



					current_messagecount = 0
					for member_object in valid_members:
						if message.content[6:] in messages_currently_sending:
							error_bool = True
							while error_bool:
								try:
									await bot.send_message(member_object, message.content[6:])
									filedata["members_already_messaged"].append(member_object.id)
									current_messagecount += 1
									error_bool = False
								except discord.Forbidden as e:
									
									if e[30:].lower() == "cannot send messages to this user":
										error_bool = False
									else:
										if errordelay == 1:
											await bot.send_message(message.channel, """**FORBIDDEN ERROR: Sending PMs too quickly, bot has stopped sending PMs for {0} second!**\n```{1}```""".format(str(errordelay), e))
										else:
											await bot.send_message(message.channel, """**FORBIDDEN ERROR: Sending PMs too quickly, bot has stopped sending PMs for {0} seconds!**\n```{1}```""".format(str(errordelay), e))
										await asyncio.sleep(errordelay)

								except Exception:
									error_bool = False

							if current_messagecount == messagecount:
								current_messagecount = 0
								await save_data(filedata)		#SAVE TO FILE
								await asyncio.sleep(delay)
					if message.content[6:] in messages_currently_sending:
						messages_currently_sending.remove(message.content[6:])



				else:
					await bot.send_message(message.channel, """**Message not sent - you haven't added any servers yet.**""")



			elif (message.content[:8] == "!cancel ") or (message.content == "!cancel"):
				if len(messages_currently_sending) > 0:
					if message.content.strip() != "!cancel":
						if message.content[8:] in messages_currently_sending:
							messages_currently_sending.remove(message.content[8:])
							await bot.send_message(message.channel, """**The message *{0}* is not being sent anymore.**""".format(message.content[8:]))
						else:
							await bot.send_message(message.channel, """**Invalid message - not being sent.**""")
					else:
						list_sender = ""
						list_sender = list_sender + """**Here are all the messages currently being sent:**\n"""
						for message_currently_sending in messages_currently_sending:
							list_sender = list_sender + ("""\n• {0}""".format(message_currently_sending))
						await bot.send_message(message.channel, list_sender)
				else:
					await bot.send_message(message.channel, """**There are currently no messages being sent.**""")



			elif (message.content[:16] == "!serverlist add ") or (message.content == "!serverlist add"):
				if (message.content[:20] == "!serverlist add all ") or (message.content == "!serverlist add all"):
					added_count = 0
					for server_object in bot.servers:
						if not (server_object.id in serverlist):
							serverlist.append(server_object.id)
							filedata["serverlist"] = serverlist		#SAVE TO FILE
							await save_data(filedata)
							added_count += 1
					if added_count == 1:
						await bot.send_message(message.channel, """**[1] server was added to the server list.**""")
					else:
						await bot.send_message(message.channel, """**[{0}] servers were added to the server list.**""".format(str(added_count)))
				else:
					if message.content.strip() != "!serverlist add":
						temp_bool = True
						for server_object in bot.servers:
							if (message.content[16:] == server_object.name) or (message.content[16:] == server_object.id):
								temp_bool = False
								if not (server_object.id in serverlist):
									serverlist.append(server_object.id)
									filedata["serverlist"] = serverlist		#SAVE TO FILE
									await save_data(filedata)
									await bot.send_message(message.channel, """**The server *{0} ({1})* has been added to the server list.**""".format(server_object.name, server_object.id))
								else:
									await bot.send_message(message.channel, """**Invalid server - already in the server list.**""")
						if temp_bool:
							await bot.send_message(message.channel, """**Invalid server - does not exist.**""")
					else:
						list_sender = ""
						list_sender = (list_sender + """**Here are all the servers I'm in:**\n\n\n""")
						for server_object in bot.servers:
							if not (server_object.id in serverlist):
								list_sender = (list_sender + """• {0} ({1})\n\n""".format(server_object.name, server_object.id))
						await bot.send_message(message.channel, list_sender)



			elif (message.content[:19] == "!serverlist remove ") or (message.content == "!serverlist remove"):
				if len(serverlist) > 0:
					if (message.content[:23] == "!serverlist remove all ") or (message.content == "!serverlist remove all"):
						removed_count = len(serverlist)
						serverlist = []
						filedata["serverlist"] = serverlist		#SAVE TO FILE
						await save_data(filedata)
						if removed_count == 1:
							await bot.send_message(message.channel, """**[1] server was removed from the server list.**""")
						else:
							await bot.send_message(message.channel, """**[{0}] servers were removed from the server list.**""".format(str(removed_count)))
					else:
						if message.content.strip() != "!serverlist remove":
							temp_bool = True
							for server_object in bot.servers:
								if (message.content[19:] == server_object.name) or (message.content[19:] == server_object.id):
									temp_bool = False
									if server_object.id in serverlist:
										serverlist.remove(server_object.id)
										filedata["serverlist"] = serverlist		#SAVE TO FILE
										await save_data(filedata)
										await bot.send_message(message.channel, """**The server *{0} ({1})* has been removed from the server list.**""".format(server_object.name, server_object.id))
									else:
										await bot.send_message(message.channel, """**Invalid server - not in the server list.**""")
							if temp_bool:
								await bot.send_message(message.channel, """**Invalid server - does not exist.**""")
						else:
							list_sender = ""
							list_sender = (list_sender + """**Here are all the servers in the server list:**\n\n\n""")
							for server_id in serverlist:
								try:
									server_object = bot.get_server(server_id)
								except Exception:
									pass
								list_sender = (list_sender + """• {0} ({1})\n\n""".format(server_object.name, server_object.id))
							await bot.send_message(message.channel, list_sender)
				else:
					await bot.send_message(message.channel, """**There are currently no servers in the server list.**""")



			elif (message.content[:14] == "!rolelist add ") or (message.content == "!rolelist add"):
				if len(serverlist) > 0:
					if message.content.strip() != "!rolelist add":
						temp_bool = True
						for server_object, role_objects in role_dict.items():
							for role_object in role_objects:
								if (message.content[14:] == role_object.name) or (message.content[14:] == role_object.id):
									temp_bool = False
									if not (role_object.id in rolelist):
										rolelist.append(role_object.id)
										filedata["rolelist"] = rolelist		#SAVE TO FILE
										await save_data(filedata)
										await bot.send_message(message.channel, """**The role *{0} ({1})* has been added to the role list.**""".format(role_object.name, role_object.id))
									else:
										await bot.send_message(message.channel, """**Invalid role - already in the role list.**""")
						if temp_bool:
							await bot.send_message(message.channel, """**Invalid role - does not exist.**""")
					else:
						list_sender = ""
						list_sender = (list_sender + """**Here are all the roles in the servers in the server list:**\n\n\n""")
						for server_object, role_objects in role_dict.items():
							list_sender = (list_sender + """**{0} ({1})**\n\n""".format(server_object.name, server_object.id))
							temp_bool = True
							for role_object in role_objects:
								if not (role_object.id in rolelist):
									temp_bool = False
									list_sender = (list_sender + """• {0} ({1})\n\n""".format(role_object.name, role_object.id))
							if temp_bool:
								list_sender = (list_sender + """No roles.\n\n""")
						await bot.send_message(message.channel, list_sender)
				else:
					await bot.send_message(message.channel, """**You must add at least one server before adding a role.**""")



			elif (message.content[:17] == "!rolelist remove ") or (message.content == "!rolelist remove"):
				if len(rolelist) > 0:
					if message.content.strip() != "!rolelist remove":
						temp_bool = True
						for server_object, role_objects in role_dict.items():
							for role_object in role_objects:
								if (message.content[17:] == role_object.name) or (message.content[17:] == role_object.id):
									temp_bool = False
									if role_object.id in rolelist:
										rolelist.remove(role_object.id)
										filedata["rolelist"] = rolelist		#SAVE TO FILE
										await save_data(filedata)
										await bot.send_message(message.channel, """**The role *{0} ({1})* has been removed from the role list.**""".format(role_object.name, role_object.id))
									else:
										await bot.send_message(message.channel, """**Invalid role - not in the role list.**""")
						if temp_bool:
							await bot.send_message(message.channel, """**Invalid role - does not exist.**""")
					else:
						list_sender = ""
						list_sender = (list_sender + """**Here are all the roles in the role list:**\n\n\n""")
						for server_object, role_objects in role_dict.items():
							temp_bool = False
							for role_object in role_objects:
								if role_object.id in rolelist:
									temp_bool = True
							if temp_bool:
								list_sender = (list_sender + """**{0} ({1})**\n\n""".format(server_object.name, server_object.id))
								for role_object in role_objects:
									if role_object.id in rolelist:
										list_sender = (list_sender + """• {0} ({1})\n\n""".format(role_object.name, role_object.id))
						await bot.send_message(message.channel, list_sender)
				else:
					await bot.send_message(message.channel, """**There are currently no roles in the role list.**""")



			elif (message.content[:16] == "!memberlist add ") or (message.content == "!memberlist add"):
				if len(serverlist) > 0:
					if message.content.strip() != "!memberlist add":
						temp_bool = False
						for server_id in serverlist:
							if temp_bool:
								break
							server_object = bot.get_server(server_id)
							for member_object in server_object.members:
								if (message.content[16:] == member_object.name) or (message.content[16:] == member_object.id):
									if not (member_object.id in memberlist):
										memberlist.append(member_object.id)
										filedata["memberlist"] = memberlist		#SAVE TO FILE
										await save_data(filedata)
										await bot.send_message(message.channel, """**The member *{0} ({1})* has been added to the memberlist.**""".format(member_object.name, member_object.id))
									else:
										await bot.send_message(message.channel, """**Invalid member - already in the memberlist.**""")
									temp_bool = True
									break
						if not temp_bool:
							await bot.send_message(message.channel, """**Invalid member - does not exist.**""")
					else:
						await bot.send_message(message.channel, """**Use the command like this -> *!memberlist add member*.**""")
				else:
					await bot.send_message(message.channel, """**You must add at least one server before adding a member.**""")



			elif (message.content[:19] == "!memberlist remove ") or (message.content == "!memberlist remove"):
				if len(memberlist) > 0:
					if message.content.strip() != "!memberlist remove":
						temp_bool = True
						for server_object in bot.servers:
							if not temp_bool:
								break
							for member_object in server_object.members:
								if (message.content[19:] == member_object.name) or (message.content[19:] == member_object.id):
									temp_bool = False
									if member_object.id in memberlist:
										memberlist.remove(member_object.id)
										filedata["memberlist"] = memberlist		#SAVE TO FILE
										await save_data(filedata)
										await bot.send_message(message.channel, """**The member *{0} ({1})* has been removed from the member list.**""".format(member_object.name, member_object.id))
									else:
										await bot.send_message(message.channel, """**Invalid member - not in the member list.**""")
										break
						if temp_bool:
							await bot.send_message(message.channel, """**Invalid member - does not exist.**""")
					else:
						list_sender = ""
						list_sender = (list_sender + """**Here are all the members in the member list:**\n\n\n""")
						for member_id in memberlist:
							for server_object in bot.servers:
								try:
									member_object = server_object.get_member(member_id)
									list_sender = (list_sender + """• {0} ({1})\n\n""".format(member_object.name, member_object.id))
								except Exception:
									pass
								else:
									break
						await bot.send_message(message.channel, list_sender)
				else:
					await bot.send_message(message.channel, """**There are currently no members in the memberlist.**""")



			elif (message.content[:11] == "!set delay ") or (message.content == "!set delay"):
				if message.content.strip() == "!set delay":
					if delay == 1:
						await bot.send_message(message.channel, """**The current delay between messages is {0} second.**""".format(str(delay)))
					else:
						await bot.send_message(message.channel, """**The current delay between messages is {0} seconds.**""".format(str(delay)))
				else:
					# try:
					if float(message.content[11:]) < 0:
						raise Exception
					delay = float(message.content[11:])
					filedata["delay"] = delay		#SAVE TO FILE
					await save_data(filedata)
					if delay == 1:
						await bot.send_message(message.channel, """**The delay between messages has been set to {0} second.**""".format(str(delay)))
					else:
						await bot.send_message(message.channel, """**The delay between message has been set to {0} seconds.**""".format(str(delay)))
					# except Exception:
					# 	await bot.send_message(message.channel, """**The delay must be an positive number!**""")



			elif (message.content[:16] == "!set errordelay ") or (message.content == "!set errordelay"):
				if message.content.strip() == "!set errordelay":
					if errordelay == 1:
						await bot.send_message(message.channel, """**The current delay when sending PMs too quickly is {0} second.**""".format(str(errordelay)))
					else:
						await bot.send_message(message.channel, """**The current delay when sending PMs too quickly is {0} seconds.**""".format(str(errordelay)))
				else:
					try:
						if float(message.content[16:]) < 0:
							raise Exception
						errordelay = float(message.content[16:])
						filedata["errordelay"] = errordelay		#SAVE TO FILE
						await save_data(filedata)
						if errordelay == 1:
							await bot.send_message(message.channel, """**The delay when sending PMs too quickly has been set to {0} second.**""".format(str(errordelay)))
						else:
							await bot.send_message(message.channel, """**The delay when sending PMs too quickly has been set to {0} seconds.**""".format(str(errordelay)))
					except Exception:
						await bot.send_message(message.channel, """**The error delay must be an positive number!**""")



			elif (message.content[:18] == "!set messagecount ") or (message.content == "!set messagecount"):
				if message.content.strip() == "!set messagecount":
					if messagecount == 1:
						await bot.send_message(message.channel, """**Currently {0} message is being sent between each delay.**""".format(str(messagecount)))
					else:
						await bot.send_message(message.channel, """**Currently {0} messages are being sent between each delay.**""".format(str(messagecount)))
				else:
					try:
						if int(message.content[18:]) < 1:
							raise Exception
						messagecount = int(message.content[18:])
						filedata["messagecount"] = messagecount		#SAVE TO FILE
						await save_data(filedata)
						await bot.send_message(message.channel, """**The messages being sent between each delay has been set to {0}.**""".format(str(messagecount)))
					except Exception:
						await bot.send_message(message.channel, """**The messagecount must be an positive integer (cannot be 0)!**""")



			elif (message.content[:6] == "!help ") or (message.content == "!help"):
				await bot.send_message(message.channel, """
**Here are all the commands in the PM Bot:**

*• !send **message** : Sends a PM to all the members in the servers in the server list.*
*• !cancel **message** : Cancels a PM currently being sent.*

*• !serverlist add **server** : Adds a server to send PMs to.*
*• !serverlist remove **server** : Removes a server that has PMs being send to it.*

*• !rolelist add **role** : Adds a role to ignore when sending PMs.*
*• !rolelist remove **role** : Removes a role that is being ignored when sending PMs.*

*• !memberlist add **member** : Adds a member to ignore when sending PMs.*
*• !memberlist remove **member** : Removes a member that is being ignored when sending PMs.*

*• !set delay **time in seconds** : Sets the delay (in seconds) between every PM(s) that are sent.*
*• !set errordelay **time in seconds** : Sets the delay (in seconds) that the bot waits when it is sending PMs too quickly.*
*• !set messagecount **amount of messages** : Sets the amount of PMs to be sent between each delay.*
""")



bot.loop.run_until_complete(asyncio.gather(
	bot.start(token, bot=not(selfbot)),
	filebot.start(filebot_token)
))
