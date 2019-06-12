import boto3
import os
import unittest

from unittest import mock
from unittest.mock import MagicMock

from sosw.app import Processor, LambdaGlobals, get_lambda_handler
from sosw.components.sns import SnsManager
from sosw.components.siblings import SiblingsManager


os.environ["STAGE"] = "test"
os.environ["autotest"] = "True"


class app_UnitTestCase(unittest.TestCase):
    TEST_CONFIG = {'test': True}


    def setUp(self):
        pass


    def tearDown(self):
        try:
            del (os.environ['AWS_LAMBDA_FUNCTION_NAME'])
        except:
            pass


    @mock.patch("boto3.client")
    def test_app_init(self, mock_boto_client):
        Processor(custom_config=self.TEST_CONFIG)
        self.assertTrue(True)


    @mock.patch("boto3.client")
    def test_app_init__fails_without_custom_config(self, mock_boto_client):
        self.assertRaises(RuntimeError, Processor)


    @mock.patch("boto3.client")
    def test_app_init__with_some_clients(self, mock_boto_client):
        custom_config = {
            'init_clients': ['Sns', 'Siblings'],
            'siblings_config': {
                "test": True
            }
        }

        processor = Processor(custom_config=custom_config)
        self.assertIsInstance(getattr(processor, 'sns_client'), SnsManager,
                              "SnsManager was not initialized. Probably boto3 sns instead of it.")
        self.assertIsNotNone(getattr(processor, 'siblings_client'))


    @mock.patch("boto3.client")
    def test_app_init__boto_and_components_custom_clients(self, mock_boto_client):
        custom_config = {
            'init_clients': ['dynamodb', 'Siblings'],
            'siblings_config': {
                "test": True
            }
        }

        processor = Processor(custom_config=custom_config)
        self.assertIsInstance(getattr(processor, 'siblings_client'), SiblingsManager)

        # Clients of boto3 will not be exactly of same type (something dynamic in boto3), so we can't compare classes.
        # Let us assume that checking the class_name is enough for this test.
        self.assertEqual(str(type(getattr(processor, 'dynamodb_client'))), str(type(boto3.client('dynamodb'))))


    @mock.patch("boto3.client")
    def test_app_init__with_some_invalid_client(self, mock_boto_client):
        custom_config = {
            'init_clients': ['NotExists']
        }
        Processor(custom_config=custom_config)
        mock_boto_client.assert_called_with('not_exists')


    @mock.patch("sosw.app.get_config")
    def test_app_calls_get_config(self, mock_ssm):

        mock_ssm.return_value = {'mock': 'called'}
        os.environ['AWS_LAMBDA_FUNCTION_NAME'] = 'test_func'

        Processor(custom_config=self.TEST_CONFIG)
        mock_ssm.assert_called_once_with('test_func_config')


    # @unittest.skip("https://github.com/bimpression/sosw/issues/40")
    # def test__account(self):
    #     raise NotImplementedError
    #
    #
    # @unittest.skip("https://github.com/bimpression/sosw/issues/40")
    # def test__region(self):
    #     raise NotImplementedError


    def test_lambda_handler(self):

        class Child(Processor):
            def __call__(self, event):
                super().__call__(event)
                return event.get('k')

        global_vars = LambdaGlobals()
        self.assertIsNone(global_vars.processor)
        self.assertIsNone(global_vars.lambda_context)

        lambda_handler = get_lambda_handler(Child, global_vars, self.TEST_CONFIG)
        self.assertIsNotNone(lambda_handler)

        for i in range(3):
            result = lambda_handler(event={'k': 'success'}, context={'context': 'test'})
            self.assertEqual(type(global_vars.processor), Child)
            self.assertEqual(global_vars.lambda_context, {'context': 'test'})
            self.assertEqual(result, 'success')
            self.assertEqual(global_vars.processor.stats['total_processor_calls'], i + 1)
            self.assertEqual(global_vars.processor.stats['total_calls_register_clients'], 1)
