import os
import asyncio
import json
from typing import List, Dict
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


# ✅ Schema chuẩn
class Blog(BaseModel):
    url: str = Field(..., description="The url of the article.")
    title: str = Field(..., description="The title of the article.")
    date: str = Field(..., description="The published date in MM-DD-YY.")
    author: str = Field(..., description="The author name or 'staff'")
    content: str = Field(..., description="The original article body, not summarized.")


# ✅ Cấu hình crawler 1 lần, dùng lại cho nhiều URL
markdown_generator = DefaultMarkdownGenerator(
    content_filter=PruningContentFilter(threshold=0.8)
)

llm_strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(
        provider="gemini/gemini-2.0-flash-001",
        api_token='AIzaSyCvSWj5RjXFhZ5rSNd-czRyyTHmt6E8R3o'
    ),
    schema=Blog.model_json_schema(),
    extraction_type="schema",
    instruction="""
You are given the cleaned markdown of a news article webpage.

Your task is to extract:

- url: the article's URL
- title: the main article title (usually large header)
- date: publication date in MM-DD-YY format
- author: name of the article's author (use "staff" if missing)
- content: the entire original article body as-is, without summarizing or rewriting. Keep all paragraphs in the original form.

⚠️ Do NOT summarize, paraphrase, or rewrite the content. Extract exactly the original paragraph-level text that constitutes the main body of the article.

Exclude menus, sidebars, ads, comments, related articles, or download links.
Return valid JSON matching the schema.
    """,
    
    chunk_token_threshold=1500,
    apply_chunking=False,
    input_format="markdown",
    use_prompt_template=False,
    extra_args={"temperature": 0.0, "top_p": 0.9, "max_tokens": 4000}
)

run_conf = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    markdown_generator=markdown_generator,
    extraction_strategy=llm_strategy,
    page_timeout=30000
)


# ✅ Hàm xử lý từng URL
async def extract_from_url(crawler: AsyncWebCrawler, url: str) -> Dict:
    result = await crawler.arun(url=url, config=run_conf)

    if result and result.success:
        try:
            data = json.loads(result.extracted_content)
            return {
                "url": url,
                "title": data[0].get("title") if isinstance(data, list) else None,
                "date": data[0].get("date") if isinstance(data, list) else None,
                "author": data[0].get("author") if isinstance(data, list) else None,
                "content": data[0].get("content") if isinstance(data, list) else None,
                "error": None
            }
        except Exception as e:
            return {
                "url": url,
                "title": None,
                "date": None,
                "author": None,
                "content": None,
                "error": f"JSON decode error: {str(e)}"
            }
    else:
        return {
            "url": url,
            "title": None,
            "date": None,
            "author": None,
            "content": None,
            "error": result.error_message if result else "Unknown error"
        }


# ✅ Hàm chạy hàng loạt URL song song
async def run_bulk_extraction(urls: List[str]):
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        tasks = [extract_from_url(crawler, url) for url in urls]
        results = await asyncio.gather(*tasks)

    # ✅ In từng kết quả ra màn hình
    for idx, item in enumerate(results):
        print(f"\n📄 Result {idx+1}/{len(urls)}:")
        print(json.dumps(item, indent=2, ensure_ascii=False))

    # ✅ Ghi file JSON
    with open("extracted_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Finished extracting {len(urls)} URLs. Results saved to 'extracted_results.json'")
    return results


if __name__ == "__main__":
    # 🔗 Danh sách URL để xử lý
    urls = [
        "https://vnexpress.net/ty-phu-cong-nghe-my-goc-an-ai-gioi-hon-nhung-gia-su-dat-nhat-4923102.html"
        # ... thêm bao nhiêu tuỳ bạn
    ]

    asyncio.run(run_bulk_extraction(urls))
