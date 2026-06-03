import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from RAG import (
    DocumentProcessor, TextChunker,
    VectorStore, RetrievalEngine, RerankService,
)
from DAG import SEOWorkflow


app = FastAPI(title="SEO RAG API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_store = VectorStore()
rerank_service = RerankService()
retrieval_engine = RetrievalEngine(vector_store)
document_processor = DocumentProcessor()
text_chunker = TextChunker()
seo_workflow = SEOWorkflow(vector_store)


class SearchRequest(BaseModel):
    query: str
    tenant_id: str = "default"
    collection_name: str = "default"


class GenerateStartRequest(BaseModel):
    topic: str
    keywords: str
    tenant_id: str = "default"
    collection_name: str = "default"
    llm_provider: str = "deepseek"


class ChooseTitleRequest(BaseModel):
    thread_id: str
    selected_title: str


class ChooseOutlineRequest(BaseModel):
    thread_id: str
    selected_outline: str


@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    tenant_id: str = Form("default"),
    collection_name: str = Form("default"),
):
    """上传文档并索引。tenant_id / collection_name 通过 Form 传入，保证租户隔离生效。"""
    try:
        upload_dir = Path("uploads") / tenant_id / collection_name
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file.filename

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        text = document_processor.load_document(str(file_path))
        docs = [{"text": text, "metadata": {"filename": file.filename, "tenant_id": tenant_id}}]
        chunks = text_chunker.chunk_documents(docs)
        vector_store.insert_documents(chunks, collection_name, tenant_id)

        return {
            "status": "success",
            "message": "Document uploaded and indexed successfully",
            "tenant_id": tenant_id,
            "collection_name": collection_name,
            "chunks_count": len(chunks),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search")
async def search(request: SearchRequest):
    """双路召回 + 重排，返回 Top-K。"""
    try:
        docs = retrieval_engine.hybrid_search(
            request.query, request.collection_name, request.tenant_id
        )
        reranked = rerank_service.rerank(request.query, docs)
        return {"status": "success", "results": reranked}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/titles")
async def generate_titles(request: GenerateStartRequest):
    """第一步：基于 RAG + SerpAPI 生成 5 个标题，返回 thread_id 用于后续步骤。"""
    try:
        thread_id = uuid.uuid4().hex
        initial_state = {
            "topic": request.topic,
            "keywords": request.keywords,
            "tenant_id": request.tenant_id,
            "collection_name": request.collection_name,
            "llm_provider": request.llm_provider,
        }
        titles = seo_workflow.start(initial_state, thread_id)
        return {"status": "success", "thread_id": thread_id, "titles": titles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/outlines")
async def generate_outlines(request: ChooseTitleRequest):
    """第二步：用户选定标题后，生成 3 套大纲。"""
    try:
        outlines = seo_workflow.choose_title(request.thread_id, request.selected_title)
        return {"status": "success", "thread_id": request.thread_id, "outlines": outlines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/article")
async def generate_article(request: ChooseOutlineRequest):
    """第三步：用户选定大纲后，生成完整文章。"""
    try:
        article = seo_workflow.choose_outline(request.thread_id, request.selected_outline)
        return {"status": "success", "thread_id": request.thread_id, "article": article}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
