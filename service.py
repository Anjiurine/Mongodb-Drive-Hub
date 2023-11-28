from utils import mongo_utils, user_io
import json
import os
import traceback
import logging
from concurrent.futures import ThreadPoolExecutor
import sys
import atexit
import signal
from flask import Flask, send_file, after_this_request, render_template
from flask import jsonify
from flask import request

client_list = []

def remove_temp_files():
    save_path = "./cache/"
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    for file_name in os.listdir(save_path):
        file_path = os.path.join(save_path, file_name)
        try:
            os.unlink(file_path)
        except Exception as e:
            logging.warning(f"Error removing temporary file: {str(e)}")

def run_cli_mode():
    try:
        if os.path.exists('./uri_list.json') == False:
            print("uri_list.json not found")
            sys.exit()
        with open("uri_list.json", "r") as f:
            uri_list = json.load(f)["uri_list"]
        client_list = mongo_utils.connect_mongo_cluster(uri_list)
        user_io.print_welcome()
        while True:
            user_input = input("Please enter the command：")
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(user_io.parse_input, user_input, client_list)]
                for future in futures:
                    future.result()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
        remove_temp_files()
        sys.exit(0)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}\n{traceback.format_exc()}")

app = Flask(__name__, instance_relative_config=True, template_folder='templates')

@app.route('/')
def js_rendered_files():
    return render_template('index.html')

@app.route('/status')
def js_rendered_status():
    return render_template('status.html')


@app.route('/download/<file_sha256>')
def download_file(file_sha256):
    save_path = "./cache/"
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    try:
        file_path = mongo_utils.download_file(client_list, file_sha256, save_path)
        if file_path:
            @after_this_request
            def remove_temp_file(response):
                return response
            return send_file(file_path, as_attachment=True)
        else:
            return "File does not exist", 404
    except Exception as e:
        return str(e), 500

@app.route('/api/files')
def api_list_files():
    search_term = request.args.get('search', '')  # 获取搜索条件，默认为空字符串
    file_list = mongo_utils.list_files(client_list, cli_output=False)

    if search_term:
        # 如果有搜索条件，筛选出符合条件的文件
        file_list = [file for file in file_list if search_term in file['name']]

    return jsonify(file_list)

@app.route('/api/status')
def api_get_status():
    status_result = mongo_utils.dbstatus(client_list, cli_output=False)
    return jsonify(status_result)

def signal_handler(sig, frame):
    print("\nProgram terminated by user.")
    remove_temp_files()
    sys.exit(0)

def run_server_mode():
    try:
        global client_list
        if os.path.exists('./uri_list.json') == False:
            print("uri_list.json not found")
            sys.exit()
        with open("uri_list.json", "r") as f:
            uri_list = json.load(f)["uri_list"]
        client_list = mongo_utils.connect_mongo_cluster(uri_list)
        atexit.register(remove_temp_files)
        signal.signal(signal.SIGINT, signal_handler)
        app.run(debug=False, host='0.0.0.0', port=19198, use_reloader=False)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}\n{traceback.format_exc()}")