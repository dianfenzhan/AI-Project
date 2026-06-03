from typing import List, Dict, Any
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from elasticsearch import Elasticsearch
from .config import Config
from .embedding import EmbeddingService

class VectorStore:
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
    
    def create_collection(self, collection_name: str, tenant_id: str = "default"):
        collection = f"{collection_name}_{tenant_id}"
        
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
            es_mappings = {
                "mappings": {
                    "properties": {
                        "text": {"type": "text", "analyzer": "standard"},
                        "metadata": {"type": "object"}
                    }
                }
            }
            self.es_client.indices.create(index=collection, body=es_mappings)
        self.es_index = collection
    
    def insert_documents(self, docs: List[Dict[str, Any]], collection_name: str, tenant_id: str = "default"):
        self.create_collection(collection_name, tenant_id)
        
        texts = [doc["text"] for doc in docs]
        embeddings = self.embedding_service.embed_texts(texts)
        # 在 metadata 中冗余 tenant_id，便于排查与二次校验（物理隔离由独立索引/集合保证）
        metadatas = []
        for doc in docs:
            md = dict(doc.get("metadata", {}))
            md["tenant_id"] = tenant_id
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
        collection = f"{collection_name}_{tenant_id}"
        if utility.has_collection(collection):
            self.milvus_collection = Collection(name=collection)
            self.milvus_collection.load()
            self.es_index = collection
        else:
            raise ValueError(f"Collection {collection} not found")
