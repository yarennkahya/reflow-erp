import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import ChatMessage, Conversation
from .services import ask_assistant

_ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.csv', '.md', '.xlsx', '.xls'}
_MAX_CHARS = 20_000


@csrf_exempt
@require_POST
@login_required
def file_upload_view(request):
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'Dosya bulunamadı.'}, status=400)

    name = f.name.lower()
    ext = next((e for e in _ALLOWED_EXTENSIONS if name.endswith(e)), None)
    if ext is None:
        return JsonResponse({'error': 'Desteklenmeyen dosya türü.'}, status=415)

    try:
        if ext == '.pdf':
            import pypdf
            reader = pypdf.PdfReader(f)
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        elif ext in ('.xlsx', '.xls'):
            import openpyxl
            wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
            rows = []
            for ws in wb.worksheets:
                rows.append(f'=== {ws.title} ===')
                for row in ws.iter_rows(values_only=True):
                    rows.append('\t'.join('' if c is None else str(c) for c in row))
            text = '\n'.join(rows)
        else:
            text = f.read().decode('utf-8', errors='replace')
    except Exception as exc:
        return JsonResponse({'error': f'Dosya okunamadı: {exc}'}, status=422)

    text = text.strip()[:_MAX_CHARS]
    return JsonResponse({'filename': f.name, 'chars': len(text), 'text': text})


@csrf_exempt
@require_POST
@login_required
def chat_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Gecersiz JSON.'}, status=400)

    message = data.get('message')
    if not message:
        return JsonResponse({'error': 'message alani zorunlu.'}, status=400)

    conversation_id = data.get('conversation_id')
    if conversation_id:
        conversation = get_object_or_404(Conversation, pk=conversation_id, user=request.user)
        history = [m.raw_data for m in conversation.messages.all()]
    else:
        conversation = Conversation.objects.create(user=request.user)
        history = None

    existing_count = conversation.messages.count()

    try:
        result = ask_assistant(message, conversation_history=history)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)

    new_messages = result['conversation_history'][existing_count:]
    for msg in new_messages:
        ChatMessage.objects.create(
            conversation=conversation, role=msg.get('role', ''), raw_data=msg
        )

    if not conversation.title:
        conversation.title = message[:60]
    conversation.save()

    return JsonResponse({
        'answer': result['answer'],
        'conversation_id': conversation.pk,
    })