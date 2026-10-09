# Hugging Face Hub Integration Plan for ARIA

## Goal
Add Hugging Face as ARIA's model and AI-resource catalog, while keeping the current local-first setup and the user's low-resource laptop in mind.

## What Hugging Face adds
The Hugging Face Hub hosts model repositories, datasets, and Spaces. Its Inference Providers can route requests to supported hosted models; availability, rate limits, pricing, and account requirements depend on the selected model/provider and may change.

Official references:
- Hub overview: https://huggingface.co/docs/hub/en/index
- Model repositories: https://huggingface.co/docs/hub/models
- Inference Providers: https://huggingface.co/docs/hub/models-inference
- Inference guide: https://huggingface.co/docs/huggingface_hub/main/guides/inference

## Proposed ARIA architecture
1. Local default: Ollama + qwen3:1.7b for basic chat when available.
2. Optional remote model: Hugging Face Inference Providers through the official `huggingface_hub.InferenceClient`, only when internet is available and the owner has configured a token.
3. Fallback: if remote inference fails or no token is configured, return to the local Ollama model.
4. Keep model selection explicit and record which backend answered, without logging prompts or secrets unnecessarily.
5. Treat all model output as untrusted: tool calls go through ARIA's permission engine; never execute model-generated commands automatically.

## Low-resource implementation plan
- Do not download large Transformers/PyTorch model weights to the current 8 GB RAM laptop by default.
- Begin with Hub browsing/model metadata and optional remote inference; keep local Qwen as the fallback.
- Add a small adapter module only after reviewing the current runtime code and tests.
- Read tokens from an environment variable such as `HF_TOKEN`; never commit tokens to GitHub or place them in Android/web client code.
- Start with read-only model discovery and a mock-based test; test live inference only after the owner provides/configures a token and understands that remote prompts are sent to a provider.
- Check model card, license, supported task, language quality, provider availability, and cost before choosing a model.

## Security and privacy
- Never upload ARIA's private memory database, personal notes, credentials, or source secrets to a model repository.
- Do not make remote inference mandatory; network access can be unreliable.
- Require explicit owner approval before adding a paid provider, enabling billing, uploading datasets, or publishing a model/Space.
- Do not claim that a model is free merely because its weights are public. Hosted inference may have quotas or charges.

## Initial milestone
Documented integration plan only. Hugging Face is not yet connected to the running ARIA server, and no model has been downloaded or called from the project.
