# LLM Logic

## Agent Roles

- **Planner** – `GPTClient.get_workflow()` asks the model which tools to call.
- **Executor** – `Functions.execute_workflow()` performs API calls (Google, Spotify, timers) and feeds results back.
- **Validator** – after tool execution, the conversation manager checks outputs before sending them to the user.

## Prompt Engineering

Example system prompt used when announcing tool execution:

```
{"role": "system", "content": "Act as Weatly from portal 2. in 10 words summarize the function call as if you are doing what it says..."}
```

Temperature and model are configured in `config.yaml`; default model is `gpt-4o-mini`.

## Decision Workflow

```
User message
  |
  v
ConversationManager -> GPTClient.get_workflow()
  |
  v
Functions.execute_workflow() -- may schedule timers or call APIs
  |
  v
GPTClient.get_text() -> final assistant reply
  |
  +--> GPTClient.reply_with_animation() -> servo mood
```

The result is parsed to extract text and animation. If parsing fails, a fallback animation of `neutral` is used and the text "Sorry, I didn't get that" is returned.

## Fallback & Error Handling

- Retries up to three times when the OpenAI API fails
- Emotion counters stored in `emotion_counter.json` prevent repetitive moods
- Dry-run mode for hardware avoids crashes when serial ports are missing
