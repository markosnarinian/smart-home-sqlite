from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import abort
from flask import jsonify
from requests import post
from requests.exceptions import ConnectionError
from requests.exceptions import ConnectTimeout
from secrets import token_hex
from json import loads
from json import dumps
from time import time
import sqlite3

print_ff_request_response = True
auth_enabled = True

app = Flask(__name__)

file_config = open('./config/config.json', 'rt')
config = loads(file_config.read())
file_config.close()

def slcefa(command):
    database = sqlite3.connect(config['database']['database_name'], check_same_thread=False)
    cursor = database.cursor()
    cursor.execute(command)
    return cursor.fetchall()


def slc_exe(command):
    database = sqlite3.connect(config['database']['database_name'], check_same_thread=False)
    cursor = database.cursor()
    cursor.execute(command)
    database.commit()


def on_off(on, device_identifier, username):
    file_devices = open('./config/devices.json', 'rt')
    devices_json = loads(file_devices.read())
    file_devices.close()

    devices_json['device_states'][username][device_identifier]['on'] = on

    drive_param = None
    if on:
        drive_param = 'dl'
    elif not on:
        drive_param = 'dh'

    gpio_pin = None
    if device_identifier == '1':
        gpio_pin = 2

    payload = {'command': 'raspi-gpio set {pin} op {drive}'.format(drive=drive_param, pin=gpio_pin)}
    request = post('http://192.168.1.2:5000/command', json=dumps(payload))

    file_devices = open('./config/devices.json', 'wt')
    file_devices.write(dumps(devices_json))
    file_devices.close()

    return request


def lock_unlock(lock, device_identifier, username):
    file_devices = open('./config/devices.json', 'rt')
    devices_json = loads(file_devices.read())
    file_devices.close()

    payload = {}
    if device_identifier == '2':
        if lock:
            pass
        elif not lock:
            payload = {'command': 'python3 /home/pi/smart-home/unlock_front_door.py'}

            devices_json['device_states'][username][device_identifier]['isLocked'] = True
            devices_json['device_states'][username][device_identifier]['isJammed'] = False

    request = post('http://192.168.1.2:5000/command', json=dumps(payload))

    file_devices = open('./config/devices.json', 'wt')
    file_devices.write(dumps(devices_json))
    file_devices.close()

    return request


def open_close(open_percent, device_identifier, username):
    file_devices = open('./config/devices.json', 'rt')
    devices_json = loads(file_devices.read())
    file_devices.close()

    payload = {}
    if open_percent == 0:
        payload = {'command': 'ShutterClose'}

        devices_json['device_states'][username][device_identifier]['openState'][0]['openPercent'] = 0
    elif open_percent != 0:
        payload = {'command': 'ShutterOpen'}

        devices_json['device_states'][username][device_identifier]['openState'][0]['openPercent'] = 100

    request = post('http://192.168.1.7:5000/command', data=payload)

    file_devices = open('./config/devices.json', 'wt')
    file_devices.write(dumps(devices_json))
    file_devices.close()

    return request


def set_fan_speed(fan_speed, device_identifier, username):
    file_devices = open('./config/devices.json', 'rt')
    devices_json = loads(file_devices.read())
    file_devices.close()

    payload = {'command': 'SetFanSpeed', 'fan_speed': fan_speed}
    devices_json['device_states'][username][device_identifier]['currentFanSpeedSetting'] = fan_speed

    request = post('http://192.168.1.9:5000/command', data=payload)
    # class request:
    #     status_code = 200

    file_devices = open('./config/devices.json', 'wt')
    file_devices.write(dumps(devices_json))
    file_devices.close()

    return request


@app.route('/ping', methods=['POST'])
def ping():
    return jsonify({})


@app.route('/google/login', methods=['GET'])
def auth():
    return render_template(
        'google_login_page.html',
        client_id=request.args['client_id'],
        redirect_uri=request.args['redirect_uri'],
        state=request.args['state'],
        response_type=request.args['response_type']
    )


