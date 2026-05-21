# Discord AI Character Bot on Docker

Discordで `@CE-bot` のようにBotをメンションすると、Ubuntu上のDockerコンテナで動いているローカルLLMが返答する構成です。

OpenAI APIなどの外部AI APIを使わず、Ubuntu上のDocker Composeで以下を動かします。

- Discord Bot: `discord.py`
- ローカルLLMサーバー: `Ollama`
- 実行基盤: Docker Compose

## 構成

```text
Discord
  ↓ @CE-bot にメンション
bot container
  ↓ http://ollama:11434/api/chat
ollama container
  ↓
local LLM model
```

OllamaのAPIポートはDocker内部ネットワークだけで使い、ホストや外部には公開しません。

## 前提条件

- Ubuntu環境がある
- Docker / Docker Composeが使える
- Discordアカウントがある
- Botを追加したいDiscordサーバーで「サーバー管理」権限を持っている

## Discord Botを作成する

### 1. Applicationを作成する

1. [Discord Developer Portal](https://discord.com/developers/applications) を開く
2. 右上の **New Application** を押す
3. Application名を入力する
   - 例: `CE-bot`
4. **Create** を押す

Applicationは、Botユーザーやスラッシュコマンドなどの親になる単位です。

### 2. Botユーザーを作成する

1. 左メニューの **Bot** を開く
2. Botが存在しない場合は **Add Bot** を押す
3. Bot名やアイコンを設定する

ここで作られるBotユーザーが、Discordサーバー上に表示されるBot本体です。

### 3. Bot Tokenを取得する

1. 左メニューの **Bot** を開く
2. **Token** セクションを探す
3. **Reset Token** または **View Token** を押す
4. 表示されたTokenを控える

Bot Tokenはパスワードと同じ扱いです。

- GitHubに公開しない
- READMEに貼らない
- スクリーンショットに写さない
- 漏れた場合はDeveloper PortalでTokenを再発行する

このリポジトリでは、Tokenは `.env` に保存します。

### 4. Privileged Gateway Intentsを設定する

`@CE-bot` のように、Botがメンションされた時だけ反応する構成なら、最初は以下で問題ありません。

```text
Presence Intent: OFF
Server Members Intent: OFF
Message Content Intent: OFF
```

通常メッセージを常に読み取るBotや、`!ai` のようなprefixコマンドを使うBotにする場合は、Developer Portal側で **Message Content Intent** をONにし、コード側でも有効化する必要があります。

今回はメンションされた時だけ反応するため、Message Content Intentなしで開始します。

### 5. Installation設定を行う

1. 左メニューの **Installation** を開く
2. **Installation Contexts** で **Guild Install** を有効にする
3. **Install Link** は **Discord Provided Link** を選ぶ
4. **Default Install Settings** を設定する

Guild InstallのScopesは以下を設定します。

```text
bot
applications.commands
```

Bot Permissionsは、最低限以下を付与します。

```text
View Channels
Send Messages
Read Message History
```

日本語UIの場合は、だいたい以下の表記です。

```text
チャンネルを見る
メッセージを送信
メッセージ履歴を読む
```

最初から `Administrator / 管理者` は付けない方が安全です。

### 6. Botをサーバーに追加する

1. InstallationページのInstall Linkを開く
2. 追加先のDiscordサーバーを選ぶ
3. 権限一覧を確認する
4. **Authorize** を押す
5. CAPTCHAが出た場合は完了する

追加後、サーバーのメンバー一覧にBotが表示されるか確認します。

`@CE-bot` と入力して候補に出てくれば、Botユーザーとして追加されています。

## プロジェクト構成

```text
discord-ai-bot/
  compose.yaml
  .env
  .env.example
  .gitignore
  bot/
    Dockerfile
    requirements.txt
    bot.py
```

## 実装コード

### `.env`

`.env` はGitHubに公開しません。

```env
DISCORD_TOKEN=ここにDiscord Bot Tokenを入れる
OLLAMA_MODEL=llama3.2:1b
OLLAMA_URL=http://ollama:11434/api/chat
```

### `.env.example`

GitHubには `.env` ではなく、例として `.env.example` を置きます。

```env
DISCORD_TOKEN=replace_with_your_discord_bot_token
OLLAMA_MODEL=llama3.2:1b
OLLAMA_URL=http://ollama:11434/api/chat
```

### `.gitignore`

```gitignore
.env
__pycache__/
*.pyc
.venv/
```

### `compose.yaml`

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
    expose:
      - "11434"
    networks:
      - ai-net
    restart: unless-stopped

  bot:
    build:
      context: ./bot
    env_file:
      - .env
    environment:
      OLLAMA_URL: ${OLLAMA_URL:-http://ollama:11434/api/chat}
      OLLAMA_MODEL: ${OLLAMA_MODEL:-llama3.2:1b}
    depends_on:
      - ollama
    networks:
      - ai-net
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true

volumes:
  ollama-data:

networks:
  ai-net:
    driver: bridge
```

### `bot/Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

USER appuser

CMD ["python", "bot.py"]
```

### `bot/requirements.txt`

```text
discord.py==2.4.0
aiohttp==3.9.5
```

### `bot/bot.py`

```python
import os

import aiohttp
import discord


DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

CHARACTER_PROMPT = """
あなたはDiscord上のAIキャラクターです。
日本語で1〜3文だけ返してください。
雑談は自然に、長文説明は避けてください。
攻撃的な表現、危険な助言、過度な煽りは避けてください。
"""

intents = discord.Intents.default()
intents.messages = True

client = discord.Client(intents=intents)


async def ask_ollama(text: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "keep_alive": "30m",
        "messages": [
            {"role": "system", "content": CHARACTER_PROMPT},
            {"role": "user", "content": text},
        ],
        "options": {
            "num_predict": 256,
            "num_ctx": 2048,
        },
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(OLLAMA_URL, json=payload, timeout=180) as response:
            response.raise_for_status()
            data = await response.json()
            return data["message"]["content"].strip()


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if client.user not in message.mentions:
        return

    text = message.content
    text = text.replace(f"<@{client.user.id}>", "")
    text = text.replace(f"<@!{client.user.id}>", "")
    text = text.strip() or "呼ばれたので、軽く挨拶してください。"

    async with message.channel.typing():
        reply = await ask_ollama(text)

    await message.reply(
        reply[:1900],
        mention_author=False,
        allowed_mentions=discord.AllowedMentions.none(),
    )


client.run(DISCORD_TOKEN)
```

## セットアップ

### 1. ディレクトリを作成する

```bash
mkdir -p discord-ai-bot/bot
cd discord-ai-bot
```

### 2. 各ファイルを配置する

以下を作成します。

```text
compose.yaml
.env
.env.example
.gitignore
bot/Dockerfile
bot/requirements.txt
bot/bot.py
```

### 3. `.env` にBot Tokenを設定する

```bash
nano .env
```

```env
DISCORD_TOKEN=ここにDiscord Bot Tokenを入れる
OLLAMA_MODEL=llama3.2:1b
OLLAMA_URL=http://ollama:11434/api/chat
```

### 4. Dockerイメージをビルドする

```bash
docker compose build
```

### 5. コンテナを起動する

```bash
docker compose up -d
```

### 6. Ollamaモデルをダウンロードする

```bash
docker compose exec ollama ollama pull llama3.2:1b
```

日本語の返答品質を上げたい場合は、以下のようなモデルも試せます。

```bash
docker compose exec ollama ollama pull qwen3:4b
```

その場合は `.env` を変更します。

```env
OLLAMA_MODEL=qwen3:4b
```

反映します。

```bash
docker compose up -d
```

## 動作確認

Botが起動しているかログを確認します。

```bash
docker compose logs -f bot
```

以下のようなログが出ればDiscordに接続できています。

```text
Logged in as CE-bot
```

DiscordのチャンネルでBotにメンションします。

```text
@CE-bot こんにちは
```

返答が返ってくれば成功です。

## 停止と再起動

一時停止します。

```bash
docker compose stop
```

再開します。

```bash
docker compose start
```

コンテナを停止して削除します。

```bash
docker compose down
```

Ollamaのモデルデータも削除する場合だけ、以下を使います。

```bash
docker compose down -v
```

`-v` を付けると、ダウンロード済みモデルも削除されます。

## 速度が遅い場合

ローカルLLMは、CPUだけで動かすと遅くなることがあります。

まずは軽いモデルを使います。

```env
OLLAMA_MODEL=llama3.2:1b
```

返答を短くするため、`bot.py` では以下を設定しています。

```python
"options": {
    "num_predict": 256,
    "num_ctx": 2048,
}
```

さらに短くしたい場合は、`num_predict` を `128` に下げます。

```python
"num_predict": 128
```

NVIDIA GPUを使う場合は、Ubuntuホスト側にNVIDIA Container Toolkitを導入し、`compose.yaml` の `ollama` にGPU設定を追加します。

```yaml
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
    expose:
      - "11434"
    networks:
      - ai-net
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## セキュリティと脆弱性対応

この構成では、以下を意識しています。

- Bot Tokenは `.env` に入れ、GitHubに公開しない
- `.env` は `.gitignore` に追加する
- Ollamaのポート `11434` をホストに公開しない
- Botコンテナは非rootユーザーで実行する
- Botコンテナに `cap_drop: ALL` を設定する
- Botコンテナに `no-new-privileges:true` を設定する
- Botコンテナのファイルシステムを `read_only: true` にする
- DockerイメージとPythonパッケージを定期的に更新する

更新例です。

```bash
docker compose pull
docker compose build --pull
docker compose up -d
```

Docker Scoutが使える場合は、CVEを確認できます。

```bash
docker scout cves ollama/ollama:latest
docker scout cves discord-ai-bot-bot
```

Trivyを使う場合は、以下のようにスキャンできます。

```bash
trivy image ollama/ollama:latest
trivy image discord-ai-bot-bot
```

## GitHubにpushする

`.env` がGit管理対象に入っていないことを確認します。

```bash
git status
```

初回コミット例です。

```bash
git init
git add .
git commit -m "Add Discord AI bot with Docker"
```

GitHubでpersonal repositoryを作成したあと、表示されたURLを使ってpushします。

```bash
git remote add origin git@github.com:your-user/discord-ai-bot.git
git branch -M main
git push -u origin main
```

HTTPSを使う場合は、GitHubの画面に表示されたHTTPS URLを設定します。

```bash
git remote add origin https://github.com/your-user/discord-ai-bot.git
git branch -M main
git push -u origin main
```

## トラブルシューティング

### `@CE-bot` の候補にBotが出ない

- Botがサーバーに追加されているか確認する
- InstallationのScopesに `bot` が入っているか確認する
- `applications.commands` だけで招待していないか確認する
- サーバーのメンバー一覧にBotがいるか確認する
- Bot名やサーバーニックネームが違っていないか確認する

### Botがオフラインのまま

Botコンテナが起動していない可能性があります。

```bash
docker compose ps
docker compose logs -f bot
```

### Botが返信しない

- `.env` の `DISCORD_TOKEN` が正しいか確認する
- 対象チャンネルでBotに送信権限があるか確認する
- Botを正しくメンションしているか確認する
- Ollamaモデルがダウンロード済みか確認する

```bash
docker compose exec ollama ollama list
```

### Ollamaへの接続で失敗する

`OLLAMA_URL` はDocker内部のサービス名を使います。

```env
OLLAMA_URL=http://ollama:11434/api/chat
```

`localhost` にすると、Botコンテナ自身を指してしまうため、Ollamaに接続できません。

### 初回だけ返答が遅い

モデルの初回ロードに時間がかかることがあります。

このBotでは `keep_alive` を設定して、モデルを一定時間メモリに残すようにしています。

```python
"keep_alive": "30m"
```

## 参考

- [Discord Developer Portal](https://discord.com/developers/applications)
- [Discord Developer Documentation](https://docs.discord.com/developers/docs/intro)
- [discord.py Documentation](https://discordpy.readthedocs.io/)
- [Ollama Docker Documentation](https://docs.ollama.com/docker)
- [Ollama API Documentation](https://docs.ollama.com/api)
