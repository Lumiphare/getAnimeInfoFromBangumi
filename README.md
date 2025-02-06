# 简介
 一个用于抓取 bangumi 排行榜网址如 https://age.wpcoder.cn/anime/browser/airtime/2024?sort=collects的 动画海报和主要角色及其海报的 Python 应用程序。
 可以具体排行榜和抓取动画数量
## 环境搭建指南

### 前提条件

确保你已经安装了 Python 3.x 和 pip（Python 包管理工具）。你可以通过以下命令检查是否已安装：

```bash
python --version
pip --version
```
### 创建虚拟环境

建议在开始之前创建一个新的虚拟环境来避免库版本冲突。

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# 在 Windows 上：
.\venv\Scripts\activate
# 在 macOS/Linux 上：
source venv/bin/activate
```
### 安装依赖

激活虚拟环境后，请使用以下命令安装所有必要的依赖项：

```bash
pip install -r requirements.txt
```

## 运行项目

执行以下命令以启动应用程序：

```bash
python getAnimeInfo.py
```