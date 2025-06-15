import logging
import logging.handlers
import os
import stat
from lib import logging as my_logging

import argparse


# --------------------------------------------------------------------------
# 2. メイン処理
# --------------------------------------------------------------------------
def main():
    """メインの処理"""
    # --- 引数の設定 ---
    parser = argparse.ArgumentParser(
        description="ログローテーションのテストスクリプト。パーミッションを指定できます。"
    )
    parser.add_argument(
        "--group-writable",
        action="store_true",  # この引数があればTrueになるフラグ
        help="ログファイルをグループ書き込み可能にする",
    )
    args = parser.parse_args()

    # --- ログファイルのパス設定 ---
    try:
        script_path = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_path)
    except NameError:
        script_dir = os.getcwd()
        print("Warning: '__file__' is not defined. Using current working directory.")

    log_dir = os.path.join(script_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    LOG_FILE = os.path.join(log_dir, "my_app.log")  # ファイル名を少しシンプルに変更

    # --- 引数に応じて使用するハンドラを切り替える ---
    if args.group_writable:
        print(
            "INFO: '--group-writable'が指定されたため、グループ書き込み可能モードで実行します。"
        )
        handler_class = my_logging.GroupWritableRotatingFileHandler
    else:
        print("INFO: デフォルトのパーミッション（umask依存）で実行します。")
        # 標準のローテーションハンドラを使用
        handler_class = logging.handlers.RotatingFileHandler

    # --- ロガーのセットアップ ---
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # 選択したクラスでハンドラのインスタンスを作成
    handler = handler_class(
        LOG_FILE,
        maxBytes=50 * 1024,  # 50KB
        backupCount=3,
        encoding="utf-8",  # エンコーディングを明示
    )
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # 防御的プログラミング
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)

    # --- ログ出力の実行 ---
    print(f"INFO: ログを '{LOG_FILE}' に出力します。")
    for i in range(1000):
        logger.debug(f"テストメッセージ番号 {i+1}。")

    print("INFO: 処理完了。")
    print(f"INFO: ログファイルは '{os.path.abspath(log_dir)}' に作成されました。")


if __name__ == "__main__":
    main()
