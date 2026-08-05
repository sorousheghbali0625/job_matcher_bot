import asyncio
import logging
from datetime import datetime

from models.schemas import JobPost, UserPreferences
from database.relational_db import RelationalDB
from database.vector_db import VectorDB
from ai_engine.embedder import Embedder
from ai_engine.filter import RuleBasedFilter
from ai_engine.llm_evaluator import LLMEvaluator

# Set up basic console logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def test_pipeline():
    print("🚀 Initializing System Components (Loading ML models)...")
    
    # 1. Initialize Components (Paths loaded automatically from settings.py/.env)
    relational_db = RelationalDB()
    await relational_db.initialize_database()
    
    vector_db = VectorDB()
    embedder = Embedder()
    llm_evaluator = LLMEvaluator()

    # 2. Mock a User Registration (Simulating your friend's Telegram UI)
    mock_user = UserPreferences(
        user_id=12345,
        resume_text="Senior Python Backend Engineer. 10 years experience. Expert in Asyncio, FastAPI, Pydantic, and building scalable SaaS multi-tenant architectures. Solid understanding of databases like PostgreSQL and SQLite.",
        min_budget=500.0,
        unwanted_keywords=["PHP", "WordPress", "Java"],
        preferred_skills=["Python", "Asyncio", "Pydantic", "SQLite"],
        similarity_threshold=0.3
    )
    
    print("\n👤 Saving Mock User to Databases...")
    # Save to SQLite
    await relational_db.upsert_user(mock_user)
    # Generate Vector & Save to ChromaDB
    user_embedding = await embedder.generate_embedding(mock_user.resume_text)
    await vector_db.upsert_user_resume(mock_user.user_id, user_embedding, mock_user.resume_text)

    # 3. Mock an Incoming Job (Simulating your friend's Scraper)
    mock_job = JobPost(
        job_id="job_abc_001",
        source="Upwork",
        title="Need an expert Python dev for Async Data Pipeline",
        description="We are building a highly concurrent data processing pipeline. You must know Python 3.11, asyncio, and Pydantic. We are using SQLite for local caching. DO NOT apply if you only know Django/Flask. This is purely a backend engine project.",
        budget=1200.0,
        url="https://example.com/job/123",
        posted_at=datetime.utcnow()
    )

    print(f"\n📨 Simulating Incoming Job: {mock_job.title}")

    # 4. RUN THE PIPELINE
    
    # Step A: Deduplication
    is_processed = await relational_db.is_job_processed(mock_job.job_id, mock_job.source)
    if is_processed:
        print("❌ Job already processed. Skipping.")
        return
    print("✅ Job is new. Proceeding...")

    # Step B: Fetch all active users
    users = await relational_db.get_all_users()
    
    for user in users:
        print(f"\n🔍 Evaluating job for User {user.user_id}...")
        
        # Step C: Rule-Based Filtering
        passes_rules = await RuleBasedFilter.evaluate(mock_job, user)
        if not passes_rules:
            print("❌ Failed rule-based filtering (Budget/Keywords).")
            continue
        print("✅ Passed rule-based filtering.")

        # Step D: Vector Similarity
        job_embedding = await embedder.generate_embedding(mock_job.description)
        similarity = await vector_db.check_similarity(user.user_id, job_embedding)
        print(f"📊 Vector Similarity Score: {similarity:.2f} (Threshold: {user.similarity_threshold})")
        
        if similarity >= user.similarity_threshold:
            print("✅ Passed vector similarity threshold. Calling Groq LLM...")
            
            # Step E: LLM Evaluation
            llm_result = await llm_evaluator.evaluate_job(mock_job, user)
            
            if llm_result:
                print("\n🎉 SUCCESS! TELEGRAM BOT SHOULD SEND THIS:")
                print("-" * 50)
                print(f"Match Score: {llm_result.match_score}/100")
                print(f"Summary: {llm_result.one_line_summary}")
                print("Top Reasons:")
                for i, reason in enumerate(llm_result.top_3_reasons, 1):
                    print(f" {i}. {reason}")
                print("-" * 50)
            else:
                print("❌ LLM Evaluation failed or returned None.")
        else:
            print("❌ Failed vector similarity threshold.")

if __name__ == "__main__":
    asyncio.run(test_pipeline())