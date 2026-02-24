"""
PubMed 引用数検索システム — エントリーポイント

実行フロー:
  1. config.py から設定読み込み
  2. 日本語キーワードを MeSH クエリに変換
  3. PubMed API で指定期間の PMID 一覧を取得
  4. PMID からメタデータ（DOI・ジャーナル名・アブストラクト）を取得
  5. OpenCitations COCI で合計引用数を取得し閾値（10回以上）でフィルタ
  6. 条件合致論文を SQLite DB に記録
  7. 未通知レコードを取得
  8. Gemini API でアブストラクトを日本語要約
  9. ジャーナル IF を辞書から取得
  10. メール本文を生成して Gmail 送信
  11. 送信済み論文の notified を更新
"""

import argparse
import logging
import sys

import config
import opencitations
from dictionary import get_mesh_query
from pubmed_fetcher import search_pmids, fetch_article_details
from gemini_summarizer import summarize_abstract
from database import init_db, insert_alert, get_pending_alerts, mark_as_notified
from alert import send_alert_email

# =========================================================
# ロギング設定
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)



def run(start_date: str = None, end_date: str = None,
        article_types: list[str] = None, dry_run: bool = False) -> None:
    """
    メイン実行フロー。

    Args:
        start_date: 検索開始日 (YYYY/MM/DD)
        end_date: 検索終了日 (YYYY/MM/DD)
        article_types: 対象 Article Type リスト。None の場合は config から取得。
        dry_run: True の場合、メール送信をスキップ
    """
    logger.info("=" * 60)
    logger.info("PubMed 引用数検索システム — 実行開始")
    logger.info("=" * 60)

    if dry_run:
        logger.info("*** ドライランモード: メール送信はスキップされます ***")

    # ステップ 1: 設定読み込み
    logger.info("ステップ 1: 設定読み込み")
    fields = config.DEFAULT_FIELDS
    if article_types is None:
        article_types = config.DEFAULT_ARTICLE_TYPES
    # 合計引用数の閾値は 10 に固定（または設定から取得）
    threshold = 10
    logger.info(f"  対象分野: {fields}")
    logger.info(f"  Article Type: {article_types if article_types else '全タイプ'}")
    logger.info(f"  引用数閾値: {threshold}")

    # DB初期化
    init_db()

    # ステップ 2: MeSH クエリ変換
    logger.info("ステップ 2: 日本語→MeSH クエリ変換")
    mesh_queries = []
    for field in fields:
        query = get_mesh_query(field)
        if query:
            mesh_queries.append(query)
            logger.info(f"  '{field}' → '{query}'")

    if not mesh_queries:
        logger.error("有効な MeSH クエリがありません。終了します。")
        return

    # ステップ 3: PubMed 検索
    logger.info("ステップ 3: PubMed API で PMID 一覧を取得")
    all_pmids = []
    for query in mesh_queries:
        pmids = search_pmids(
            query,
            mindate=start_date,
            maxdate=end_date,
            article_types=article_types,
        )
        all_pmids.extend(pmids)

    # 重複除去
    all_pmids = list(dict.fromkeys(all_pmids))
    logger.info(f"  合計 PMID 数: {len(all_pmids)}")

    if not all_pmids:
        logger.info("対象 PMID がありません。終了します。")
        return

    # ステップ 4: メタデータ取得
    logger.info("ステップ 4: PubMed efetch でメタデータ取得")
    articles = fetch_article_details(all_pmids)
    logger.info(f"  取得した論文数: {len(articles)}")

    # ステップ 5-6: 引用数確認 + DB記録
    logger.info("ステップ 5-6: OpenCitations で合計引用数確認 + DB 記録")
    # 検索対象期間を検出月として扱う（ログ用）
    detected_period = f"{start_date or 'base'} to {end_date or 'base'}"
    hit_count = 0

    total = len(articles)
    for idx, article in enumerate(articles, 1):
        doi = article.get("doi")
        if not doi:
            continue

        if idx % 50 == 0:
            logger.info(f"  進捗: {idx}/{total} 件処理済み...")

        total_citations = opencitations.get_total_citations(doi)
        if total_citations is None:
            continue

        if total_citations >= threshold:
            hit_count += 1
            logger.info(
                f"  ✅ 条件合致: PMID={article['pmid']}, "
                f"合計引用数={total_citations}, タイトル={article['title'][:60]}..."
            )
            insert_alert(
                pmid=article["pmid"],
                doi=doi,
                title=article["title"],
                journal=article["journal"],
                published_date=article["published_date"],
                citation_increase=total_citations, # カラム名はそのまま流用（実体は合計数）
                detected_month=detected_period,
            )

    logger.info(f"  閾値超過 (>= {threshold}): {hit_count}")

    # ステップ 7: 未通知レコード取得
    logger.info("ステップ 7: 未通知レコードの取得")
    pending = get_pending_alerts(detected_period)
    logger.info(f"  未通知レコード数: {len(pending)}")

    if not pending:
        logger.info("通知対象がありません。終了します。")
        return

    # ステップ 8: Gemini 要約
    logger.info("ステップ 8: Gemini API でアブストラクト日本語要約")
    for alert_record in pending:
        pmid = alert_record["pmid"]
        # アブストラクトを取得（articlesから検索）
        abstract = None
        for article in articles:
            if article["pmid"] == pmid:
                abstract = article.get("abstract")
                break

        if abstract:
            summary = summarize_abstract(abstract)
        else:
            summary = "（アブストラクトが存在しないため要約できません）"

        alert_record["summary"] = summary
        logger.info(f"  PMID={pmid}: 要約完了")

    # ステップ 9: IF はメール生成時に dictionary.py から自動取得

    # ステップ 10: メール送信
    logger.info("ステップ 10: アラートメール送信")
    if dry_run:
        logger.info("  [ドライラン] メール送信をスキップ")
        logger.info("  === メール内容プレビュー ===")
        for alert_record in pending:
            logger.info(
                f"  タイトル: {alert_record.get('title', 'N/A')}"
            )
            logger.info(
                f"  合計引用数: {alert_record.get('citation_increase', 0)}"
            )
            logger.info(
                f"  要約: {alert_record.get('summary', 'N/A')[:100]}..."
            )
            logger.info("  ---")
    else:
        success = send_alert_email(pending)
        if not success:
            logger.error("メール送信に失敗しました")
            return

    # ステップ 11: notified 更新
    logger.info("ステップ 11: notified フラグを更新")
    alert_ids = [a["id"] for a in pending]
    if not dry_run:
        mark_as_notified(alert_ids)
        logger.info(f"  {len(alert_ids)} 件を通知済みに更新")
    else:
        logger.info(f"  [ドライラン] {len(alert_ids)} 件の更新をスキップ")

    logger.info("=" * 60)
    logger.info("PubMed 引用数検索システム — 実行完了")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="PubMed 引用数検索システム"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="検索開始日 (YYYY/MM/DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="検索終了日 (YYYY/MM/DD)",
    )
    parser.add_argument(
        "--article-types",
        type=str,
        nargs="*",
        metavar="TYPE",
        help=(
            "対象 Article Type を空白区切りで指定。"
            "例: --article-types 'Clinical Trial' 'Review' "
            "省略時は config.DEFAULT_ARTICLE_TYPES を使用。"
            "フィルタなしにする場合は --article-types（値なし）を指定。"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="メール送信をスキップしてフロー全体をテスト実行",
    )
    args = parser.parse_args()

    # --article-types が指定されなかった場合は None（config から自動取得）
    # --article-types だけ指定されて値なしの場合は [] (フィルタなし)
    article_types = args.article_types  # None or list

    try:
        run(
            start_date=args.start_date,
            end_date=args.end_date,
            article_types=article_types,
            dry_run=args.dry_run
        )
    except Exception as e:
        logger.exception(f"予期せぬエラーが発生: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