@app.route('/google/auth', methods=['POST'])
def google_auth():
    if not auth_enabled:
        abort(403)

    valid_credentials = {
        'usernames': (),
        'password': None
    }

    result = slcefa('select username from users')
    users = []
    for user in result:
        users.append(user[0])
    valid_credentials['usernames'] = tuple(users)
    result = slcefa('select password from users where username = "{username}"'.format(username=request.form['uname']))
    if len(result) == 1: valid_credentials['password'] = result[0][0]
    elif len(result) != 1: abort(401)

    criteria = [
        request.form['client_id'] == config['google']['client']['client_id'],
        request.form['redirect_uri'] == config['google']['google_user_content']['redirect_uri'],
        request.form['response_type'] == 'code',
        request.form['uname'] in valid_credentials['usernames'],
        request.form['passwd'] == valid_credentials['password']
    ]
    authorized = True
    for c in criteria:
        if not c:
            authorized = False
            break

    if authorized:
        tokens = [None]
        while True:
            authorization_code = token_hex(512)

            tokens = slcefa('SELECT username FROM tokens WHERE token = "{token}" AND token_type = "auth_code" AND service = "google" AND username = "{username}" AND ({time} - timestamp) <= 600' \
                .format(token=authorization_code, username=request.form['uname'], time=str(int(time()))))

            if len(tokens) == 0:
                slc_exe('INSERT INTO tokens (token, token_type, service, username, timestamp) VALUES ("{token}", "auth_code", "google", "{username}", {timestamp})' \
                    .format(token=authorization_code, username=request.form['uname'], timestamp=str(int(time()))))

                redirect_url = '{0}?code={1}&state={2}' \
                    .format(config['google']['google_user_content']['redirect_uri'], authorization_code, request.form['state'])
                return redirect(redirect_url)
            else:
                abort(401)
    else:
        abort(401)


@app.route('/google/token', methods=['GET', 'POST'])
def google_token():
    response = {'error': 'invalid_grant'}

    if request.form['client_id'] == config['google']['client']['client_id'] and \
        request.form['client_secret'] == config['google']['client']['client_secret']:

        usernames = []
        if request.form['grant_type'] == 'authorization_code':
            tokens = [None]
            while True:
                usernames = slcefa('SELECT username FROM tokens WHERE token = "{token}" AND token_type = "auth_code" AND service = "google" AND ({time} - timestamp) <= 600' \
                    .format(token=request.form['code'], time=str(int(time()))))

                if len(usernames) == 1:
                    username_by_code = usernames[0][0]
                    break
        elif request.form['grant_type'] == 'refresh_token':
            tokens = [None]
            while True:
                usernames = slcefa('SELECT username FROM tokens WHERE token = "{token}" AND token_type = "refresh_token" AND service = "google"' \
                    .format(token=request.form['refresh_token']))

                if len(usernames) == 1:
                    username_by_code = usernames[0][0]
                    break

        if len(usernames)  == 1:
            result = slcefa('select username from users')

            users = []
            for user in result:
                users.append(user[0])

            if len(users) == 1:
                if request.form['grant_type'] == 'authorization_code':
                    if request.form['redirect_uri'] == config['google']['google_user_content']['redirect_uri']:

                        tokens = [None]
                        while True:
                            access_token = token_hex(512)

                            tokens = slcefa('SELECT token, token_type, username, timestamp FROM tokens WHERE token = "{token}" AND token_type = "access_token" AND service = "google" AND username = "{username}" AND ({time} - timestamp) <= 3600' \
                                .format(token=access_token, username=username_by_code, time=str(int(time()))))

                            if len(tokens) == 0:
                                break

                        tokens = [None]
                        while True:
                            refresh_token = token_hex(512)

                            tokens = slcefa('SELECT token, token_type, username, timestamp FROM tokens WHERE token = "{token}" AND token_type = "refresh_token" AND service = "google" AND username = "{username}"' \
                                .format(token=refresh_token, username=username_by_code))

                            if len(tokens) == 0:
                                break

                        slc_exe('insert into tokens (token, token_type, service, username, timestamp) values ("{token}", "access_token", "google", "{username}", "{timestamp}")' \
                            .format(token=str(access_token), username=str(username_by_code), timestamp=str(int(time()))))
                        slc_exe('insert into tokens (token, token_type, service, username, timestamp) values ("{token}", "refresh_token", "google", "{username}", "{timestamp}")' \
                            .format(token=str(refresh_token), username=str(username_by_code), timestamp=str(int(time()))))

                        response = {
                            'token_type': 'Bearer',
                            'access_token': access_token,
                            'refresh_token': refresh_token,
                            'expires_in': 3600
                        }
                elif request.form['grant_type'] == 'refresh_token':
                    tokens = [None]
                    while True:
                        access_token = token_hex(512)

                        tokens = slcefa('SELECT token, token_type, username, timestamp FROM tokens WHERE token = "{token}" AND token_type = "access_token" AND service = "google" AND username = "{username}" AND ({time} - timestamp) <= 3600' \
                            .format(token=access_token, username=username_by_code, time=str(int(time()))))

                        if len(tokens) == 0:
                            break

                    slc_exe('insert into tokens (token, token_type, service, username, timestamp) values ("{token}", "access_token", "google", "{username}", "{timestamp}")' \
                        .format(token=str(access_token), username=str(username_by_code), timestamp=str(int(time()))))

                    response = {
                        'token_type': 'Bearer',
                        'access_token': access_token,
                        'expires_in': 3600
                    }
    return jsonify(response)


