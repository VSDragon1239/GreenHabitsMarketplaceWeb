import logging
import json
import re
import requests
from django.conf import settings
from apps.marketplace.models import UserTaskCompletion

logger = logging.getLogger(__name__)


def moderate_task_completion(completion: UserTaskCompletion) -> dict:
    task = completion.task
    proof_description = ""
    if completion.proof_text:
        proof_description += f"Текстовое доказательство: {completion.proof_text}\n"
    if completion.proof_image:
        proof_description += "К доказательству приложена фотография.\n"

    prompt = f"""Проверь выполнение эко-задания.
Задание: {task.title}
Описание задания: {task.description}
Доказательство пользователя:
{proof_description or 'Доказательств нет.'}
"""

    api_url = settings.ANYTHINGLLM_API_URL
    workspace = settings.ANYTHINGLLM_WORKSPACE
    api_key = settings.ANYTHINGLLM_API_KEY

    if not all([api_url, workspace, api_key]):
        raise ValueError("ANYTHINGLLM env vars are not set!")

    url = f"{api_url}/api/v1/workspace/{workspace}/chat"
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    payload = {
        'message': prompt,
        'mode': 'chat',
        'sessionId': f'task-{completion.id}',
    }

    # Логируем для отладки
    logger.info(f"Sending request to AnythingLLM: URL={url}, Payload={payload}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()

        # Логируем сырой ответ
        logger.info(f"AnythingLLM raw response: {response.text}")

        data = response.json()
        raw_text = data.get('textResponse', '').strip()

        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not match:
            return {'verdict': 'needs_human', 'reason': f'ИИ вернул не-JSON: {raw_text[:200]}'}

        verdict_data = json.loads(match.group(0))
        verdict_data.setdefault('verdict', 'needs_human')
        verdict_data.setdefault('reason', '—')
        return verdict_data

    except requests.RequestException as e:
        logger.error(f"AnythingLLM request failed: {e}")
        # Если AnythingLLM вернул ошибку, пробуем прочитать текст ответа
        err_text = e.response.text if hasattr(e, 'response') and e.response else ""
        raise Exception(f"Сетевая ошибка к ИИ: {e}. Ответ сервера: {err_text}")
