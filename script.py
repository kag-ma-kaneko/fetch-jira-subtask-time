#!/usr/bin/env python3
import datetime
import json
import re
import requests


# Sprint情報取得処理
def get_sprint_info(url, username, password):
    response = requests.get(url=url, auth=(username, password))
    return response.json().get("values")


# 特定の名前のSprint情報を取得
def get_specific_sprint(sprints, sprint_name):
    for sprint in sprints:
        if sprint["name"] == sprint_name:
            return sprint
    return None


# Subtask情報取得処理
def get_subtask_info(url, username, password):
    response = requests.get(url=url, auth=(username, password))
    return response.json().get("issues")


# Sprint情報を整形する処理
def format_sprint_info(sprint_info):
    sprint_name = sprint_info.get("name")
    sprint_number = int(re.sub("[^0-9]+", "", sprint_name)) if sprint_name else 0
    start_date = datetime.datetime.fromisoformat(sprint_info.get("startDate"))
    end_date = datetime.datetime.fromisoformat(sprint_info.get("endDate"))

    return {
        "sprintNo": sprint_number,
        "beginDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "endDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
    }


# Subtask情報を整形する処理
def format_subtask_info(issues):
    backlogs = []
    subtasks = []

    for issue in issues:
        fields = issue.get("fields")
        if not fields:
            continue

        parent = fields.get("parent")
        if parent is None:
            backlog = {
                "name": fields.get("summary"),
                "key": issue.get("key"),
                "subtasks": [],
            }
            backlogs.append(backlog)
        else:
            subtask = create_subtask(fields, issue, parent)
            subtasks.append(subtask)

    associate_subtasks_with_backlogs(backlogs, subtasks)
    return backlogs


#
def create_subtask(fields, issue, parent):
    assignee = fields.get("assignee")
    assignees = fields.get("customfield_10205")
    assignee_names = [a.get("displayName") for a in assignees] if assignees else []
    assignee_name_str = (
        ",".join([assignee.get("displayName")] + assignee_names)
        if assignee
        else "未割り当て"
    )

    subtask = {
        "name": fields.get("summary"),
        "parent_key": parent.get("key"),
        "pic": assignee_name_str.replace("\u3000", ""),
    }

    change_logs = issue.get("changelog", {}).get("histories", [])
    for history in change_logs:
        items = history.get("items", [])
        for item in items:
            if item.get("field") == "status":
                update_subtask_status(subtask, item, history)

    return subtask


def update_subtask_status(subtask, item, history):
    from_status = item.get("fromString", "なし")
    to_status = item.get("toString", "なし")
    status_change_datetime = history.get("created").replace("+0900", "")

    if (from_status in ["ToDo", "Assigned"]) and to_status != "Done":
        subtask["start"] = status_change_datetime
    elif to_status == "Done":
        subtask["end"] = status_change_datetime


def associate_subtasks_with_backlogs(backlogs, subtasks):
    for backlog in backlogs:
        for subtask in subtasks:
            if subtask["parent_key"] == backlog["key"]:
                if subtask.get("start") and subtask.get("end"):
                    backlog["subtasks"].append(subtask)
        del backlog["key"]


def main():
    # 設定ファイル読み込み
    with open("config.json", "r") as f:
        config = json.load(f)

    # Sprint情報取得
    sprint_url = config["SPRINT_INFO_URL"].format(
        BOARD_ID=config["BOARD_ID"],
    )
    sprint_info = get_specific_sprint(
        get_sprint_info(sprint_url, config["JIRA_USERNAME"], config["JIRA_PASSWORD"]),
        config["TARGET_SPRINT_NAME"],
    )

    # Subtask情報取得
    jql = config["JQL"].format(
        TARGET_TEAM_LABEL=config["TARGET_TEAM_LABEL"],
        TARGET_SPRINT_NAME=config["TARGET_SPRINT_NAME"],
    )
    subtask_url = config["SUBTASK_INFO_URL"].format(JQL=jql)
    subtask_info = get_subtask_info(
        subtask_url, config["JIRA_USERNAME"], config["JIRA_PASSWORD"]
    )

    # 出力処理
    output_json = {
        "metaData": format_sprint_info(sprint_info),
        "backlogs": format_subtask_info(subtask_info),
    }

    with open(config["OUTPUT_FILE"], "w") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
