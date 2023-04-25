from flask import Flask
from flask import render_template
from flask import redirect
from flask import request
from flask import make_response
from flask import abort
from flask import jsonify
from secrets import token_hex
from json import loads
from json import dumps

users = {
    'users': ['manarinian'],
    'passwd': {
        'manarinian': 'pwd'
    },
    'tokens': {
        'tokens': ['token'],
        'users': {'token': 'manarinian'}
    }}

with open('/home/pi/smart-home-fulfillment/config/config.json', 'rt') as file_config:
    config = loads(file_config.read())
    file_config.close()

server = Flask(__name__)

@server.route('/', methods=['GET'])
def index():
    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens']:
            return render_template('homepage_logged_in.html')
        elif request.cookies['token'] not in users['tokens']['tokens']:
            return render_template('homepage.html')
    elif 'token' not in request.cookies:
        return render_template('homepage.html')


@server.route('/login', methods=['GET'])
def login():
    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens']:
            return render_template('already_logged_in.html')
        elif request.cookies['token'] not in users['tokens']['tokens']:
            if 'redirect_uri' in request.args:
                return render_template('login_page.html', redirect_uri=request.args['redirect_uri'])
            elif 'redirect_uri' not in request.args:
                return render_template('login_page.html')
    elif 'token' not in request.cookies:
        if 'redirect_uri' in request.args:
            return render_template('login_page.html', redirect_uri=request.args['redirect_uri'])
        elif 'redirect_uri' not in request.args:
            return render_template('login_page.html')


@server.route('/login_action', methods=['POST'])
def login_action():
    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens'] and \
            request.form['uname'] == users['tokens']['users'][request.form['token']]:

            return render_template('already_logged_in.html')
        else:
            if request.form['uname'] in users['users'] and \
                request.form['passwd'] == users['passwd'][request.form['uname']]:

                token = token_hex(8)

                users['tokens']['tokens'].append(token)
                users['tokens']['users'].update({token: request.form['uname']})

                response = make_response(redirect('/'))
                if 'redirect_uri' in request.form:
                    response = make_response(redirect(request.form['redirect_uri']))
                    response.set_cookie('token', 'token')

                return response
            elif request.form['uname'] not in users['users'] or \
                request.form['passwd'] != users['passwd'][request.form['uname']]:
                abort(401)
            elif request.form['uname'] not in users['users'] and \
                request.form['passwd'] != users['passwd'][request.form['uname']]:
                abort(401)
    elif 'token' not in request.cookies:
        if request.form['uname'] in users['users'] and \
            request.form['passwd'] == users['passwd'][request.form['uname']]:

            token = token_hex(8)

            users['tokens']['tokens'].append(token)
            users['tokens']['users'].update({token: request.form['uname']})

            response = make_response(redirect('/'))
            if 'redirect_uri' in request.form:
                response = make_response(redirect(request.form['redirect_uri']))
                response.set_cookie('token', 'token')

            return response
        elif request.form['uname'] not in users['users'] or \
            request.form['passwd'] != users['passwd'][request.form['uname']]:
            abort(401)
        elif request.form['uname'] not in users['users'] and \
            request.form['passwd'] != users['passwd'][request.form['uname']]:
            abort(401)


@server.route('/commit_changes', methods=['GET', 'POST'])
def commit_changes():
    response = redirect('/login?redirect_uri=/devices/edit?id={0}'.format(request.form['device_id']))
    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens']:
            username_by_token = users['tokens']['users'][request.cookies['token']]

            with open('/home/pi/smart-home-fulfillment/config/devices.json') as devices_file:
                devices_json = loads(devices_file.read())
                devices_file.close()

            for device in devices_json['devices'][username_by_token]:
                if device['id'] == request.form['device_id']:
                    device['type'] = request.form['device_type']

                    device['traits'] = []
                    for trait_form in devices_json['traits']:
                        if trait_form in request.form:
                            if request.form[trait_form] == 'on':
                                device['traits'].append(trait_form)

                    if len(device['traits']) == 0:
                        response = render_template('zero_traits.html')
                        break

                    device['name']['name'] = request.form['default_name']

                    with open('/home/pi/smart-home-fulfillment/config/devices.json', 'wt') as devices_file:
                        devices_file.write(dumps(devices_json))
                        devices_file.close()

            response = redirect('/devices/edit?id={0}'.format(request.form['device_id']))

    return response


