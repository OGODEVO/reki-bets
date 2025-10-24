import os
from client import nba_client

def get_daily_schedule(year: int, month: int, day: int) -> dict:
    """Fetches the NBA daily schedule for a given date."""
    endpoint = f"games/{year}/{month}/{day}/schedule.json"
    return nba_client._make_request(endpoint)

def get_daily_injuries(year: int, month: int, day: int) -> dict:
    """Fetches the NBA daily injuries for a given date."""
    endpoint = f"league/{year}/{month}/{day}/daily_injuries.json"
    return nba_client._make_request(endpoint)

def get_game_summary(game_id: str) -> dict:
    """Fetches the game summary for a given game_id."""
    endpoint = f"games/{game_id}/summary.json"
    return nba_client._make_request(endpoint)

def get_seasonal_stats(season_year: str, season_type: str, team_id: str) -> dict:
    """Fetches complete team and player seasonal statistics for a given season and season type."""
    endpoint = f"seasons/{season_year}/{season_type}/teams/{team_id}/statistics.json"
    return nba_client._make_request(endpoint)

def get_teams_list() -> dict:
    """Fetches a list of all NBA teams and their IDs."""
    endpoint = "league/teams.json"
    return nba_client._make_request(endpoint)