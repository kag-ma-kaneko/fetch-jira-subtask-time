# fetch-and-generate-cycle-time-data

サイクルタイムに必要なデータを Jira から引っ張って整形、出力するツール

# 使い方

1. ローカル環境に clone する
1. poetry install
1. ローカル環境にある`config-template.json`を`config.json`にリネームして必要情報を入力する
   1. JIRA_USERNAME と JIRA_PASSWORD に自分の Jira のログイン情報を入力する
   1. OUTPUT_FILE を変更する
   1. TARGET_SPRINT_NAME と TARGET_TEAM_LABEL にスプリントの名前とフィルターするチーム名のラベルを入力する
   1. BOARD_ID にボードの ID を入力する（ボードの ID は Jira の URL から確認できる）
1. poetry run ./script.py を実行する

# 関連情報

UI 側については以下から取得する
https://github.com/kag-ma-kaneko/sprint-cycle-time

# 参考：出力ファイルのイメージ

<img width="1022" alt="image" src="https://media.github.kddi.com/user/534/files/84ab6ee3-f2e7-4ff8-9c33-b90e1b046114">
