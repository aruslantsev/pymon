import json

import pandas as pd


def read_log(logfile):
    values = []
    dates = []
    with open(logfile, 'r') as logfile:
        for line in logfile.readlines():
            data = json.loads(line)
            date = list(data.keys())[0]
            info = list(data.values())[0]
            dates.append(date)
            values.append(info)

        return pd.concat([pd.DataFrame(dates, columns=['datetime']), pd.DataFrame(values)], axis=1)


def expand_column(df, column, deep=True):
    if isinstance(df[column][0], dict):
        sub_df = df[column].apply(pd.Series)
        sub_df.columns = [column + '_' + col for col in sub_df.columns]
        sub_df_columns = sub_df.columns
        if deep:
            for col in sub_df_columns:
                if isinstance(sub_df[col][0], dict):
                    sub_df = expand_column(sub_df, col, deep=True)
        return pd.concat([df.drop(column, axis=1).copy(), sub_df], axis=1)
    else:
        return df.copy()


def expand_smart_attrs(df, column):
    row_dfs = []
    for _, row in df.iterrows():
        smart_array = row[column]
        attr_names = []
        attr_values = []
        for item in smart_array:
            attr_names.append(str(item['num']) + '_' + item['name'])
            attr_values.append(item['value'])

        row_dfs.append(pd.DataFrame([attr_values], columns=attr_names))

    smart_attrs_df = pd.concat(row_dfs)
    smart_attrs_df.columns = [column + '_' + col for col in smart_attrs_df.columns]
    return pd.concat([
        df.drop(column, axis=1).copy().reset_index(drop=True),
        smart_attrs_df.reset_index(drop=True)],
        axis=1)


def parse_log(logfile):
    device_stats = read_log(logfile)
    device_stats_expanded = device_stats.copy()
    device_stats_expanded_columns = device_stats_expanded.columns
    for column in device_stats_expanded_columns:
        if column != 'datetime':
            device_stats_expanded = expand_column(device_stats_expanded, column)
    device_stats_full = device_stats_expanded.copy()
    device_stats_full_columns = device_stats_full.columns
    for column in device_stats_full_columns:
        if ('SMART' in column) and ('attributes' in column):
            device_stats_full = expand_smart_attrs(device_stats_full, column)

    return device_stats_full
