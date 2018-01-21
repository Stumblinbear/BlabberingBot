import time
import asyncio

import telepot
from telepot.aio.loop import MessageLoop
from telepot.aio.delegate import per_chat_id, create_open, pave_event_space

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer, ListTrainer


import botan


botan.set_key('06de9876-3ab0-49a7-8772-bd9ca817bc82')

bot = ChatBot(
    'Birden',
    storage_adapter='chatterbot.storage.MongoDatabaseAdapter', 
    database='chatterbot-database',
    logic_adapters=[
        'chatterbot.logic.MathematicalEvaluation',
        'chatterbot.logic.BestMatch',
#        {
#            'import_path': 'chatterbot.logic.LowConfidenceAdapter',
#        'threshold': 0.65,
#            'default_response': 'I-I\'m sorry I... I don\'t know how you want me to respond...'
#        }
    ]
)

bot.set_trainer(ListTrainer)
#with open('log.txt', 'r') as f:
#	bot.train(f.readlines())

#bot.set_trainer(ChatterBotCorpusTrainer)
#bot.train("chatterbot.corpus.english")

log = open('log.txt', 'a')

class ChatHandler(telepot.aio.helper.ChatHandler):
	def __init__(self, *args, **kwargs):
		super(ChatHandler, self).__init__(*args, **kwargs)

		self.conv_id = bot.storage.create_conversation()
		
		self.prev_msg = None

	async def on_chat_message(self, msg):
		botan.track(msg['from']['id'], msg)

		if 'username' not in msg['from']:
			return

		data = get_data(msg)

		if data is None: return

		log.write(data.encode('UTF-8').decode('ascii', errors='ignore'))

		reply = (msg['chat']['type'] == 'private')

		if msg['date'] + 10 < time.time():
			reply = False

		print('inp: %s' % data.encode('UTF-8').decode('ascii', errors='ignore'))

		if 'reply_to_message' in msg:
			self.prev_msg = get_data(msg['reply_to_message'])

		if reply:
			await tbot.sendChatAction(msg['chat']['id'], 'typing')
			response = str(bot.get_response(data, self.conv_id))
			print('bot: %s' % response.encode('UTF-8').decode('ascii', errors='ignore'))

			if response.startswith('file.sticker='):
				await self.sender.sendSticker(response.split('=', 2)[1])
			elif response.startswith('file.document='):
				await self.sender.sendDocument(response.split('=', 2)[1])
			else:
				await tbot.sendChatAction(msg['chat']['id'], 'typing')
				await asyncio.sleep(2)
				await self.sender.sendMessage(response)
		elif self.prev_msg is not None:
			bot.train([self.prev_msg, data])

		self.prev_msg = data

def get_data(msg):
	data = None
	if 'text' in msg: data = msg['text']
	if 'sticker' in msg: data = 'file.sticker=' + msg['sticker']['file_id']
	if 'document' in msg: data = 'file.document=' + msg['document']['file_id']
	return data

tbot = telepot.aio.DelegatorBot('284668264:AAG_nlxgILhFZiB_IwwjwgCph6xn5bjwZnU', [
	pave_event_space()(
		per_chat_id(), create_open, ChatHandler, timeout=20
	)
])

loop = asyncio.get_event_loop() 
loop.create_task(MessageLoop(tbot).run_forever())
print('Listening...')
loop.run_forever()
