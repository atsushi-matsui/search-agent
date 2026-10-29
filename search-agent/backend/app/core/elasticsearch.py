from elasticsearch import Elasticsearch

from app.config import settings


class ElasticsearchClient:
    def __init__(self):
        self.client = Elasticsearch([settings.ELASTICSEARCH_HOST], verify_certs=False)

    def get_client(self) -> Elasticsearch:
        return self.client

    def search(self, index_name: str, query: dict, size: int = 10) -> dict:
        return self.client.search(index=index_name, size=size, **query)

    def get_mapping(self, index_name: str) -> dict:
        return self.client.indices.get_mapping(index=index_name)

    def get_sample_documents(self, index_name: str, size: int = 3) -> list[dict]:
        result = self.client.search(
            index=index_name, query={"match_all": {}}, size=size
        )
        return [hit["_source"] for hit in result["hits"]["hits"]]


es_client = ElasticsearchClient()
