# Mini-Project 1 — report

Write every section in your own words. Each section needs at least a few real sentences: replace every line that
starts with `TODO`. The checker reads this file, and at the demo you explain any section the instructor picks.

## 1. Me, and how I used AI
TODO: your name and GitHub username. Then an honest AI-use log: which tool (ChatGPT, Copilot, Claude...), for which
task, and ONE suggestion you rejected or corrected, and why. Using AI is allowed; not understanding your own code
is not. (Never paste your .env or a key into any AI tool.)

## 2. How a request flows
TODO: follow ONE message, e.g. "Can I return the shoes in ORD-10231?", from `POST /chat/stream` to the last SSE
event. Name the functions it passes through, where memory, the system prompt and the tools come in, and the hop
through the gateway (which container calls which, on which URL).

## 3. Memory: my choice, with numbers
TODO: window or summary, and your KEEP_TURNS. Use numbers from your Session 19 report (tokens per call, recall at
turn 17), and say what your choice forgets, or risks getting wrong. What would a customer notice?

## 4. Tools and validation
TODO: your three tools and what you validate (order id format, pincode, speed, reason). Give one bad argument your
validation catches, and what the model did after it got the INVALID message (from a real run).

## 5. Defending the prompt
TODO: summarise your Security rules section. Which of the four attacks came closest to working, and why? If any
attack broke through, what did you change, and did it help?

## 6. Results
TODO: copy the Summary block from experiments/mp1_results.md. Then explain at least TWO golden questions that
failed, or would fail on a smaller model: was it the wrong tool, a wrong argument, or the wording?

## 7. Gateway, Docker and honest limits
TODO: what the gateway gives you that calling Groq directly wouldn't (one header you saw, and the fallback). Then
at least three things that would break in production (think: memory in RAM, session ids, one master key, one
server, the model inventing things) and what you would do about each one.
