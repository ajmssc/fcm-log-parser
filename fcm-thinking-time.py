import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler()])
import math
from datetime import datetime, timedelta
import requests as requests
import re

# url = "http://play.boardgamecore.net/fcm/98593"
url = "http://play.boardgamecore.net/Json"
form_data = {'id': '98593', 'action': 'load'}

response = requests.post(url, form_data)

markers = ["@", "$", "-", "+", "[", "]", "?", ":", "&"]
markers_map = {
    '@': lambda x: decode64(x),
    '&': lambda x: -decode64(x),
    '$': lambda x: string_clean(x),
    '-': lambda x: decode_array_of_numbers(x),
    '+': lambda x: decode_array_of_numbers(x, True),
    ':': lambda x: [],
    '?': lambda x: None
}
REF = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l",
       "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "A", "B", "C", "D", "E", "F", "G", "H",
       "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "*", "%"]


def decode_array_of_numbers(chars, negative=False):
    num_of_digits = decode64(chars[0])
    chaine = chars[1:]
    res = []
    i = 0
    while i < len(chaine):
        value = decode64(chaine[i:i + num_of_digits])
        res.append(value if not negative else -value)
        i += num_of_digits
    return res


def string_clean(chars):
    chars = re.sub('/__DOL__/g', '$', chars)
    chars = re.sub('/__OP__/g', '[', chars)
    chars = re.sub('/__CLO__/g', ']', chars)
    chars = re.sub('/__ARO__/g', "@", chars)
    chars = re.sub('/__TIR__/g', "-", chars)
    chars = re.sub('/__PLU__/g', "+", chars)
    chars = re.sub('/__AMP__/g', "&", chars)
    chars = re.sub('/__QUE__/g', "?", chars)
    chars = re.sub('/__COL__/g', ":", chars)
    return chars


def decode64(chars):
    res = 0
    for i, c in enumerate(chars):
        idx = len(chars) - i - 1
        res += REF.index(c) * math.pow(64, idx)
    return int(res)


def map_token(token):
    if token[0] in markers_map:
        return markers_map[token[0]](token[1:])
    else:
        return token


def tokenize(substr):
    tokens = []
    current_token = ""

    i = 0
    while i < len(substr):
        letter = substr[i]
        if letter in markers:
            if current_token != "":
                mapped_token = map_token(current_token)
                tokens.append(mapped_token)
            current_token = ''

            if letter == '[':
                open_count = 1

                while open_count > 0 and i < len(substr):
                    i += 1
                    if substr[i] == '[':
                        open_count += 1
                    elif substr[i] == ']':
                        open_count -= 1
                    current_token += substr[i]
                tokens.append(tokenize(current_token))
                current_token = ""
            else:
                current_token += letter
        else:
            current_token += letter
        i += 1
    return tokens


data = response.content.decode("utf-8")
fcm_data = tokenize(data)[0]
actions = fcm_data[17][1:]
timestamps = fcm_data[18]

actions_to_id = {
    'SETUP_GAME': 0,
    'CHOOSE_RESTAURANT_STARTING_POSITION': 1,
    'CHOOSE_RESERVE_CARD': 2,
    'CHOOSE_STRUCTURE': 3,
    'DELAY_SETUP': 4,
    'CHOOSE_TURN_ORDER': 5,
    'HIRE': 6,
    'TRAIN': 7,
    'START_MARKETING_CAMPAIGN': 8,
    'PRODUCE_FOOD_DRINKS': 9,
    'BANK_BREAK': 10,
    'BUILD_GARDEN': 11,
    'BUILD_HOUSE': 12,
    'OPEN_RESTAURANT': 13,
    'MOVE_RESTAURANT': 14,
    'DINNER_TIME': 15,
    'SALARY': 16,
    'MARKETING_CAMPAIGN': 17,
    'INCOME': 18,
    'NEW_MILESTONE': 19,
    'DISPLAY_RESERVE': 20,
    'FIRE': 21,
    'DELETE_RESOURCES': 22,
    'NEW_TURN': 23,
    'END_GAME': 24,
    'BANKRUPT': 25,
    'TOTAL_BANKRUPT': 26,
    'ONE_LEFT': 27,
    'MARKETING_EARNING': 28,
    'PIZZA_BOMB': 29,
    'DISCOUNT_MILESTONE': 30
}
id_to_action = {v: k for k, v in actions_to_id.items()}

players = {-1: 'GAME', 63: 'GAME'}
origin_timestamp = fcm_data[17][0]
start_of_game_timestamp = datetime.fromtimestamp(origin_timestamp)
parsed_actions = []
for action, timestamp in zip(actions, timestamps):
    action_player, action_type, action_options = action
    formatted_timestamp = start_of_game_timestamp + timedelta(seconds=timestamp)
    action_type = id_to_action[action_type]
    if action_type == 'SETUP_GAME':
        player_id = 0
        for i in range(4, len(action_options), 2):
            players[player_id] = action_options[i]
            player_id += 1
    parsed_actions.append({'timestamp': formatted_timestamp, 'player': players[action_player], 'type': action_type, 'options': action_options})

players_thinking_time = {k:0 for k in players.values()}
parsed_actions.sort(key=lambda x: x['timestamp'])
last_timestamp = start_of_game_timestamp
last_player = 'GAME'
for action in parsed_actions:
    logging.info(f"{action['timestamp']} - player:{action['player']} {action['type']} - {action['options']}")
    time_spent = (action['timestamp'] - last_timestamp).seconds
    if action['player'] == 'GAME' and last_player != 'GAME':
        players_thinking_time[last_player] += time_spent
    elif last_player == 'GAME' and action['player'] != 'GAME':
        players_thinking_time[action['player']] += time_spent
    else:
        players_thinking_time[action['player']] += time_spent
    last_player = action['player']
    last_timestamp = action['timestamp']



for player, thinking_time in players_thinking_time.items():
    logging.info(f"Thinking time for {player}: {timedelta(seconds=thinking_time)}")