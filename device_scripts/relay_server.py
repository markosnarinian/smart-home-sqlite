from flask import Flask
from flask import request
from flask import jsonify
from flask import abort
from multiprocessing import Process
from os import system
from json import loads

server = Flask(__name__)


@server.route('/command', methods=['POST'])
def command():
    if 'command' in loads(request.json):
        try:
            process = Process(target=system, args=(loads(request.json)['command'],))
            process.run()
        except:
            return jsonify({'status': 'ERROR', 'errorCode': 'unknownError'}), 500
        else:
            return jsonify({'status': 'SUCCESS'}), 200
    elif 'command' not in loads(request.json):
        return jsonify({'status': 'ERROR', 'errorCode': 'commandNotSpecified'}), 400


if __name__ == '__main__':
    server.run(host='192.168.1.2', port=5000, debug=False)
