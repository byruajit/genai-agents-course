# Python for agents — the six patterns (one page)

| # | Pattern | Shape | Where you meet it |
|---|---|---|---|
| 1 | Errors as data | `try: ... except Exception as e: return {"error": str(e)}` | Every tool; the agent loop never crashes |
| 2 | Registry + kwargs | `FUNCS = {"name": fn}; FUNCS[name](**args)` | Tool dispatch in the ReAct loop |
| 3 | Decorator | `def deco(fn): def wrapper(*a, **k): ...; return wrapper` | `@tool`, `@function_tool` in SDKs |
| 4 | Typing for state | `class S(TypedDict): x: int` · `Annotated[list, add_messages]` · `Literal["a","b"]` | LangGraph state and routers |
| 5 | Pydantic | `class M(BaseModel): amount: int = Field(gt=0)` → `M(**data)` coerces or raises | Validating tool arguments |
| 6 | JSON | `json.loads(s) -> dict` · `json.dumps(d) -> str` · strip ``` fences first | Tool arguments in, results out |

Rule for the whole course: every Python command starts with `uv run`.
