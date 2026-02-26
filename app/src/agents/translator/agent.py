import os
from langchain_core.messages import AIMessage
from ..state import OverallState

# Import our pure Python tools
from .tools.db_tools import get_news_to_translate, save_translation
from .tools.translate_llm import get_translator_llm, translate_content

def translator_node(state: OverallState) -> dict:
    print("🌍 [Translator] Executing Data Pipeline for Translation...")
    
    translated_count = 0
    
    # 1. Fetch news (Pure Python, no LLM cost)
    rows = get_news_to_translate(limit=200)
    
    if not rows:
        print("   ✅ No pending news to translate.")
        return {"messages": [AIMessage(content="Translation finished. No pending news.")]}
        
    # 2. Instantiate LLM once
    llm = get_translator_llm()
    
    print(f"   📥 Found {len(rows)} news to translate.")
    
    # 3. Iterate and translate
    for item_id, title, summary in rows:
        print(f"\n   🔄 Processing item ID {item_id}...")
        
        try:
            # A) Invoke structured output LLM
            trans_data = translate_content(llm, title, summary)
            
            # B) Save to DB using pure Python
            success = save_translation(item_id, trans_data.title_eu, trans_data.summary_eu)
            
            if success:
                translated_count += 1
                print(f"      ✅ Item {item_id} translated and saved successfully.")
                
        except Exception as e:
            # If it fails (e.g., API timeout), it skips to the next one.
            # It will remain as 'evaluated' and get picked up in the next run.
            print(f"      ❌ Error translating ID {item_id}: {e}")
            
    message = f"Translation pipeline completed. Successfully translated {translated_count} news items."
    print(f"\n✅ {message}")
    
    return {"messages": [AIMessage(content=message)]}