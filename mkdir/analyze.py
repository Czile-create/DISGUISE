from skimage.io import imread
import numpy as np
import matplotlib.pyplot as plt

def analyze(INPUT):
    content = imread(INPUT)
    if content.dtype == 'uint16':                                               # 提取有用信息
        content &= 255
    elif content.shape[2] == 4:
        content %= 16
        contents = np.split(content, 2, axis=2)
        content = contents[0] * 16 + contents[1]

    content = bytearray(content.astype(np.uint8))                               # 读入图片文件

    x = range(256)
    y = np.zeros(256)
    for i in range(256):
        y[i] = content.count(i)
    plt.bar(x, y)
    plt.xlabel('Data')
    plt.ylabel('Number')
    plt.show()


INPUT = '../test/output.png'
analyze(INPUT)
