from typing import List, Dict, Any
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from elasticsearch import Elasticsearch
from .config import Config
from .embedding import EmbeddingService


class VectorStore:
    """向量 + 全文双存储。

    文档两级权限：
    - 系统级（scope=system）：写入 tenant_id = Config.SYSTEM_TENANT_ID 的共享集合，所有租户可检索。
    - 租户级（scope=tenant）：写入各租户自己的集合，仅该租户可检索。

    集合/索引命名：f"{collection_name}_{tenant_id}"，物理隔离不同租户的数据。
    """

    def __init__(self):
        self.milvus_host = Config.MILVUS_HOST
        self.milvus_port = Config.MILVUS_PORT
        self.es_host = Config.ES_HOST
        self.es_port = Config.ES_PORT
        self.embedding_dim = Config.EMBEDDING_DIM

        self._connect_milvus()
        self._connect_es()
        self.embedding_service = EmbeddingService()

    def _connect_milvus(self):
        connections.connect("default", host=self.milvus_host, port=self.milvus_port)

    def _connect_es(self):
        self.es_client = Elasticsearch([f"http://{self.es_host}:{self.es_port}"])

    @staticmethod
    def resolve_tenant_id(scope: str, tenant_id: str) -> str:
        """根据 scope 解析真实存储用的 tenant 标识。

        system -> 固定的系统租户标识（共享）；tenant -> 调用方传入的 tenant_id。
        """
        if scope == Config.SCOPE_SYSTEM:
            return Config.SYSTEM_TENANT_ID
        return tenant_id

    @staticmethod
    def collection_id(collection_name: str, tenant_id: str) -> str:
        profile = Config.INDEX_PROFILE.strip()
        base = f"{collection_name}_{tenant_id}"
        return f"{base}_{profile}" if profile else base

    def create_collection(self, collection_name: str, tenant_id: str = "default"):
        collection = self.collection_id(collection_name, tenant_id)

        if not utility.has_collection(collection):
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            schema = CollectionSchema(fields, description=f"Document chunks for tenant {tenant_id}")
            self.milvus_collection = Collection(name=collection, schema=schema)

            index_params = {
                "metric_type": "COSINE",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            self.milvus_collection.create_index("embedding", index_params)
        else:
            self.milvus_collection = Collection(name=collection)

        if not self.es_client.indices.exists(index=collection):
            # 中英双语：standard 照顾英文，text.cjk 照顾中文分词（无需 IK 插件）
            es_mappings = {
                "mappings": {
                    "properties": {
                        "text": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "cjk": {"type": "text", "analyzer": "cjk"},
                            },
                        },
                        "metadata": {"type": "object"},
                    }
                }
            }
            self.es_client.indices.create(index=collection, body=es_mappings)
        self.es_index = collection

    def insert_documents(
        self,
        docs: List[Dict[str, Any]],
        collection_name: str,
        tenant_id: str = "default",
        scope: str = Config.SCOPE_TENANT,
    ):
        store_tenant_id = self.resolve_tenant_id(scope, tenant_id)
        self.create_collection(collection_name, store_tenant_id)

        texts = [doc["text"] for doc in docs]
        embeddings = self.embedding_service.embed_texts(texts)
        # metadata 冗余 scope / tenant / collection，便于排查与二次校验（物理隔离由独立集合保证）
        metadatas = []
        for doc in docs:
            md = dict(doc.get("metadata", {}))
            md["scope"] = scope
            md["tenant_id"] = tenant_id
            md["store_tenant_id"] = store_tenant_id
            md["collection_name"] = collection_name
            metadatas.append(md)

        milvus_docs = []
        for text, embedding, metadata in zip(texts, embeddings, metadatas):
            milvus_docs.append({
                "text": text,
                "embedding": embedding,
                "metadata": metadata
            })
        self.milvus_collection.insert(milvus_docs)
        self.milvus_collection.flush()

        for text, metadata in zip(texts, metadatas):
            self.es_client.index(
                index=self.es_index,
                document={
                    "text": text,
                    "metadata": metadata,
                }
            )
        self.es_client.indices.refresh(index=self.es_index)

    def load_collection(self, collection_name: str, tenant_id: str = "default"):
        collection = self.collection_id(collection_name, tenant_id)
        if utility.has_collection(collection):
            self.milvus_collection = Collection(name=collection)
            self.milvus_collection.load()
            self.es_index = collection
        else:
            raise ValueError(f"Collection {collection} not found")

    # ---------------- 按 (collection, tenant) 维度的只读检索（支持跨 scope 合并） ----------------

    def search_milvus(
        self,
        query_embedding: List[float],
        collection_name: str,
        tenant_id: str,
        top_k: int = None,
    ) -> List[Dict[str, Any]]:
        top_k = top_k or Config.RECALL_TOP_K
        collection = self.collection_id(collection_name, tenant_id)
        if not utility.has_collection(collection):
            return []

        col = Collection(name=collection)
        col.load()
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        results = col.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["text", "metadata"],
        )

        docs = []
        for hit in results[0]:
            docs.append({
                "text": hit.entity.get("text"),
                "metadata": hit.entity.get("metadata"),
                "score": float(hit.score),
                "source": "milvus",
            })
        return docs

    def search_es(
        self,
        query: str,
        collection_name: str,
        tenant_id: str,
        top_k: int = None,
    ) -> List[Dict[str, Any]]:
        top_k = top_k or Config.RECALL_TOP_K
        collection = self.collection_id(collection_name, tenant_id)
        if not self.es_client.indices.exists(index=collection):
            return []

        results = self.es_client.search(
            index=collection,
            query={
                "multi_match": {
                    "query": query,
                    "fields": ["text", "text.cjk"],
                    "type": "best_fields",
                }
            },
            size=top_k,
        )

        docs = []
        for hit in results["hits"]["hits"]:
            docs.append({
                "text": hit["_source"]["text"],
                "metadata": hit["_source"].get("metadata", {}),
                "score": float(hit["_score"]),
                "source": "elasticsearch",
            })
        return docs
