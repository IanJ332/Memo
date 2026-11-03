"""Public synthetic schema checks; no private manifests or scientific requests."""
import pytest
from jsonschema import Draft202012Validator
from memlife.nlip.model_adapter import ALIGNED_SCHEMA

@pytest.mark.parametrize('value,valid', [
    ({'outcome':'ABSTAIN','tool':None,'arguments':None}, True),
    ({'outcome':'ABSTAIN','tool':None,'arguments':{'project_id':'p','recipient':'r'}}, False),
    ({'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'p','recipient':'r'}}, True),
    ({'outcome':'PROPOSE_ACTION','tool':'send_report','arguments':{'project_id':'p\n','recipient':'r'}}, False),
])
def test_public_schema(value, valid):
    Draft202012Validator.check_schema(ALIGNED_SCHEMA)
    assert Draft202012Validator(ALIGNED_SCHEMA).is_valid(value) is valid
