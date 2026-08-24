from openai import OpenAI
import json

from inventory.services import get_stock_summary

from .models import Document
from pgvector.django import CosineDistance

EMBEDDING_MODEL = 'text-embedding-3-small'

client = OpenAI()  # OPENAI_API_KEY'i ortam değişkeninden otomatik okur


def generate_embedding(text):
    """Verilen metni OpenAI'ye gönderip embedding vektörünü döner."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def embed_document(document):
    """Bir Document kaydının content'ini embedding'e çevirir ve kaydeder."""
    document.embedding = generate_embedding(document.content)
    document.save(update_fields=['embedding'])
    return document

def search_similar_documents(query_embedding, top_k=3):
    """
    Verilen bir embedding vektorune en yakin Document'lari bulur.
    Bu fonksiyon OpenAI'ye hic istek atmaz, sadece PostgreSQL sorgusu yapar --
    embedding'i ureten sorumluluk baska bir fonksiyonda (generate_embedding).
    """
    return (
        Document.objects
        .filter(embedding__isnull=False)
        .annotate(distance=CosineDistance('embedding', query_embedding))
        .order_by('distance')[:top_k]
    )


def answer_question(question, top_k=3):
    """
    RAG akisinin tamami: soruyu embed'ler, en alakali belgeleri bulur,
    bu belgeleri baglam olarak LLM'e verip soruyu cevaplatir.
    """
    question_embedding = generate_embedding(question)
    relevant_docs = search_similar_documents(question_embedding, top_k=top_k)

    if not relevant_docs:
        return {
            'answer': 'Bu soruyla ilgili sistemde henuz bir bilgi bulamadim.',
            'sources': [],
        }

    context = '\n\n'.join(
        f'[{doc.title}]\n{doc.content}' for doc in relevant_docs
    )

    system_prompt = (
        'Sen bir kahve kavurma isletmesinin ic bilgi asistanisin. '
        'Sadece asagida verilen baglama dayanarak cevap ver. '
        'Baglamda cevap yoksa, "bu konuda bilgim yok" de, uydurma.'
    )

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': f'{system_prompt}\n\nBaglam:\n{context}'},
            {'role': 'user', 'content': question},
        ],
    )

    return {
        'answer': response.choices[0].message.content,
        'sources': [doc.title for doc in relevant_docs],
    }


TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'get_stock_summary',
            'description': (
                'Belirli bir urunun toplam kalan stogunu ve her lotunun '
                'tazelik durumunu (NORMAL, PRIORITY_SALE, WASTE) dondurur.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'product_name': {
                        'type': 'string',
                        'description': 'Aranacak urunun adi (tam olmasi gerekmez)',
                    },
                },
                'required': ['product_name'],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    'get_stock_summary': get_stock_summary,
}


def ask_with_tools(question):
    """
    LLM'e soruyu, kullanabilecegi araclarin listesiyle birlikte gonderir.
    LLM bir arac cagirmak isterse GERCEK Python fonksiyonunu biz calistirir,
    sonucu LLM'e geri veririz, o da dogal dilde son cevabi uretir.
    """
    messages = [
        {
            'role': 'system',
            'content': (
                'Sen bir kahve kavurma isletmesinin ic bilgi asistanisin. '
                'Stok sorularinda elindeki araclari kullan, tahmin yurutme.'
            ),
        },
        {'role': 'user', 'content': question},
    ]

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        tools=TOOLS,
    )
    message = response.choices[0].message

    if not message.tool_calls:
        return {'answer': message.content, 'tool_used': None}

    tool_call = message.tool_calls[0]
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)

    function_to_call = AVAILABLE_FUNCTIONS[function_name]
    function_result = function_to_call(**function_args)

    messages.append(message)
    messages.append({
        'role': 'tool',
        'tool_call_id': tool_call.id,
        'content': json.dumps(function_result),
    })

    second_response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
    )

    return {
        'answer': second_response.choices[0].message.content,
        'tool_used': function_name,
    }