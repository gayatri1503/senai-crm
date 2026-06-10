import json
import os
from typing import Optional
from groq import Groq
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tools import (
    tool_get_thread_history,
    tool_get_contact_profile,
    tool_search_knowledge_base,
    tool_escalate_to_human,
    tool_flag_for_legal,
    tool_create_internal_ticket,
    tool_draft_reply,
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MAX_STEPS = 6

AGENT_SYSTEM_PROMPT =AGENT_SYSTEM_PROMPT = """You are an autonomous CRM triage agent.

CRITICAL INSTRUCTION: Output ONLY ONE action per response. Never output multiple actions at once.

Use EXACTLY this format for each response:

Thought: <your reasoning about what to do NEXT — one step only>
Action: <single tool name — exactly as listed below>
Action Input: <valid JSON object for that tool>

When you have taken all necessary actions and are done, use this format:
Thought: I have completed my analysis and all necessary actions have been taken.
Final Answer: <summary of what you found and what actions you took>

## Available tools (use exact names):
- get_thread_history
- get_contact_profile
- search_knowledge_base
- escalate_to_human
- flag_for_legal
- create_internal_ticket
- draft_reply

## Rules:
- NEVER auto-reply to security threats or legal threats
- NEVER output more than one Action per response
- Always start with get_thread_history for any sender with prior emails
- GDPR requests: flag_for_legal AND create_internal_ticket
- Maximum {max_steps} total actions — then escalate_to_human
- Critical urgency: always escalate_to_human, never draft_reply
""".format(max_steps=MAX_STEPS)


async def run_agent(
    email_id: int,
    sender: str,
    subject: str,
    body: str,
    heuristic_flags: dict,
    classification: dict,
    db: AsyncSession,
    dry_run: bool = False,
) -> dict:
    """
    ReAct agent loop.
    Reasons step by step, calls tools, stores reasoning trace.
    Returns full reasoning log.
    """

    reasoning_trace = []
    steps_taken = 0

    # Initial context for the agent
    initial_prompt = f"""Analyse this email and take appropriate actions:

Email ID: {email_id}
From: {sender}
Subject: {subject}
Body: {body}

Pre-classification:
- Category: {classification.get('category')}
- Urgency: {classification.get('urgency')}
- Sentiment: {classification.get('sentiment')}
- Requires human: {classification.get('requires_human')}
- Escalation reason: {classification.get('escalation_reason')}
- Heuristic flags: {json.dumps(heuristic_flags)}

Begin your analysis. Use tools to gather context before deciding on actions.
Remember: get_thread_history first if this sender may have prior emails."""

    messages = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": initial_prompt},
    ]

    final_answer = None

    while steps_taken < MAX_STEPS:
        # Call LLM
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.2,
            max_tokens=800,
        )

        llm_output = response.choices[0].message.content.strip()
        messages.append({"role": "assistant", "content": llm_output})

        # Parse Thought/Action/Final Answer
        if "Final Answer:" in llm_output:
            final_answer = llm_output.split("Final Answer:")[-1].strip()
            reasoning_trace.append({
                "step": steps_taken + 1,
                "type": "final",
                "content": llm_output,
            })
            break

        # Extract action
        action_name, action_input = _parse_action(llm_output)

        if not action_name:
            reasoning_trace.append({
                "step": steps_taken + 1,
                "type": "thought",
                "content": llm_output,
            })
            break

        reasoning_trace.append({
            "step": steps_taken + 1,
            "type": "action",
            "action": action_name,
            "input": action_input,
            "content": llm_output,
        })

        # Execute tool (skip in dry_run mode)
        if dry_run:
            observation = f"[DRY RUN] Would execute {action_name} with {action_input}"
        else:
            observation = await _execute_tool(
                action_name, action_input, email_id, sender, db
            )

        obs_str = json.dumps(observation) if isinstance(observation, dict) else str(observation)

        reasoning_trace.append({
            "step": steps_taken + 1,
            "type": "observation",
            "action": action_name,
            "result": observation,
        })

        messages.append({
            "role": "user",
            "content": f"Observation: {obs_str}\n\nContinue your analysis."
        })

        steps_taken += 1

    # If max steps reached without resolution
    if steps_taken >= MAX_STEPS and not final_answer:
        final_answer = f"Max steps ({MAX_STEPS}) reached. Escalating to human."
        if not dry_run:
            await tool_escalate_to_human(
                email_id=email_id,
                reason=f"Agent reached max steps ({MAX_STEPS}) without resolution",
                priority="High",
                db=db,
            )

    return {
        "email_id": email_id,
        "dry_run": dry_run,
        "steps_taken": steps_taken,
        "final_answer": final_answer,
        "reasoning_trace": reasoning_trace,
    }


def _parse_action(llm_output: str) -> tuple:
    """Extract action name and input from LLM output."""
    lines = llm_output.split("\n")
    action_name = None
    action_input = {}

    for i, line in enumerate(lines):
        if line.startswith("Action:"):
            action_name = line.replace("Action:", "").strip()
        if line.startswith("Action Input:"):
            input_str = line.replace("Action Input:", "").strip()
            # Try to parse remaining lines as JSON
            full_input = input_str
            for j in range(i + 1, min(i + 5, len(lines))):
                full_input += lines[j]
            try:
                action_input = json.loads(full_input)
            except json.JSONDecodeError:
                # Try just the first line
                try:
                    action_input = json.loads(input_str)
                except json.JSONDecodeError:
                    action_input = {"raw": input_str}

    return action_name, action_input


async def _execute_tool(
    action_name: str,
    action_input: dict,
    email_id: int,
    sender: str,
    db: AsyncSession,
) -> dict:
    """Route tool name to implementation."""
    name = action_name.lower().strip()

    if name == "get_thread_history":
        return await tool_get_thread_history(
            action_input.get("sender_email", sender), db
        )
    elif name == "get_contact_profile":
        return await tool_get_contact_profile(
            action_input.get("email", sender), db
        )
    elif name == "search_knowledge_base":
        return await tool_search_knowledge_base(
            action_input.get("query", "")
        )
    elif name == "escalate_to_human":
        return await tool_escalate_to_human(
            email_id=email_id,
            reason=action_input.get("reason", "Agent escalation"),
            priority=action_input.get("priority", "High"),
            db=db,
        )
    elif name == "flag_for_legal":
        return await tool_flag_for_legal(
            email_id=email_id,
            issue_type=action_input.get("issue_type", "Legal threat"),
            db=db,
        )
    elif name == "create_internal_ticket":
        return await tool_create_internal_ticket(
            title=action_input.get("title", "Support ticket"),
            body=action_input.get("body", ""),
            assignee=action_input.get("assignee", "support-team"),
            email_id=email_id,
            db=db,
        )
    elif name == "draft_reply":
        return await tool_draft_reply(
            context=action_input.get("context", ""),
            tone=action_input.get("tone", "professional"),
            policy_refs=action_input.get("policy_refs", []),
            email_id=email_id,
            db=db,
        )
    else:
        return {"error": f"Unknown tool: {action_name}"}