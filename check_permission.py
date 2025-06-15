import os
import stat
import logging
import shutil


def _create_log_file(path, logger_name):
    """
    指定されたパスにログファイルを作成するヘルパー関数。
    ロガーがキャッシュされることを考慮し、毎回異なるロガー名を使うか、
    ハンドラをクリアすることで独立性を保つ。
    """
    logger = logging.getLogger(logger_name)
    # 既存のハンドラがあればクリアして、テストの独立性を確保
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(path)
    logger.addHandler(handler)
    logger.info(f"Log message for {logger_name}")
    handler.close()
    # ロガーからハンドラを削除して、次回の呼び出しに影響を与えないようにする
    logger.removeHandler(handler)


def run_permission_tests():
    """umaskとログファイルのパーミッションの関係をテストする一連の処理"""

    # --- 1. セットアップ ---
    original_umask = os.umask(0)  # 現在のumaskを取得し、マスクを0に設定
    os.umask(original_umask)  # すぐに元の値に戻す（目的は値の取得）

    test_dir = "temp_permission_test"

    print("--- ログファイルパーミッションのテストを開始します ---")
    print(f"元のumask: 0o{original_umask:03o}")

    # テスト用ディレクトリが既存なら削除して、クリーンな状態から開始
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    log_file_path = os.path.join(test_dir, "test.log")

    try:
        # --- 2. テストの実行 ---

        # === テストケース1: グループ書き込みが「許可」されるべきケース ===
        print("\n[テストケース1: umask = 0o002]")
        umask_to_test_1 = 0o002
        os.umask(umask_to_test_1)
        print(f"  umaskを 0o{umask_to_test_1:03o} に設定しました。")

        _create_log_file(log_file_path, "logger_test_1")

        mode1 = os.stat(log_file_path).st_mode
        is_group_writable1 = bool(mode1 & stat.S_IWGRP)

        print(f"  作成されたファイルのパーミッション: {stat.filemode(mode1)}")
        if is_group_writable1:
            print("  ✅ SUCCESS: 期待通り、グループ書き込み可能です。")
        else:
            print("  ❌ FAILURE: グループ書き込み可能になりませんでした。")

        os.remove(log_file_path)  # 次のテストのためファイルを削除

        # === テストケース2: グループ書き込みが「不許可」になるべきケース ===
        print("\n[テストケース2: umask = 0o022]")
        umask_to_test_2 = 0o022
        os.umask(umask_to_test_2)
        print(f"  umaskを 0o{umask_to_test_2:03o} に設定しました。")

        _create_log_file(log_file_path, "logger_test_2")

        mode2 = os.stat(log_file_path).st_mode
        is_group_writable2 = bool(mode2 & stat.S_IWGRP)

        print(f"  作成されたファイルのパーミッション: {stat.filemode(mode2)}")
        if not is_group_writable2:
            print(" SUCCESS: 期待通り、グループ書き込みは不可です。")
        else:
            print(" FAILURE: グループ書き込み可能になってしまいました。")

    finally:
        # --- 3. クリーンアップ ---
        print("\n--- テストを終了し、クリーンアップを実行します ---")
        os.umask(original_umask)
        print(f"umaskを元の値 (0o{original_umask:03o}) に戻しました。")

        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print(f"テストディレクトリ '{test_dir}' を削除しました。")


# --- スクリプトの実行 ---
if __name__ == "__main__":
    run_permission_tests()
