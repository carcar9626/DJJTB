#!/usr/bin/env python3
import os
import csv
import datetime
from pathlib import Path
from collections import defaultdict

def prompt_folder():
    folder = input("📂 Enter path to folder containing JoyTag .txt files: ").strip()
    return Path(folder).expanduser().resolve()

def collect_txt_files(folder: Path):
    return list(folder.rglob("*.txt"))

def parse_tag_file(file_path):
    tags = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().rsplit(" ", 1)
            if len(parts) == 2:
                tag, conf = parts
                conf = conf.rstrip("%")
                try:
                    tags.append((tag, float(conf)))
                except ValueError:
                    continue
    return tags

def analyze_tags(txt_files):
    tag_data = defaultdict(lambda: {"count": 0, "total_conf": 0.0})
    total_tag_entries = 0
    total_confidence_sum = 0.0

    for file_path in txt_files:
        seen_tags = set()
        tags = parse_tag_file(file_path)
        total_tag_entries += len(tags)
        for tag, conf in tags:
            if tag not in seen_tags:
                tag_data[tag]["count"] += 1
                tag_data[tag]["total_conf"] += conf
                seen_tags.add(tag)
            total_confidence_sum += conf

    return tag_data, total_tag_entries, total_confidence_sum

def export_csv(tag_data, total_files, total_tag_entries, total_confidence_sum, output_folder):
    today = datetime.date.today().isoformat()
    output_path = output_folder / f"tag_summary_{today}.csv"
    
    # Step 1: prepare raw stats
    rows = []
    for tag, data in tag_data.items():
        avg_conf = round(data["total_conf"] / data["count"], 2)
        rows.append({
            "tag": tag,
            "frequency": avg_conf,
            "count": data["count"],
        })

    # Step 2: assign ranks by image count
    rows.sort(key=lambda x: (-x["count"], x["tag"]))
    for idx, row in enumerate(rows):
        row["rank_by_count"] = idx + 1

    # Step 3: assign ranks by average confidence
    rows.sort(key=lambda x: (-x["frequency"], x["tag"]))
    for idx, row in enumerate(rows):
        row["rank_by_frequency"] = idx + 1

    # Step 4: write to CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "tag",
            "frequency (%)",
            "number of images tagged",
            "rank (by image count)",
            "rank (by frequency)"
        ])
        for row in rows:
            writer.writerow([
                row["tag"],
                f'{row["frequency"]}%',
                row["count"],
                row["rank_by_count"],
                row["rank_by_frequency"]
            ])

        # Summary block as comment rows
        avg_tags_per_image = round(total_tag_entries / total_files, 2)
        avg_conf_all = round(total_confidence_sum / total_tag_entries, 2) if total_tag_entries else 0.0

        writer.writerow([])
        writer.writerow(["# Summary"])
        writer.writerow([f"# Total images processed: {total_files}"])
        writer.writerow([f"# Total unique tags: {len(tag_data)}"])
        writer.writerow([f"# Total tag entries: {total_tag_entries}"])
        writer.writerow([f"# Average tags per image: {avg_tags_per_image}"])
        writer.writerow([f"# Average confidence across all tags: {avg_conf_all}%"])

    print(f"\n✅ Summary CSV saved to:\n{output_path}")

def main():
    folder = prompt_folder()
    if not folder.exists():
        print("❌ Folder does not exist.")
        return

    txt_files = collect_txt_files(folder)
    if not txt_files:
        print("❌ No .txt files found.")
        return

    print(f"🔍 Found {len(txt_files)} .txt files. Processing...")

    tag_data, total_tag_entries, total_confidence_sum = analyze_tags(txt_files)
    export_csv(tag_data, len(txt_files), total_tag_entries, total_confidence_sum, folder)

if __name__ == "__main__":
    main()