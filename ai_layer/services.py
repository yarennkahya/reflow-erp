import importlib
import json

from openai import OpenAI
from pgvector.django import CosineDistance

from inventory.services import get_stock_summary
from sales.services import get_demand_forecast

from .models import Document
from .query_registry import QUERY_REGISTRY

EMBEDDING_MODEL = 'text-embedding-3-small'

client = OpenAI()  # OPENAI_API_KEY'i ortam degiskeninden otomatik okur


def generate_embedding(text):
    """Verilen metni OpenAI'ye gonderip embedding vektorunu doner."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def embed_document(document):
    """Bir Document kaydinin content'ini embedding'e cevirir ve kaydeder."""
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


def _search_documents_tool(query):
    """
    search_documents aracinin gercek calisan tarafi -- RAG'in arama kismini
    (embedding uret + benzer belge bul) bir fonksiyon olarak sarmalar.
    """
    query_embedding = generate_embedding(query)
    docs = search_similar_documents(query_embedding, top_k=3)
    return {
        'results': [
            {'title': doc.title, 'content': doc.content} for doc in docs
        ]
    }


def query_module(module_key, filters=None, limit=10):
    """
    QUERY_REGISTRY'de tanimli modeller uzerinde GUVENLI, SALT OKUMA sorgusu
    yapar. LLM asla ham SQL veya serbest model adi veremez -- sadece
    registry'de onceden listelenmis module_key'lerden birini secebilir,
    sadece o modul icin izin verilen alanlarla filtreleyebilir. Yazma/
    silme islemi bu fonksiyonda YOKTUR.
    """
    if module_key not in QUERY_REGISTRY:
        return {
            'error': f'"{module_key}" gecerli bir modul degil. '
                     f'Gecerli secenekler: {list(QUERY_REGISTRY.keys())}'
        }

    config = QUERY_REGISTRY[module_key]
    app_label, model_name = config['model'].split('.')
    model = importlib.import_module(f'{app_label}.models').__dict__[model_name]

    queryset = model.objects.all()
    filters = filters or {}
    applied = {}
    for key, value in filters.items():
        if key not in config['filterable_fields']:
            continue  # izin verilmeyen alan sessizce atlanir, hata vermez
        applied[key] = value

    if applied:
        queryset = queryset.filter(**applied)

    queryset = queryset[:min(limit, 20)]  # LLM ne isterse istesin, 20 ust siniri asilmaz

    results = []
    for obj in queryset:
        row = {}
        for field in config['display_fields']:
            value = obj
            for part in field.split('__'):
                value = getattr(value, part, None)
                if value is None:
                    break
            row[field] = str(value) if value is not None else None
        results.append(row)

    return {
        'module': module_key,
        'applied_filters': applied,
        'result_count': len(results),
        'results': results,
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
    {
        'type': 'function',
        'function': {
            'name': 'search_documents',
            'description': (
                'Kurumsal dokumanlarda (prosedurler, tedarikci notlari, '
                'politikalar) arama yapar, en alakali belgeleri dondurur.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Aranacak konu veya soru',
                    },
                },
                'required': ['query'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_demand_forecast',
            'description': (
                'Bir urunun son 90 gunluk satis hizina gore basit bir talep '
                'tahmini uretir ve mevcut stogun yetip yetmeyecegini soyler.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'product_name': {
                        'type': 'string',
                        'description': 'Aranacak urunun adi (tam olmasi gerekmez)',
                    },
                    'days_ahead': {
                        'type': 'integer',
                        'description': 'Kac gunluk tahmin yapilsin, varsayilan 30',
                    },
                },
                'required': ['product_name'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'query_module',
            'description': (
                'Sistemdeki herhangi bir modulu (stok, satin alma, uretim, '
                'satis, musteri, iade, CRM firsati, fatura, personel, izin '
                'talebi, toplanti) filtreli olarak sorgular. Hangi modullerin '
                've hangi filtrelerin gecerli oldugunu bilmiyorsan, once bos '
                'filtreyle dene, hata mesaji sana gecerli secenekleri '
                'gosterecektir.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'module_key': {
                        'type': 'string',
                        'description': (
                            'Sorgulanacak modul anahtari. Secenekler: '
                            'inventory_products, inventory_lots, '
                            'purchasing_orders, production_batches, '
                            'sales_orders, sales_customers, sales_returns, '
                            'crm_opportunities, finance_invoices, '
                            'hr_employees, hr_leave_requests, meetings'
                        ),
                    },
                    'filters': {
                        'type': 'object',
                        'description': (
                            'Anahtar-deger filtre ciftleri, orn. '
                            '{"status": "pending"}. Bos birakilabilir.'
                        ),
                    },
                    'limit': {
                        'type': 'integer',
                        'description': 'Kac sonuc donsun, en fazla 20, varsayilan 10',
                    },
                },
                'required': ['module_key'],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    'get_stock_summary': get_stock_summary,
    'search_documents': _search_documents_tool,
    'get_demand_forecast': get_demand_forecast,
    'query_module': query_module,
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


def ask_assistant(message, conversation_history=None):
    """
    Frontend'in cagiracagi tek giris noktasi. Konusma gecmisini destekler
    (JSON'a cevrilebilir duz sozlukler olarak saklanir), LLM'in ayni
    yanitta birden fazla arac cagirmasina izin verir.
    """
    if conversation_history is None:
        conversation_history = [
            {
                'role': 'system',
                                'content': (
                    'Sen bir kahve kavurma isletmesinin ic bilgi asistanisin. '
                    'Stok sorularinda ve dokuman aramalarinda elindeki '
                    'araclari kullan, tahmin yurutme. Urun adlari '
                    'veritabaninda Ingilizce kayitlidir (orn. Ethiopia, '
                    'Brazil, Colombia). Turkce soru sorulsa bile, arac '
                    'cagirirken urun adini Ingilizceye cevirerek kullan. '
                    'search_documents aracindan bir sonuc geldiginde, SADECE '
                    'o sonuctaki bilgiyi kullan; kendi genel bilgini ekleme '
                    'veya tamamlama yapma. Genel/spesifik olmayan sorularda '
                    '(orn. "kac tane X var", "hangi Y durumda") '
                    'query_module aracini kullan, hangi module_key ve '
                    'filtrenin uygun oldugunu sen belirle.'
                ),
            }
        ]

    messages = conversation_history + [{'role': 'user', 'content': message}]

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        tools=TOOLS,
    )
    response_message = response.choices[0].message

    if not response_message.tool_calls:
        messages.append({'role': 'assistant', 'content': response_message.content})
        return {'answer': response_message.content, 'conversation_history': messages}

    messages.append({
        'role': 'assistant',
        'content': response_message.content,
        'tool_calls': [
            {
                'id': tc.id,
                'type': 'function',
                'function': {'name': tc.function.name, 'arguments': tc.function.arguments},
            }
            for tc in response_message.tool_calls
        ],
    })

    for tool_call in response_message.tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        function_to_call = AVAILABLE_FUNCTIONS[function_name]
        function_result = function_to_call(**function_args)
        messages.append({
            'role': 'tool',
            'tool_call_id': tool_call.id,
            'content': json.dumps(function_result),
        })

    second_response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
    )
    final_answer = second_response.choices[0].message.content
    messages.append({'role': 'assistant', 'content': final_answer})

    return {'answer': final_answer, 'conversation_history': messages}
