import os
import asyncio
import json
from pydantic import BaseModel, Field
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMConfig
)
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.extraction_strategy import LLMExtractionStrategy


# ✅ Schema: đầy đủ và có hướng dẫn fallback author
class Blog(BaseModel):
    url: str = Field(..., description="The url of the article.")
    title: str = Field(..., description="The title of the article.")
    date: str = Field(..., description="The published date of the article in the format MM-DD-YY.")
    author: str = Field(..., description="The author of the article. If not found, fill with 'staff'.")
    content: str = Field(..., description="The entire body content of the article in paragraph form.")


async def run_optimized_extraction():
    print("\n🚀 Starting Crawl4AI with Optimized LLM Extraction Strategy")

    # 1. Markdown filter để loại bỏ nội dung phụ, đoạn ngắn
    markdown_generator = DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(
            threshold=0.6,
            threshold_type="fixed"
        )
    )

    # 2. LLM extraction strategy với schema + prompt cụ thể
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="gemini/gemini-2.0-flash-001",
            api_token='AIzaSyCvSWj5RjXFhZ5rSNd-czRyyTHmt6E8R3o'  # <-- Thay API key của bạn
        ),
        schema=Blog.model_json_schema(),
        extraction_type="schema",
        instruction="""
You are given the cleaned markdown version of a news article webpage.

Your task is to extract:

- url: the article's URL
- title: the main article title (usually large header)
- date: publication date in MM-DD-YY format
- author: name of the article's author (use "staff" if missing)
- content: **the entire original article body** as-is, without summarizing or rewriting. Keep all paragraphs in the original form.

⚠️ Do NOT summarize, paraphrase, or rewrite the content. Extract exactly the original paragraph-level text that constitutes the main body of the article.

Focus on **actual article content**, ignore sidebars, ads, menus, comments, related links, etc.
Return the result in JSON format matching the given schema.
        """,
        chunk_token_threshold=1200,  # cân bằng giữa ngữ cảnh & độ dài
        apply_chunking=True,
        input_format="markdown",
        use_prompt_template=False,
        extra_args={
            "temperature": 0.0,
            "top_p": 0.9,
            "max_tokens": 2048
        }
    )

    # 3. Run config
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=markdown_generator,
        extraction_strategy=llm_strategy,
        #page_timeout=30000
    )

    # 4. Test URL
    url = "https://insideainews.com/2025/02/06/genai-platform-squirro-reports-nearly-60-growth/"

    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(url=url, config=run_conf)

        if result and result.success:
            print("\n✅ Crawl Successful!")
            print("📄 Markdown Input Preview (first 1000 chars):")
            print(result.markdown.fit_markdown[:1000])

            try:
                extracted = json.loads(result.extracted_content)
                output = {
                    "url": url,
                    "title": extracted[0].get("title") if isinstance(extracted, list) else None,
                    "date": extracted[0].get("date") if isinstance(extracted, list) else None,
                    "author": extracted[0].get("author") if isinstance(extracted, list) else None,
                    "content": extracted[0].get("content") if isinstance(extracted, list) else None,
                    "error": None
                }
            except Exception as e:
                output = {
                    "url": url,
                    "title": None,
                    "date": None,
                    "author": None,
                    "content": None,
                    "error": f"JSON decode error: {str(e)}"
                }
        else:
            output = {
                "url": url,
                "title": None,
                "date": None,
                "author": None,
                "content": None,
                "error": result.error_message if result else "Unknown error"
            }

        print("\n📦 Final Output:")
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run_optimized_extraction())
