# Decision Model for ARIA: Fixed-Choice, Single-Pass Decisions

Source article: https://nishtahir.com/build-your-own-decision-model/
Author: Nish Tahir (published 10 October 2026)

## Summary

The article demonstrates a lightweight way to make a language model choose among a fixed set of allowed answers (for example A–E), instead of generating a multi-token answer. With a compatible causal language model and tokenizer, run one forward pass over the prompt, inspect the next-token logits, keep only the token IDs corresponding to the allowed choices, and normalize their scores with softmax.

This can make structured, bounded decisions simpler and faster than generating a long response. The example uses Qwen/Qwen3-1.7B and Hugging Face Transformers.

## Important distinction: masking vs. calibration

Restricting choices guarantees only that the selected output belongs to the allowed set, assuming each option maps cleanly to the intended token IDs. It does not guarantee that the selected answer is correct.

The raw softmax values over the allowed choices are not automatically calibrated probabilities of correctness. They indicate relative preference among those candidate tokens under the model's current logits. The article evaluates this issue on a CommonsenseQA sample and demonstrates temperature scaling fitted on evaluation data. Its reported metrics are the author's experiment, not a guarantee that the same temperature or accuracy will transfer to ARIA or another dataset.

Implementation details to verify:
- Ensure each choice is represented by the correct complete token sequence. Taking only the first token from tokenizer.encode(...) is safe only when each option is indeed represented by a single token in the exact prompt context.
- Use a held-out dataset to evaluate accuracy and calibration; do not fit calibration parameters on the final test set.
- Compare against a simple baseline and track per-class performance, confusion matrix, calibration error, and Brier score where appropriate.
- Avoid treating a high score as proof that an action is safe.

## Proposed use in ARIA

Build a small Decision Engine for bounded routing and prioritization, such as:
- Select task type: RESEARCH, CODE, EXPLAIN, or CHAT.
- Select a specialist profile: RESEARCHER, ENGINEER, SECURITY_REVIEWER, or PLANNER.
- Classify a proposed action into SAFE, APPROVAL_REQUIRED, or BLOCKED.
- Choose which of a few pre-approved next steps to recommend.

Use the local Ollama Qwen3:1.7B model as ARIA's current chat model. A Transformers implementation of this article would load a separate model through Hugging Face and may require additional disk, RAM, compatible libraries, and model downloads. On the current 8 GB laptop, do not assume that the Transformers model can run alongside Ollama comfortably. Prototype with a tiny isolated test or use the existing Ollama stack first; measure resource use before integrating another runtime.

## Safety architecture

The model may recommend a category, but it must never be the sole authority for permissions. Enforce the final decision in ordinary application code:
- SAFE: allow only explicitly defined low-risk operations.
- APPROVAL_REQUIRED: pause and ask the owner for confirmation.
- BLOCKED: reject prohibited or unsupported operations.

External messages, deployments, payments, destructive file operations, and credential changes require explicit owner approval. Treat all model outputs as untrusted input and validate the result against an allowlist. A classifier can be wrong, so fail closed when the output is missing, malformed, or uncertain.

## Suggested implementation milestones

1. Create a small labeled dataset of ARIA routing examples.
2. Implement deterministic rule-based routing as a baseline.
3. Prototype constrained-choice inference separately from the current server.
4. Evaluate accuracy, latency, RAM use, and calibration on held-out examples.
5. Add temperature scaling only after measuring calibration on validation data.
6. Integrate as a suggestion layer, while keeping the Permission Engine deterministic and authoritative.
7. Add tests for invalid choices, tokenization edge cases, ambiguous prompts, and fail-closed behavior.

## Status

This document records the research and a proposed design. It does not claim that a decision model has been implemented, trained, calibrated, or benchmarked in ARIA.

## Links

- Article: https://nishtahir.com/build-your-own-decision-model/
- Qwen3-1.7B: https://huggingface.co/Qwen/Qwen3-1.7B
- Transformers documentation: https://huggingface.co/docs/transformers/
- ARIA repository: https://github.com/Miladdeljoui/ARIA
