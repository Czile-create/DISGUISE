import zlib, math, argparse, rsa, secrets
from PIL import Image
import numpy as np
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

def fixPhoto(im):                                                 # 修复因改变冗余信息而降低质量的图像
    im1 = im & 240
    rand = np.random.random(im.shape) * 16
    im2 = im & 15
    im2[im2 > rand] = 16
    im2[im2 != 16] = 0
    im2[im1 == 240] = 0
    im2 += im1
    return im2

def encode(INPUT, OUTPUT, rate, lock, password, guise, bit16):
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

        n = 2                                                               # 记录每个像素点可以记录的信息数
        if guise != 'none' and bit16 or guise == 'none':                    # 若不伪装或使用16位伪装格式则每像素点可记录3字节信息
            n = 3                                                           # 否则每像素点只能记录两字节信息

        sizeW = int(math.sqrt(len(content)/n) + 1)                          # 计算图片的宽高
        sizeH = int(len(content)/sizeW/n + 1)
        extendLength = int(sizeH * sizeW * n - len(content))                # 计算应该补充的像素点数量
        content.extend(secrets.token_bytes(extendLength - 3))               # 补充像素点
        
        content.append(myHash(content))                                     # 验证码，验证文件是否损坏
        content.append(extendLength//256%256)                               # 最后一个像素记录补充的像素点数量
        content.append(extendLength%256)

        if n == 3:
            content = np.array(bytearray(content)).reshape((sizeH, sizeW, 3))       # 重设内容矩阵的大小
        else:
            content = np.array(bytearray(content)).reshape((sizeH, sizeW, 2))
            content = np.concatenate([content >> 4, content & 15], axis=2)

        if guise != 'none' and bit16:                                               # 使用16位深度伪装图片
            im = np.array(Image.open(guise).convert('RGB').resize((sizeW, sizeH)), dtype=np.uint16)
            content = im * 256 + content.astype(np.uint16)
            imsave(OUTPUT, content, plugin='tifffile')                              
        elif guise != 'none':                                                       # 使用8位深度伪装图片
            im = np.array(Image.open(guise).convert('RGBA').resize((sizeW, sizeH)))
            content = fixPhoto(im) + content
            Image.fromarray(content).save(OUTPUT)
        else:                                                                       # 不伪装图片
            Image.fromarray(content).save(OUTPUT)

def decode(INPUT, OUTPUT, password):
    content = imread(INPUT)
    if content.dtype == 'uint16':                                               # 提取有用信息
        content &= 255
    elif content.shape[2] == 4:
        content %= 16
        contents = np.split(content, 2, axis=2)
        content = contents[0] * 16 + contents[1]

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
parser.add_argument('--OUTPUT', '-o', nargs=1, help='转化后的文件名，如果是文件转化为图片，你应该选择使用.tif或.png格式', required=True)
parser.add_argument('--rate', '-r', nargs=1, help='压缩效果，取值0-9', default=['9'], required=False)
parser.add_argument('--encode', '-e', help='使用程序将文件写成图片格式', required=False, action='store_true')
parser.add_argument('--decode', '-d', help='将图片格式的程序还原成文件', required=False, action='store_true')
parser.add_argument('--lock', '-l', help='转化格式的时候使用RSA加密',required=False, action='store_true')
parser.add_argument('--password', '-p', nargs=1, help='使用指定密码加密或解密', required=False, default=['none'])
parser.add_argument('--guise', '-g', nargs=1, help='使用指定的图片进行伪装', required=False, default=['none'])
parser.add_argument('--version', '-v', action='version', version='1.0.2')
parser.add_argument('--bit16', '-b', help='使用16位三通道图像伪装信息，使用该方法的时候应该选择.tif格式输出', action='store_true')

args = parser.parse_args()


if args.encode:
    encode(args.INPUT[0], args.OUTPUT[0], int(args.rate[0]), args.lock, args.password[0], args.guise[0], args.bit16)
else:
    decode(args.INPUT[0], args.OUTPUT[0], args.password[0])
