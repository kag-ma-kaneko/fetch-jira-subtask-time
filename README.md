# fetch-and-generate-cycle-time-data
サイクルタイムに必要なデータをJiraから引っ張って整形、出力するツール

# 使い方
1. ローカル環境にcloneする
1. poetry install
1. ローカル環境にあるscript.pyを以下の通り修正する
    1. （必須）JIRA_USERNAMEとJIRA_PASSWORDに自分のJiraのログイン情報を入力する
    1. （必須）TARGET_SPRINT_NUMBER、SPRINT_INFO_URL、SUBTASK_INFO_URLに適切な情報を入力する<br>なお、SPRINT_INFO_URL内のrapidViewIdは自チームのJiraカンバンのURLから確認できる<br>同じくSUBTASK_INFO_URLについては自チームのカンバンの情報をもとに入力する
    1. （任意）OUTPUT_FILEを変更する
1. poetry run script.py を実行する
1. 同一階層に出力される出力ファイルをUI側に食わせる ※出力ファイル名はOUTPUT_FILEで自分で指定したもの

# 関連情報
UI側については以下から取得する
https://github.com/kag-ma-kaneko/sprint-cycle-time

# 参考：出力ファイルのイメージ
<img width="1022" alt="image" src="https://media.github.kddi.com/user/534/files/84ab6ee3-f2e7-4ff8-9c33-b90e1b046114">
