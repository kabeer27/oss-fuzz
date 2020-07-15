# Copyright 2020 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################
"""Unit tests for Cloud Function request builds which builds projects."""

import datetime
import os
import unittest
from unittest import mock

import requests

from google.cloud import ndb

from datastore_entities import Project
from request_build import get_build_steps
import test_utils


# pylint: disable=arguments-differ
class SpoofedDatetime(datetime.datetime):
  """Mocking Datetime class for now() function."""

  @classmethod
  def now(cls):
    return datetime.datetime(2020, 1, 1, 0, 0, 0)


class TestRequestBuilds(unittest.TestCase):
  """Unit tests for sync."""

  @classmethod
  def setUpClass(cls):
    ds_emulator = test_utils.start_datastore_emulator()
    test_utils._wait_for_emulator_ready(ds_emulator, 'datastore',
                                        test_utils._DATASTORE_READY_INDICATOR)
    os.environ['DATASTORE_EMULATOR_HOST'] = 'localhost:' + str(
        test_utils._DATASTORE_EMULATOR_PORT)
    os.environ['GOOGLE_CLOUD_PROJECT'] = test_utils._TEST_PROJECT_ID
    os.environ['DATASTORE_DATASET'] = test_utils._TEST_PROJECT_ID
    os.environ['GCP_PROJECT'] = 'test-project'
    os.environ['FUNCTION_REGION'] = 'us-central1'

  def setUp(self):
    req = requests.post('http://localhost:{}/reset'.format(
        test_utils._DATASTORE_EMULATOR_PORT))
    req.raise_for_status()

  @mock.patch('build_lib.get_signed_url', return_value='test_url')
  @mock.patch('datetime.datetime')
  def test_get_build_steps(self, mocked_url, mocked_time):
    """Test for get_build_steps."""
    del mocked_url, mocked_time
    datetime.datetime = SpoofedDatetime
    project_yaml_contents = 'language: c++\nsanitizers:\n  - address\narchitectures:\n  - x86_64\n'
    image_project = 'oss-fuzz'
    base_images_project = 'oss-fuzz-base'
    testcase_path = os.path.join(os.path.dirname(__file__),
                                 'expected_build_steps.txt')
    with open(testcase_path) as testcase_file:
      expected_build_steps = testcase_file.readline()

    with ndb.Client().context():
      Project(name='test-project',
              project_yaml_contents=project_yaml_contents,
              dockerfile_contents='test line').put()

    build_steps = get_build_steps('test-project', image_project,
                                  base_images_project)
    self.assertEqual(str(build_steps), expected_build_steps)

  def test_get_build_steps_no_project(self):
    """Test for when project isn't available in datastore."""
    with ndb.Client().context():
      self.assertRaises(RuntimeError, get_build_steps, 'test-project',
                        'oss-fuzz', 'oss-fuzz-base')

  @classmethod
  def tearDownClass(cls):
    # TODO: replace this with a cleaner way of killing the process
    os.system('pkill -f datastore')


if __name__ == '__main__':
  unittest.main(exit=False)
