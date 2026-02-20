import os
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from langchain_core.tools import tool

# Reutilizamos el mismo modelo
model = SentenceTransformer("all-MiniLM-L6-v2")
COLLECTION_NAME = "techwatch_items"

@tool
def check_semantic_memory_tool(topic: str, title: str, content: str) -> str:
    """
    Skill: Memoria Semántica (Qdrant).
    Busca si una noticia es un duplicado o un eco de algo que ya hemos analizado en el pasado.
    Proporciona el topic, title y content del artículo actual.
    """
    print(f"🧠 [Analyst Skill: Memory] Consultando Qdrant para: '{title[:40]}...'")
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    
    try:
        qdrant = QdrantClient(url=qdrant_url)
        text_to_embed = f"{topic}\n{title}\n{content}"
        vector = model.encode(text_to_embed).tolist()
        
        # Buscar similitudes en la base vectorial
        search_result = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=1
        )
        
        if search_result and search_result[0].score > 0.85:
            match = search_result[0]
            return f"⚠️ ALERTA DUPLICADO: Muy similar a una noticia pasada (Score de similitud: {match.score:.2f}). Item ID anterior: {match.payload.get('item_id')}."
        else:
            return "✅ NOTICIA NUEVA: No hay coincidencias semánticas fuertes en la memoria."
            
    except Exception as e:
        return f"❌ Error conectando a la memoria vectorial: {str(e)}"