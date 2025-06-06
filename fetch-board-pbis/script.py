#!/usr/bin/env python3
from datetime import datetime, timedelta
from dateutil import parser
from workalendar.asia import Japan
import json
import re
import requests


# === 設定/定数定義 =======================================
# スプリント情報取得API
SPRINT_INFO_URL = "https://agile.kddi.com/jira/rest/agile/1.0/board/{BOARD_ID}/sprint?&state=active,future"

# Subtask情報取得API
SUBTASK_INFO_URL = "https://agile.kddi.com/jira/rest/api/2/search?maxResults=300&jql={JQL}&expand=changelog,subtasks"

# フィルター
JQL = (
    'project = EVASS AND labels = "{TARGET_TEAM_LABEL}" '
    'AND スプリント = "{TARGET_SPRINT_NAME}" '
    'AND labels not in (Impediment) ORDER BY ランク'
)


# === クラス定義（WorkHours） =============================
class WorkHours:
    def __init__(self, work_hours, weekends):
        self.time_ranges = [
            (self.parse_time(hours["start"]), self.parse_time(hours["end"]))
            for hours in work_hours
        ]
        self.weekends = weekends

    def parse_time(self, time_str):
        return datetime.strptime("2024-01-01 " + time_str, "%Y-%m-%d %H:%M").time()

    def is_within(self, dt):
        for start_time, end_time in self.time_ranges:
            if start_time <= dt.time() <= end_time:
                if dt.strftime("%A") not in self.weekends:
                    return True
        return False


# start/endから差の時間を計算する
def calc_duration(start_time, end_time, work_hours):
    cal = Japan()
    duration = 0
    current_time = start_time
    while current_time <= end_time:
        if not cal.is_holiday(current_time) and work_hours.is_within(current_time):
            duration += 10
        current_time += timedelta(minutes=10)
    return duration


# === APIアクセス関数群 ===================================
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


def get_start_time_from_history(histories):
    for history in histories:
        items = history.get("items", [])
        for item in items:
            if item.get("field") == "status":
                if (
                    item.get("fromString") == "ToDo"
                    and item.get("toString") == "IN-PROGRESS"
                ):
                    return history.get("created")
    return None


def get_end_time_from_history(histories):
    for history in histories:
        items = history.get("items", [])
        for item in items:
            if item.get("field") == "status":
                if (
                    item.get("fromString") == "IN-PROGRESS"
                    and item.get("toString") == "Done"
                ):
                    return history.get("created")
    return None


# Subtask情報を整形する処理
def format_subtask_info(issues, work_hours):
    backlogs = []
    subtasks = []

    for issue in issues:
        fields = issue.get("fields")
        if not fields:
            continue

        parent = fields.get("parent")

        # 親Issueがない場合、Backlogとして扱う
        if parent is None:

            pbi = create_backlogItem(fields, issue, work_hours)
            backlogs.append(pbi)
        else:
            subtask = create_subtask(fields, issue, parent, work_hours)
            subtasks.append(subtask)

    associate_subtasks_with_backlogs(backlogs, subtasks)
    return backlogs


def create_backlogItem(fields, issue, work_hours):
    histories = issue.get("changelog", {}).get("histories", [])
    start = get_start_time_from_history(histories)
    end = get_end_time_from_history(histories)
    cycle = None
    if start and end:
        dt1 = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.%f%z")
        dt2 = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S.%f%z")
        cycle = calc_duration(dt1, dt2, work_hours)

    return {
        "name": fields.get("summary"),
        "labels": fields.get("labels"),
        "point": int(fields.get("customfield_10008", 0)),
        "key": issue.get("key"),
        "start": start,
        "end": end,
        "cycle": cycle,
        "subtasks": [],
    }


#
def create_subtask(fields, issue, parent, work_hours):

    # 担当者情報取得
    # 担当者情報が二箇所に存在するため、両方取得して結合
    # customfield_10205には複数の担当者が存在するためそれらも結合
    assignee = fields.get("assignee")
    main_name = [assignee.get("displayName")] if assignee else []

    assignees = fields.get("customfield_10205")
    sub_names = [a.get("displayName") for a in assignees] if assignees else []

    assignee_name_str = ",".join(main_name + sub_names)
    if assignee_name_str == "":
        assignee_name_str = "未割り当て"

    subtask = {
        "name": fields.get("summary"),
        "labels": fields.get("labels"),
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
    elif to_status == "Done" or "DONE" in to_status:
        subtask["end"] = status_change_datetime

    # startとendが両方存在する場合、その間の時間（分）を計算
    if "start" in subtask and "end" in subtask:
        start_time = parser.parse(subtask["start"])
        end_time = parser.parse(subtask["end"])
        subtask["duration"] = calc_duration(start_time, end_time, work_hours)


# SubtaskをBacklogに紐付ける処理
def associate_subtasks_with_backlogs(backlogs, subtasks):
    for backlog in backlogs:
        for subtask in subtasks:
            if subtask["parent_key"] == backlog["key"]:
                if subtask.get("start") and subtask.get("end"):
                    backlog["subtasks"].append(subtask)

        # PBI毎にSubtaskの合計時間を計算
        backlog["subtask_total"] = sum(
            sub_task["duration"] for sub_task in backlog["subtasks"]
        )


def load_config(path="config.json"):
    with open(path, "r") as f:
        return json.load(f)


def fetch_sprint_info(config):
    sprint_url = SPRINT_INFO_URL.format(
        BOARD_ID=config["BOARD_ID"],
    )
    return get_specific_sprint(
        get_sprint_info(sprint_url, config["JIRA_USERNAME"], config["JIRA_PASSWORD"]),
        config["TARGET_SPRINT_NAME"],
    )


def fetch_subtask_info(config, sprint):
    jql = JQL.format(
        TARGET_TEAM_LABEL=config["TARGET_TEAM_LABEL"],
        TARGET_SPRINT_NAME=config["TARGET_SPRINT_NAME"],
    )
    subtask_url = SUBTASK_INFO_URL.format(JQL=jql)
    return get_subtask_info(
        subtask_url, config["JIRA_USERNAME"], config["JIRA_PASSWORD"]
    )


def generate_output(config, issues):
    with open("debug.json", "w") as f:
        json.dump(issues, f, ensure_ascii=False, indent=4)

    work_hours = WorkHours(config["work_hours"], config["weekends"])
    backlogs = format_subtask_info(issues, work_hours)
    return {
        "backlogs": backlogs,
    }


# === メイン処理（設定読込〜結果出力） ======================
def main():
    config = load_config()
    if not config:
        print("設定ファイルが読み込めませんでした。")
        return

    sprint_info = fetch_sprint_info(config)
    if not sprint_info:
        print("指定されたスプリントが見つかりません。")
        return

    issues = fetch_subtask_info(config, sprint_info)
    if not issues:
        print("Subtask情報が取得できませんでした。")
        return

    output_json = generate_output(config, issues)

    with open(config["OUTPUT_FILE"], "w") as f:
        json.dump(output_json, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
