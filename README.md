# Lysai
*An AI agent that autonomously explores the Pagila database, plans SQL queries, reflects on results, and explains insights*

## Overview 

**Goal**: Build an agentic system using **LangGraph + MCP + PostgreSQL (Pagila Docker** that performs end-to-end reasoning:
1. Understand the user's question
2. Plan which queries to run
3. Execute those queries 
4. Reflect and self-correct on errors or poor results
5. Summarize findings in natural language and charts 

### Tech Stack 
- LangGraph
- Qwen2.5-7B-Instruct
- PostgreSQL (Pagila)
- MCP_SQL
- MCP_Visualizer
- Docker Compose

