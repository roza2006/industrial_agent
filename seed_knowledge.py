# seed_knowledge.py
from rag_knowledge import get_knowledge_base
from config import CFG

if __name__ == "__main__":
    kb = get_knowledge_base()
    print(f"导入知识库目录: {CFG.knowledge_dir}")
    kb.ingest_directory(CFG.knowledge_dir)
    print("✅ 知识库导入完成")