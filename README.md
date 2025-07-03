# 🧠 Multi-Agent AI DevOps Engineer

This project is a multi-agent system designed to function as an intelligent DevOps engineer. By combining large language models (LLMs), ReAct-style reasoning, and modular agents, it enables automation of DevOps tasks such as CI/CD pipeline generation, containerization, and deployment - all through natural language input.

## 🧩 Project Overview

The system consists of:
- **Orchestrator**: Assigns the AI agents to maintain execution flow
- **Reasoning Agent**: Interprets user input, plans next steps, and generates shell commands
- **Prompt Agent**: Refines and structures prompts for better LLM output
- **Reflector Agent**: Handles rejections and failed commands, suggesting alternatives
- **Frontend UI**: Allows users to interact with the system, view reasoning, and approve/reject actions

It follows the **Thought → Action → Result** loop and has human-in-the-loop control.

## 📁 Project Structure

```plaintext
multi-agent-devops-engineer/
│
├── backend/              # FastAPI backend (LLM + agent coordination logic)
├── frontend/             # React frontend (user interface with live log streaming)
├── .gitignore
└── README.md             # You’re here
```

## 🚀 Getting Started Locally

To start the full application locally, follow these steps:

### 1. Start the Frontend

```bash
cd frontend
npm install
npm start
```

This launches the React UI on [http://localhost:3000](http://localhost:3000)

### 2. Start the Backend

In a separate terminal, from the **project root folder**, run:
```bash
uvicorn backend.main:app --reload
```

This launches the FastAPI backend on http://localhost:8000


## 🖥️ User Interface

<img width="484" alt="Eugenius Multi Agent Devops Engineer" src="https://github.com/user-attachments/assets/dac9f4d0-1421-4fc6-9c11-9ec764cf7955" />


## 🧠 Features

- Modular multi-agent architecture (Reasoning, Prompt Engineering, Reflection)
- ReAct-style reasoning loop (**Thought → Action → Result**)
- Live command preview, approval, rejection, and editing
- GitHub Actions automation
- Docker containerization support
- Human-in-the-loop DevOps execution
- Designed to be extended with additional automation scenarios (e.g., GitLab CI/CD, Kubernetes, cloud deployment)

## 🙋‍♂️ Developer

**Eugen Lucchiari Hartz**  
MSc Software Engineering of Distributed Systems  
Knowit Connectivity, Stockholm

This system was developed as part of the Master’s thesis project of Eugen Lucchiari Hartz.
