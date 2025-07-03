from PIL import Image
import os

# 输入输出路径
input_dir = "C:/Users/28926/Desktop/文档/py/照片"
output_dir = "MusicPlayer/resources/icons"

# 要转换的文件列表
files_to_convert = [
    "app.png",
    "云服务.png", 
    "循环.png",
    "播放.png",
    "暂停.png",
    "顺序.png"
]

# 创建输出目录（如果不存在）
os.makedirs(output_dir, exist_ok=True)

# 转换函数
def convert_to_ico(input_path, output_path, size=(256,256)):
    img = Image.open(input_path)
    img.save(output_path, sizes=[(size[0], size[1])])

# 批量转换
for filename in files_to_convert:
    input_path = os.path.join(input_dir, filename)
    output_filename = os.path.splitext(filename)[0] + ".ico"
    output_path = os.path.join(output_dir, output_filename)
    
    try:
        convert_to_ico(input_path, output_path)
        print(f"成功转换: {filename} -> {output_filename}")
    except Exception as e:
        print(f"转换失败 {filename}: {str(e)}")

print("图标转换完成！")