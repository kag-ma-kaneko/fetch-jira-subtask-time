#!/usr/bin/env python3
from datetime import datetime, timedelta
from dateutil import parser
from workalendar.asia import Japan
import pytz
import json
import re
import requests


# 設定\
# スプリント情報取得API
SPRINT_INFO_URL = "https://agile.kddi.com/jira/rest/agile/1.0/board/{BOARD_ID}/sprint?&state=active,future"

# Subtask情報取得API
SUBTASK_INFO_URL = "https://agile.kddi.com/jira/rest/api/2/search?maxResults=300&jql={JQL}&expand=changelog"

# フィルター
JQL = 'project = EVASS AND labels = "{TARGET_TEAM_LABEL}" AND スプリント = "{TARGET_SPRINT_NAME}" AND labels not in (Impediment) ORDER BY ランク'


class WorkHours:
    def __init__(self, start, end, weekends):
        self.start = start
        self.end = end
        self.weekends = weekends

    def is_within(self, dt):
        return (
            dt.strftime("%A") not in self.weekends
            and self.start <= dt.time() <= self.end
        )


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
    start_date = datetime.fromisoformat(sprint_info.get("startDate"))
    end_date = datetime.fromisoformat(sprint_info.get("endDate"))

    return {
        "sprintNo": sprint_number,
        "beginDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "endDate": end_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
    }


# Subtask情報を整形する処理
def format_subtask_info(issues, sprint, work_hours):
    backlogs = []
    subtasks = []

    for issue in issues:
        fields = issue.get("fields")
        if not fields:
            continue

        parent = fields.get("parent")

        # 親Issueがない場合、Backlogとして扱う
        if parent is None:
            backlog = {
                "name": fields.get("summary"),
                "key": issue.get("key"),
                "subtasks": [],
            }
            backlogs.append(backlog)
        else:
            subtask = create_subtask(fields, issue, parent, work_hours)
            subtasks.append(subtask)

    associate_subtasks_with_backlogs(backlogs, subtasks)
    return backlogs


#
def create_subtask(fields, issue, parent, work_hours):
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
                update_subtask_status(subtask, item, history, work_hours)

    return subtask


def update_subtask_status(subtask, item, history, work_hours):
    from_status = item.get("fromString", "なし")
    to_status = item.get("toString", "なし")
    status_change_datetime = history.get("created")

    if (from_status in ["ToDo", "Assigned"]) and to_status != "Done":
        subtask["start"] = status_change_datetime
    elif to_status == "Done":
        subtask["end"] = status_change_datetime

    # startとendが両方存在する場合、その間の時間（分）を計算
    if "start" in subtask and "end" in subtask:
        start_time = parser.parse(subtask["start"])
        end_time = parser.parse(subtask["end"])

        # 休日と祝日を除外
        cal = Japan()
        duration = 0
        current_time = start_time
        while current_time <= end_time:
            if not cal.is_holiday(current_time) and work_hours.is_within(current_time):
                duration += 10
            current_time += timedelta(minutes=10)

        subtask["duration"] = duration


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
    sprint_url = SPRINT_INFO_URL.format(
        BOARD_ID=config["BOARD_ID"],
    )
    sprint_info = get_specific_sprint(
        get_sprint_info(sprint_url, config["JIRA_USERNAME"], config["JIRA_PASSWORD"]),
        config["TARGET_SPRINT_NAME"],
    )

    # Subtask情報取得
    jql = JQL.format(
        TARGET_TEAM_LABEL=config["TARGET_TEAM_LABEL"],
        TARGET_SPRINT_NAME=config["TARGET_SPRINT_NAME"],
    )
    subtask_url = SUBTASK_INFO_URL.format(JQL=jql)
    subtask_info = get_subtask_info(
        subtask_url, config["JIRA_USERNAME"], config["JIRA_PASSWORD"]
    )

    # 出力処理
    work_hours = WorkHours(
        datetime.strptime(config["work_hour"]["start"], "%H:%M").time(),
        datetime.strptime(config["work_hour"]["end"], "%H:%M").time(),
        config["weekends"],
    )
    output_json = {
        "metaData": format_sprint_info(sprint_info),
        "backlogs": format_subtask_info(subtask_info, sprint_info, work_hours),
    }

    with open(config["OUTPUT_FILE"], "w") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
