from backend.config import settings


def is_influencer(follower_count: int) -> bool:
    return follower_count >= settings.INFLUENCER_FOLLOWER_THRESHOLD
