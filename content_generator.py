import json
import os
import re
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

@dataclass
class GeneratedContent:
    tg_post: str
    page_body_html: str
    description: str

def _safe_json_extract(text: str) -> dict:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON found in model output")
    return json.loads(m.group(0))

def _template_content(title: str, url: str) -> GeneratedContent:
    desc = f"Краткий разбор по теме: {title}. Пошагово и без лишней воды."
    page = f"""
    <h2>Пошагово</h2>
    <ol>
      <li>Определи цель и формат: что именно хочешь получить.</li>
      <li>Собери инструменты: бот/канал/напоминания/закреп.</li>
      <li>Сделай простой первый вариант и протестируй 1–2 дня.</li>
      <li>Улучшай: добавляй шаблоны, категории и правила.</li>
    </ol>

    <h2>FAQ</h2>
    <p><b>С чего начать быстрее всего?</b> С одного списка задач и ежедневных напоминаний.</p>
    <p><b>Как не бросить?</b> Делай маленькие шаги и фиксируй прогресс.</p>
    """
    post = (
        f"{title}\n"
        f"Коротко: собрал понятный план, чтобы сделать это быстро и без хаоса ✅\n\n"
        f"1) Определи цель 🎯\n"
        f"2) Настрой список/канал/бота 🧩\n"
        f"3) Добавь напоминания ⏰\n"
        f"4) Проверь 1–2 дня и поправь 🔧\n\n"
        f"👉 Узнать больше: {url}"
    )
    return GeneratedContent(tg_post=post, page_body_html=page.strip(), description=desc)

def generate_content(query: str, title: str, url: str) -> GeneratedContent:
    """
    Если OPENAI_API_KEY задан — генерим через GPT.
    Если нет — возвращаем аккуратный шаблон (проект всё равно рабочий).
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5-nano").strip()

    if not api_key:
        return _template_content(title, url)

    client = OpenAI(api_key=api_key)

    instructions = (
        "Ты генерируешь контент для SEO-страницы и поста Telegram.\n"
        "Верни СТРОГО JSON с ключами:\n"
        "- tg_post: строка (до 1800–2200 символов), с заголовком и в конце CTA со ссылкой.\n"
        "- page_body_html: HTML-фрагмент без <html>/<head> (h2/ol/p/ul), полезный текст.\n"
        "- description: короткое meta description (до 160–180 символов).\n\n"
        "Правила:\n"
        "- Никаких обещаний прибыли/гарантий.\n"
        "- Пиши нейтрально, без опасных/незаконных инструкций.\n"
        "- Не упоминай, что ты ИИ.\n"
    )

    user_input = (
        f"Запрос: {query}\n"
        f"Заголовок (H1): {title}\n"
        f"Ссылка для CTA: {url}\n"
        "Сгенерируй контент."
    )

    resp = client.responses.create(
        model=model,
        instructions=instructions,
        input=user_input,
    )
    data = _safe_json_extract(resp.output_text)

    tg_post = str(data.get("tg_post") or "").strip()
    page_body_html = str(data.get("page_body_html") or "").strip()
    description = str(data.get("description") or "").strip()

    if url not in tg_post:
        tg_post = tg_post.rstrip() + f"\n\n👉 Узнать больше: {url}"

    # Жёсткий предохранитель по длине поста, чтобы не улетать в лимиты
    if len(tg_post) > 3500:
        tg_post = tg_post[:3400].rstrip() + f"\n\n👉 Узнать больше: {url}"

    if not page_body_html:
        page_body_html = _template_content(title, url).page_body_html
    if not description:
        description = _template_content(title, url).description

    return GeneratedContent(tg_post=tg_post, page_body_html=page_body_html, description=description)
