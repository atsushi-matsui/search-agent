from fastapi import APIRouter, HTTPException

from app.agents.orchestrator import SearchOrchestrator
from app.core.redis import redis_client
from app.models.search import SearchRequest, SearchResponse
from app.models.user import QueryHistory, UserPreferenceData

router = APIRouter(prefix="/search", tags=["search"])

orchestrator = SearchOrchestrator(index_name="movies")


@router.post("", response_model=SearchResponse)
async def search_agent(request: SearchRequest) -> SearchResponse:
    """AI Agentによる検索"""
    try:
        response = orchestrator.search(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/preference")
async def get_user_preference(user_id: str) -> UserPreferenceData | dict:
    """ユーザー嗜好を取得"""
    preference = redis_client.get_user_preference(user_id)
    if preference is None:
        return {"message": "ユーザー嗜好データがありません", "user_id": user_id}
    return preference


@router.get("/user/{user_id}/history")
async def get_user_query_history(user_id: str, limit: int = 20) -> list[QueryHistory]:
    """ユーザーの検索クエリ履歴を取得"""
    return redis_client.get_query_history(user_id, limit)


@router.delete("/user/{user_id}")
async def delete_user_data(user_id: str) -> dict:
    """ユーザーデータを削除"""
    redis_client.delete_user_data(user_id)
    return {"message": "ユーザーデータを削除しました", "user_id": user_id}