@app.route('/google/fulfillment', methods=['GET', 'POST'])
def google_fulfillment():
    token = request.headers['Authorization']
    token_formatted = token.replace('Bearer ', '')

    usernames = [None]
    while True:
        usernames = slcefa('SELECT username FROM tokens WHERE token = "{token}" AND token_type = "access_token" AND service = "google" AND ({time} - timestamp) <= 3600' \
            .format(token=token_formatted,
            time=str(int(time()))))

        if len(usernames) == 1:
            username_by_token = usernames[0][0]
            break

    if len(usernames) == 1:
        for i in request.json['inputs']:
            if i['intent'] == 'action.devices.DISCONNECT':
                slc_exe('DELETE FROM tokens WHERE username = "{username}" AND service = "google"'.format(username=username_by_token))

                response = {}
            elif i['intent'] == 'action.devices.SYNC':
                agent_user_id = slcefa('SELECT agent_user_id FROM users WHERE username = "{username}"'.format(username=username_by_token))[0][0]

                file_devices = open('./config/devices.json', 'rt')
                devices_json = loads(file_devices.read())
                file_devices.close()

                response = {
                    'requestId': str(request.json['requestId']),
                    'payload': {
                        'agentUserId': agent_user_id,
                        'devices': devices_json['devices'][username_by_token]
                    }
                }
            elif i['intent'] == 'action.devices.QUERY':
                file_devices = open('./config/devices.json', 'rt')
                devices_json = loads(file_devices.read())
                file_devices.close()

                device_id = []
                for device in i['payload']['devices']:
                    for dev in devices_json['devices'][username_by_token]:
                        if dev['id'] == device['id']:
                            device_id.append((str(device['id']), dev['traits']))

                response = {
                    'request_id': str(request.json['requestId']),
                    'payload': {
                        'devices': {}
                    }
                }
                

                values = []
                for device in device_id:
                    param_args = {device[0]: {}}
                    for trait in device[1]:
                        value = None
                        if trait == 'action.devices.traits.OnOff':
                            param_args[device[0]].update({'on': devices_json['device_states'][username_by_token][device[0]]['on']})
                        elif trait == 'action.devices.traits.LockUnlock':
                            param_args[device[0]].update({'isLocked': devices_json['device_states'][username_by_token][device[0]]['isLocked'], \
                                'isJammed': devices_json['device_states'][username_by_token][device[0]]['isJammed']})
                        elif trait == 'action.devices.traits.OpenClose':
                            param_args[device[0]].update({'openPercent': devices_json['device_states'][username_by_token][device[0]]['openState'][0]['openPercent'], \
                                'isJammed': devices_json['device_states'][username_by_token][device[0]]['isJammed']})
                        elif trait == 'action.devices.traits.FanSpeed':
                            param_args[device[0]].update({'currentFanSpeedSetting': devices_json['device_states'][username_by_token][device[0]]['currentFanSpeedSetting']})
                        values.append(value)

                response['payload']['devices'] = dict(**param_args)
            elif i['intent'] == 'action.devices.EXECUTE':
                challenge_ok = 2
                commands_final = []

                file_devices = open('./config/devices.json', 'rt')
                devices_json = loads(file_devices.read())
                file_devices.close()

                for command in i['payload']['commands']:
                    device_id = []
                    for device in command['devices']:
                        device_id.append(device['id'])

                    for identifier in device_id:
                        for execution in command['execution']:
                            if identifier in devices_json['challenge'][username_by_token]:
                                if execution['command'] in devices_json['challenge'][username_by_token][identifier]['commands']:
                                    if devices_json['challenge'][username_by_token][identifier]['challenge_type'] == 'ackNeeded':
                                        if 'challenge' in execution:
                                            if execution['challenge']['ack'] == devices_json['challenge'][username_by_token][identifier]['desired_challenge_value']:
                                                challenge_ok = 0
                                            elif execution['challenge']['ack'] != devices_json['challenge'][username_by_token][identifier]['desired_challenge_value']:
                                                challenge_ok = 1
                                        elif 'challenge' not in execution:
                                            challenge_ok = 2
                                    elif devices_json['challenge'][username_by_token][identifier]['challenge_type'] == 'pinNeeded':
                                        if 'challenge' in execution:
                                            if execution['challenge']['pin'] == devices_json['challenge'][username_by_token][identifier]['desired_challenge_value']:
                                                challenge_ok = 0
                                            elif execution['challenge']['pin'] != devices_json['challenge'][username_by_token][identifier]['desired_challenge_value']:
                                                challenge_ok = 1
                                        elif 'challenge' not in execution:
                                            challenge_ok = 2
                                elif execution['command'] not in devices_json['challenge'][username_by_token][identifier]['commands']:
                                    challenge_ok = 0
                            elif identifier not in devices_json['challenge'][username_by_token]:
                                challenge_ok = 0

                            command_to_append = None
                            if challenge_ok == 0:
                               try:
                                    class post_object: status_code = 500

                                    if execution['command'] == 'action.devices.commands.OnOff':
                                        post_object = on_off(on=execution['params']['on'], device_identifier=identifier, username=username_by_token)
                                    elif execution['command'] == 'action.devices.commands.LockUnlock':
                                        post_object = lock_unlock(lock=execution['params']['lock'], device_identifier=identifier, username=username_by_token)
                                    elif execution['command'] == 'action.devices.commands.OpenClose':
                                        post_object = open_close(open_percent=execution['params']['openPercent'], device_identifier=identifier, username=username_by_token)
                                    elif execution['command'] == 'action.devices.commands.SetFanSpeed':
                                        post_object = set_fan_speed(fan_speed=execution['params']['fanSpeed'], device_identifier=identifier, username=username_by_token)
                               except ConnectionError:
                                   command_to_append = {
                                       'ids': [str(identifier)],
                                       'status': 'ERROR',
                                       'errorCode': 'deviceOffline'
                                   }
                               except ConnectTimeout:
                                   command_to_append = {
                                       'ids': [str(identifier)],
                                       'status': 'ERROR',
                                       'errorCode': 'deviceOffline'
                                   }
                               else:
                                if post_object.status_code == 200:
                                    command_to_append = {
                                        'ids': [str(identifier)],
                                        'status': 'SUCCESS',
                                        'states': {
                                            'online': True
                                        }
                                    }

                                if post_object.status_code in [400, 500]:
                                    command_to_append = {
                                        'ids': [str(identifier)],
                                        'status': 'ERROR',
                                        'errorCode': 'deviceOffline'
                                    }

                                if post_object.status_code == 200:
                                    if execution['command'] == 'action.devices.commands.OnOff':
                                        command_to_append['states'].update({'on': execution['params']['on']})
                                    elif execution['command'] == 'action.devices.commands.LockUnlock':
                                        command_to_append['states'].update({'isLocked': execution['params']['lock'], 'isJammed': devices_json['device_states'][username_by_token][identifier]['isJammed']})
                                    elif execution['command'] == 'action.devices.commands.OpenClose':
                                        open_percent = 0

                                        command_to_append['states'].update({'isLocked': open_percent, 'isJammed': devices_json['device_states'][username_by_token][identifier]['isJammed']})
                                    elif execution['command'] == 'action.devices.commands.SetFanSpeed':
                                        command_to_append['states'].update({'currentFanSpeedSetting': execution['params']['fanSpeed']})


                            elif challenge_ok == 1 and devices_json['challenge'][username_by_token][identifier]['challenge_type'] == 'pinNeeded':
                                command_to_append = {
                                    'ids': [str(identifier)],
                                    'status': 'ERROR',
                                    'errorCode': 'challengeNeeded',
                                    'challengeNeeded': {
                                        'type': 'challengeFailedPinNeeded'
                                    }
                                }

                            elif challenge_ok == 2:
                                command_to_append = {
                                    'ids': [str(identifier)],
                                    'status': 'ERROR',
                                    'errorCode': 'challengeNeeded',
                                    'challengeNeeded': {
                                        'type': devices_json['challenge'][username_by_token][identifier]['challenge_type']
                                    }
                                }
                            commands_final.append(command_to_append)

                    response = {
                        'requestId': request.json['requestId'],
                        'payload': {
                            'commands': commands_final
                        }
                    }

                    if challenge_ok == 1 and devices_json['challenge'][username_by_token][identifier]['challenge_type'] == 'ackNeeded':
                        response = {}

    print('\n\n', end='')
    print(request.json)
    print('\n', end='')
    print(dumps(response))
    print('\n\n', end='')


    return jsonify(response)


if __name__ == '__main__':
    if config['server_config']['ssl_tls']['ssl_certification']:
        app.run(
            host=config['server_config']['host'],
            port=config['server_config']['port'],
            debug=config['server_config']['debug_mode'],
            ssl_context=(
                config['server_config']['ssl_tls']['ssl_context']['certificate'],
                config['server_config']['ssl_tls']['ssl_context']['private_key']
            )
        )
    if not config['server_config']['ssl_tls']['ssl_certification']:
        app.run(
            host=config['server_config']['host'],
            port=config['server_config']['port'],
            debug=config['server_config']['debug_mode']
        )
