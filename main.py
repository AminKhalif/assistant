import os
from openai import OpenAI
import time
import json

# initiliaze secrets
openai_secret = os.environ['OPENAI_API_KEY']
pplx_secret = os.environ["PPLX_API_KEY"]

# Initialize clients
openai_client = OpenAI(api_key=openai_secret)
pplx_client = OpenAI(base_url='https://api.perplexity.ai', api_key=pplx_secret)


# define tools
def ask_an_analyst(payload: dict):
    analyst_response = pplx_client.chat.completions.create(
        model="llama-3-sonar-small-32k-online",
        messages=[{
            "role": "system",
            "content": payload['thought_process']
        }, {
            "role": "user",
            "content": payload['query']
        }]).choices[0].message.content

    return analyst_response


# define agent

# basic_instructions = """
# You are a highly skilled and creative expert stock market analyst and portfolio manager at the renowned firm Stoxy. Your role is to provide accurate and innovative stock recommendations to your clients, and manage investment portfolios with a unique perspective with an emphasis on alpha.

# Answer client questions based on their own portfolio. When answering, for each stock in the client's portfolio use every one of the following tools to get the most accurate and up-to-date information, then aggregate all the data to create a comprehensive answer:
# 1. market_research: Retrieve financial data, news, and market trends related to a stock/company
# 2. fundamental_analysis: Analyze the company's financial statements, management.
# 3. risk_assessment: Evaluate the potential risks associated with an investment.

# When answering:
# - Pay close attention to detail and rigorously fact-check all information.
# - Break down problems using a chain of thought approach.
# - Gather relevant information systematically.
# - Embrace contrarian thinking to uncover hidden opportunities and risks.
# - Make informed decisions based on thorough and creative analysis.
# - Your expertise is well-respected, and your ability to think outside the box sets you apart.

# - Present your recommendations clearly, ensuring they are:
#     - Easy to understand,
#     - Actionable,
#     - Well-organized,
#     - While challenging conventional wisdom when necessary,
#     - Short and concise

# Use headings, bullet points, and bold text to enhance readability.
# Structure your responses with clear sections and logical flow.

# MARKDOWN_MODE = ON
# """

basic_instructions = """
You are a highly skilled and creative expert stock market analyst and portfolio manager at the renowned firm Stoxy. Your role is to provide accurate and innovative stock recommendations to your clients, and manage investment portfolios with a unique perspective with an emphasis on alpha.

Answer client questions based on their own portfolio. When answering, for each stock in the client's portfolio use every one of the following tools to get the most accurate and up-to-date information, then aggregate all the data to create a comprehensive answer:
1. market_research: Retrieve financial data, news, and market trends related to a stock/company
2. fundamental_analysis: Analyze the company's financial statements, management.
3. risk_assessment: Evaluate the potential risks associated with an investment.

Analyze the result of each tool for yourself and use it to generate a recommendation for the client. In your recommendation do not tell the client the analyzed information, just the conclusion. The concluded recommendation should be a one line statement with a clear proposed action to take: buy, sell or hold, and a sentence explaining the reasoning behind it.

Then a couple lines below have a report explaning your reasoning with the logic from the market research with a heading , and bullet points , fundamental analysis with a header and bullet points, then the risk analysis with a header and bullet points. Don't be vague in your report, be specific and clear and display factual evidence and data! to back your points up. Keep jargon to a minimum when answering, make it friendly for the layman and complete stock noobs.

MARKDOWN_MODE = ON
"""

stoxi_with_tools = openai_client.beta.assistants.create(
    instructions=basic_instructions,
    name="Stoxy AI Financial Analyst",
    model="gpt-4o",
    tools=[{
        "type": "function",
        "function": {
            "name": "market_research",
            "description":
            "Retrieves financial data, news, and market trends related to a stock/company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought_process": {
                        "type":
                        "string",
                        "description":
                        "four to five sentences about how to precisely scope a good keyword search.",
                    },
                    "query": {
                        "type":
                        "string",
                        "description":
                        "The precise and well-scoped query to research by.",
                    },
                },
                "required": ["thought_process", "query"],
            },
        },
    }, {
        "type": "function",
        "function": {
            "name": "fundamental_analysis",
            "description":
            "Analyzes a company's financial statements, management.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought_process": {
                        "type":
                        "string",
                        "description":
                        "four to five sentences about how to precisely scope a good keyword search.",
                    },
                    "query": {
                        "type":
                        "string",
                        "description":
                        "The precise and well-scoped query to research by.",
                    },
                },
                "required": ["thought_process", "query"],
            },
        },
    }, {
        "type": "function",
        "function": {
            "name": "risk_assessment",
            "description":
            "Evaluate the potential risks associated with an investment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought_process": {
                        "type":
                        "string",
                        "description":
                        "four to five sentences about how to precisely scope a good keyword search.",
                    },
                    "query": {
                        "type":
                        "string",
                        "description":
                        "The precise and well-scoped query to research by.",
                    },
                },
                "required": ["thought_process", "query"],
            },
        },
    }])

# answer to user's query
user_query = input("Welcome to Stoxy. Enter your stock question : ")

run = openai_client.beta.threads.create_and_run(
    assistant_id=stoxi_with_tools.id,
    thread={
        "messages": [{
            'role':
            'user',
            'content':user_query
        }]
    })

while run.status != "completed":
    print(f"Run status: {run.status}")

    if (run.status == "requires_action"):
        # Define the list to store tool outputs
        tool_outputs = []

        # Loop through each tool in the required action section
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            print(f"Tool: {tool.function.name}")
            q = json.loads(tool.function.arguments)
            content = ask_an_analyst(q)
            # print(content)
            tool_outputs.append({"tool_call_id": tool.id, "output": content})

        # Submit all tool outputs at once after collecting them in a list
        if tool_outputs:
            try:
                run = openai_client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=run.thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs)
                # print("Tool outputs submitted successfully.")
            except Exception as e:
                print("Failed to submit tool outputs:", e)
        else:
            print("No tool outputs to submit.")

    time.sleep(1)  # Check every second

    run = openai_client.beta.threads.runs.retrieve(run_id=run.id,
                                                   thread_id=run.thread_id)

if run.status == 'completed':
    messages_finished = openai_client.beta.threads.messages.list(
        thread_id=run.thread_id, )
    print(messages_finished.data[0].content[0].text.value)
else:
    print(run.status)
