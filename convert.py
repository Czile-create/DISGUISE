import zlib
from PIL import Image
import numpy as np
import math
import argparse
import base64
import rsa
from tqdm import tqdm
from skimage.io import imread, imsave

def myHash(content):
    answer = 0
    for i in content:
        answer = answer ^ i
    return answer

def createRSAKey():
    pub, pri = rsa.newkeys(2048)                                # 生成秘钥对实例对象：2048是秘钥的长度
    with open("rsa", "wb") as f:                                # 写入密钥
        f.write(pri.save_pkcs1())
    with open("rsa.pub", "wb") as f:
        f.write(pub.save_pkcs1())


def encode(INPUT, OUTPUT, rate, lock, password, guise):
    if lock and password == 'none':
        createRSAKey()                                          # 若需要加密但不指定公钥，则生成一组密钥
        password = 'rsa.pub'                                    # 重设默认值
    
    with open(INPUT, 'rb') as f:
        content = bytearray(f.read())                                       # 读取文件
        if lock:
            val = []
            pub = rsa.PublicKey.load_pkcs1(open(password, 'rb').read())     # 读取公钥
            for i in range(0, len(content), 245):
                val.append(rsa.encrypt(content[i:min(i+245, len(content))], pub))              # 加密
            content = b''.join(val)                                         # 获取加密后内容

        content = bytearray(zlib.compress(content, level=rate))             # 将文件进行压缩
        content.append(0)                                                   # 分隔文件和信息

        sizeW = int(math.sqrt(len(content)/3) + 1)                          # 计算图片的宽高
        sizeH = int(len(content)/sizeW/3 + 1)
        extendLength = int(sizeH * sizeW * 3 - len(content))                # 计算应该补充的像素点数量
        content.extend([0 for i in range(extendLength - 3)])                # 补充像素点
        
        content.append(myHash(content))                                     # 验证码，验证文件是否损坏
        content.append(extendLength//256%256)                               # 最后一个像素记录补充的像素点数量
        content.append(extendLength%256)
        content = np.array(bytearray(content)).reshape((sizeH, sizeW, 3))   # 重设内容矩阵的大小
        content = content.astype(np.uint16)

        if guise != 'none':                                                 # 伪装图片
            im = np.array(Image.open(guise).convert('RGB').resize((sizeW, sizeH)), dtype=np.uint16)
            content = im * 256 + content
        else:
            content *= 256
        imsave(OUTPUT, content, plugin='tifffile')                              # 保存图片

def decode(INPUT, OUTPUT, password, guise):
    content = imread(INPUT, plugin='tifffile') % 256
    if sum(sum(sum(content))) == 0:                                             # 判断是否为伪装
        content = imread(INPUT, plugin='tifffile') / 256
    content = bytearray(content.astype(np.uint8))                               # 读入图片文件
    if content[-3] != myHash(content[0:-3]):
        raise("图片或已经被更改，请检查是否使用压缩后格式")                        # 检测图片是否被更改
    extendLength = int(content[-2])*256 + int(content[-1])                      # 补充像素点的数量
    content = content[0:-extendLength]
    content = zlib.decompress(content)                                          # 解压文件内容
    if (password != 'none'):
        val = []
        pri = rsa.PrivateKey.load_pkcs1(open(password, 'rb').read())            # 读取公钥
        for i in tqdm(range(0, len(content), 256)):
            val.append(rsa.decrypt(content[i:min(i+256, len(content))], pri))   # 加密
        content = b''.join(val)                                                 # 获取加密后内容
    with open(OUTPUT, 'wb') as f:
        f.write(content)                                                        # 写入文件

parser = argparse.ArgumentParser(prog='convert.py', description="本程序可对文件进行RSA加密/解密操作，并压缩文件大小，将其伪装成图片")
parser.add_argument('--INPUT', '-i', nargs=1, help='要转化的文件名', required=True)
parser.add_argument('--OUTPUT', '-o', nargs=1, help='转化后的文件名，如果是文件转化为图片，你应该选择使用.tif格式', required=True)
parser.add_argument('--rate', '-r', nargs=1, help='压缩效果，取值0-9', default=['9'], required=False)
parser.add_argument('--encode', '-e', help='使用程序将文件写成图片格式', required=False, action='store_true')
parser.add_argument('--decode', '-d', help='将图片格式的程序还原成文件', required=False, action='store_true')
parser.add_argument('--lock', '-l', help='转化格式的时候使用RSA加密',required=False, action='store_true')
parser.add_argument('--password', '-p', nargs=1, help='使用指定密码加密或解密', required=False, default=['none'])
parser.add_argument('--guise', '-g', nargs=1, help='使用指定的图片进行伪装', required=False, default=['none'])
parser.add_argument('--version', '-v', action='version', version='1.0.1')

args = parser.parse_args()


if args.encode:
    encode(args.INPUT[0], args.OUTPUT[0], int(args.rate[0]), args.lock, args.password[0], args.guise[0])
else:
    decode(args.INPUT[0], args.OUTPUT[0], args.password[0], args.guise[0])
