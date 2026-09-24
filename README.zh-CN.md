# Checkpoint Courier：训练断点备份与恢复

[English](README.md) · [一键 Colab 示例](https://colab.research.google.com/github/B-jack7/checkpoint-courier/blob/main/notebooks/quickstart.ipynb)

把**已经写完的断点文件**复制到指定目录，计算 SHA-256 并读回校验。恢复时拒绝覆盖现有文件。仅依赖 Python 3.10+ 标准库，不需要 GPU，也不加载模型对象。

```bash
git clone https://github.com/B-jack7/checkpoint-courier.git
cd checkpoint-courier
python -m pip install .
python examples/demo.py
```

示例使用合成字节，演示备份、删除原文件、恢复，不是真实模型训练。

```python
from checkpoint_courier import Store

# 在 Colab 中先自行挂载 Drive，再使用这个路径。
store = Store("/content/drive/MyDrive/training-backups")
saved = store.save("/content/epoch-15.pt", tag="epoch-15")
print(saved["id"])
store.verify(saved["id"])
store.restore(saved["id"], "/content/recovered.pt")
```

`save` 要在 `torch.save` 等操作完成后调用。每次保存生成新版本。训练恢复所需的模型、优化器、轮次等状态，需要由训练脚本先写入同一个文件。

注意：这是早期版本，已测试本地文件流程，尚未验证真实 Colab/Drive 持久化。挂载目录写入成功不等于云端同步完成；重连后应再次校验。它不能防止运行时断开，也不会自动定时备份。不要把 `/content` 临时目录当成持久存储。详细边界见英文 README。

测试：`python -m unittest discover -s tests -v`。欢迎提交能复现的问题和实际使用反馈。
