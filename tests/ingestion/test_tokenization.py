import json

import pytest
from tokenizers import Tokenizer

from magi.ingestion.domain import TokenCounter
from magi.ingestion.infrastructure import HuggingFaceTokenCounter, HuggingFaceTokenizerConfig


def test_hugging_face_counter_uses_supplied_tokenizer() -> None:
    tokenizer = Tokenizer.from_str(
        json.dumps(
            {
                "version": "1.0",
                "truncation": None,
                "padding": None,
                "added_tokens": [],
                "normalizer": None,
                "pre_tokenizer": {"type": "Whitespace"},
                "post_processor": None,
                "decoder": None,
                "model": {
                    "type": "WordLevel",
                    "vocab": {"[UNK]": 0, "hello": 1, "world": 2},
                    "unk_token": "[UNK]",
                },
            }
        )
    )
    counter: TokenCounter = HuggingFaceTokenCounter(tokenizer)

    assert counter.count_tokens("hello world") == 2


@pytest.mark.parametrize(
    ("model_id", "model_revision"),
    [("", "revision"), ("model", ""), (" ", "revision"), ("model", " ")],
)
def test_tokenizer_config_requires_pinned_identity(
    model_id: str,
    model_revision: str,
) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        HuggingFaceTokenizerConfig(model_id=model_id, model_revision=model_revision)
