"""
PubMed 引用数検索システム — 辞書ファイル
日本語→MeSHクエリ変換辞書 / ジャーナル被引用数取得
"""

import logging

from openalex import fetch_citedness

logger = logging.getLogger(__name__)

# =========================================================
# 日本語 → PubMed MeSH クエリ変換辞書
# =========================================================
MESH_DICTIONARY: dict[str, str] = {
    '眼科':         'Ophthalmology[MeSH]',
    '緑内障':       'Glaucoma[MeSH]',
    '網膜':         'Retina[MeSH]',
    '黄斑変性':     'Macular Degeneration[MeSH]',
    '加齢黄斑変性': 'Macular Degeneration[MeSH]',
    '糖尿病網膜症': 'Diabetic Retinopathy[MeSH]',
    '白内障':       'Cataract[MeSH]',
    '近視':         'Myopia[MeSH]',
    '視神経':       'Optic Nerve[MeSH]',
    '角膜':         'Cornea[MeSH]',
    '網膜剥離':     'Retinal Detachment[MeSH]',
    '視野':         'Visual Field Tests[MeSH]',
    '眼圧':         'Intraocular Pressure[MeSH]',
    '人工知能（眼科）': 'Artificial Intelligence[MeSH] AND Ophthalmology[MeSH]',
}

# =========================================================
# ジャーナル名 → インパクトファクター辞書
# =========================================================
IMPACT_FACTOR_DICTIONARY: dict[str, float] = {
    'Ophthalmology':                                          14.0,
    'JAMA Ophthalmology':                                      8.1,
    'Progress in Retinal and Eye Research':                    18.3,
    'American Journal of Ophthalmology':                        5.2,
    'British Journal of Ophthalmology':                         4.1,
    'Investigative Ophthalmology & Visual Science':             4.2,
    'Investigative Ophthalmology and Visual Science':           4.2,
    'IOVS':                                                     4.2,
    'Eye':                                                      3.0,
    'Cornea':                                                   2.8,
    'Journal of Glaucoma':                                      2.4,
    'Retina':                                                   4.5,
    "Graefe's Archive for Clinical and Experimental Ophthalmology": 3.2,
    'Ocular Surface':                                           7.6,
    'The Ocular Surface':                                       7.6,
    'Translational Vision Science & Technology':                3.0,
    'Translational Vision Science and Technology':              3.0,
}


def get_mesh_query(keyword: str) -> str | None:
    """
    日本語キーワードを PubMed MeSH クエリに変換する。

    Args:
        keyword: 日本語の分野キーワード

    Returns:
        MeSH クエリ文字列。辞書に存在しない場合は None を返しログに記録。
    """
    query = MESH_DICTIONARY.get(keyword)
    if query is None:
        logger.error(f"辞書に存在しないキーワード: '{keyword}' — スキップします")
    return query


def get_impact_factor(journal_name: str) -> str | float:
    """
    ジャーナル名から 2yr_mean_citedness（2年平均被引用数）を取得する。
    OpenAlex API → ハードコード辞書（フォールバック）の順で検索。

    Args:
        journal_name: ジャーナル名

    Returns:
        被引用数（float）、見つからない場合は 'N/A'
    """
    if not journal_name:
        return 'N/A'

    # OpenAlex API から取得
    citedness = fetch_citedness(journal_name)
    if citedness is not None:
        return citedness

    # フォールバック: ハードコード辞書
    journal_lower = journal_name.strip().lower()

    for key, value in IMPACT_FACTOR_DICTIONARY.items():
        if key.lower() == journal_lower:
            return value

    best_match: tuple[int, float] | None = None
    for key, value in IMPACT_FACTOR_DICTIONARY.items():
        key_lower = key.lower()
        if key_lower in journal_lower:
            if best_match is None or len(key_lower) > best_match[0]:
                best_match = (len(key_lower), value)

    if best_match is not None:
        return best_match[1]

    return 'N/A'
