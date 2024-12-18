#!/usr/bin/env python3

import argparse
import json
from collections import defaultdict
from datetime import datetime

# ラベルと工程のマッピング
LABEL_TO_STAGE = {
    "要求定義": ["要求定義"],
    "設計": ["設計"],
    "実装": ["実装"],
    "試験": ["試験", "テスト"],
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


def safe_parse_datetime(date_str, default="2030-01-01T00:00:00.000+0000"):
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    except (ValueError, TypeError):  # TypeErrorはNoneの場合
        return datetime.strptime(default, "%Y-%m-%dT%H:%M:%S.%f%z")


def calculate_stage_times_by_pbi(backlogs):
    """
    各PBI内でサブタスクを工程ごとにグルーピングし、工程の所要時間を計算する
    """
    results = []

    for backlog in backlogs:
        pbi_name = backlog.get("name", "Unnamed PBI")
        pbi_start = safe_parse_datetime(backlog.get("start"))
        pbi_end = safe_parse_datetime(backlog.get("end"))
        pbi_minutes = int((pbi_end - pbi_start).total_seconds() / 60)

        subtasks = backlog.get("subtasks", [])
        stage_times = defaultdict(
            lambda: {"total_duration": 0, "start": None, "end": None}
        )

        # サブタスクを工程ごとにグルーピング
        for subtask in subtasks:
            labels = subtask.get("labels", [])
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
                total_minutes = int((end - start).total_seconds() / 60)
                formatted_stages[stage] = {
                    "start": times["start"],
                    "end": times["end"],
                    "total_doing_time": total_minutes,
                }

        results.append(
            {
                "pbi_name": pbi_name,
                "pbi_minutes": pbi_minutes,
                "pbi_start": backlog.get("start"),
                "pbi_end": backlog.get("end"),
                "stages": formatted_stages,
            }
        )

    return results


# メイン処理
def main():

    # 引数を解析
    parser = argparse.ArgumentParser(description="PBI情報を処理するスクリプト")
    parser.add_argument(
        "input_file", type=str, help="処理対象のJSONファイルのパスを指定してください"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="output.json",
        help="結果を保存するJSONファイルのパスを指定してください (デフォルト: output.json)",
    )
    args = parser.parse_args()

    # データを読み込む
    with open(args.input_file, "r") as f:
        data = json.load(f)

    # PBIごとのバリューストリームを計算
    value_stream_by_pbi = calculate_stage_times_by_pbi(data["backlogs"])

    # 結果を出力
    print("PBIごとの工程ごとの時間:")
    for pbi in value_stream_by_pbi:
        print(f"PBI: {pbi['pbi_name']}")
        print(f"  総所要時間: {pbi['pbi_minutes']}分")
        print(f"  開始時刻: {pbi['pbi_start']}")
        print(f"  終了時刻: {pbi['pbi_end']}")
        for stage, details in pbi["stages"].items():
            print(f"    {stage}: {details['total_doing_time']}分")
            print(f"    開始時刻: {details['start']}")
            print(f"    終了時刻: {details['end']}")
            print()
        print()

    # 必要に応じてファイルに保存
    with open(args.output_file, "w") as f:
        json.dump(value_stream_by_pbi, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
