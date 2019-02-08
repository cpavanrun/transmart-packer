import re

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)
try:
    from transmart.api.v2.data_structures import ObservationSet
except ImportError as e:
    logging.warning(f'Import errors for {__file__!r}: {str(e)}')

DATE_FORMAT = '%Y-%m-%d'
ID_COLUMNS = ['Patient Id', 'Diagnosis Id', 'Biosource Id', 'Biomaterial Id']


def from_obs_json_to_export_pdbb_df(obs_json):
    """
    :param obs_json: json returned by transmart v2/observations call
    :return: data frame that has 4 (patient, diagnosis, biosource, biomaterial) index columns.
    The rest of columns represent concepts (aka variables)
    """

    obs = ObservationSet(obs_json).dataframe
    pdbb_df = from_obs_df_to_pdbb_df(obs)
    renamded_pdbb_df = pdbb_df.raname(index=str, columns=_concept_path_to_name(obs))
    formated_pdbb_df = format_columns(indexed_pdbb_df)
    return formated_pdbb_df


def from_obs_df_to_pdbb_df(obs):
    if obs.empty:
        logger.warn('Retrieved hypercube is empty! Exporting empty result.')
        return obs
    # order rows by concept_paths:
    # 1)Patient -> 2)Diagnosis -> 3)Biosource -> 4)Biomaterial -> 5)Studies
    obs.rename(index=str, columns={'patient.trial': 'Patient Id'}, inplace=True)
    obs.sort_values(by=['concept.conceptPath'], inplace=True)
    concept_path_col = obs['concept.conceptPath']
    unq_concept_paths_ord = concept_path_col.unique().tolist()
    logger.info('Reformatting columns...')
    id_columns = _detect_index_columns(obs)
    obs = _reformat_columns(obs, id_columns)
    # transform concept rows to column headers
    obs_pivot = _concepts_row_to_columns(obs)
    # propagate data to lower levels and display only rows that represent the lowest level
    obs_pivot = _merge_redundant_rows(obs_pivot, id_columns)
    # fix columns order
    obs_pivot = obs_pivot[id_columns + unq_concept_paths_ord]
    obs_pivot.set_index(id_columns, inplace=True)
    return obs_pivot


def _concept_path_to_name(df):
    return dict(zip(df['concept.conceptPath'], df['concept.name']))


def _detect_index_columns(df):
    columns = list(df.columns.values)
    return [id_column for id_column in ID_COLUMNS if id_column in columns]

def format_columns(df):
    """
    :param df: pandas dataframe with various data types of columns
    :return: modified data frame with all collumns converted to formatted string
    """
    result_df = pd.DataFrame()
    for col_num, col in enumerate(df.columns):
        # update datetime fields
        if re.match(r'.*\bdate\b.*', col, flags=re.IGNORECASE):
            result_df[col_num] = df.iloc[:, col_num].apply(_to_datetime)
        elif np.issubdtype(df.iloc[:, col_num].dtype, np.number):
            result_df[col_num] = df.iloc[:, col_num].apply(_num_to_str)
        else:
            result_df[col_num] = df.iloc[:, col_num]
    result_df = result_df.fillna('')
    result_df.columns=df.columns
    return result_df


def _num_to_str(x):
    if pd.isnull(x):
        return ''
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def _merge_redundant_rows(data, id_columns):
    if data.empty:
        return
    # sort rows by identifying columns, merging of rows strongly depends on sorting
    rows = data.sort_values(id_columns, na_position='last').to_dict('records')
    result_rows = [rows[0]]
    for row in rows[1:]:
        row_copied = False
        for result_row in reversed(result_rows):
            if _is_ancestor_row(row, result_row, id_columns):
                _copy_missing_value_to_descendant_row(row, result_row, id_columns)
                row_copied = True
            else:
                break
        if not row_copied:
            result_rows.append(row)
    return pd.DataFrame(result_rows)


def _is_ancestor_row(ancestor_row_candidate, descendant_row_candidate, id_columns):
    for id_column in id_columns:
        if pd.isnull(ancestor_row_candidate[id_column]):
            break
        if ancestor_row_candidate[id_column] != descendant_row_candidate[id_column]:
            return False
    return True


def _copy_missing_value_to_descendant_row(ancestor_row, descendant_row, id_columns):
    for column, value in ancestor_row.items():
        if column in id_columns or pd.isnull(value):
            continue
        if column not in descendant_row or pd.isnull(descendant_row[column]):
            descendant_row[column] = ancestor_row[column]


def _to_datetime(date_str, string_format=DATE_FORMAT):
    if pd.notnull(date_str) and date_str is not None and date_str != '':
        try:
            return pd.to_datetime(date_str).strftime(string_format)
        except:
            return date_str
    else:
        return date_str


def _reformat_columns(obs, id_columns):
    # rename columns and set indexes
    obs.reset_index(inplace=True)
    headers = np.append(id_columns, 'concept.conceptPath')

    # prepare 'value' column
    if {'stringValue', 'numericValue'}.issubset(obs.columns):
        # merge stringValue and numericValue into value column
        obs['value'] = obs['stringValue'].fillna(obs['numericValue'])
        obs.drop(['stringValue', 'numericValue'], axis=1, inplace=True)
    elif 'stringValue' in obs:
        obs.rename(columns={"stringValue": "value"}, inplace=True)
    elif 'numericValue' in obs:
        obs.rename(columns={"numericValue": "value"}, inplace=True)
    else:
        obs['value'] = ""
    obs = obs.set_index(list(headers), append=True)[['value']]
    return obs


def _concepts_row_to_columns(obs):
    # use unstack to move the last level of the index to column names
    obs_pivot = obs.unstack(level=-1)
    # update column names by dropping value level
    obs_pivot.columns = obs_pivot.columns.droplevel(level=0)
    # fix indexes
    obs_pivot.reset_index(inplace=True)
    obs_pivot.drop(obs_pivot.columns[[0]], axis=1, inplace=True)
    return obs_pivot
