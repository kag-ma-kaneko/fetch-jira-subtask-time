#!/usr/bin/env python3

import json
from collections import defaultdict
from datetime import datetime

# ラベルと工程のマッピング
LABEL_TO_STAGE = {
    "要求定義": ["要求定義"],
    "設計": ["設計"],
    "実装": ["実装"],
    "試験": ["試験"],
    "リリース": ["リリース"],
}


def get_stage_from_labels(labels):
    """
    サブタスクのラベルから対応する工程を特定する
    """
    for stage, valid_labels in LABEL_TO_STAGE.items():
        if any(label in valid_labels for label in labels):
            return stage
    return None  # マッチする工程がない場合


def calculate_stage_times_by_pbi(backlogs):
    """
    各PBI内でサブタスクを工程ごとにグルーピングし、工程の所要時間を計算する
    """
    results = []

    for backlog in backlogs:
        pbi_name = backlog.get("name", "Unnamed PBI")
        subtasks = backlog.get("subtasks", [])
        stage_times = defaultdict(
            lambda: {"total_duration": 0, "start": None, "end": None}
        )

        # サブタスクを工程ごとにグルーピング
        for subtask in subtasks:
            labels = subtask.get("label", [])
            stage = get_stage_from_labels(labels)

            if not stage:
                continue  # 該当する工程がない場合はスキップ

            start_time = subtask.get("start")
            end_time = subtask.get("end")

            # 開始時間と終了時間の更新
            if start_time:
                if (
                    not stage_times[stage]["start"]
                    or start_time < stage_times[stage]["start"]
                ):
                    stage_times[stage]["start"] = start_time
            if end_time:
                if (
                    not stage_times[stage]["end"]
                    or end_time > stage_times[stage]["end"]
                ):
                    stage_times[stage]["end"] = end_time

        # PBIごとの結果を追加
        formatted_stages = {}
        for stage, times in stage_times.items():
            if times["start"] and times["end"]:
                start = datetime.strptime(times["start"], "%Y-%m-%dT%H:%M:%S.%f%z")
                end = datetime.strptime(times["end"], "%Y-%m-%dT%H:%M:%S.%f%z")
                total_minutes = (end - start).total_seconds() / 60
                formatted_stages[stage] = {
                    "start": times["start"],
                    "end": times["end"],
                    "total_doing_time": total_minutes,
                }

        results.append({"pbi_name": pbi_name, "stages": formatted_stages})

    return results


# メイン処理
def main():
    # データを読み込む
    with open("peach-sprint216.json", "r") as f:
        data = json.load(f)

    # PBIごとのバリューストリームを計算
    value_stream_by_pbi = calculate_stage_times_by_pbi(data["backlogs"])

    # 結果を出力
    print("PBIごとの工程ごとの時間:")
    for pbi in value_stream_by_pbi:
        print(f"PBI: {pbi['pbi_name']}")
        for stage, details in pbi["stages"].items():
            print(f"  開始時刻: {details['start']}")
            print(f"  終了時刻: {details['end']}")
            print(f"  {stage}: {details['total_doing_time']}分")
        print()

    # 必要に応じてファイルに保存
    with open("value_stream_by_pbi.json", "w") as f:
        json.dump(value_stream_by_pbi, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()