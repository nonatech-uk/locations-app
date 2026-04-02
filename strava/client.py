"""Strava API client with OAuth token refresh."""

import time
import httpx

STRAVA_AUTH_URL = "https://www.strava.com/oauth/token"
STRAVA_API_URL = "https://www.strava.com/api/v3"


class StravaClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token: str | None = None
        self.token_expires_at: int = 0
        self._http = httpx.Client(timeout=30)

    def _ensure_token(self):
        """Refresh access token if expired or missing."""
        if self.access_token and time.time() < self.token_expires_at - 60:
            return

        resp = self._http.post(STRAVA_AUTH_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.token_expires_at = data["expires_at"]

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        self._ensure_token()
        resp = self._http.get(
            f"{STRAVA_API_URL}{path}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params=params or {},
        )
        resp.raise_for_status()
        return resp.json()

    def get_activities(self, after: int | None = None, page: int = 1,
                       per_page: int = 200) -> list[dict]:
        """Fetch athlete activities. Returns list of activity summaries."""
        params = {"page": page, "per_page": per_page}
        if after is not None:
            params["after"] = after
        return self._get("/athlete/activities", params)

    def get_activity(self, activity_id: int) -> dict:
        """Fetch detailed activity by ID."""
        return self._get(f"/activities/{activity_id}")

    def get_all_activities(self, after: int | None = None) -> list[dict]:
        """Paginate through all activities since `after` timestamp."""
        all_activities = []
        page = 1
        while True:
            batch = self.get_activities(after=after, page=page, per_page=200)
            if not batch:
                break
            all_activities.extend(batch)
            print(f"  Fetched page {page}: {len(batch)} activities")
            if len(batch) < 200:
                break
            page += 1
        return all_activities

    def close(self):
        self._http.close()
