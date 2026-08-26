import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import ask_assistant


@csrf_exempt
@require_POST
def chat_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Gecersiz JSON.'}, status=400)

    message = data.get('message')
    if not message:
        return JsonResponse({'error': 'message alani zorunlu.'}, status=400)

    conversation_history = data.get('conversation_history')

    try:
        result = ask_assistant(message, conversation_history=conversation_history)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)

    return JsonResponse(result)