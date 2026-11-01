# rag_knowledge.py
import os
import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from config import CFG

class IndustrialKnowledgeBase:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=CFG.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="industrial_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, chunk_overlap=100,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""]
        )

    def ingest_file(self, file_path: str):
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
        chunks = self.splitter.split_documents(docs)
        for i, chunk in enumerate(chunks):
            doc_id = f"{os.path.basename(file_path)}_{i}"
            self.collection.upsert(
                documents=[chunk.page_content],
                metadatas=[{"source": os.path.basename(file_path)}],
                ids=[doc_id]
            )
        print(f"  ✅ {os.path.basename(file_path)}: {len(chunks)} 片段")

    def ingest_directory(self, dir_path: str):
        for f in os.listdir(dir_path):
            if f.endswith((".txt", ".md")):
                self.ingest_file(os.path.join(dir_path, f))

    def search(self, query: str, top_k: int = 3) -> str:
        results = self.collection.query(query_texts=[query], n_results=top_k)
        if not results["documents"] or not results["documents"][0]:
            return "知识库中未找到相关信息"
        chunks = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            chunks.append(f"[来源: {meta.get('source', '未知')}]\n{doc}")
        return "\n\n---\n\n".join(chunks)


_kb = None
def get_knowledge_base() -> IndustrialKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = IndustrialKnowledgeBase()
    return _kb

def retrieve_context(event_desc: str) -> str:
    return get_knowledge_base().search(event_desc, top_k=3)