#!/usr/bin/env python3
import json
import requests


# 設定
# Subtask情報取得API
FETCH_PBI_API = "https://agile.kddi.com/jira/rest/api/2/search?maxResults=300&jql={JQL}&expand=changelog"

# フィルター
JQL = 'project = EVASS AND スプリント = "{TARGET_SPRINT_NAME}" AND labels = "{TARGET_LABEL}" AND labels not in (Impediment) ORDER BY ランク'


# Subtask情報取得処理
def fetch_pbis(url, username, password):
    response = requests.get(url=url, auth=(username, password))
    return response.json().get("issues")


# PBI情報を整形する処理
def format_pbis(issues):
    backlogs = []

    for issue in issues:
        fields = issue.get("fields")
        if not fields:
            continue

        # 親Issueがある場合はSubtaskなので処理不要
        parent = fields.get("parent")
        if parent:
            continue

        backlogs.append(
            {
                "key": issue.get("key"),
                "name": fields.get("summary"),
                "labels": fields.get("labels"),
                "description": fields.get("description", ""),
            }
        )

    return backlogs


def main():
    # 設定ファイル読み込み
    with open("config.json", "r") as f:
        config = json.load(f)

    # PBI情報取得
    jql = JQL.format(
        TARGET_SPRINT_NAME=config["TARGET_SPRINT_NAME"],
        TARGET_LABEL=config["TARGET_LABEL"],)
    api = FETCH_PBI_API.format(JQL=jql)
    pbis = fetch_pbis(api, config["JIRA_USERNAME"], config["JIRA_PASSWORD"])

    # 出力用JSON作成
    output_json = {
        "pbis": format_pbis(pbis),
    }

    # 出力処理
    with open(config["OUTPUT_FILE"], "w") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
