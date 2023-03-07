import csv
import os
import re


def create_csv_dataset(key_value_list: list[tuple[str, str]]):
    dataset_path = 'datasets/dataset.csv'
    os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
    with open(dataset_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(('Date', 'Text'))
        writer.writerows(key_value_list)


def read_data_from_files(root_folder: str = 'row_data') -> list[tuple[str, str]]:
    files_data_by_date = []
    for subdir, dirs, files in os.walk(root_folder):
        for file in files:
            name, _ = os.path.splitext(file)
            with open(os.path.join(subdir, file), encoding='utf-8') as f:
                files_data_by_date.append((name, re.sub('\n', ' ', f.read())))
    return files_data_by_date


def main():
    create_csv_dataset(read_data_from_files())


if __name__ == '__main__':
    main()
