import asyncio
import json
import os
import ast
from datetime import datetime
from math import ceil
import pandas as pd
from flask import Flask, request, jsonify
from flask import json

from views.rubbish import validate_login, register_user, getRubbish, update_password, get_user_info

app = Flask(__name__)
if __name__ == '__main__':
    app.run()

app = Flask(__name__)

# 全局字典，存储用户的分类进度
progress = {}


# 登录功能
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    if validate_login(username, password):
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'})


# 注册功能
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if validate_login(username, password):
        return jsonify({'success': False, 'message': '用户名已存在'})
    else:
        register_user(username, password)
        return jsonify({'success': True, 'message': '注册成功'})


# 获取用户个人信息
@app.route('/user_info', methods=['GET'])
def user_info():
    username = request.args.get('username')

    user = get_user_info(username)
    if user:
        return jsonify({'success': True, 'user': user})
    else:
        return jsonify({'success': False, 'message': '用户不存在'})


# 修改密码
@app.route('/change_password', methods=['POST'])
def change_password():
    username = request.form.get('username')
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')

    result = update_password(username, old_password, new_password)
    if result:
        return jsonify({'success': True, 'message': '密码修改成功'})
    else:
        return jsonify({'success': False, 'message': '原密码错误'})


# 垃圾批量异步处理
@app.route('/rubbish', methods=['POST'])
def rubbish():
    df = pd.read_csv('static/label.csv', encoding='gbk', header=None, names=["name", "class"])
    labels = df.iloc[:, 0]
    files = request.files.getlist('file')  # 获取多个文件

    async def process_file(file, username):
        rest = await asyncio.get_event_loop().run_in_executor(None, getRubbish, file)  # 异步执行分类任务
        rest = labels[rest].values[0]
        bgroup, sgroup = rest.split('/')
        formatted_rest = {"Bgroup": bgroup, "Sgroup": sgroup}

        # 更新进度
        if username in progress:
            progress[username] += 1
        else:
            progress[username] = 1

        return formatted_rest

    async def process_files(fileIO, username):
        tasks = []
        for file in fileIO:
            task = asyncio.create_task(process_file(file, username))
            tasks.append(task)
        return await asyncio.gather(*tasks)

    username = request.form.get('username')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(process_files(files, username))

    # 将垃圾分类记录存储在history.csv文件中
    image_paths = [os.path.normpath(os.path.join('C:/Users/27877/Desktop/validate', file.filename)) for file in files]

    history_file = 'static/history.csv'

    # 检查文件是否存在
    if os.path.exists(history_file):
        # 检查文件是否为空
        if os.stat(history_file).st_size > 0:
            history = pd.read_csv(history_file, encoding='gbk')
        else:
            # 如果文件为空，创建一个空的DataFrame
            history = pd.DataFrame(columns=['username', 'result', 'image_path', 'process_time'])
    else:
        # 如果文件不存在，创建一个空的DataFrame
        history = pd.DataFrame(columns=['username', 'result', 'image_path', 'process_time'])

    # 获取当前时间
    current_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    new_records = [
        {'username': username, 'result': json.dumps(result, ensure_ascii=False), 'image_path': path,
         'process_time': current_time} for
        result, path in
        zip(results, image_paths)]
    new_records_df = pd.DataFrame(new_records)
    history = pd.concat([history, new_records_df], ignore_index=True)
    history.to_csv('static/history.csv', index=False, encoding='gbk')

    return jsonify(results)


# 添加进度查询接口
@app.route('/progress', methods=['GET'])
def get_progress():
    username = request.args.get('username')
    if username and username in progress:
        return jsonify({"progress": progress[username]})
    else:
        return jsonify({"error": "User not found"}), 404


# 查询用户的垃圾分类记录
@app.route('/history', methods=['GET'])
def get_history():
    username = request.args.get('username')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    date = request.args.get('date', None)
    bgroup = request.args.get('bgroup', None)

    history = pd.read_csv('static/history.csv', encoding='gbk')
    user_history = history[history['username'] == username]

    # 根据日期筛选
    if date:
        user_history = user_history[user_history['process_time'].apply(
            lambda x: datetime.strptime(x.split(' ')[0], '%Y/%m/%d').date() == datetime.strptime(date,
                                                                                                 '%Y-%m-%d').date())]

    # 根据 result 中的 Bgroup 筛选
    if bgroup:
        user_history = user_history[
            user_history['result'].apply(lambda x: bgroup in ast.literal_eval(x).get('Bgroup', ''))]

    total_records = len(user_history)
    total_pages = ceil(total_records / per_page)

    start = (page - 1) * per_page
    end = start + per_page
    user_history = user_history.iloc[start:end]

    user_records = []
    for _, row in user_history.iterrows():
        record = {
            'image_path': row['image_path'],
            'result': ast.literal_eval(row['result']),
            'process_time': row['process_time']
        }
        user_records.append(record)

    return jsonify({
        'success': True,
        'records': user_records,
        'total_records': total_records,
        'total_pages': total_pages,
        'current_page': page,
        'per_page': per_page
    })
