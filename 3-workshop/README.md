# Singapore Outing Planner (proof of concept)

Helps you plan an outing by checking weather, haze and route. Tools are blocked if agent does not have permission.

Tell if where you would like to go: Eg. "Gardens by the Bay now, from Tampines Mall". Each of the 3 agents check live data (weather, haze, route), and a Trip Planner decides who speaks next. After each round, it gives you a recommendation.


## The agents and their tools

| Agent | Role | Tool | Data source |
|---|---|---|---|
| Hui Min | Weather Forecaster | `weather` | NEA 24-hour forecast (data.gov.sg, no key) |
| Dr. Farah | Health & Safety Officer | `haze` | NEA PSI readings (data.gov.sg, no key) |
| Ravi | Getting-there Guide | `journey` | OneMap public transport routes (free account, token) |
| Trip Planner | Orchestrator | none | picks who speaks next |
| Summarizer | Writes the recommendation after each round | none | |

Each agent can only use its own tool. If an agent asks for another agent's tool, it gets "ACCESS DENIED" and is told to ask that teammate.

## Set up

```sh
uv sync
cp .env.example .env
```

Put your OpenAI key in `.env`.
For journey tool, register for OneMap account at https://www.onemap.gov.sg/apidocs/register, get an API token from your account.
Put into `.env` as `ONEMAP_TOKEN`.

## Run

```sh
uv run python main.py
```

Type your request. The team sends up to 4 messages, then you get a recommendation and it is your
turn again. Type `exit` to finish.