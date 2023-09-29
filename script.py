import datetime
import json
import re
import requests

# 使用者の情報を入力する↓ここから

# JIRAのログインユーザー名とパスワードを入力する
JIRA_USERNAME = ""
JIRA_PASSWORD = ""

# 最終的に出力するファイル名を入力する
OUTPUT_FILE = "Sprint188.json"

target_sprint_no = 'Sprint188'

# データ出力対象のスプリント情報およびサブタスク情報を取得するためのURLを入力する
# 2414の部分はJiraボードによって異なるので、自チームのボードIDに置き換える
sprint_info_url  = "https://agile.kddi.com/jira/rest/greenhopper/1.0/xboard/work/allData.json?rapidViewId=2414&selectedProjectKey=EVASS"
# jql部分は自チームのカンバンの設定にあわせて調整する
subtask_info_url = f'https://agile.kddi.com/jira/rest/api/2/search?maxResults=300&jql=project%20%3D%20EVASS%20AND%20labels%20%3D%22%E9%87%91%E5%A4%AA%E9%83%8E%22%20AND%20%E3%82%B9%E3%83%97%E3%83%AA%E3%83%B3%E3%83%88%20%3D%20%22%E9%87%91%E5%A4%AA%E9%83%8E{target_sprint_no}%22%20AND%20labels%20not%20in%20(Impediment)%20AND%20summary%20!~%20template%20AND%20type%20!%3D%20Bug%20ORDER%20BY%20%E3%83%A9%E3%83%B3%E3%82%AF&expand=changelog'

# 使用者の情報を入力する↑ここまで

def main(): 

    STATUS_TODO = "ToDo"
    STATUS_ASSIGNED = "Assigned"
    STATUS_DONE = "Done"

    sprint_info_response = requests.get(
        url=sprint_info_url,
        auth=(JIRA_USERNAME, JIRA_PASSWORD)
    )
    sprint_info_list = sprint_info_response.json().get("sprintsData").get("sprints")
    sprint_info_json = sprint_info_list[0]

    subtask_info_response = requests.get(
        url=subtask_info_url,
        auth=(JIRA_USERNAME, JIRA_PASSWORD)
    )

    subtask_info_json = subtask_info_response.json()

    # 最終的にファイルに出力する情報をこの辞書に格納していく
    output_json = {}

    if sprint_info_json:
        sprint_name = sprint_info_json.get("name")
        # Sprint番号をSprint名から取得する
        sprint_number = int(re.sub('[^0-9]+', '', sprint_name))
        if sprint_number is None:
            sprint_number = 0
        sprint_start_date_datetime = datetime.datetime.strptime(sprint_info_json.get("startDate"), '%Y/%m/%d %H:%M')
        sprint_end_date_datetime = datetime.datetime.strptime(sprint_info_json.get("endDate"), '%Y/%m/%d %H:%M')
        output_json["metaData"] = {"sprintNo": sprint_number, "beginDete": sprint_start_date_datetime.strftime('%Y-%m-%dT%H:%M:%S.000'), "endDate": sprint_end_date_datetime.strftime('%Y-%m-%dT%H:%M:%S.000')}

    issues = subtask_info_json.get("issues")

    backlogs = []
    subtasks = []

    for issue in issues:
        fields = issue.get("fields")
        if fields:
            parent = fields.get("parent")
            if parent is None:
                backlog = {}
                backlog["name"] = fields.get("summary")
                backlog["key"] = issue.get("key")
                backlog["subtasks"] = []
                backlogs.append(backlog)
            else:
                subtask = {}
                subtask["name"] = fields.get("summary")
                subtask["parent_key"] = parent.get("key")

                assignees = fields.get("customfield_10205")
                assignee = fields.get("assignee")
                if assignee:
                    subtask_assigee_name = assignee.get("displayName")
                    if assignees:
                        subtask_assignees_name_list = []
                        for assignee in assignees:
                            subtask_assignees_name_list.append(assignee.get("displayName"))
                        subtask_assignee_name_str = subtask_assigee_name + "," + ",".join(subtask_assignees_name_list)
                    else:
                        subtask_assignee_name_str = subtask_assigee_name
                else:
                    subtask_assignee_name_str = "未割り当て"

                subtask["pic"] = subtask_assignee_name_str.replace('\u3000', '')

                change_logs = issue.get("changelog")
                if change_logs:
                    histories = change_logs.get("histories")
                    for history in histories:
                        items = history.get("items")
                        for item in items:
                            field = item.get("field")
                            # サブタスクのステータス変更に関わる履歴のみ情報を抽出する
                            if field == "status":
                                status_change_datetime = history.get("created")
                                fromString = item.get("fromString")
                                toString = item.get("toString")
                                if fromString:
                                    subtask_from_string = fromString                                    
                                else:
                                    subtask_from_string = "なし"
                                if toString:
                                    subtask_to_string = toString
                                else:
                                    subtask_to_string = "なし"
                                # TODOやAssignedからDone以外のステータスに変更された場合は開始日を設定する
                                if (subtask_from_string == STATUS_TODO or subtask_from_string == STATUS_ASSIGNED) and subtask_to_string != STATUS_DONE:
                                    subtask["start"] = status_change_datetime
                                # DONEにステータスが変更された場合は終了日を設定する
                                if (subtask_to_string == STATUS_DONE):
                                    subtask["end"] = status_change_datetime
                subtasks.append(subtask)
    
    for backlog in backlogs:
        for subtask in subtasks:
            if subtask["parent_key"] == backlog["key"]:
                if subtask.get("start") and subtask.get("end"):
                    # UIに食わせたときにエラーになるのでタイムゾーンを削除する
                    subtask["start"] = subtask["start"].replace('+0900', '')
                    subtask["end"] = subtask["end"].replace('+0900', '')
                    backlog["subtasks"].append(subtask)

    # 余計な属性が残っていると出力データをUIに食わせたときにエラーになるので削除する
        if backlog.get("key"):
            del backlog["key"]

    # 余計な属性が残っていると出力データをUIに食わせたときにエラーになるので削除する
    for subtask in subtasks:
        if subtask["parent_key"]:
            del subtask["parent_key"]


    if backlogs:
        output_json["backlogs"] = backlogs

    f= open(OUTPUT_FILE, 'w')
    f.write(json.dumps(output_json, ensure_ascii=False, indent=4))


if __name__ == '__main__':
    main()
