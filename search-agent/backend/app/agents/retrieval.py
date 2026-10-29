from app.agents.base import BaseAgent
from app.core.elasticsearch import es_client
from app.models.query import ElasticsearchDSL
from app.models.search import Movie


class RetrievalAgent(BaseAgent):
    """Elasticsearchから検索結果を取得するエージェント"""

    def __init__(self, index_name: str = "movies"):
        super().__init__("RetrievalAgent")
        self.index_name = index_name

    def execute(self, dsl: ElasticsearchDSL) -> list[Movie]:
        self.log_step("Elasticsearch検索を開始")
        self.log_input({"index": self.index_name, "size": dsl.size})

        query_body = {"query": dsl.query}
        if dsl.sort:
            query_body["sort"] = dsl.sort

        self.log_step("ESクエリを実行")
        result = es_client.search(self.index_name, query_body, size=dsl.size)

        total_hits = result["hits"]["total"]["value"]
        self.log_step(f"検索完了: total_hits={total_hits}, returned={len(result['hits']['hits'])}")

        movies = []
        for hit in result["hits"]["hits"]:
            source = hit["_source"]
            movie = Movie(
                id=str(hit["_id"]),
                title=source.get("title", ""),
                original_title=source.get("original_title", ""),
                overview=source.get("overview", ""),
                genres=source.get("genres", []),
                popularity=source.get("popularity", 0.0),
                vote_average=source.get("vote_average", 0.0),
                release_date=source.get("release_date", ""),
                homepage=source.get("homepage", ""),
                poster_path=source.get("poster_path", ""),
                backdrop_path=source.get("backdrop_path", ""),
                score=hit.get("_score", 0.0),
            )
            movies.append(movie)

        self.log_step(f"取得結果: {len(movies)}件")
        for i, m in enumerate(movies[:5], 1):
            self.logger.info(f"  {i}. {m.title} (score={m.score:.2f}, genres={m.genres})")
        if len(movies) > 5:
            self.logger.info(f"  ... (他 {len(movies) - 5}件)")

        return movies
