# 📊 PubMed 引用数検索システム

**PubMed Citation Search System**

PubMed に掲載された論文を指定期間・Article Type でフィルタリングし、合計引用数が10回以上の論文を Gemini API による日本語要約付きでメール通知するシステムです。

## ✨ 主な機能

- **期間指定検索** — 任意の日付範囲で論文を検索（デフォルト: 直近1年間）
- **Article Type フィルタ** — Clinical Trial / RCT / Review など論文種別で絞り込み
- **引用数フィルタ** — OpenCitations COCI API で合計引用数10回以上の論文を抽出
- **日本語キーワード対応** — 日本語で分野を指定するだけで MeSH クエリに自動変換
- **AI 要約** — Gemini 2.0 Flash でアブストラクトを日本語3〜5文に自動要約
- **インパクトファクター表示** — 主要眼科ジャーナルの IF を自動付与
- **HTML メール通知** — リッチなデザインのアラートメールを Gmail で送信
- **GitHub Actions 自動実行** — 毎月1日に自動実行（手動トリガーも可）

## 📁 ファイル構成

```
├── config.py                 # 全設定（閾値・分野・Article Typeなど）
├── dictionary.py             # 日本語→MeSH変換辞書 / ジャーナルIF辞書
├── pubmed_fetcher.py         # PubMed API連携（PMID検索・メタデータ取得）
├── opencitations.py          # OpenCitations COCI API（合計引用数取得）
├── gemini_summarizer.py      # Gemini API（アブストラクト日本語要約）
├── database.py               # SQLiteデータベース操作
├── alert.py                  # メール本文生成・Gmail SMTP送信
├── main.py                   # エントリーポイント（実行フロー制御）
├── requirements.txt          # 依存パッケージ
└── .github/workflows/
    └── citation_alert.yml    # GitHub Actionsワークフロー
```

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. GitHub Secrets の設定

リポジトリの **Settings > Secrets and variables > Actions** に以下を登録：

| シークレット名 | 内容 |
|---|---|
| `GMAIL_ADDRESS` | 送信元 Gmail アドレス |
| `GMAIL_APP_PASSWORD` | Gmail アプリパスワード（※2段階認証が必要） |
| `RECIPIENT_EMAIL` | 通知先メールアドレス |
| `GEMINI_API_KEY` | Google Gemini API キー |

### 3. 対象分野の設定（任意）

`config.py` の `DEFAULT_FIELDS` を編集して検索分野を変更できます：

```python
# 単一分野
DEFAULT_FIELDS = ['眼科']

# 複数分野
DEFAULT_FIELDS = ['眼科', '緑内障', '網膜']
```

対応キーワード一覧：眼科、緑内障、網膜、黄斑変性、加齢黄斑変性、糖尿病網膜症、白内障、近視、視神経、角膜、網膜剥離、視野、眼圧、人工知能（眼科）

## ▶️ 実行方法

### 自動実行（GitHub Actions）

毎月1日 09:00 JST に自動実行されます。Actions タブの **Run workflow** から手動実行も可能です。

### ローカル実行

```bash
# 通常実行（デフォルト: 直近1年間を検索）
python main.py

# ドライラン（メール送信スキップ）
python main.py --dry-run
```

ローカル実行時は環境変数を設定してください：

```bash
export GMAIL_ADDRESS="your@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
export RECIPIENT_EMAIL="recipient@example.com"
export GEMINI_API_KEY="your-gemini-api-key"
```

## 🗓️ 論文検索期間の変更方法

デフォルトでは **実行日を基準にした直近1年間** が検索対象になります。

### コマンドライン引数で指定する（その場限りの変更）

```bash
# 2024年全年を検索する場合
python main.py --start-date 2024/01/01 --end-date 2024/12/31

# 2023年7月〜2024年6月を検索する場合
python main.py --start-date 2023/07/01 --end-date 2024/06/30

# ドライランと組み合わせる場合
python main.py --start-date 2024/01/01 --end-date 2024/12/31 --dry-run
```

### GitHub Actions で期間を固定したい場合

`.github/workflows/citation_alert.yml` の `run` ステップに引数を追加します：

```yaml
- name: Run Citation Search System
  run: |
    python main.py --start-date 2024/01/01 --end-date 2024/12/31
```

## 📄 Article Type の変更方法

デフォルトでは以下の5種類が検索対象です：

| Article Type | 説明 |
|---|---|
| `Clinical Trial` | 臨床試験 |
| `Meta-Analysis` | メタアナリシス |
| `Randomized Controlled Trial` | ランダム化比較試験（RCT）|
| `Review` | レビュー |
| `Systematic Review` | システマティックレビュー |

### `config.py` で永続的に変更する

```python
# config.py の DEFAULT_ARTICLE_TYPES を編集

# Case Reports も追加したい場合
DEFAULT_ARTICLE_TYPES = [
    'Clinical Trial',
    'Meta-Analysis',
    'Randomized Controlled Trial',
    'Review',
    'Systematic Review',
    'Case Reports',       # ← 追加
]

# Review と Systematic Review だけにする場合
DEFAULT_ARTICLE_TYPES = [
    'Review',
    'Systematic Review',
]

# フィルタなし（全 Article Type を対象にする）
DEFAULT_ARTICLE_TYPES = []
```

指定可能な Article Type 一覧：
- `Clinical Trial`
- `Meta-Analysis`
- `Randomized Controlled Trial`
- `Review`
- `Systematic Review`
- `Case Reports`
- `Books and Documents`

### コマンドライン引数でその場限りの変更

```bash
# Case Reports だけを検索
python main.py --article-types "Case Reports"

# Review と Case Reports を検索
python main.py --article-types "Review" "Case Reports"

# Article Type フィルタを解除して全種類を検索
python main.py --article-types
```

## ⚙️ 設定項目

| 設定キー | デフォルト値 | 説明 |
|---|---|---|
| `DEFAULT_FIELDS` | `['眼科']` | 検索対象分野（日本語リスト） |
| `DEFAULT_ARTICLE_TYPES` | 上記5種類 | 対象 Article Type |

## 📋 実行フロー

1. 日本語キーワードを MeSH クエリに変換
2. PubMed API で指定期間（デフォルト: 直近1年）の論文を Article Type フィルタ付きで検索
3. 各論文の DOI から OpenCitations で合計引用数を取得
4. 合計引用数10回以上の論文を SQLite DB に記録
5. Gemini API でアブストラクトを日本語要約
6. ジャーナル IF を辞書から取得
7. HTML メールを生成して Gmail 送信

## ⚠️ 注意事項

- **OpenCitations カバレッジ**: DOI 未付与・Crossref 未登録の論文は引用数を取得できません
- **API レート制限**: PubMed（0.35秒）、OpenCitations（1秒）、Gemini（5秒）のウェイトを設けています
- **Gemini 無料枠**: 論文数が多い場合は 429 エラーが発生することがあります。その際は時間をおいて再実行してください
- **IF の更新**: `dictionary.py` の IF 辞書は年1回手動更新が必要です
- **DB 永続化**: GitHub Actions の artifacts 保持期間は90日です（長期運用時は要検討）
- **Gmail 認証**: 2段階認証を有効にしてアプリパスワードを発行してください

## 📄 ライセンス

MIT License
