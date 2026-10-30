# S21 version card — paste this into ChatGPT (or any AI assistant) BEFORE you ask for help

ChatGPT learned LangChain from years of old tutorials. Without this card it usually writes code for old LangChain
versions (`LLMChain`, `ConversationBufferMemory`, `initialize_agent`, `from langchain.chat_models import ...`) that
**will not run** in this course. Copy everything in the box below, paste it as your first message, then ask your
question underneath it.

```text
I am a student working in Python 3.12 with these exact versions:
  langchain==1.4.7, langchain-core==1.7.3, langchain-openai==1.1.9, openai 1.x, python-dotenv.

Use ONLY these imports and APIs:
  from langchain_openai import ChatOpenAI
  from langchain_core.prompts import ChatPromptTemplate
  from langchain_core.output_parsers import StrOutputParser
  from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
  from langchain_core.tools import tool            # use @tool(parse_docstring=True)
  llm = ChatOpenAI(model=..., base_url=..., api_key=..., temperature=0)
  chain = prompt | llm | StrOutputParser()          # LCEL pipe
  llm_with_tools = llm.bind_tools([...])
  ai = llm_with_tools.invoke(messages); ai.tool_calls  # list of dicts: name, args, id
  tool_message = my_tool.invoke(tool_call)          # returns a ToolMessage with the matching id

Do NOT use: LLMChain, ConversationChain, ConversationBufferMemory, initialize_agent, AgentExecutor,
create_react_agent, langchain.chat_models, langchain.llms, langchain_community, or .run()/.predict().
I write my own tool loop with a step cap - do not replace it with an agent.

Explain what each line does. Do not rewrite my whole file - show only the lines I need to change.

My question:
```

## Three rules for today
1. **Never paste your `.env` file or your API key** into any chat. Not even "just to check".
2. **Ask it to explain or fix *your* code**, not to write the whole file. You will be asked to explain your code at the exit check.
3. **If its answer imports something on the "do not use" list, it ignored the card.** Paste the card again and say "use only the APIs on the card".
