import logging
import json
import re
import requests
from django.conf import settings
from apps.marketplace.models import UserTaskCompletion

logger = logging.getLogger(__name__)

import logging
import json
import re
import base64
import os
import requests
from django.conf import settings
from apps.marketplace.models import UserTaskCompletion

logger = logging.getLogger(__name__)


def moderate_task_completion(completion: UserTaskCompletion) -> dict:
    task = completion.task
    proof_description = ""

    # 1. Готовим текстовое описание
    if completion.proof_text:
        proof_description += f"Текстовое доказательство: {completion.proof_text}\n"

    # 2. Готовим картинку для отправки (если она есть)
    attachments = []
    if completion.proof_image:
        proof_description += "К доказательству приложена фотография (см. вложение).\n"

        try:
            # Получаем абсолютный путь к файлу на диске
            image_path = completion.proof_image.path
            if os.path.exists(image_path):
                # Читаем файл и кодируем в Base64
                with open(image_path, 'rb') as img_file:
                    base64_str = base64.b64encode(img_file.read()).decode('utf-8')

                # Определяем MIME-тип (jpeg, png, webp)
                ext = os.path.splitext(image_path)[1].lower().replace('.', '')
                if ext == 'jpg': ext = 'jpeg'
                mime = f"image/{ext}" if ext in ['jpeg', 'png', 'webp', 'gif'] else "image/jpeg"

                attachments.append({
                    "name": f"proof_{completion.id}.{ext}",
                    "mime": mime,
                    "contentString": base64_str
                })
            else:
                logger.warning(f"Image file not found on disk: {image_path}")
                proof_description += "ВНИМАНИЕ: Файл фото не найден на сервере!\n"
        except Exception as e:
            logger.error(f"Error reading image {completion.proof_image.path}: {e}")
            proof_description += f"ВНИМАНИЕ: Ошибка чтения файла фото: {e}\n"
    else:
        proof_description += "Фотографии нет.\n"

    # 3. Формируем промпт
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

    # Добавляем attachments в payload, если картинка была обработана
    payload = {
        'message': prompt,
        'mode': 'chat',
        'sessionId': f'task-{completion.id}',
    }
    if attachments:
        payload['attachments'] = attachments

    logger.info(f"Sending request to AnythingLLM: URL={url}, Attachments={len(attachments)}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=300)

        if response.status_code != 200:
            err_msg = "Неизвестная ошибка"
            try:
                err_data = response.json()
                err_msg = err_data.get('error', str(err_data))
            except ValueError:
                err_msg = response.text
            logger.error(f"AnythingLLM Error Body: {err_msg}")
            raise Exception(f"Сервер ИИ вернул {response.status_code}: {err_msg}")

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
        raise Exception(f"Сетевая ошибка к ИИ: {e}")


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
