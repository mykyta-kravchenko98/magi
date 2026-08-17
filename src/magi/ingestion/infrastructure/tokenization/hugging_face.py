"""Token counting with a tokenizer artifact pinned on Hugging Face Hub."""

from dataclasses import dataclass

from tokenizers import Tokenizer


@dataclass(frozen=True, slots=True, kw_only=True)
class HuggingFaceTokenizerConfig:
    model_id: str
    model_revision: str

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.model_revision.strip():
            raise ValueError("model_id and model_revision must not be blank")


class HuggingFaceTokenCounter:
    """Count tokens exactly as described by the pinned tokenizer.json artifact."""

    def __init__(self, tokenizer: Tokenizer) -> None:
        self._tokenizer = tokenizer

    @classmethod
    def from_pretrained(cls, config: HuggingFaceTokenizerConfig) -> "HuggingFaceTokenCounter":
        tokenizer = Tokenizer.from_pretrained(
            config.model_id,
            revision=config.model_revision,
        )
        return cls(tokenizer)

    def count_tokens(self, text: str) -> int:
        return len(self._tokenizer.encode(text, add_special_tokens=True).ids)
