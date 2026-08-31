import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import ChatMessage, Conversation
from .services import ask_assistant


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