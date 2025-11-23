# TensorFlow DLL 加载失败问题解决方案

## 问题原因

模型加载失败的根本原因是：**TensorFlow DLL 加载失败**。

### 为什么需要 TensorFlow？

虽然 `sentence-transformers` 主要使用 **PyTorch**，但它的依赖库 `transformers` 在某些情况下会尝试导入 TensorFlow。当 TensorFlow 的 DLL 文件缺失或损坏时，就会导致加载失败。

### 常见原因

1. **缺少 Visual C++ Redistributable**
   - TensorFlow 需要 Microsoft Visual C++ Redistributable
   - Windows 系统可能没有安装或版本不匹配

2. **TensorFlow 安装不完整**
   - TensorFlow 可能没有正确安装
   - 或者安装的版本与系统不兼容

3. **环境冲突**
   - 多个 Python 环境之间的依赖冲突
   - 虚拟环境配置问题

## 解决方案

### 方案一：安装 Visual C++ Redistributable（推荐）

1. **下载并安装 Visual C++ Redistributable**
   - 访问：https://aka.ms/vs/17/release/vc_redist.x64.exe
   - 或者搜索 "Microsoft Visual C++ Redistributable 2015-2022"
   - 下载并安装 x64 版本

2. **重启系统**（有时需要）

3. **重新测试**

### 方案二：重新安装 TensorFlow

```bash
# 卸载现有版本
pip uninstall tensorflow tensorflow-cpu

# 安装 CPU 版本（更稳定，不需要 GPU）
pip install tensorflow-cpu

# 或者安装完整版本
pip install tensorflow
```

### 方案三：使用 Conda 安装（最稳定）

```bash
# 使用 conda 安装，会自动处理依赖
conda install tensorflow

# 或者
conda install tensorflow-cpu
```

### 方案四：禁用 TensorFlow（如果不需要）

如果确定不需要 TensorFlow，可以设置环境变量：

```bash
# Windows PowerShell
$env:TRANSFORMERS_NO_TF="1"

# Windows CMD
set TRANSFORMERS_NO_TF=1

# 或者在代码中设置
import os
os.environ['TRANSFORMERS_NO_TF'] = '1'
```

### 方案五：使用替代方案

如果 TensorFlow 问题无法解决，可以考虑：

1. **使用 OpenAI Embeddings API**（需要 API Key）
2. **使用其他向量化库**（如 `gensim`）
3. **使用在线向量化服务**

## 验证修复

修复后，可以运行以下命令测试：

```python
# 测试脚本
python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2'); print('模型加载成功！')"
```

## 临时解决方案

如果暂时无法修复 TensorFlow 问题：

1. **论文已保存到数据库**：爬虫已经成功保存了 7029 篇论文
2. **手动索引**：修复环境后，使用索引 API 将论文添加到向量数据库
3. **API 接口**：`POST /api/matching/index-papers`

## 推荐步骤

1. **首先尝试方案一**（安装 Visual C++ Redistributable）- 这是最常见的原因
2. **如果不行，尝试方案二**（重新安装 TensorFlow）
3. **如果还不行，尝试方案三**（使用 Conda）
4. **最后考虑方案四或五**（禁用或替代方案）

## 检查当前环境

运行以下命令检查环境：

```bash
# 检查 Python 版本
python --version

# 检查已安装的包
pip list | findstr tensorflow
pip list | findstr sentence-transformers
pip list | findstr transformers

# 检查 Visual C++ Redistributable
# 在"程序和功能"中查看是否安装了 Microsoft Visual C++ Redistributable
```

