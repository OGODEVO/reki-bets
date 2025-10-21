# Reki-Bets AI Agent

This is an AI agent that provides sports betting analysis for the NFL and NBA. It uses a variety of tools to gather information about games, teams, and players, and then provides a recommendation on which team to bet on.

## Tools

### NFL Tools
- **find_game_by_teams_and_date**: Finds a specific NFL game by team names and date.
- **get_current_week_schedule**: Retrieves the NFL schedule for the current week.
- **get_game_statistics**: Retrieves statistics for a specific NFL game.
- **get_game_roster**: Retrieves the roster for a specific NFL game.
- **get_team_season_stats**: Retrieves the seasonal statistics for a specific NFL team.

### NBA Tools
- **get_daily_schedule**: Fetches the NBA daily schedule for a given date.
- **get_daily_injuries**: Fetches the NBA daily injuries for a given date.
- **get_game_summary**: Fetches the game summary for a given game_id.

### Betting Odds Tools
- **get_daily_schedule_odds**: Fetches the daily schedule for a given sport, returning a list of scheduled events and their unique sport_event_id.
- **get_sport_event_markets**: Fetches and filters the available pre-match markets (moneyline, spread, total) for a specific sport event.

## Workflows

### Fetching All Betting Odds (NFL & NBA)
1.  **Get Event ID:** You MUST start by calling `get_daily_schedule_odds` with the correct `sport_name` and `date` to find the game's unique `sport_event_id`.
2.  **Get Market Odds:** You MUST use the `sport_event_id` from Step 1 as the input for `get_sport_event_markets`.

### Analyzing a Specific NFL Game
1.  **Find the Game:** You MUST use `find_game_by_teams_and_date` with the two team names and the date to get the correct `game_id`.
2.  **Get Team Stats:** You MUST call `get_team_season_stats` for both teams to get their seasonal statistics.
3.  **Use Game ID:** Once you have the `game_id`, you can then call `get_game_statistics` or `get_game_roster`.

### Analyzing a Specific NBA Game
1.  **Get Game ID:** You MUST first call `get_daily_schedule` to find the correct `game_id`.
2.  **Check Injuries:** Your second step is ALWAYS to call `get_daily_injuries` for the same date.
3.  **Use Game ID:** Once you have the `game_id`, you can then call `get_game_summary`.
