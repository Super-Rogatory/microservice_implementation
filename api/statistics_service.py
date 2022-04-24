import sqlite3
import uuid
from contextlib import closing, contextmanager
from fastapi import FastAPI, HTTPException, Depends
from utils import (
    start_connection,
    validate_game_result,
    get_streak,
    get_guesses,
    analyze_guess_data,
    filter_top_wins,
)
from pydantic import BaseModel, BaseSettings


# defines a valid game in request body
class Game(BaseModel):
    game_id: int
    finished: str
    guesses: int
    game_status: bool


# Allows us to retrieve NAME_OF_DB from Procfile
class Settings(BaseSettings):
    name_of_db: str


# Connect to necessary dependencies
app = FastAPI()
settings = Settings()
users_db = start_connection("users")
shard_connections = [
    (start_connection("stats_1"), "games_1"),
    (start_connection("stats_2"), "games_2"),
    (start_connection("stats_3"), "games_3"),
]


@contextmanager
def get_db():
    with closing(start_connection(settings.name_of_db)) as db:
        yield db


# CREATE TABLE games(
#     user_id INTEGER NOT NULL,
#     game_id INTEGER NOT NULL,
#     finished DATE DEFAULT CURRENT_TIMESTAMP,
#     guesses INTEGER,
#     won BOOLEAN,
#     PRIMARY KEY(user_id, game_id),
#     FOREIGN KEY(user_id) REFERENCES users(user_id)
# );

# So we can see the uuid in the terminal!
sqlite3.register_converter("GUID", lambda b: uuid.UUID(bytes_le=b))
sqlite3.register_adapter(uuid.UUID, lambda u: bytes(u.bytes_le))

# every route connects to a db, depending on env
@app.get("/statistics/top_ten_in_wins")
async def get_top_ten_in_wins():
    shard_scan_results = []
    names = []
    try:
        users_cur = users_db.cursor()
        for (connection, _) in shard_connections:
            cur = connection.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            cur.execute("""SELECT * FROM wins ORDER BY "COUNT(won)" DESC LIMIT 10""")
            shard_scan_results.append(cur.fetchall())
        filtered_list = filter_top_wins(shard_scan_results)  # utilizing helper function
        for (guid, _) in filtered_list:
            users_cur.execute(
                f"SELECT username FROM users WHERE guid=:id", {"id": guid}
            )
            name = users_cur.fetchone()[0]
            names.append(name)
        print(names)
    except Exception as e:
        print(f"An error has occured! => {e}")


# @app.get("/statistics/top_ten_in_streaks")
# async def get_top_ten_in_streaks():
#     # don't user get_db here
#     # c = db.cursor()
#     # c.execute(
#     #     """
#     #         SELECT username FROM users JOIN streaks USING(user_id) ORDER BY streak DESC LIMIT 10
#     #     """
#     # )
#     # res = c.fetchall()
#     # return {"users": res}


# @app.get("/statistics/{user_id}")
# async def get_statistics(user_id: int, db: sqlite3.Connection = Depends(get_db)):
#     # execute query to finished|guesses|won
#     c = db.cursor()
#     c.execute(
#         """
#             SELECT finished, guesses, won
#             FROM games g
#             WHERE user_id=:uid
#             ORDER BY finished
#         """,
#         {"uid": user_id},
#     )
#     res = c.fetchall()
#     # use helper functions to parse data instead of making extra calls to db
#     (cur_streak, max_streak) = get_streak(res)
#     guesses = get_guesses(res)
#     (win_percentage, games_played, games_won, avg_guesses) = analyze_guess_data(guesses)
#     return {
#         "stats": {
#             "currentStreak": cur_streak,
#             "maxStreak": max_streak,
#             "guesses": guesses,
#             "winPercentage": win_percentage,
#             "gamesPlayed": games_played,
#             "gamesWon": games_won,
#             "averageGuesses": avg_guesses,
#         }
#     }


# """
# CREATE TABLE games(
#     user_id INTEGER NOT NULL,
#     game_id INTEGER NOT NULL,
#     finished DATE DEFAULT CURRENT_TIMESTAMP,
#     guesses INTEGER,
#     won BOOLEAN,
#     PRIMARY KEY(user_id, game_id),
#     FOREIGN KEY(user_id) REFERENCES users(user_id)
# );
# """


# @app.post("/statistics/game_result/{user_id}")
# async def game_result(
#     user_id: int, game: Game, db: sqlite3.Connection = Depends(get_db)
# ):
#     c = db.cursor()
#     # validate query
#     isValid = validate_game_result(game.game_status, game.finished, game.guesses)
#     if not isValid:
#         raise HTTPException(status_code=400, detail="Query is invalid.")

#     # avoiding duplicate dates - doesn't make sense for wordle game.
#     c.execute(
#         "SELECT * FROM games WHERE finished=:date_finished AND user_id=:uid",
#         {"date_finished": game.finished, "uid": user_id},
#     )
#     res = c.fetchall()
#     if len(res):
#         raise HTTPException(status_code=400, detail="Duplicate dates error.")

#     # uid and gid uniquely identify game, update properties
#     c.execute(
#         """
#             INSERT INTO games
#             VALUES (:uid, :gid, :finished, :guesses, :won)
#         """,
#         {
#             "uid": user_id,
#             "gid": game.game_id,
#             "finished": game.finished,
#             "guesses": game.guesses,
#             "won": game.game_status,
#         },
#     )
#     db.commit()
#     # retreive information after update to ensure it has updated.
#     c.execute(
#         "SELECT * FROM games WHERE game_id=:gid AND user_id=:uid",
#         {"gid": game.game_id, "uid": user_id},
#     )
#     res = c.fetchone()

#     return {"gameResults": res}
