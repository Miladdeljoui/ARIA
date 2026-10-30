# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo>=0.16,<1.0", "transformers>=4.50", "accelerate>=1.0", "sentencepiece"]
# ///

import marimo

__generated_with = "0.16.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import torch
    import marimo as mo
    return mo, torch


@app.cell
def _(mo, torch):
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        hardware_text = (
            f"**GPU:** {gpu_name}  \n"
            f"**VRAM:** {vram_gb:.1f} GiB  \n"
            f"**CUDA:** {torch.version.cuda or 'available'}"
        )
    else:
        hardware_text = (
            "**GPU شناسایی نشد.** در Molab از منوی مشخصات Notebook، "
            "گزینهٔ GPU را فعال کن و Notebook را دوباره راه‌اندازی کن."
        )
    mo.md(
        "# ARIA · آزمایشگاه شخصی مدل‌های هوش مصنوعی\n\n"
        "این Notebook برای آزمایش تعاملی مدل‌های متن‌باز است. "
        "به‌صورت پیش‌فرض هیچ API، پراکسی یا سرور عمومی ایجاد نمی‌کند.\n\n"
        + hardware_text
    )
    return


@app.cell
def _(mo):
    model_choice = mo.ui.dropdown(
        options={
            "Qwen3 · 4B": "Qwen/Qwen3-4B",
            "Qwen3 · 8B": "Qwen/Qwen3-8B",
        },
        value="Qwen/Qwen3-4B",
        label="مدل",
    )
    load_button = mo.ui.run_button(label="بارگذاری مدل روی GPU")
    question = mo.ui.text_area(
        value="سلام. خودت را به فارسی معرفی کن و سه کاری که می‌توانی انجام بدهی بگو.",
        label="پرسش",
        rows=5,
    )
    max_tokens = mo.ui.slider(
        start=64, stop=512, step=64, value=256, label="حداکثر توکن پاسخ"
    )
    generate_button = mo.ui.run_button(label="تولید پاسخ")
    mo.vstack(
        [
            model_choice,
            load_button,
            question,
            max_tokens,
            generate_button,
        ],
        gap=1,
    )
    return generate_button, load_button, max_tokens, model_choice, question


@app.cell
def _(load_button, mo, model_choice, torch):
    loaded_model = None
    tokenizer = None
    model_status = "برای دانلود و بارگذاری مدل، دکمهٔ «بارگذاری مدل روی GPU» را بزن."
    if load_button.value:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            model_id = model_choice.value
            with mo.status.spinner(f"در حال دریافت و بارگذاری {model_id} ..."):
                tokenizer = AutoTokenizer.from_pretrained(model_id)
                loaded_model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    torch_dtype="auto",
                    device_map="auto" if torch.cuda.is_available() else None,
                )
            model_status = f"مدل {model_id} با موفقیت بارگذاری شد."
        except Exception as exc:
            loaded_model = None
            tokenizer = None
            model_status = f"بارگذاری مدل ناموفق بود: {type(exc).__name__}: {exc}"
    mo.md(f"**وضعیت مدل:** {model_status}")
    return loaded_model, tokenizer


@app.cell
def _(
    generate_button,
    loaded_model,
    max_tokens,
    mo,
    question,
    tokenizer,
    torch,
):
    answer_text = "ابتدا مدل را بارگذاری کن و سپس «تولید پاسخ» را بزن."
    if generate_button.value:
        if loaded_model is None or tokenizer is None:
            answer_text = "مدل هنوز بارگذاری نشده است."
        elif not question.value.strip():
            answer_text = "ابتدا پرسش را بنویس."
        else:
            try:
                prompt_ids = tokenizer.apply_chat_template(
                    [{"role": "user", "content": question.value.strip()}],
                    add_generation_prompt=True,
                    return_tensors="pt",
                )
                prompt_ids = prompt_ids.to(loaded_model.device)
                with torch.inference_mode():
                    output_ids = loaded_model.generate(
                        prompt_ids,
                        max_new_tokens=int(max_tokens.value),
                        do_sample=True,
                        temperature=0.7,
                        top_p=0.8,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                answer_text = tokenizer.decode(
                    output_ids[0][prompt_ids.shape[-1]:],
                    skip_special_tokens=True,
                ).strip()
            except Exception as exc:
                answer_text = f"تولید پاسخ ناموفق بود: {type(exc).__name__}: {exc}"
    mo.md("## پاسخ مدل\n\n" + answer_text)
    return


if __name__ == "__main__":
    app.run()
