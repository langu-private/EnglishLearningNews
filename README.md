# English Learning News Podcast Generator

这是一个为你量身定制的自动化英语学习工具。它会每天抓取全球最新新闻，然后利用大模型（如 ChatGPT / DeepSeek）将其翻译成仅包含 **Basic English 850 核心词汇**的英语（专有名词除外），最后生成原汁原味的美音音频播客，以及中英双语的博客阅读版。

## 目录结构
- `basic_english_850.txt`: 已经抓取好的 850 个基础英语单词列表，这是大模型的词汇边界。
- `generate_podcast.py`: 核心自动化脚本（抓取新闻、调用大模型、生成音频）。
- `run_morning.sh`: 早报执行脚本（快捷入口）。
- `run_evening.sh`: 晚报执行脚本（快捷入口）。
- `editions/`: 每天生成的内容都会存放在这个目录下，按日期分类。
- `venv/`: 隔离的 Python 运行环境。

## 使用准备
1. 打开 `run_morning.sh` 和 `run_evening.sh` 文件。
2. 找到 `API_KEY="your-api-key-here"`，将其替换为你的真实大模型 API Key（可以使用 OpenAI, DeepSeek, Moonshot 等兼容 OpenAI SDK 的模型服务）。
3. 如果使用的是非 OpenAI 官方接口，请修改 `BASE_URL`（例如 DeepSeek: `https://api.deepseek.com/v1`）和 `MODEL` 名称。

## 如何运行
你只需要在终端双击运行或者输入以下命令：

**生成早报**：
```bash
./run_morning.sh
```

**生成晚报**：
```bash
./run_evening.sh
```

## 输出物
运行完成后，请去 `editions/YYYY-MM-DD_Morning` (或 Evening) 目录下查看：
1. **Podcast.mp3**: 纯正美式发音的纯英文播客，专供通勤路上泛听。
2. **Blog.md**: 中英双语对照的博客文章，专供精读和词汇学习。

## 自动化设置（可选）
如果你希望 Mac 每天自动帮你生成早报和晚报，你可以把这两个脚本加入到 Mac 的 `crontab` 定时任务中：
```bash
crontab -e
```
添加以下内容（比如早上 7点 和 晚上 6点 自动运行）：
```
0 7 * * * /Users/langu/Documents/4-能力提升/EnglishLearningNews/run_morning.sh >> /tmp/morning_news.log 2>&1
0 18 * * * /Users/langu/Documents/4-能力提升/EnglishLearningNews/run_evening.sh >> /tmp/evening_news.log 2>&1
```