@server.route('/submit_form_new_device', methods=['GET', 'POST'])
def submit_form_new_device():
    print(request.form)
    response = redirect('/login?redirect_uri=/devices/new')
    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens']:
            username_by_token = users['tokens']['users'][request.cookies['token']]

            with open('/home/pi/smart-home-fulfillment/config/devices.json') as devices_file:
                devices_json = loads(devices_file.read())
                devices_file.close()

            traits = []
            for trait in devices_json['traits']:
                if trait in request.form:
                    if request.form[trait] == 'on':
                        traits.append(trait)

            device = {
                "id": request.form['device_id'],
                "type": request.form['device_type'],
                "traits": traits,
                "name": {
                    "name": request.form['default_name']
                },
                "willReportState": False,
                "otherDeviceIds": [
                    {
                        "deviceId": "local_{id}".format(id=request.form['device_id'])
                    }
                ]
            }
            challenge = {
                request.form['device_id']: {
                    "challenge_type": None,
                    "desired_challenge_value": None,
                    "commands": []
                }
            }

            if request.form['device_type'] == 'action.devices.types.LIGHT':
                state = {
                    request.form['device_id']: {
                        'online': True,
                        'on': True
                    }
                }
            elif request.form['device_type'] == 'action.devices.types.LOCK':
                state = {
                    request.form['device_id']: {
                        'online': True,
                        'isLocked': True,
                        'isJammed': False
                    }
                }
            elif request.form['device_type'] == 'action.devices.types.DOOR':
                state = {
                    request.form['device_id']: {
                        'online': True,
                        'isLocked': True,
                        'isJammed': False
                    }
                }

            devices_json['devices'][username_by_token].append(device)
            devices_json['device_states'][username_by_token].update(state)
            devices_json['challenge'][username_by_token].update(challenge)

            with open('/home/pi/smart-home-fulfillment/config/devices.json', 'wt') as file_devices:
                file_devices.write(dumps(devices_json))
                file_devices.close()

            response = redirect('/devices?id={0}'.format(request.form['device_id']))

    return response


@server.route('/signup')
def signup():
    return render_template('signup.html')


@server.route('/logout', methods=['GET'])
def logout():
    response = make_response(redirect('/'))
    response.set_cookie('token', '')

    return response


@server.route('/devices', methods=['GET'])
def devices():
    response = redirect('/login?redirect_uri=/devices')
    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens']:
            username_by_token = users['tokens']['users'][request.cookies['token']]

            with open('/home/pi/smart-home-fulfillment/config/devices.json', 'rt') as devices_file:
                devices_json = loads(devices_file.read())
                devices_file.close()

            html_file_r = open('/home/pi/smart-home-fulfillment/templates/devices.html', 'rt')
            html_from_template = html_file_r.read()
            html_file_r.close()

            values_to_insert = ''
            for device in devices_json['devices'][username_by_token]:
                values_to_insert += '<tr class="clickable-row" onclick="window.location=\'/devices/edit?id={device_id}\'"><td>{device_id}</td><td>{device_type}</td></tr>' \
                    .format(device_id=device['id'], device_type=device['type'])

            html_from_template = html_from_template.replace('devices_length_header', str(len(devices_json['devices'][username_by_token])))
            response = f'{html_from_template}<table class="table table-hover table-bordered"><thead><tr><th>Device ID</th><th>Device Type</th></tr></thead><tbody>{values_to_insert}</tbody></table></body></html>'

    return response


