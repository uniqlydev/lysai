from core.memory import log_episode, search_similar, recent_successes

ep = log_episode(
    question="Top 5 cities by revenue?",
    plan={"steps":["join payment→rental→customer→address→city","group/order/limit"]},
    sql="SELECT ...",
    rows=[{"city":"Aurora","revenue":1234.56}],
    outcome="success",
    insight="Aurora leads the ranking."
)
print("episode:", ep)
print("search_similar:", search_similar("cities revenue"))
print("recent_successes:", recent_successes())