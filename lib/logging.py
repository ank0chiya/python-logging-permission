import logging
import logging.handlers
import os
import stat


class GroupWritableRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    ファイル作成後とローテーション後にグループ書き込み権限を付与する
    RotatingFileHandler。
    """

    def __init__(
        self, filename, mode="a", maxBytes=0, backupCount=0, encoding=None, delay=False
    ):
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
        # 初期ファイルのパーミッションを設定
        self._chmod_group_writable()

    def doRollover(self):
        """
        ログのローテーションを実行し、新しいファイルのパーミッションを設定する。
        """
        # 親クラスのローテーション処理を先に実行
        super().doRollover()
        # ローテーション後に作られた新しいログファイルに権限を付与
        self._chmod_group_writable()

    def _chmod_group_writable(self):
        """現在のログファイルにグループ書き込み権限を付与するヘルパーメソッド"""
        if os.path.exists(self.baseFilename):
            try:
                # 現在のパーミッションを取得し、グループ書き込み権限を追加
                current_permissions = stat.S_IMODE(os.stat(self.baseFilename).st_mode)
                os.chmod(self.baseFilename, current_permissions | stat.S_IWGRP)
            except OSError as e:
                # エラーハンドリング (例: ログに出力)
                # このハンドラ自体からログを出すと無限ループになる可能性があるので注意
                print(
                    f"Warning: Could not set permission for log file {self.baseFilename}: {e}"
                )