@server.route('/devices/edit', methods=['GET'])
def devices_edit():
    response = redirect('/login?redirect_uri=/devices/edit')
    if 'id' in request.args:
        response = redirect('/login?redirect_uri=/devices/edit?id={0}'.format(request.args['id']))

    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens']:
            username_by_token = users['tokens']['users'][request.cookies['token']]

            with open('/home/pi/smart-home-fulfillment/config/devices.json', 'rt') as devices_file:
                devices_json = loads(devices_file.read())
                devices_file.close()

            html_file_r = open('/home/pi/smart-home-fulfillment/templates/edit.html', 'rt')
            html_from_template = html_file_r.read()
            html_file_r.close()

            response = None

            if 'id' not in request.args: response = 'Device ID not specified'
            elif 'id' in request.args:
                selected_device = None
                devices = devices_json['devices'][username_by_token]
                for device in devices:
                    if device['id'] == request.args['id']:
                        selected_device = device

                if selected_device == None: response = 'Device not Found'
                elif selected_device != None:
                    device_type = ''
                    for device in devices_json['devices'][username_by_token]:
                        if device['id'] == request.args['id']: device_type = device['type']

                    response = html_from_template.replace('--|-|--device_id--|-|--', request.args['id'])
                    response += '<h6>Device ID</h6><input type="text" class="form-control" value="{id}" disabled><br/ >'.format(id=request.args['id'])
                    
                    # response_commands = ''
                    # response_pin = ''

                    response += '<h6>Type</h6><div class="form-group"><select class="form-control" name="device_type" required>'
                    for device_type in devices_json['types']:
                        input_state = ' disabled'
                        if device_type == selected_device['type']:
                            input_state = ' selected'
                        elif device_type != selected_device['type']:
                            input_state = ''

                        response += f'<option{input_state}>{device_type}</option>'

                    response += '</select></div><h6>Traits</h6>'
                    for trait in devices_json['traits']:
                        state = ' disabled'
                        if trait in selected_device['traits']: state = ' checked'
                        elif trait not in selected_device['traits']: state = ''

                        response += f'<div class="form-check"><label class="form-check-label" for="{trait}"><input type="checkbox" class="form-check-input" id="{trait}" name="{trait}"{state}>{trait}</label></div>'

                    response += '<br /><h6>Default name</h6><input type="text" class="form-control" value="{0}" name="default_name" required><br />' \
                        .format(selected_device['name']['name'],)

                    # response += '<h6>Challenge type</h6><div class="form-group"><select class="form-control" name="challenge_type" id="challenge_type" onchange="challengeChanged()" required>'
                    # for challenge in devices_json['challenges']:
                    #     challenge_name = 'None'
                    #     input_state = ' disabled'
                    #     if challenge == devices_json['challenge'][username_by_token][selected_device['id']]['challenge_type']:
                    #         input_state = ' selected'
                    #         if challenge == 'ackNeeded': challenge_name = 'Acknowledgement needed'
                    #         elif challenge == 'pinNeeded': challenge_name = 'PIN needed'
                    #     elif challenge != selected_device['type']:
                    #         input_state = ''
                    #         if challenge == 'ackNeeded': challenge_name = 'Acknowledgement needed'
                    #         elif challenge == 'pinNeeded': challenge_name = 'PIN needed'

                    #     response += f'<option{input_state}>{challenge_name}</option>'
                    
                    # response += '</select></div>'
                    # response_commands += '<div id="challenge_commands_div"><br /><h6>Challenge commands</h6>'

                    # for command in devices_json['commands']:
                    #     state = ' disabled'
                    #     if command in devices_json['challenge'][username_by_token][selected_device['id']]['commands']: state = ' checked'
                    #     elif command not in devices_json['challenge'][username_by_token][selected_device['id']]['commands']: state = ''

                    #     response_commands += f'<div class="form-check"><label class="form-check-label" for="{command}"><input type="checkbox" class="form-check-input" id="{command}" name="{command}"{state}>{command}</label></div>'
                    
                    # response_commands += '</div>'
                    # response_pin += '<div id="pin_div"><br /><h6>PIN</h6><div class="form-group"><input type="text" class="form-control" name="PIN"></div></div>'

                    # response += response_commands
                    # response += response_pin
                    # response = response.replace("--|-|--html_commands_div--|-|--", response_commands)
                    # response = response.replace("--|-|--html_pin_div--|-|--", response_pin)
                    
                    response += '</br><input type="hidden" value={0} name="device_id"><input type="hidden" name="challenge_type" value="{1}"><div class="btn-group"><button type="submit" class="btn btn-outline-primary" id="sbmt">Save</button></form><button class="btn btn-outline-danger" type="button" onclick="deleteConfirmation()">Delete</button></div></div><br /></body></html>' \
                        .format(request.args['id'], devices_json['challenge'][username_by_token][selected_device['id']]['challenge_type'])

    return response


@server.route('/devices/delete')
def delete_device():
    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens']:
            username_by_token = users['tokens']['users'][request.cookies['token']]

            with open('/home/pi/smart-home-fulfillment/config/devices.json', 'rt') as devices_file:
                devices_json = loads(devices_file.read())
                devices_file.close()

            for device in devices_json['devices'][username_by_token]:
                if device['id'] == request.args['id']:
                    del devices_json['devices'][username_by_token][devices_json['devices'][username_by_token].index(device)]
                    break
            del devices_json['device_states'][username_by_token][request.args['id']]
            del devices_json['challenge'][username_by_token][request.args['id']]
    
            with open('/home/pi/smart-home-fulfillment/config/devices.json', 'wt') as devices_file:
                devices_file.write(dumps(devices_json))
                devices_file.close()
            
    return redirect('/devices')


@server.route('/devices/new', methods=['GET'])
def new_device():
    response = redirect('/login?redirect_uri=/devices/new')
    if 'token' in request.cookies:
        if request.cookies['token'] in users['tokens']['tokens']:
            username_by_token = users['tokens']['users'][request.cookies['token']]

            with open('/home/pi/smart-home-fulfillment/config/devices.json', 'rt') as devices_file:
                devices_json = loads(devices_file.read())
                devices_file.close()

            html_file_r = open('/home/pi/smart-home-fulfillment/templates/new_device.html', 'rt')
            response = html_file_r.read()
            html_file_r.close()

            new_device_id = len(devices_json['devices'][username_by_token]) + 1
            response += f'<h6>Device ID</h6><input type="text" class="form-control" value="{new_device_id}" disabled><input type="hidden" name="device_id" id="device_id" value="{new_device_id}"><br /><h6>Type</h6><div class="form-group"><select class="form-control" id="device_type" name="device_type">'
            for device_type in devices_json['types']: response += f'<option>{device_type}</option>'
            response += '</select></div><h6>Traits</h6>'
            for trait in devices_json['traits']: response += f'<div class="form-check"><label class="form-check-label" for="{trait}"><input type="checkbox" class="form-check-input" id="{trait}" name="{trait}">{trait}</label></div>'
            response += f'<br /><h6>Default name</h6><input type="text" class="form-control" name="default_name" required><br /><button type="submit" class="btn btn-outline-success">Create device</button></form></div><br /></body></html>'

    return response


if __name__ == '__main__':
    server.run(
        host='192.168.1.9',
        port='5000',
        debug=True
    )
