import logging
import json
import re
import requests
from django.conf import settings
from apps.marketplace.models import UserTaskCompletion

logger = logging.getLogger(__name__)


def moderate_task_completion(completion: UserTaskCompletion) -> dict:
    """
    Отправляет доказательство в AnythingLLM и возвращает вердикт ИИ.
    """
    task = completion.task

    # Собираем текст для отправки ИИ
    proof_description = ""
    if completion.proof_text:
        proof_description += f"Текстовое доказательство: {completion.proof_text}\n"
    if completion.proof_image:
        # В MVP отправляем только текст. Фото ИИ не видит, но знает, что оно есть.
        proof_description += "К доказательству приложена фотография.\n"

    prompt = f"""Проверь выполнение эко-задания.
Задание: {task.title}
Описание задания: {task.description}
Доказательство пользователя:
{proof_description or 'Доказательств нет.'}
"""

    # Используем переменные из settings.py
    api_url = settings.ANYTHINGLLM_API_URL
    workspace = settings.ANYTHINGLLM_WORKSPACE
    api_key = settings.ANYTHINGLLM_API_KEY

    if not all([api_url, workspace, api_key]):
        logger.error("AnythingLLM settings are not configured properly in .env")
        return {'verdict': 'needs_human', 'reason': 'ИИ не настроен'}

    try:
        response = requests.post(
            f"{api_url}/api/v1/workspace/{workspace}/chat",
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json={
                'message': prompt,
                'mode': 'chat',
                'sessionId': f'task-{completion.id}',
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        # AnythingLLM возвращает ответ в поле textResponse
        raw_text = data.get('textResponse', '').strip()

        # Ищем JSON в ответе (на случай если ИИ добавил лишний текст)
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not match:
            return {'verdict': 'needs_human', 'reason': f'ИИ вернул не-JSON: {raw_text[:200]}'}

        verdict_data = json.loads(match.group(0))

        # Нормализуем данные
        verdict_data.setdefault('verdict', 'needs_human')
        verdict_data.setdefault('reason', '—')
        return verdict_data

    except requests.RequestException as e:
        logger.error(f"AnythingLLM request failed: {e}")
        return {'verdict': 'needs_human', 'reason': f'Сетевая ошибка к ИИ: {e}'}
    except Exception as e:
        logger.exception("AI moderation unexpected error")
        return {'verdict': 'needs_human', 'reason': f'Внутренняя ошибка: {e}'}


def apply_ai_verdict(completion: UserTaskCompletion, verdict: dict) -> None:
    """Применяет вердикт ИИ к completion: меняет статус и сохраняет feedback."""
    ai_verdict_str = verdict.get('verdict', 'needs_human').lower()
    reason = verdict.get('reason', '—')

    completion.ai_feedback = f"[{ai_verdict_str.upper()}] {reason}"

    if ai_verdict_str == 'approved':
        completion.status = UserTaskCompletion.Status.AI_APPROVED
    elif ai_verdict_str == 'rejected':
        completion.status = UserTaskCompletion.Status.AI_REJECTED
    else:  # needs_human
        completion.status = UserTaskCompletion.Status.PENDING

    completion.save(update_fields=['status', 'ai_feedback', 'reviewed_at'])
