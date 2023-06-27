import csv

import cv2
import numpy as np
import onnxruntime as ort

model_path = 'static/e10_resnet50.onnx'
ort_session = ort.InferenceSession(model_path, providers=ort.get_available_providers())


def getRubbish(img):
    predictions = []
    img = cv2.imdecode(np.fromfile(img, dtype=np.uint8), 1)
    img = cv2.resize(img, (224, 224))
    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, 0)
    img = img.astype(np.float32)
    img /= 255
    ort_inputs = {ort_session.get_inputs()[0].name: img}
    ort_outputs = ort_session.run(None, ort_inputs)

    # 获取预测结果
    predictions.extend(ort_outputs[0])

    # 将预测结果转换为numpy数组
    predictions_np = np.array(predictions)

    # 对预测结果应用softmax
    predictions_softmax = softmax(predictions_np)

    # 获取预测标签
    predicted_labels = np.argmax(predictions_softmax, axis=1)
    return predicted_labels


def softmax(x):
    exp_x = np.exp(x)
    softmax_x = exp_x / np.sum(exp_x, axis=1, keepdims=True)
    return softmax_x


def validate_login(username, password):
    with open('static/user_pwd.csv', 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[0] == username and row[1] == password:
                return True
    return False


def register_user(username, password):
    with open('static/user_pwd.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, password])


def get_user_info(username):
    user_data = {}
    with open('static/user_pwd.csv', mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['username'] == username:
                user_data = row
                break
    return user_data


def update_password(username, old_password, new_password):
    success = False
    users = []
    with open('static/user_pwd.csv', mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['username'] == username:
                if row['password'] == old_password:
                    row['password'] = new_password
                    success = True
            users.append(row)

    if success:
        with open('static/user_pwd.csv', mode='w', newline='') as csvfile:
            fieldnames = ['username', 'password']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for user in users:
                writer.writerow(user)

    return success
