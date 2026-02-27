import os
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..state import OverallState
from .tools.skill_reader import read_expert_skill
from .tools.db_tools import get_pending_news, save_analysis
from .tools.semantic_memory import check_semantic_memory

# We force the LLM to reply exactly with this structure
class EvaluationResult(BaseModel):
    score: float = Field(description="Score from 0.0 to 10.0 based strictly on the rubric")
    summary_short: str = Field(description="Direct, journalistic summary of the news. No intro phrases.")

def get_analyst_llm():
    """Instantiates the LLM with structured output support."""
    provider = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if provider == "ollama":
        from langchain_openai import ChatOpenAI
        base_url = os.environ.get("OLLAMA_API_URL", "http://ollama:11434").replace("/api", "") + "/v1"
        llm = ChatOpenAI(
            base_url=base_url,
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            model=os.environ.get("OLLAMA_MODEL", "gemma3:12b-cloud"),
            max_retries=2,       
            timeout=45.0
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.environ.get("GEMINI_API_KEY", "PUT_YOUR_KEY_HERE_IF_IT_FAILS")
        api_key = api_key.replace('"', '').replace("'", "")
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key,
        max_retries=2,       
        timeout=45.0
        )
    return llm.with_structured_output(EvaluationResult)


def analyst_node(state: OverallState) -> dict:
    print("🧠 [Analyst] Starting Expert Evaluation Pipeline...")
    
    llm_with_structure = get_analyst_llm()
    topics = ["plone", "django", "ai"]
    
    # --- CONFIGURATION ---
    MAX_NEWS_PER_TOPIC = 200  # Will fetch up to 100 news per topic safely
    # ---------------------
    
    total_evaluated = 0
    total_duplicates = 0

    for topic in topics:
        print(f"\n   🎯 [Analyst] Waking up {topic.upper()} Expert...")
        
        # 1. Fetch pending news for this specific topic
        pending_news = get_pending_news(topic, limit=MAX_NEWS_PER_TOPIC)
        if not pending_news:
            print(f"      No pending news for {topic.upper()}. Expert goes back to sleep.")
            continue
            
        # 2. Inject the skill into the Expert's brain (System Prompt)
        rubric_content = read_expert_skill(f"{topic.upper()}_EVALUATION")
        if not rubric_content:
            print(f"      ⚠️ Missing {topic.upper()}_EVALUATION.md skill. Skipping.")
            continue
            
        system_prompt = SystemMessage(content=f"""
        You are a Senior Technical Analyst. Your absolute area of expertise is {topic.upper()}.
        You must evaluate technical news using the following rubric strictly.
        
        RUBRIC:
        {rubric_content}
        """)
        
        print(f"      Expert awake. Evaluating {len(pending_news)} news items...")
        
        # 3. Feed news to the expert one by one
        for row in pending_news:
            item_id, title, content, source_type = row
            
            # A) Ask Semantic Memory (Qdrant) FIRST
            mem_result = check_semantic_memory(item_id, topic, title, content, source_type)
            
            # If Qdrant says it's an echo/trend, skip the LLM entirely
            if mem_result["action"] == "duplicate":
                save_analysis(item_id, topic, status="duplicate")
                print(f"      🗑️  Item {item_id}: Marked as duplicate (Trend detected).")
                total_duplicates += 1
                continue
                
            # B) LLM Evaluation (The Expert evaluates ONLY this news using its injected skill)
            user_msg = HumanMessage(content=f"Evaluate this news:\n\nTitle: {title}\nSource Type: {source_type}\nContent: {content[:1500]}")
            
            try:
                # The expert returns the score and the summary based on the rubric
                eval_data: EvaluationResult = llm_with_structure.invoke([system_prompt, user_msg])
                
                # C) Combine Expert Score + Qdrant Modifier
                raw_score = eval_data.score
                modifier = mem_result["modifier"]
                final_score = max(0.0, min(10.0, raw_score + modifier))
                
                # D) Save results
                save_analysis(
                    item_id=item_id,
                    topic=topic,
                    status="evaluated",
                    summary=eval_data.summary_short,
                    final_score=final_score,
                    vector=mem_result["vector"]
                )
                print(f"      ✅ Item {item_id}: Evaluated. Final Score: {final_score}/10")
                total_evaluated += 1
                
            except Exception as e:
                print(f"      ❌ Failed to evaluate item {item_id}: {e}")

    final_message = f"Analyst evaluation completed. {total_evaluated} evaluated, {total_duplicates} duplicates skipped. Passes turn to Translator."
    print(f"\n✅ {final_message}")
    
    return {"messages": [AIMessage(content=final_message)]}