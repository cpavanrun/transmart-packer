import logging

import requests
from celery.exceptions import Ignore
from ..table_transformations.patient_diagnosis_biosource_biomaterial import from_obs_json_to_export_pdbb_df
from ..table_transformations.utils import filter_rows

from packer.task_status import Status
from ..config import transmart_config
from ..tasks import BaseDataTask, app
from ..export import save

logger = logging.getLogger(__name__)


@app.task(bind=True, base=BaseDataTask)
def patient_diagnosis_biosource_biomaterial_export(self: BaseDataTask, constraint, **params):
    """
    Reformat hypercube data into a specific export file.
    Export table with the following IDs: Patient, Diagnosis, Biosource, Biomaterial

    :param self: Required for bind to BaseDataTask
    :param constraint: should be in job_parameters.
    :param params: optional in job_parameters.
    """
    obs_json = observations_json(self, constraint)
    self.update_status(Status.RUNNING, 'Observations gotten, transforming.')
    export_df = from_obs_json_to_export_pdbb_df(obs_json)
    if 'row_filter' in params:
        self.update_status(Status.RUNNING, 'Observations gotten, transforming.')
        row_filter_constraint = params['row_filter']
        row_filter_obs_json = observations_json(self, row_filter_constraint)
        row_export_df = from_obs_json_to_export_pdbb_df(row_filter_obs_json)
        export_df = filter_rows(export_df, row_export_df)

    custom_name = params['custom_name']
    self.update_status(Status.RUNNING, 'Writing export to disk.')
    save(export_df, self.task_id, custom_name)
    logger.info(f'Stored to disk: {self.task_id}')


def observations_json(self, constraint):
    '''
    :param self: Required for bind to BaseDataTask
    :param constraint: transmart API constraint to request
    :return: response body (json) of the observation call of transmart API
    '''
    handle = f'{transmart_config.get("host")}/v2/observations'
    self.update_status(Status.FETCHING, f'Getting data from observations from {handle!r}')
    r = requests.post(url=handle,
                      json={'type': 'clinical', 'constraint': constraint},
                      headers={
                          'Authorization': self.request.get('Authorization')
                      })
    if r.status_code == 401:
        logger.error('Export failed. Unauthorized.')
        self.update_status(Status.FAILED, 'Unauthorized.')
        raise Ignore()
    if r.status_code != 200:
        logger.error('Export failed. Error occurred.')
        self.update_status(Status.FAILED, f'Connection error occurred when fetching {handle}. '
                                          f'Response status {r.status_code}')
        raise Ignore()
    return r.json()
