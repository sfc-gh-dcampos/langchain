import asyncio
import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models import llms as base
from tenacity import wait_none

from langchain_openai.llms import OpenAI
from langchain_openai.utils import is_openai_v1

os.environ["OPENAI_API_KEY"] = "foo"


def _openai_v1_installed() -> bool:
    try:
        return is_openai_v1()
    except Exception as _:
        return False


def test_openai_model_param() -> None:
    llm = OpenAI(model="foo")
    assert llm.model_name == "foo"
    llm = OpenAI(model_name="foo")
    assert llm.model_name == "foo"


def test_openai_model_kwargs() -> None:
    llm = OpenAI(model_kwargs={"foo": "bar"})
    assert llm.model_kwargs == {"foo": "bar"}


def test_openai_invalid_model_kwargs() -> None:
    with pytest.raises(ValueError):
        OpenAI(model_kwargs={"model_name": "foo"})


def test_openai_incorrect_field() -> None:
    with pytest.warns(match="not default parameter"):
        llm = OpenAI(foo="bar")
    assert llm.model_kwargs == {"foo": "bar"}


@pytest.fixture
def mock_completion() -> dict:
    return {
        "id": "cmpl-3evkmQda5Hu7fcZavknQda3SQ",
        "object": "text_completion",
        "created": 1689989000,
        "model": "text-davinci-003",
        "choices": [
            {"text": "Bar Baz", "index": 0, "logprobs": None, "finish_reason": "length"}
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
    }


def _patched_retry(*args: Any, **kwargs: Any) -> Any:
    """Patched retry for unit tests that does not wait."""
    from tenacity import retry

    assert "wait" in kwargs
    kwargs["wait"] = wait_none()
    r = retry(*args, **kwargs)
    return r


@pytest.mark.skipif(
    _openai_v1_installed(), reason="Retries only handled by LangChain for openai<1"
)
def test_openai_retries(mock_completion: dict) -> None:
    llm = OpenAI()
    mock_client = MagicMock()
    completed = False
    raised = False
    import openai

    def raise_once(*args: Any, **kwargs: Any) -> Any:
        nonlocal completed, raised
        if not raised:
            raised = True
            raise openai.error.APIError
        completed = True
        return mock_completion

    mock_client.create = raise_once

    # Patch the retry to avoid waiting during a unit test
    with patch.object(base, "retry", _patched_retry):
        with patch.object(
            llm,
            "client",
            mock_client,
        ):
            res = llm.predict("bar")
            assert res == "Bar Baz"
    assert completed
    assert raised


@pytest.mark.skipif(
    _openai_v1_installed(), reason="Retries only handled by LangChain for openai<1"
)
async def test_openai_async_retries(mock_completion: dict) -> None:
    llm = OpenAI()
    mock_client = MagicMock()
    completed = False
    raised = False
    import openai

    async def araise_once(*args: Any, **kwargs: Any) -> Any:
        nonlocal completed, raised
        if not raised:
            raised = True
            raise openai.error.APIError
        await asyncio.sleep(0)
        completed = True
        return mock_completion

    mock_client.acreate = araise_once
    # Patch the retry to avoid waiting during a unit test
    with patch.object(base, "retry", _patched_retry):
        with patch.object(
            llm,
            "client",
            mock_client,
        ):
            res = await llm.apredict("bar")
            assert res == "Bar Baz"
    assert completed
    assert raised
