素晴らしいユースケースをご提示いただき、ありがとうございます。その要求は非常に現実的で、多くのコマンドラインツールやサーバーアプリケーションで共通の課題です。

「様々なユーザーが実行するが、ログは単一のファイルに集約したい」という要件を、安全かつ堅牢に実現するための**ベストプラクティス**をご提案します。

この問題の解決策は、Python コードの実装**だけ**で完結させるのではなく、**「OS レベルの事前設定」**と**「Python コードの実装」**を組み合わせるのが最も効果的です。

---

### 全体像：役割分担による堅牢な設計

-   **OS の役割（管理者の仕事）**: どのユーザーとグループがファイルにアクセスできるかを管理する。
-   **Python の役割（開発者の仕事）**: OS の設定に従って、適切にログを書き出す。

この役割分担に基づいた、2 ステップのアプローチをご紹介します。

---

### ステップ 1：環境設定（管理者による事前準備）

まず、ツールのインストール時やサーバーのセットアップ時に、一度だけ以下の設定を行います。これにより、ログファイルを安全に共有するための「土台」ができます。

#### 1. ログ共有用の専用グループを作成

ツール利用者をまとめるための専用グループを作成します。ここでは `my-cli-loggers` という名前にします。

```bash
sudo groupadd my-cli-loggers
```

#### 2. ツール利用者を専用グループに追加

このコマンドラインツールを実行する可能性のある全てのユーザーを、作成したグループに追加します。

```bash
# userAとuserBをグループに追加する例
sudo usermod -aG my-cli-loggers userA
sudo usermod -aG my-cli-loggers userB
# 新しいグループに所属させるため、ユーザーは一度再ログインが必要な場合があります
```

#### 3. ログディレクトリの作成と権限設定（最重要）

ログファイルを格納するディレクトリを作成し、特殊なパーミッション`setgid`を設定します。

```bash
# ログディレクトリを作成
sudo mkdir -p /var/log/my-cli-tool

# ディレクトリのグループを専用グループに変更
sudo chgrp my-cli-loggers /var/log/my-cli-tool

# ディレクトリにグループ書き込み権限と`setgid`ビットを設定
sudo chmod 2775 /var/log/my-cli-tool
```

**`chmod 2775` の意味は？**
これは `drwxrwsr-x` というパーミッションを設定します。`s`が`setgid`ビットです。

-   **`g+s` (`setgid`)**: このディレクトリ内に**新しく作成されたファイルやディレクトリは、親ディレクトリのグループ（`my-cli-loggers`）を自動的に継承します。** これが今回の仕組みの核となります。どのユーザーがファイルを作っても、グループは常に `my-cli-loggers` になります。
-   **`g+w`**: `my-cli-loggers` グループに所属するユーザーが、このディレクトリ内にファイルを作成・削除する権限を与えます。

この事前設定により、パーミッション管理の大部分が OS レベルで自動的に行われるようになります。

---

### ステップ 2：Python コードの実装

上記の環境設定を前提とすると、Python コードは驚くほどシンプルになります。カスタムハンドラで`chmod`を呼び出す必要はなく、**プロセスの`umask`を一時的に変更する**だけで十分です。

`try...finally`ブロックで`umask`の変更を囲むことで、ツールの実行中だけパーミッションを緩め、終了時には必ず元に戻す安全な実装です。

```python
import os
import logging
import logging.handlers
import argparse

# ログファイルのパスは、設定した共有ディレクトリ内に固定
LOG_FILE_PATH = '/var/log/my-cli-tool/activity.log'

def setup_logging():
    """ログファイルに書き込むためのロガーをセットアップする"""

    # -------------------------------------------------------------
    # umaskを一時的に変更し、グループ書き込みを許可する
    # -------------------------------------------------------------
    # 0o002 は、デフォルトのファイルパーミッション(666)から
    # グループ書き込み権限を「取り除かない」設定。
    # setgidディレクトリ内でこれが実行されると、
    # 664 (-rw-rw-r--) のパーミッションを持つファイルが作成される。
    original_umask = os.umask(0o002)

    try:
        # ログローテーション機能付きのハンドラを使用
        # 5MBでローテーションし、バックアップは3つまで保持
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE_PATH,
            maxBytes=5*1024*1024, # 5MB
            backupCount=3,
            encoding='utf-8'
        )

        # どのユーザーが実行したかわかるように、ユーザー名をフォーマットに含める
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - User:%(user)s - %(message)s'
        )
        handler.setFormatter(formatter)

        logger = logging.getLogger('my_cli_tool_logger')

        # ログに実行ユーザー名を追加するためのFilter
        class UserLogFilter(logging.Filter):
            def filter(self, record):
                record.user = os.getlogin()
                return True

        logger.addFilter(UserLogFilter())

        # ハンドラの重複登録を防ぐ
        if logger.hasHandlers():
            logger.handlers.clear()

        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    finally:
        # -------------------------------------------------------------
        # 処理が終わったら、必ず元のumaskに戻す
        # -------------------------------------------------------------
        os.umask(original_umask)

    return logger


def main():
    """コマンドラインツールのメイン処理"""
    parser = argparse.ArgumentParser(description="My CLI Tool")
    parser.add_argument('action', help="実行するアクション")
    args = parser.parse_args()

    # ロガーをセットアップ
    logger = setup_logging()

    logger.info(f"アクション '{args.action}' が実行されました。")

    # ... ここにツールの本体処理 ...
    print(f"アクション '{args.action}' を実行しました。詳細はログファイルを確認してください。")
    print(f"ログファイル: {LOG_FILE_PATH}")


if __name__ == '__main__':
    main()

```

### このアプローチの利点

1.  **堅牢性**: アプリケーションコードで`os.chmod()`を呼び出すよりも、OS の`setgid`と`umask`という実績のある仕組みに頼る方がはるかに堅牢です。
2.  **役割の分離**: OS の管理（ユーザー、グループ、ディレクトリ権限）とアプリケーションのロジックが明確に分かれ、コードがクリーンになります。
3.  **シンプルさ**: Python コードは`umask`を一時的に変更するだけでよく、複雑なカスタムハンドラが不要になります。
4.  **保守性**: 将来、ツールを実行できるユーザーを追加したい場合、Python コードを変更せず、管理者が`usermod`コマンドでユーザーをグループに追加するだけで対応できます。

この「`setgid`ディレクトリ + `umask`制御」は、マルチユーザー環境でファイルを共有する際の、Linux/Unix における確立されたベストプラクティスです。ぜひこのアプローチをご検討ください。
