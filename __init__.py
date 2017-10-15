import time
import threading
from random import random
import re
import sys

import nltk
from nltk.tag import pos_tag
import telepot
from telepot.delegate import per_chat_id, create_open, pave_event_space


nltk.download('averaged_perceptron_tagger')

reply_request = []
last_msg_id = {}
last_user_id = {}

def get_query(the_input):
	query = the_input

	tags = pos_tag(query.split())
	def get_search_pos(tags):
		tag_priority = ['NN', 'NNP', 'PRP', 'WP']

		i = 0
		while i < len(tag_priority):
			test = [word for word, pos in tags if pos == tag_priority[i]]
			if len(test) != 0:
				return test[len(test) - 1]
			i += 1

		return None

	search_pos = get_search_pos(tags)
	if search_pos is not None:
		query = search_pos

	return query

def handle_reply(b, request):
	tries = 5

	query = get_query(request['msg']['text'])

	# Prevent duplicate replies
	the_reply = b.reply(query)
	while the_reply == request['msg']['text'] and tries > 0:
		the_reply = b.reply(query)
		tries = tries - 1

	if the_reply == request['msg']['text']:
		the_reply = 'what'
	else:
		# Replace any tailbot or birden references with the user's name
		the_reply = re.sub(r'@?(?:tail\s?bot|(?:b|d)\Srd\Sn)', request['msg']['from']['first_name'], the_reply, flags=re.MULTILINE | re.IGNORECASE)

	def delayed():
		bot.sendChatAction(request['msg']['chat']['id'], 'typing')
		time.sleep(.1 * len(the_reply))
		if last_msg_id[request['msg']['chat']['id']] == request['msg']['message_id']:
			request['sender'].sendMessage(the_reply, parse_mode='HTML')
		else:
			request['sender'].sendMessage(the_reply, parse_mode='HTML', reply_to_message_id=None if request['msg']['chat']['type'] == 'private' else request['msg']['message_id'])

	if request['msg']['date'] + 10 < time.time():
		print('I would\'ve responded, but the message was outside my reply threshold.')
		return

	thread = threading.Thread(target=delayed)
	thread.daemon = True
	thread.start()

	spacing = ''
	for i in range(len(request['msg']['from']['username']) + 6):
		spacing = spacing + ' '
	print('%sI replied: %r' % (spacing, the_reply.encode('UTF-8', errors='ignore')))

def brain_function():
	global reply_request

	from cobe.brain import Brain
	b = Brain("cobe.brain")

	while True:
		time.sleep(.1)
		if len(reply_request) > 0:
			for request in reply_request:
				if request['msg']['text'].startswith('/'):
					if request['msg']['text'] == '/info':
						c = b.graph.cursor()

						words = int(c.execute('SELECT COUNT(*) FROM tokens').fetchone()[0])
						connections = int(c.execute('SELECT COUNT(*) FROM edges').fetchone()[0])
						branches = int(c.execute('SELECT SUM(count) FROM nodes').fetchone()[0])
						request['sender'].sendMessage('I know %s words and have a total of %s connections with %s possible branches between them.' % (words, connections, branches))
					continue

				for line in request['msg']['text'].split('\n'):
					b.learn(line)

				spacing = ''
				for i in range(10 - len(request['msg']['chat']['type'])):
					spacing = spacing + ' '
				print('[%s]%s %r: %r' % (request['msg']['chat']['type'], spacing,
								request['msg']['from']['username'].encode('UTF-8', errors='ignore'),
								request['msg']['text'].encode('UTF-8', errors='ignore')))

				last_msg_id[request['msg']['chat']['id']] = request['msg']['message_id']
				if request['reply'] or (request['msg']['chat']['id'] in last_user_id and last_user_id[request['msg']['chat']['id']] == request['msg']['from']['id']):
                                        if not request['reply'] and random() < .1:
						del last_user_id[request['msg']['chat']['id']]
					handle_reply(b, request)
					last_user_id[request['msg']['chat']['id']] = request['msg']['from']['id']
				elif request['msg']['chat']['id'] in last_user_id:
					del last_user_id[request['msg']['chat']['id']]

			reply_request = []

thread = threading.Thread(target=brain_function)
thread.daemon = True
thread.start()

class HALHandler(telepot.helper.ChatHandler):
	def __init__(self, *args, **kwargs):
		super(HALHandler, self).__init__(*args, **kwargs)

	def on_chat_message(self, msg):
		if 'text' not in msg or 'username' not in msg['from']:
			return

		reply = (msg['chat']['type'] == 'private')

		if not reply and (random() < .03):
			reply = True
		if not reply and 'reply_to_message' in msg and 'username' in msg['reply_to_message']['from']:
			if msg['reply_to_message']['from']['username'] == 'BlabberingFurryBot':
				reply = True
		new_text = re.sub('^(?:hey|hoi|sup|yo)?\s?(?:b|d)\Srd\Sn,?\s*?', '', msg['text'], flags=re.MULTILINE | re.IGNORECASE)
		if msg['text'] != new_text:
			msg['text'] = new_text
			reply = True

		reply_request.append({'sender': self.sender, 'msg': msg, 'reply': reply})

bot = telepot.DelegatorBot('284668264:AAG_nlxgILhFZiB_IwwjwgCph6xn5bjwZnU', [
	pave_event_space()(
		per_chat_id(), create_open, HALHandler, timeout=60
	)
])
bot.message_loop(run_forever='Listening ...')
