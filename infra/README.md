# This is a mock database for the LLM 

# Pre req
- Have docker installed 

# How to run
- cd infra/ 
- `docker compose up -d --build` 

# Sanity check
- `docker exec -it pagila-db psql -U pagila -d pagila`