
import csv
import json
import warnings
from collections import OrderedDict

import openpyxl

from attributecode import CRITICAL, Error


def read_csv_rows(location):
    """Read CSV rows as lists of values."""
    with open(location, encoding="utf-8-sig", errors="replace") as csvfile:
        yield from csv.reader(csvfile)


def read_csv_dicts(location):
    """Read CSV rows as dictionaries with normalized column names."""
    with open(location, mode="r", encoding="utf-8-sig", errors="replace") as csvfile:
        return [
            {key.lower().strip(): value for key, value in row.items()}
            for row in csv.DictReader(csvfile)
        ]


def read_json(location):
    """Read and return JSON data without changing its structure."""
    with open(location, encoding="utf-8", errors="replace") as jsonfile:
        return json.load(jsonfile)


def read_excel(location, worksheet=None):
    """Read an Excel worksheet into a list of ordered dictionaries."""
    results = []
    errors = []

    with warnings.catch_warnings(record=True):
        workbook = openpyxl.load_workbook(location)

    if worksheet:
        if worksheet not in workbook.sheetnames:
            raise ValueError(
                "The input worksheet name does not exist: {}".format(worksheet)
            )
        sheet = workbook[worksheet]
    else:
        sheet = workbook.active

    headers = [
        sheet.cell(row=1, column=index).value
        for index in range(1, sheet.max_column + 1)
    ]

    seen = set()
    for header in headers:
        if header in seen:
            msg = "Duplicated column name, {}, detected.".format(header)
            errors.append(Error(CRITICAL, msg))
            return errors, results
        seen.add(header)

    for row in sheet.iter_rows(min_row=2, values_only=True):
        row_dict = OrderedDict(
            (header, value if value is not None else "")
            for header, value in zip(headers, row)
        )
        results.append(row_dict)

    return errors, results


def write_csv(location, data, field_names=None):
    """Write dictionaries to a CSV file or file-like object."""
    if field_names is None:
        field_names = list(data[0].keys()) if data else []

    if hasattr(location, "write"):
        output = location
        writer = csv.DictWriter(output, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(data)
    else:
        with open(
            location, "w", encoding="utf-8", newline="", errors="replace"
        ) as output:
            writer = csv.DictWriter(output, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(data)


def write_json(location, data, indent=2):
    """Write JSON data to a file or file-like object."""
    if hasattr(location, "write"):
        json.dump(data, location, indent=indent)
    else:
        with open(location, "w", encoding="utf-8") as output:
            json.dump(data, output, indent=indent)


def write_excel(location, data):
    """Write dictionaries to an Excel workbook."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active

    headers = list(data[0].keys()) if data else []
    if headers:
        sheet.append(headers)

        for item in data:
            sheet.append([item.get(header) for header in headers])

    workbook.save(location)
